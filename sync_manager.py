import hashlib
import json
import os
import re
import shutil
import socket
import subprocess
import urllib.parse
from datetime import datetime
from pathlib import Path

from emulators import ScanContext, KIND_SAVE, detect_all, get_emulator
from emulators.base import SaveEntry
from utils import safe_join, slugify

CONFIG_FILE = "config.json"
SAVE_REPO_DIR = "save_repo"
META_NAME = ".pokesync.json"
META_SCHEMA = 1

DEFAULT_CONFIG = {
    "sync_mode": "local",
    "cloud_path": "",
    "github_repo_url": "",
    "github_token": "",
    "github_username": "",
    "last_sync": {},
    "scan_folders": [],
    "emulator_paths": {},
    "enabled_emulators": None,  # None means every supported emulator
    "include_savestates": False,
}


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class SyncManager:
    def __init__(self, config_file=None):
        self.config_file = config_file or CONFIG_FILE
        self.config = self.load_config()
        self._git_verified = False
        self._repo = None

    # ------------------------------------------------------------------ config
    def load_config(self):
        config = {}
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r") as f:
                    config = json.load(f)
            except Exception:
                config = {}
        for key, value in DEFAULT_CONFIG.items():
            if key not in config:
                config[key] = json.loads(json.dumps(value))
        return config

    def save_config(self):
        with open(self.config_file, "w") as f:
            json.dump(self.config, f, indent=4)

    def set_config(self, key, value):
        if self.config.get(key) == value:
            return
        self.config[key] = value
        # Invalidate cached repo if GitHub settings change
        if key in ["github_repo_url", "github_token", "github_username"]:
            self._repo = None
        self.save_config()

    def set_cloud_path(self, path):
        self.set_config("cloud_path", path)

    def add_scan_folder(self, path):
        folders = list(self.config.get("scan_folders", []))
        path = os.path.abspath(path)
        if path not in folders:
            folders.append(path)
            self.set_config("scan_folders", folders)

    def remove_scan_folder(self, path):
        self.set_config("scan_folders", [p for p in self.config.get("scan_folders", []) if p != path])

    # --------------------------------------------------------------- detection
    def _context(self):
        return ScanContext(
            scan_folders=[Path(p) for p in self.config.get("scan_folders", [])],
            overrides=dict(self.config.get("emulator_paths", {})),
            include_states=bool(self.config.get("include_savestates")),
        )

    def get_detected_games(self):
        enabled = self.config.get("enabled_emulators")
        return detect_all(self._context(), enabled=enabled)

    # ---------------------------------------------------------- remote backend
    def _is_github(self):
        return self.config.get("sync_mode") == "github"

    def _remote_root(self):
        """Returns (root folder, error message). Exactly one of them is None."""
        if self._is_github():
            ok, msg = self._init_github_repo()
            return (Path(SAVE_REPO_DIR), None) if ok else (None, msg)
        cloud_path = self.config.get("cloud_path")
        if not cloud_path:
            return None, "Cloud path not set."
        return Path(cloud_path), None

    def refresh_remote(self):
        """Pull the GitHub repo once (called once per refresh, not once per game)."""
        if not self._is_github():
            return True, "Local folder mode."
        ok, msg = self._init_github_repo()
        if not ok:
            return False, msg
        try:
            self._repo.remotes.origin.pull()
            return True, "Up to date."
        except Exception as e:
            return False, str(e)

    def _init_github_repo(self):
        from git import Repo, GitCommandError  # imported lazily so local mode needs no GitPython

        url = self.config.get("github_repo_url", "").strip()
        token = self.config.get("github_token", "").strip()
        username = self.config.get("github_username", "").strip()

        if not url or not token or not username:
            return False, "GitHub configuration incomplete. Need URL, Username, and Token."

        # Verify git is installed
        if not self._git_verified:
            try:
                subprocess.run(["git", "--version"], check=True, capture_output=True)
                self._git_verified = True
            except (subprocess.CalledProcessError, FileNotFoundError):
                return False, "Git is not installed or not in PATH. Please install Git to use GitHub sync."

        # Robust URL handling
        if not url.startswith("https://"):
            if "/" in url and not url.startswith("github.com"):
                url = "https://github.com/" + url
            else:
                url = "https://" + url

        if not url.endswith(".git"):
            url = url + ".git"

        # Safe encoding for username and token (handles spaces, etc.)
        safe_user = urllib.parse.quote(username)
        safe_token = urllib.parse.quote(token)
        auth_url = url.replace("https://", f"https://{safe_user}:{safe_token}@")

        try:
            if os.path.exists(SAVE_REPO_DIR):
                if not os.path.exists(os.path.join(SAVE_REPO_DIR, ".git")):
                    shutil.rmtree(SAVE_REPO_DIR)
                    self._repo = Repo.clone_from(auth_url, SAVE_REPO_DIR, env={"GIT_TERMINAL_PROMPT": "0"})
                else:
                    if self._repo is None:
                        self._repo = Repo(SAVE_REPO_DIR)

                    if self._repo.remotes.origin.url != auth_url:
                        self._repo.remotes.origin.set_url(auth_url)
            else:
                self._repo = Repo.clone_from(auth_url, SAVE_REPO_DIR, env={"GIT_TERMINAL_PROMPT": "0"})
            return True, "GitHub repo ready."
        except GitCommandError as e:
            if "Authentication failed" in str(e):
                return False, "GitHub authentication failed. Check your Username and Token/PAT."
            if "Could not resolve host" in str(e):
                return False, "Network error: Could not reach GitHub. Check your internet connection."
            return False, f"Git error: {str(e)}"
        except Exception as e:
            return False, f"Error: {str(e)}"

    # ------------------------------------------------------------ remote layout
    # <root>/<emulator>/<game_id>/<kind>/<files...> plus a small metadata file.
    # Saves pushed by the old Citra-only PokeSync live at <root>/<title id>/main and
    # are still read (and restored) for the "citra" emulator.
    @staticmethod
    def _remote_dir(root, entry):
        return Path(root) / slugify(entry.emulator) / slugify(entry.game_id) / entry.kind

    def _read_remote(self, root, entry):
        """Returns ({relative name: path}, metadata dict or None)."""
        folder = self._remote_dir(root, entry)
        files, meta = {}, None
        if folder.is_dir():
            for item in sorted(folder.rglob("*")):
                if item.is_file() and item.name != META_NAME:
                    files[item.relative_to(folder).as_posix()] = item
            meta_path = folder / META_NAME
            if meta_path.is_file():
                try:
                    meta = json.loads(meta_path.read_text(encoding="utf-8"))
                except Exception:
                    meta = None
        if not files and entry.emulator == "citra" and entry.kind == KIND_SAVE:
            legacy = Path(root) / slugify(entry.game_id) / "main"
            if legacy.is_file():
                files["main"] = legacy
        return files, meta

    @staticmethod
    def _remote_mtime(files, meta):
        recorded = {f["rel"]: f.get("mtime") for f in (meta or {}).get("files", [])}
        times = [recorded.get(rel) or path.stat().st_mtime for rel, path in files.items()]
        return max(times) if times else None

    # --------------------------------------------------------------- conflicts
    def check_conflict(self, game):
        """
        Compares local and remote saves.
        Returns: (status, message)
        Statuses: 'no_remote', 'no_local', 'remote_newer', 'local_newer', 'up_to_date', 'error'
        """
        root, err = self._remote_root()
        if err:
            return "error", err

        files, meta = self._read_remote(root, game)
        if not files:
            return "no_remote", "Remote save does not exist."

        local_mtime = game.latest_mtime()
        if local_mtime is None:
            return "no_local", "Local save does not exist."
        remote_mtime = self._remote_mtime(files, meta)

        # Use a small threshold (2 seconds) to account for filesystem differences
        if abs(local_mtime - remote_mtime) < 2:
            return "up_to_date", "Saves are synchronized."
        elif local_mtime > remote_mtime:
            return "local_newer", f"Local save is newer ({datetime.fromtimestamp(local_mtime).strftime('%Y-%m-%d %H:%M')})"
        else:
            return "remote_newer", f"Remote save is newer ({datetime.fromtimestamp(remote_mtime).strftime('%Y-%m-%d %H:%M')})"

    # --------------------------------------------------------------- push/pull
    def push_save(self, game):
        success, msg = self._push(game)
        if success:
            self._update_last_sync(game)
        return success, msg

    def pull_save(self, game):
        success, msg = self._pull(game)
        if success:
            self._update_last_sync(game)
        return success, msg

    def _update_last_sync(self, game):
        if "last_sync" not in self.config:
            self.config["last_sync"] = {}
        self.config["last_sync"][game.key] = datetime.now().isoformat()
        # Keep the old key (plain game id) for Citra so existing "Last Synced" values survive.
        if game.emulator == "citra" and game.kind == KIND_SAVE:
            self.config["last_sync"][game.game_id] = self.config["last_sync"][game.key]
        self.save_config()

    def last_sync(self, game):
        sync = self.config.get("last_sync", {})
        return sync.get(game.key) or (sync.get(game.game_id) if game.emulator == "citra" else None)

    def _push(self, game):
        root, err = self._remote_root()
        if err:
            return False, err
        local_files = game.files()
        if not local_files:
            return False, "No local files to push."

        try:
            if self._is_github():
                try:
                    self._repo.remotes.origin.pull()
                except Exception:
                    pass

            folder = self._remote_dir(root, game)
            for rel, src in local_files:
                dst = safe_join(folder, rel)
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
            self._write_meta(folder, game)

            if self._is_github():
                return self._commit_and_push(game, folder)
            return True, f"Successfully pushed {game.name} to local cloud."
        except Exception as e:
            prefix = "GitHub push failed: " if self._is_github() else ""
            return False, f"{prefix}{e}"

    def _write_meta(self, folder, game):
        files = []
        for item in sorted(Path(folder).rglob("*")):
            if item.is_file() and item.name != META_NAME:
                stat = item.stat()
                files.append({"rel": item.relative_to(folder).as_posix(), "size": stat.st_size,
                              "mtime": stat.st_mtime, "sha256": _sha256(item)})
        meta = {
            "schema": META_SCHEMA,
            "emulator": game.emulator,
            "emulator_name": game.emulator_name,
            "game_id": game.game_id,
            "name": game.name,
            "kind": game.kind,
            "is_pokemon": game.is_pokemon,
            "restore_hint": game.restore_hint,
            "game": {k: v for k, v in game.metadata.items() if k not in ("modified", "size", "file_count")},
            "pushed_at": datetime.now().isoformat(timespec="seconds"),
            "pushed_from": socket.gethostname(),
            "files": files,
        }
        (Path(folder) / META_NAME).write_text(json.dumps(meta, indent=2), encoding="utf-8")

    def _commit_and_push(self, game, folder):
        relative = os.path.relpath(folder, SAVE_REPO_DIR)
        self._repo.git.add("--all", "--", relative)
        try:
            staged = self._repo.is_dirty(index=True, working_tree=False, untracked_files=False)
        except Exception:
            staged = True  # e.g. a brand new repository without commits
        if not staged:
            return True, f"{game.name} is already up to date on GitHub."
        self._repo.index.commit(f"Update {game.kind} for {game.name} ({game.emulator_name}) - "
                                f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self._repo.remotes.origin.push()
        return True, f"Successfully pushed {game.name} to GitHub."

    def _pull(self, game):
        root, err = self._remote_root()
        if err:
            return False, err
        try:
            if self._is_github():
                self._repo.remotes.origin.pull()

            files, meta = self._read_remote(root, game)
            if not files:
                return False, "Save not found in GitHub repository." if self._is_github() \
                    else "Local cloud save not found."

            dest = game.dest_dir()
            if dest is None:
                return False, "Don't know where to restore this save on this computer."

            recorded = {f["rel"]: f.get("mtime") for f in (meta or {}).get("files", [])}
            targets = [(rel, src, safe_join(dest, rel)) for rel, src in files.items()]

            self._create_backup(game, [t for _, _, t in targets], dest)
            for rel, src, target in targets:
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, target)
                if recorded.get(rel):
                    os.utime(target, (recorded[rel], recorded[rel]))
            where = "GitHub" if self._is_github() else "local cloud"
            return True, f"Successfully pulled {game.name} from {where}."
        except Exception as e:
            prefix = "GitHub pull failed: " if self._is_github() else ""
            return False, f"{prefix}{e}"

    def _create_backup(self, game, targets, dest):
        existing = [t for t in targets if t.is_file()]
        if not existing:
            return
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = Path(os.getcwd()) / "backups" / slugify(game.emulator) / slugify(game.game_id) / stamp
        for target in existing:
            rel = target.relative_to(Path(dest).resolve())
            copy = backup_dir / rel
            copy.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target, copy)

    # ------------------------------------------------------------- remote-only
    def get_remote_only_entries(self, local_entries):
        """Saves that exist in the cloud but were not found on this computer.

        This is the "my save disappeared" case: they can be restored with Pull.
        """
        root, err = self._remote_root()
        if err or not root.is_dir():
            return []
        ctx = self._context()
        local_keys = {e.key for e in local_entries}
        found = []

        for meta_path in sorted(root.glob(f"*/*/*/{META_NAME}")):
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                entry = self._entry_from_meta(meta, ctx)
            except Exception:
                continue
            if entry and entry.key not in local_keys:
                found.append(entry)

        # Saves pushed by the old Citra-only version of PokeSync
        citra = get_emulator("citra")
        for legacy in sorted(root.glob("*/main")):
            title_id = legacy.parent.name.upper()
            if not re.fullmatch(r"[0-9A-F]{16}", title_id):
                continue
            entry = SaveEntry(emulator="citra", emulator_name=citra.name, game_id=title_id,
                              name=self._legacy_name(title_id), kind=KIND_SAVE, remote_only=True,
                              metadata={"platform": "Nintendo 3DS", "title_id": title_id})
            entry.dest = citra.legacy_dest(ctx, title_id) or (
                Path.home() / "PokeSync Restored" / "citra" / title_id)
            if entry.key not in local_keys and entry.key not in {e.key for e in found}:
                found.append(entry)
        return found

    @staticmethod
    def _legacy_name(title_id):
        from emulators.names_3ds import GAME_NAMES
        return GAME_NAMES.get(title_id, f"Unknown Game ({title_id})")

    def _entry_from_meta(self, meta, ctx):
        emulator = get_emulator(meta["emulator"])
        entry = SaveEntry(
            emulator=meta["emulator"],
            emulator_name=meta.get("emulator_name") or (emulator.name if emulator else meta["emulator"]),
            game_id=meta["game_id"], name=meta.get("name", meta["game_id"]),
            kind=meta.get("kind", KIND_SAVE), is_pokemon=bool(meta.get("is_pokemon")),
            metadata=dict(meta.get("game", {})), restore_hint=meta.get("restore_hint"),
            remote_only=True)
        base = emulator.restore_base(ctx) if emulator else None
        if base is not None and entry.restore_hint:
            entry.dest = safe_join(base, entry.restore_hint)
        else:
            # No known home for this save (for example a ROM-adjacent .sav): restore into a
            # clearly named folder instead of guessing, and never over an existing file.
            entry.dest = Path.home() / "PokeSync Restored" / slugify(entry.emulator) / slugify(entry.game_id)
        return entry

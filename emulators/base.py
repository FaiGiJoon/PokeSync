"""Core types for emulator support: SaveEntry, ScanContext and the Emulator base class."""
from __future__ import annotations

import os
import platform
from dataclasses import dataclass, field
from pathlib import Path

KIND_SAVE = "save"
KIND_STATES = "states"

IGNORED_DIRS = {".git", "node_modules", "$RECYCLE.BIN", "System Volume Information", "__pycache__"}


@dataclass
class SaveEntry:
    """One syncable thing: the save data (or the save states) of one game."""

    emulator: str
    emulator_name: str
    game_id: str
    name: str
    kind: str = KIND_SAVE
    # Absolute paths of files, or a single directory that holds the save.
    paths: list = field(default_factory=list)
    is_pokemon: bool = False
    metadata: dict = field(default_factory=dict)
    # Where this entry lives relative to the emulator's user directory.
    # Stored remotely so a lost save can be restored to the right place.
    restore_hint: str | None = None
    # Set for entries that exist remotely but were not found locally.
    remote_only: bool = False
    dest: Path | None = None

    @property
    def key(self):
        return f"{self.emulator}/{self.game_id}/{self.kind}"

    @property
    def id(self):
        # Kept so older UI code that used game["id"] keeps working.
        return self.game_id

    def files(self):
        """List of (relative name, absolute path) for every file in this entry."""
        out = []
        for raw in self.paths:
            path = Path(raw)
            if path.is_dir():
                for item in sorted(path.rglob("*")):
                    if item.is_file():
                        out.append((item.relative_to(path).as_posix(), item))
            elif path.is_file():
                out.append((path.name, path))
        return out

    def dest_dir(self):
        """Directory the files of this entry belong in (None if unknown)."""
        if self.dest is not None:
            return Path(self.dest)
        if not self.paths:
            return None
        paths = [Path(p) for p in self.paths]
        if len(paths) == 1 and paths[0].is_dir():
            return paths[0]
        return Path(os.path.commonpath([str(p.parent) for p in paths]))

    def latest_mtime(self):
        times = [path.stat().st_mtime for _, path in self.files()]
        return max(times) if times else None

    def total_size(self):
        return sum(path.stat().st_size for _, path in self.files())


@dataclass
class ScanContext:
    """Everything an emulator plugin needs to look around on this machine."""

    scan_folders: list = field(default_factory=list)
    overrides: dict = field(default_factory=dict)
    include_states: bool = False
    max_depth: int = 6
    system: str = field(default_factory=platform.system)
    home: Path = field(default_factory=Path.home)
    env: dict = field(default_factory=lambda: dict(os.environ))
    _files: list | None = field(default=None, repr=False)
    _index: dict | None = field(default=None, repr=False)

    # ---- well-known base directories -------------------------------------
    def appdata(self):
        return Path(self.env.get("APPDATA") or self.home / "AppData" / "Roaming")

    def documents(self):
        return self.home / "Documents"

    def xdg_data(self):
        return Path(self.env.get("XDG_DATA_HOME") or self.home / ".local" / "share")

    def xdg_config(self):
        return Path(self.env.get("XDG_CONFIG_HOME") or self.home / ".config")

    def app_support(self):
        return self.home / "Library" / "Application Support"

    def override_dirs(self, emulator_id):
        value = self.overrides.get(emulator_id)
        return [Path(value).expanduser()] if value else []

    # ---- scan folders ------------------------------------------------------
    def files(self):
        """Every file under the user's scan folders (depth limited, cached)."""
        if self._files is None:
            out, seen = [], set()
            for folder in self.scan_folders:
                root = Path(folder).expanduser()
                if not root.is_dir():
                    continue
                base_depth = len(root.parts)
                for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
                    here = Path(dirpath)
                    if len(here.parts) - base_depth >= self.max_depth:
                        dirnames[:] = []
                    else:
                        dirnames[:] = [d for d in dirnames if d not in IGNORED_DIRS]
                    for name in filenames:
                        path = here / name
                        if path not in seen:
                            seen.add(path)
                            out.append(path)
            self._files = out
        return self._files

    def siblings(self, path):
        """Files in the same folder as `path` with the same stem (case-insensitive)."""
        if self._index is None:
            index = {}
            for item in self.files():
                index.setdefault((item.parent, item.stem.lower()), []).append(item)
            self._index = index
        return self._index.get((Path(path).parent, Path(path).stem.lower()), [])


class Emulator:
    """Base class for emulator plugins.

    A plugin answers three questions: where does this emulator keep its data
    (`user_dirs`), which saves are there (`find_saves`), and optionally which
    save states (`find_savestates`).
    """

    id = "base"
    name = "Base"

    def user_dirs(self, ctx):
        """Existing user directories for this emulator on this machine."""
        return []

    def find_saves(self, ctx):
        return []

    def find_savestates(self, ctx):
        return []

    def restore_base(self, ctx):
        """Directory that `SaveEntry.restore_hint` is relative to (None if unknown)."""
        dirs = self.user_dirs(ctx)
        return dirs[0] if dirs else None

    def legacy_dest(self, ctx, game_id):
        """Destination for a legacy (pre-plugin) remote save; only Citra needs it."""
        return None


def unique_id(used, base):
    """Return `base`, or `base-2`, `base-3`... if it is already taken."""
    candidate, n = base, 2
    while candidate in used:
        candidate = f"{base}-{n}"
        n += 1
    used.add(candidate)
    return candidate

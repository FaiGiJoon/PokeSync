import os
import json
import shutil
import subprocess
import urllib.parse
from datetime import datetime
from git import Repo, GitCommandError
from utils import get_citra_base_path, get_save_data_root, find_game_saves

CONFIG_FILE = "config.json"
SAVE_REPO_DIR = "save_repo"

class SyncManager:
    def __init__(self):
        self.config = self.load_config()
        self.citra_path = get_citra_base_path()
        self.title_root = get_save_data_root(self.citra_path)
        self._git_verified = False
        self._repo = None
    
    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    config = json.load(f)
                    defaults = {
                        "sync_mode": "local",
                        "cloud_path": "",
                        "github_repo_url": "",
                        "github_token": "",
                        "github_username": ""
                    }
                    for k, v in defaults.items():
                        if k not in config:
                            config[k] = v
                    return config
            except Exception:
                pass
        return {
            "sync_mode": "local",
            "cloud_path": "",
            "github_repo_url": "",
            "github_token": "",
            "github_username": ""
        }

    def save_config(self):
        with open(CONFIG_FILE, "w") as f:
            json.dump(self.config, f, indent=4)

    def set_config(self, key, value):
        if self.config.get(key) != value:
            self.config[key] = value
            self.save_config()
            # Invalidate repo cache if GitHub settings change
            if key in ["github_repo_url", "github_username", "github_token"]:
                self._repo = None

    def set_cloud_path(self, path):
        self.set_config("cloud_path", path)

    def get_detected_games(self):
        return find_game_saves(self.title_root)

    def _get_local_sync_path(self, game_id):
        if not self.config.get("cloud_path"):
            return None
        return os.path.join(self.config["cloud_path"], game_id, "main")

    def _get_github_sync_path(self, game_id):
        return os.path.join(SAVE_REPO_DIR, game_id, "main")

    def _init_github_repo(self):
        url = self.config.get("github_repo_url", "").strip()
        token = self.config.get("github_token", "").strip()
        username = self.config.get("github_username", "").strip()

        if not url or not token or not username:
            return False, "GitHub configuration incomplete. Need URL, Username, and Token."

        # Verify git is installed (cached)
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
                    if not self._repo:
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

    def check_conflict(self, game):
        """
        Compares local and remote saves.
        Returns: (status, message)
        Statuses: 'no_remote', 'no_local', 'remote_newer', 'local_newer', 'up_to_date', 'error'
        """
        local_path = game["local_path"]
        if self.config.get("sync_mode") == "github":
            success, msg = self._init_github_repo()
            if not success: return "error", msg
            try:
                self._repo.remotes.origin.pull()
                remote_path = self._get_github_sync_path(game["id"])
            except Exception as e:
                return "error", str(e)
        else:
            remote_path = self._get_local_sync_path(game["id"])
            if not remote_path: return "error", "Cloud path not set."

        if not os.path.exists(remote_path):
            return "no_remote", "Remote save does not exist."

        if not os.path.exists(local_path):
            return "no_local", "Local save does not exist."

        local_mtime = os.path.getmtime(local_path)
        remote_mtime = os.path.getmtime(remote_path)

        # Use a small threshold (1 second) to account for filesystem differences
        if abs(local_mtime - remote_mtime) < 2:
            return "up_to_date", "Saves are synchronized."
        elif local_mtime > remote_mtime:
            return "local_newer", f"Local save is newer ({datetime.fromtimestamp(local_mtime).strftime('%Y-%m-%d %H:%M')})"
        else:
            return "remote_newer", f"Remote save is newer ({datetime.fromtimestamp(remote_mtime).strftime('%Y-%m-%d %H:%M')})"

    def push_save(self, game):
        if self.config.get("sync_mode") == "github":
            return self._push_github(game)
        else:
            return self._push_local(game)

    def pull_save(self, game):
        if self.config.get("sync_mode") == "github":
            return self._pull_github(game)
        else:
            return self._pull_local(game)

    def _push_local(self, game):
        cloud_path = self._get_local_sync_path(game["id"])
        if not cloud_path:
            return False, "Local cloud path not set."
        
        try:
            os.makedirs(os.path.dirname(cloud_path), exist_ok=True)
            shutil.copy2(game["local_path"], cloud_path)
            return True, f"Successfully pushed {game['name']} to local cloud."
        except Exception as e:
            return False, str(e)

    def _pull_local(self, game):
        cloud_path = self._get_local_sync_path(game["id"])
        if not cloud_path or not os.path.exists(cloud_path):
            return False, "Local cloud save not found."
        
        try:
            self._create_backup(game)
            shutil.copy2(cloud_path, game["local_path"])
            return True, f"Successfully pulled {game['name']} from local cloud."
        except Exception as e:
            return False, str(e)

    def _push_github(self, game):
        success, msg = self._init_github_repo()
        if not success: return False, msg

        try:
            try:
                self._repo.remotes.origin.pull()
            except Exception:
                pass

            dest_path = self._get_github_sync_path(game["id"])
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            shutil.copy2(game["local_path"], dest_path)

            relative_path = os.path.join(game["id"], "main")
            self._repo.index.add([relative_path])
            self._repo.index.commit(f"Update save for {game['name']} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            self._repo.remotes.origin.push()

            return True, f"Successfully pushed {game['name']} to GitHub."
        except Exception as e:
            return False, f"GitHub push failed: {str(e)}"

    def _pull_github(self, game):
        success, msg = self._init_github_repo()
        if not success: return False, msg

        try:
            self._repo.remotes.origin.pull()

            source_path = self._get_github_sync_path(game["id"])
            if not os.path.exists(source_path):
                return False, "Save not found in GitHub repository."

            self._create_backup(game)
            shutil.copy2(source_path, game["local_path"])
            return True, f"Successfully pulled {game['name']} from GitHub."
        except Exception as e:
            return False, f"GitHub pull failed: {str(e)}"

    def _create_backup(self, game):
        if os.path.exists(game["local_path"]):
            backup_dir = os.path.join(os.getcwd(), "backups", game["id"])
            os.makedirs(backup_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = os.path.join(backup_dir, f"main.bak_{timestamp}")
            shutil.copy2(game["local_path"], backup_path)

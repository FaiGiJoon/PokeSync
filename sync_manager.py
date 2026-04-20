import os
import json
import shutil
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
    
    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    config = json.load(f)
                    # Ensure all keys exist
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
        self.config[key] = value
        self.save_config()

    def set_cloud_path(self, path):
        """Legacy support for GUI."""
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
        url = self.config.get("github_repo_url")
        token = self.config.get("github_token")
        username = self.config.get("github_username")

        if not url or not token or not username:
            return False, "GitHub configuration incomplete. Need URL, Username, and Token."

        # Prepare authenticated URL
        # We assume URL is like https://github.com/user/repo.git
        auth_url = url.replace("https://", f"https://{username}:{token}@")

        try:
            if os.path.exists(SAVE_REPO_DIR):
                if not os.path.exists(os.path.join(SAVE_REPO_DIR, ".git")):
                    shutil.rmtree(SAVE_REPO_DIR)
                    Repo.clone_from(auth_url, SAVE_REPO_DIR)
                else:
                    repo = Repo(SAVE_REPO_DIR)
                    if repo.remotes.origin.url != auth_url:
                        repo.remotes.origin.set_url(auth_url)
            else:
                Repo.clone_from(auth_url, SAVE_REPO_DIR)
            return True, "GitHub repo ready."
        except GitCommandError as e:
            return False, f"Git error: {str(e)}"
        except Exception as e:
            return False, f"Error: {str(e)}"

    def push_save(self, game):
        """Copies local save to cloud (Local or GitHub)."""
        if self.config.get("sync_mode") == "github":
            return self._push_github(game)
        else:
            return self._push_local(game)

    def pull_save(self, game):
        """Copies cloud save to local, after creating a backup."""
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
            repo = Repo(SAVE_REPO_DIR)
            # Try to pull first to avoid conflicts
            try:
                repo.remotes.origin.pull()
            except Exception:
                pass

            dest_path = self._get_github_sync_path(game["id"])
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            shutil.copy2(game["local_path"], dest_path)

            relative_path = os.path.join(game["id"], "main")
            repo.index.add([relative_path])
            repo.index.commit(f"Update save for {game['name']} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            repo.remotes.origin.push()

            return True, f"Successfully pushed {game['name']} to GitHub."
        except Exception as e:
            return False, f"GitHub push failed: {str(e)}"

    def _pull_github(self, game):
        success, msg = self._init_github_repo()
        if not success: return False, msg

        try:
            repo = Repo(SAVE_REPO_DIR)
            repo.remotes.origin.pull()

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

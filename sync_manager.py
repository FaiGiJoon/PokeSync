import os
import json
import shutil
from datetime import datetime
from utils import get_citra_base_path, get_save_data_root, find_game_saves

CONFIG_FILE = "config.json"

class SyncManager:
    def __init__(self):
        self.config = self.load_config()
        self.citra_path = get_citra_base_path()
        self.title_root = get_save_data_root(self.citra_path)
    
    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        return {"cloud_path": ""}

    def save_config(self):
        with open(CONFIG_FILE, "w") as f:
            json.dump(self.config, f, indent=4)

    def set_cloud_path(self, path):
        self.config["cloud_path"] = path
        self.save_config()

    def get_detected_games(self):
        return find_game_saves(self.title_root)

    def get_cloud_save_path(self, game_id):
        if not self.config["cloud_path"]:
            return None
        return os.path.join(self.config["cloud_path"], game_id, "main")

    def push_save(self, game):
        """Copies local save to cloud."""
        cloud_path = self.get_cloud_save_path(game["id"])
        if not cloud_path:
            return False, "Cloud path not set."
        
        try:
            os.makedirs(os.path.dirname(cloud_path), exist_ok=True)
            shutil.copy2(game["local_path"], cloud_path)
            return True, f"Successfully pushed {game['name']} to cloud."
        except Exception as e:
            return False, str(e)

    def pull_save(self, game):
        """Copies cloud save to local, after creating a backup."""
        cloud_path = self.get_cloud_save_path(game["id"])
        if not cloud_path or not os.path.exists(cloud_path):
            return False, "Cloud save not found."
        
        try:
            # Create backup
            backup_path = game["local_path"] + ".bak_" + datetime.now().strftime("%Y%m%d_%H%M%S")
            shutil.copy2(game["local_path"], backup_path)
            
            # Copy from cloud
            shutil.copy2(cloud_path, game["local_path"])
            return True, f"Successfully pulled {game['name']} from cloud. Backup created."
        except Exception as e:
            return False, str(e)

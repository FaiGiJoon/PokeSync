import sqlite3
import os
import shutil
import logging
import platform
import subprocess
from datetime import datetime
from vault_manager import VaultManager
from notify import NotificationManager
from utils import get_citra_base_path, get_save_data_root, find_game_saves

# Constants
DB_FILE = "vault.db"
SAVE_REPO_DIR = "save_repo"
LOG_DIR = "logs"

os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    filename=os.path.join(LOG_DIR, "pokesync.log"),
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

class SyncManager:
    def __init__(self):
        self.vault = VaultManager(DB_FILE)
        self.citra_path = get_citra_base_path()
        self.title_root = get_save_data_root(self.citra_path)
        self._init_config()
        self.notifier = NotificationManager(self.get_config("discord_webhook"))

    def _init_config(self):
        cursor = self.vault.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS system_config (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        defaults = {
            "sync_mode": "local",
            "cloud_path": "",
            "github_repo_url": "",
            "github_token": "",
            "github_username": "",
            "discord_webhook": ""
        }
        for k, v in defaults.items():
            cursor.execute("INSERT OR IGNORE INTO system_config (key, value) VALUES (?, ?)", (k, v))
        self.vault.conn.commit()

    def get_config(self, key):
        cursor = self.vault.conn.cursor()
        cursor.execute("SELECT value FROM system_config WHERE key = ?", (key,))
        row = cursor.fetchone()
        return row[0] if row else ""

    @property
    def config(self):
        cursor = self.vault.conn.cursor()
        cursor.execute("SELECT key, value FROM system_config")
        return {row[0]: row[1] for row in cursor.fetchall()}

    def set_config(self, key, value):
        cursor = self.vault.conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO system_config (key, value) VALUES (?, ?)", (key, str(value)))
        self.vault.conn.commit()
        if key == "discord_webhook":
            self.notifier.webhook_url = value

    def get_detected_games(self):
        return find_game_saves(self.title_root)

    def check_conflict(self, game):
        local_path = game["local_path"]
        if not os.path.exists(local_path):
            return "no_local", "Local save missing."

        # In a real SSH/Differential scenario, we'd check remote mtime
        # For now, we use a placeholder status
        return "ready", "Ready for Vault operation."

    def push_save(self, game):
        local_hash = self.vault.get_file_hash(game["local_path"])

        # Check deduplication
        cursor = self.vault.conn.cursor()
        cursor.execute("SELECT last_hash FROM saves WHERE game_id = ?", (game["id"],))
        row = cursor.fetchone()
        if row and row[0] == local_hash:
            logging.info(f"Deduplication: {game['name']} hash unchanged. Skipping sync.")
            return True, "No changes detected (Deduplicated)."

        success, msg = self._push_local(game)
        if success:
            self.vault.update_save_metadata(game["id"], game["name"], game["local_path"], local_hash)
            self.vault.log_sync(game["id"], platform.node(), local_hash, "PUSH")
            self.vault.commit_version(SAVE_REPO_DIR, f"Vault Sync: {game['name']} from {platform.node()}")
            self.notifier.notify_sync(game["name"], platform.node())

        return success, msg

    def pull_save(self, game):
        success, msg = self._pull_local(game)
        if success:
            new_hash = self.vault.get_file_hash(game["local_path"])
            self.vault.update_save_metadata(game["id"], game["name"], game["local_path"], new_hash)
            self.vault.log_sync(game["id"], "REMOTE", new_hash, "PULL")
        return success, msg

    def _push_local(self, game):
        cloud_path = self.get_config("cloud_path")
        if not cloud_path: return False, "Vault Cloud Path not set."
        dest = os.path.join(cloud_path, game["id"], "main")
        try:
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copy2(game["local_path"], dest)
            # Sync to save_repo for FileBrowser/Git versioning
            vault_dest = os.path.join(SAVE_REPO_DIR, game["id"], "main")
            os.makedirs(os.path.dirname(vault_dest), exist_ok=True)
            shutil.copy2(game["local_path"], vault_dest)
            return True, "Archived to Vault."
        except Exception as e:
            return False, str(e)

    def _pull_local(self, game):
        cloud_path = self.get_config("cloud_path")
        if not cloud_path: return False, "Vault Cloud Path not set."
        source = os.path.join(cloud_path, game["id"], "main")
        if not os.path.exists(source): return False, "Vault source missing."
        try:
            shutil.copy2(source, game["local_path"])
            return True, "Restored from Vault."
        except Exception as e:
            return False, str(e)

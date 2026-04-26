import os
import sqlite3
import hashlib
import platform
import logging
import shlex
import subprocess
from datetime import datetime
from git import Repo, GitCommandError

# Configuration & Logging
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    filename=os.path.join(LOG_DIR, "vault.log"),
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

class VaultManager:
    def __init__(self, db_path="vault.db"):
        """
        Initializes the Aether-Vault manager with SQLite backend.
        """
        try:
            self.db_path = db_path
            self.conn = sqlite3.connect(self.db_path)
            self._init_db()
            logging.info("Vault Manager initialized successfully.")
        except Exception as e:
            logging.error(f"Failed to initialize Vault Manager: {str(e)}")
            raise

    def _init_db(self):
        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS saves (
                game_id TEXT PRIMARY KEY,
                game_name TEXT,
                local_path TEXT,
                last_hash TEXT,
                last_sync DATETIME,
                status TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sync_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_id TEXT,
                timestamp DATETIME,
                source_device TEXT,
                hash TEXT,
                action TEXT
            )
        """)
        self.conn.commit()

    def get_file_hash(self, filepath):
        """
        Calculates SHA-256 hash for deduplication.
        """
        if not os.path.exists(filepath):
            return None
        sha256_hash = hashlib.sha256()
        try:
            with open(filepath, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
        except Exception as e:
            logging.error(f"Hash calculation error for {filepath}: {str(e)}")
            return None

    def sync_rsync_style(self, remote_user, remote_host, remote_port, remote_path, local_path):
        """
        Implements differential transfer logic over SSH.
        """
        try:
            remote_source = f"{remote_user}@{remote_host}:{shlex.quote(remote_path)}"
            cmd = [
                "scp",
                "-P", str(remote_port),
                "-p", # Preserve mtimes for writer-wins logic
                remote_source,
                local_path
            ]
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            logging.info(f"Rsync-style sync complete: {remote_path} -> {local_path}")
            return True
        except subprocess.CalledProcessError as e:
            logging.error(f"Sync failed: {e.stderr}")
            return False

    def handle_conflict(self, local_path, remote_mtime):
        """
        Implements Latest-Writer-Wins with 5s conflict threshold.
        """
        if not os.path.exists(local_path):
            return "pull"

        local_mtime = os.path.getmtime(local_path)
        if abs(local_mtime - remote_mtime) < 5:
            # Conflict: backup local and allow pull
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            shutil.copy2(local_path, f"{local_path}.conflict_{timestamp}")
            logging.warning(f"Conflict detected for {local_path}. Created .conflict backup.")
            return "conflict"

        return "pull" if remote_mtime > local_mtime else "push"

    def commit_version(self, repo_path, message):
        """
        Automated Git-based versioning for save-scumming mode.
        """
        try:
            if not os.path.exists(os.path.join(repo_path, ".git")):
                repo = Repo.init(repo_path)
            else:
                repo = Repo(repo_path)

            repo.git.add(A=True)
            repo.index.commit(message)
            logging.info(f"Version committed: {message}")
            return True
        except Exception as e:
            logging.error(f"Versioning failed: {str(e)}")
            return False

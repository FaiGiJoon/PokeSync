import os
import shutil
import time
import logging
from notify import NotificationManager
from vault_manager import VaultManager

def get_disk_usage(path="/"):
    total, used, free = shutil.disk_usage(path)
    return (free / total) * 100

import requests

def monitor_pulse(webhook_url, heartbeat_url=None, interval=600):
    """
    Continuous monitoring for disk space and system heartbeat.
    """
    notifier = NotificationManager(webhook_url)
    logging.info("Pulse system initiated.")

    while True:
        try:
            # Check Disk Space
            free_percent = get_disk_usage()
            if free_percent < 10:
                notifier.notify_alert(f"Low Disk Space: {free_percent:.2f}% remaining on host.")

            # External Heartbeat Ping
            if heartbeat_url:
                try:
                    requests.get(heartbeat_url, timeout=5)
                except Exception as e:
                    logging.warning(f"Heartbeat ping failed: {str(e)}")

            logging.info(f"System Pulse: Disk Free {free_percent:.2f}%")
            time.sleep(interval)
        except Exception as e:
            logging.error(f"Pulse error: {str(e)}")
            time.sleep(60)

if __name__ == "__main__":
    # For testing
    monitor_pulse(None)

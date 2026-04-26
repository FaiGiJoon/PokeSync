import requests
import os
import logging

class NotificationManager:
    def __init__(self, webhook_url):
        self.webhook_url = webhook_url
        self.log_dir = "logs"
        os.makedirs(self.log_dir, exist_ok=True)

    def send_discord_embed(self, title, description, color=3066993):
        """
        Sends a rich embed notification to Discord.
        """
        if not self.webhook_url:
            return

        payload = {
            "embeds": [{
                "title": title,
                "description": description,
                "color": color,
                "timestamp": None
            }]
        }

        try:
            response = requests.post(self.webhook_url, json=payload, timeout=10)
            response.raise_for_status()
        except Exception as e:
            logging.error(f"Failed to send notification: {str(e)}")

    def notify_sync(self, game_name, device):
        self.send_discord_embed(
            "Save Archived",
            f"Game: {game_name}\nSource: {device}",
            color=3066993 # Green-ish
        )

    def notify_alert(self, message):
        self.send_discord_embed(
            "System Alert",
            message,
            color=15158332 # Red-ish
        )

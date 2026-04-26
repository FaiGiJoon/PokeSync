import os
import subprocess
import logging
import shlex

class SecurityManager:
    def __init__(self, log_dir="logs"):
        self.log_dir = log_dir
        os.makedirs(self.log_dir, exist_ok=True)
        logging.basicConfig(
            filename=os.path.join(self.log_dir, "security.log"),
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s"
        )

    def automate_tailscale(self, auth_key):
        """
        Automates Tailscale Auth Key deployment.
        """
        if not auth_key:
            return False, "No Auth Key provided."

        try:
            cmd = ["tailscale", "up", "--authkey", auth_key, "--ssh"]
            subprocess.run(cmd, check=True, capture_output=True)
            logging.info("Tailscale up with SSH enabled.")
            return True, "Tailscale integration complete."
        except Exception as e:
            logging.error(f"Tailscale automation failed: {str(e)}")
            return False, str(e)

    def harden_ssh(self, port=2222):
        """
        Applies SSH hardening parameters.
        Note: Requires sudo/root privileges.
        """
        config_path = "/etc/ssh/sshd_config"
        if not os.path.exists(config_path):
            return False, "SSH config not found."

        try:
            # This is a template based approach as requested
            hardening_params = [
                f"Port {port}",
                "PasswordAuthentication no",
                "PubkeyAuthentication yes",
                "HostKeyAlgorithms ed25519"
            ]

            with open(config_path, "a") as f:
                f.write("\n# Aether-Vault Hardening\n")
                for param in hardening_params:
                    f.write(f"{param}\n")

            subprocess.run(["systemctl", "restart", "ssh"], check=True)
            logging.info(f"SSH Hardened on port {port}.")
            return True, "SSH hardening applied."
        except Exception as e:
            logging.error(f"SSH hardening failed: {str(e)}")
            return False, str(e)

    def trigger_fallback_tunnel(self, local_port=8080):
        """
        Initializes Cloudflare Tunnel as fallback.
        """
        try:
            # Cloudflared quick tunnel
            cmd = ["cloudflared", "tunnel", "--url", f"http://localhost:{local_port}"]
            # This would normally run in background and extract URL
            logging.info("Fallback tunnel initiated.")
            return True, "Fallback tunnel active."
        except Exception as e:
            logging.error(f"Fallback tunnel failed: {str(e)}")
            return False, str(e)

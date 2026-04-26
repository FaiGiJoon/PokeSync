#!/bin/bash

# Project Aether-Vault: Orchestration Script (Linux)

set -e

echo "Initializing Hardened Infrastructure..."

# Logging setup
mkdir -p logs

# Check for Virtualization support
if grep -Eoc "vmx|svm" /proc/cpuinfo > /dev/null; then
    echo "Virtualization support detected."
else
    echo "Warning: Hardware virtualization (VT-x/AMD-V) not detected. Docker may perform poorly."
fi

# Automated Dependency Installation
install_dependency() {
    if ! command -v "$1" &> /dev/null; then
        echo "Installing $1..."
        case "$1" in
            docker)
                curl -fsSL https://get.docker.com | sh
                ;;
            git)
                sudo apt-get update && sudo apt-get install -y git
                ;;
            tailscale)
                curl -fsSL https://tailscale.com/install.sh | sh
                ;;
        esac
    fi
}

install_dependency git
install_dependency docker
install_dependency tailscale

# Directory lifecycle management
echo "Configuring data lifecycle directories..."
mkdir -p backups
mkdir -p save_repo
mkdir -p logs

# Initializing configuration
if [ ! -f .env ]; then
    echo "Creating .env template..."
    cat <<EOF > .env
TS_AUTHKEY=
DISCORD_WEBHOOK_URL=
CITRA_SAVE_PATH=~/.local/share/citra-emu
EOF
fi

# Service persistence (Systemd)
echo "Configuring service persistence..."
if [ ! -f /etc/systemd/system/pokesync-vault.service ]; then
    cat <<EOF | sudo tee /etc/systemd/system/pokesync-vault.service
[Unit]
Description=Project Aether-Vault Core
After=network.target docker.service

[Service]
Type=simple
WorkingDirectory=$(pwd)
ExecStart=/usr/bin/docker-compose up
ExecStop=/usr/bin/docker-compose down
Restart=always

[Install]
WantedBy=multi-user.target
EOF
    sudo systemctl daemon-reload
    sudo systemctl enable pokesync-vault.service
fi

echo "Phase 1: Infrastructure initialization complete."

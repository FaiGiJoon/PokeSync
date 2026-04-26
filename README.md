# Project Aether-Vault: Secure Save-State Infrastructure

Project Aether-Vault is a hardened, production-ready environment for synchronizing application data and Citra save files across multiple platforms using a Zero-Trust networking model.

## Features
- Distributed Vault: SQLite-backed configuration and metadata tracking.
- Atomic Synchronization: SHA-256 deduplication and Git-based versioning for all saves.
- Zero-Trust Networking: Automated Tailscale integration with SSH hardening.
- Monitoring: Heartbeat system with Discord/Slack webhook notifications.
- Orchestration: Multi-container stack (App, FileBrowser, Watchtower).

## Quick Start (3 Commands)

### 1. Initialize Infrastructure
```bash
git clone <your-repo-url> && cd pokesync
./setup.sh  # or setup_macos.sh / .\install.ps1
```

### 2. Configure Environment
Edit the `.env` file with your `TS_AUTHKEY` and `DISCORD_WEBHOOK_URL`.

### 3. Launch Stack
```bash
docker-compose up -d
```

## Security Audit
This project utilizes Tailscale SSH, which enforces identity-based authentication rather than static passwords. By moving the service behind a WireGuard-based mesh, we eliminate the need for dangerous router port forwarding (NAT traversal).

## Data Lifecycle
- All saves are hashed (SHA-256) before transfer to prevent redundant writes.
- Git commits are automatically generated for every sync, providing a "Save-Scumming" historical record.
- FileBrowser provides a secure web UI (Port 8080) for manual vault exploration.

## Monitoring
The Pulse system (pulse.py) monitors host health and disk usage, sending alerts via the configured Discord webhook if free space drops below 10%.

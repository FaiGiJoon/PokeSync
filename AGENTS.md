# Agent Instructions: Project Aether-Vault

## System Overview
Project Aether-Vault is a hardened infrastructure for distributed application data and Citra save files. It uses a Zero-Trust networking model via Tailscale and a containerized orchestration stack.

## Architecture Guidelines for AI Agents
1. **Security First**: Do not modify `sshd_config` or Tailscale settings without ensuring Ed25519 key-only authentication is maintained.
2. **Modularity**: Keep the `VaultManager`, `SecurityManager`, and `NotificationManager` as distinct modules.
3. **Data Integrity**: Always use SHA-256 hashing (via `VaultManager`) before performing sync operations to ensure deduplication.
4. **Environment Isolation**: Prefer `docker-compose` for service deployments. The host setup scripts should only be used for base dependency installation.
5. **No Slang**: All logs and documentation must remain academic, technical, and precise. Emojis are strictly prohibited.

## Data Flow
Random Network PC -> Tailscale SSH Tunnel -> Aether-Vault Container -> Git-Versioned Save Repository.

## Maintenance
- Watchtower handles automated image updates.
- Pulse handles system health monitoring and Discord alerts.

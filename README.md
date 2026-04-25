# PokeSync - Universal Citra Save Sync

PokeSync is a simple tool to keep your Citra saves synchronized between multiple computers using a Cloud folder (Dropbox/OneDrive) or GitHub.

## ✨ Features
- **Universal Sync**: Works with ALL 3DS games (Pokémon, Zelda, Mario, etc.).
- **Safe**: Automatically backs up your saves before syncing.
- **Smart**: Warns you if you are about to overwrite a newer save.
- **Easy UI**: Simple buttons to "Push" (upload) or "Pull" (download) your progress.

## 🚀 Quick Start (3 Commands)

### Linux
```bash
git clone <your-repo-url> && cd pokesync
./setup.sh
python3 main.py
```

### Windows
```powershell
git clone <your-repo-url>; cd pokesync
.\install.ps1
python main.py
```

### macOS
```bash
git clone <your-repo-url> && cd pokesync
./setup_macos.sh
python3 main.py
```

### Docker (Production Ready)
```bash
docker-compose up -d
```

## 📖 How to Sync

### Option A: Local Cloud (Easiest)
1. Set **Sync Mode** to "Local Folder".
2. Click **Browse Cloud Path** and select a folder in your Dropbox, OneDrive, or Google Drive.
3. Use **Push** to upload your save and **Pull** on your other computer.

### Option B: GitHub (Advanced)
See the [GUIDE.md](GUIDE.md) for step-by-step GitHub setup.

## 🛡️ Safety & Security
- **Backups**: Your saves are stored in `backups/` every time you pull.
- **Isolation**: When using Docker, the app runs in a containerized environment.
- **Secure Access**: We recommend using **Tailscale** for remote access (see below).

## 🌐 Remote Access (Tailscale)
To sync your saves from anywhere without opening ports on your router:
1. **Install Tailscale** on both your local and remote machines.
2. **Enable Tailscale SSH** in your Tailscale dashboard.
3. Use the included `sync_data.py` script to fetch saves securely:
   ```bash
   python sync_data.py [user] [tailscale-ip] 22 [remote-path] [local-path]
   ```

## ⚙️ Advanced: Auto-Run on Boot (Linux)
1. Copy the service file: `cp pokesync.service ~/.config/systemd/user/`
2. Enable it: `systemctl --user enable --now pokesync.service`

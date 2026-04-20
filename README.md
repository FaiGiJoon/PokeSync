# PokeSync - Universal Citra Save Sync

PokeSync is a simple tool to keep your Citra saves synchronized between multiple computers using a Cloud folder (Dropbox/OneDrive) or GitHub.

## ✨ Features
- **Universal Sync**: Works with ALL 3DS games (Pokémon, Zelda, Mario, etc.).
- **Safe**: Automatically backs up your saves before syncing.
- **Smart**: Warns you if you are about to overwrite a newer save.
- **Easy UI**: Simple buttons to "Push" (upload) or "Pull" (download) your progress.

## 🚀 Quick Start

1. **Install Python**: Make sure you have Python installed.
2. **Install requirements**:
   ```bash
   pip install -r requirements.txt
   ```
3. **Run the app**:
   ```bash
   python main.py
   ```

## 📖 How to Sync

### Option A: Local Cloud (Easiest)
1. Set **Sync Mode** to "Local Folder".
2. Click **Browse Cloud Path** and select a folder in your Dropbox, OneDrive, or Google Drive.
3. Use **Push** to upload your save and **Pull** on your other computer.

### Option B: GitHub (Advanced)
See the [GUIDE.md](GUIDE.md) for step-by-step GitHub setup.

## 🛡️ Safety
Your saves are stored in `backups/` every time you pull, so you never lose progress!

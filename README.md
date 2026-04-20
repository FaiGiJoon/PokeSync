# PokeSync - Universal Citra Save Sync Tool

PokeSync is a modern, cross-platform tool designed to synchronize your 3DS save files across different devices. Whether you're playing on a Windows PC, a Mac, or even via Docker, PokeSync ensures your saves are always up to date.

## 🚀 Features
- **Universal Detection**: Automatically identifies all 3DS games in your Citra directory.
- **Enhanced Pokémon Support**: Specialized detection for all mainline Pokémon games (X/Y, ORAS, Sun/Moon, Ultra Sun/Moon).
- **Dual Sync Modes**:
    - **Local Cloud**: Sync using services like Dropbox, OneDrive, or Google Drive.
    - **GitHub**: Sync using a private GitHub repository for version-controlled saves.
- **Search & Filter**: Easily find games by name or Title ID.
- **Safety Backups**: Automatically creates timestamped backups of your local saves before every 'Pull' operation.
- **Modern GUI**: A clean, dark-themed interface built with CustomTkinter.
- **Docker Support**: Run the application in a containerized environment.

## 🛠️ Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/yourusername/pokesync.git
   cd pokesync
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the app**:
   ```bash
   python main.py
   ```

## 📖 How to Use
Check out the [GUIDE.md](GUIDE.md) for a detailed step-by-step setup for both Local and GitHub sync modes.

## 🐳 Docker Support
For instructions on running PokeSync inside a Docker container, see [README_DOCKER.md](README_DOCKER.md).

## 🛡️ Safety
Your saves are precious! PokeSync never overwrites a local save without first creating a backup in the `backups/` directory.

## 📝 Supported Games
While PokeSync can detect **any** 3DS game with a valid save, it has built-in names for:
- All mainline Pokémon 3DS games and demos.
- Pokémon Mystery Dungeon series.
- Pokémon Rumble World.
- ...and more! Unknown games will be displayed with their Title ID.

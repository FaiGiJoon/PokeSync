# PokeSync - Citra Save Cloud Sync

PokeSync is a simple, cross-platform tool designed to synchronize your Pokémon 3DS save files across different computers (e.g., Windows and macOS) using a cloud storage service like Dropbox, Google Drive, or OneDrive.

## Features
- **Auto-detection**: Automatically finds your Citra data folder on Windows and macOS.
- **Game Support**: Supports Pokémon X, Y, Omega Ruby, and Alpha Sapphire.
- **Safe Syncing**: Creates a timestamped backup of your local save before pulling from the cloud.
- **Modern UI**: Easy-to-use interface built with CustomTkinter.

## Requirements
- Python 3.x
- `customtkinter`
- `pillow`

## Installation
1. Clone or download this repository.
2. Install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## How to Use
1. **Launch the application**:
   ```bash
   python main.py
   ```
2. **Set your Cloud Folder**:
   - Click "Browse" and select a folder that is synced to your cloud (e.g., a folder inside your Dropbox or OneDrive).
3. **Sync your saves**:
   - **Push to Cloud**: Click this on your "source" computer to upload your current save to the cloud.
   - **Pull from Cloud**: Click this on your "target" computer to download the save from the cloud into your Citra folder. A backup of the local save will be created automatically.

## Supported Games
- Pokémon X
- Pokémon Y
- Pokémon Omega Ruby
- Pokémon Alpha Sapphire

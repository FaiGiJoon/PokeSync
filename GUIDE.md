# Setup Guide

## 1. Local Cloud Sync (Dropbox, OneDrive, etc.)
1.  **Open PokeSync**.
2.  Set **Sync Mode** to "Local Folder".
3.  Click **Browse Cloud Path** and select your synced folder.
4.  **Push** to upload, **Pull** to download.

## 2. GitHub Sync (Step-by-Step)
1.  **Create a Private Repo**: Create a new private repository on GitHub (e.g. `citra-saves`).
2.  **Get a Token**:
    - Go to GitHub Settings -> Developer settings -> Personal access tokens -> Tokens (classic).
    - Generate a token with the **repo** scope.
3.  **Fill in PokeSync**:
    - **Repo URL**: The link to your repo (e.g. `https://github.com/user/citra-saves.git`).
    - **Username**: Your GitHub username.
    - **Token/PAT**: The token you just created.
4.  **First Push**: Click **Push** on a game to upload it.

## FAQ
- **Game not showing?**: Open the game once in Citra so it creates a save file.
- **Randomizers?**: Yes, they work exactly the same as normal games!

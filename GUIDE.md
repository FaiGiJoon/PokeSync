# PokeSync Setup Guide

This guide will help you set up PokeSync for both Local Cloud and GitHub synchronization.

## 1. Local Cloud Sync (Dropbox, OneDrive, etc.)
This mode is the easiest to set up if you already use a cloud storage service that syncs a folder on your computer.

1.  **Open PokeSync**.
2.  Ensure **Sync Mode** is set to "Local Folder" in the sidebar.
3.  Click **Browse Cloud Path** and select a folder inside your Dropbox, Google Drive, or OneDrive directory.
4.  You can now use **Push** to upload your save and **Pull** to download it on another computer.

## 2. GitHub Sync
GitHub sync is ideal if you want version control for your saves or don't use a standard cloud service.

### Step 2.1: Create a GitHub Repository
1.  Go to [GitHub](https://github.com/) and create a new **Private** repository (e.g., `my-citra-saves`).
2.  Do **not** initialize it with a README or .gitignore.

### Step 2.2: Generate a Personal Access Token (PAT)
1.  Go to **Settings** -> **Developer settings** -> **Personal access tokens** -> **Tokens (classic)**.
2.  Generate a new token with the `repo` scope.
3.  **Copy this token** and keep it safe.

### Step 2.3: Configure PokeSync
1.  In PokeSync, set **Sync Mode** to "GitHub".
2.  **Repo URL**: Paste the URL of your new repo (e.g., `https://github.com/youruser/my-citra-saves.git`).
3.  **Username**: Your GitHub username.
4.  **Token/PAT**: Paste the token you generated.
5.  Click **Push** on a game to initialize the repo and upload your first save.

## 3. Backups
Every time you **Pull** a save from the cloud/GitHub, PokeSync automatically creates a backup of your local save in the `backups/` folder within the PokeSync directory.

## 4. Troubleshooting
- **No games detected**: Ensure Citra is installed and you have launched the games at least once so the save folders are created.
- **Git errors**: Ensure you have [Git](https://git-scm.com/) installed on your system and it's in your PATH.

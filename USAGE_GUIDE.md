# PokeSync Usage & Setup Guide (Windows)

This guide provides the necessary steps to get PokeSync up and running on a Windows environment, including troubleshooting steps for common GUI issues.

## 1. Prerequisites
Ensure you have **Python 3.10+** installed. You can check your version by running:
```powershell
python --version
```

## 2. Installation
1. **Extract the Project**: Download and extract `PokeSync-main.zip` to a folder of your choice (e.g., `C:\Users\YourName\PokeSync`).
2. **Install Dependencies**: Open a terminal in the project directory and run:
   ```powershell
   pip install -r requirements.txt
   ```
   *Required packages: customtkinter, pillow, requests, GitPython.*

## 3. Running the Application
Launch the GUI by running the `main.py` script:
```powershell
python main.py
```

## 4. Troubleshooting: GUI Won't Open (Geometry Collision)
If you encounter an error like `_tkinter.TclError: cannot use geometry manager pack inside ... which already has slaves managed by grid`, it means the application is mixing layout managers.

### The Fix:
Open `gui.py` and ensure the `update_settings_visibility` method uses `grid` instead of `pack`.

**Incorrect Code:**
```python
def update_settings_visibility(self, mode):
    if mode == "GitHub":
        self.local_frame.pack_forget()
        self.github_frame.pack(fill="x", ...)
```

**Corrected Code:**
```python
def update_settings_visibility(self, mode):
    if mode == "GitHub":
        self.local_frame.grid_forget()
        self.github_frame.grid(row=3, column=0, sticky="ew")
    else:
        self.github_frame.grid_forget()
        self.local_frame.grid(row=3, column=0, sticky="ew")
```

## 5. Citra Integration
PokeSync automatically detects your Citra save directory on Windows at `%APPDATA%\Citra`.
- **Mainline Pokémon Games**: Automatically identified by Title ID.
- **Backups**: Every 'Pull' operation creates a timestamped backup in the `backups/` folder within the project directory.

## 6. Sync Modes
- **Local Folder**: Best for Dropbox/OneDrive/Google Drive syncing.
- **GitHub**: Requires a private repository, Username, and Personal Access Token (PAT).

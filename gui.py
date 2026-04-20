import customtkinter as ctk
from tkinter import filedialog, messagebox
import os

class PokeSyncGUI(ctk.CTk):
    def __init__(self, sync_manager):
        super().__init__()
        self.manager = sync_manager
        
        self.title("PokeSync - Universal Citra Save Sync")
        self.geometry("900x750")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.all_games = []
        self.setup_ui()
        self.refresh_games()

    def setup_ui(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Sidebar for Settings
        self.sidebar = ctk.CTkFrame(self, width=250, corner_radius=0)
        self.sidebar.grid(row=0, column=0, rowspan=2, sticky="nsew")
        self.sidebar.grid_rowconfigure(8, weight=1)

        self.logo_label = ctk.CTkLabel(self.sidebar, text="PokeSync", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.pack(padx=20, pady=(20, 10))

        # Sync Mode Toggle
        self.mode_label = ctk.CTkLabel(self.sidebar, text="Sync Mode:", anchor="w")
        self.mode_label.pack(padx=20, pady=(10, 0), fill="x")

        self.mode_switch = ctk.CTkOptionMenu(self.sidebar, values=["Local Folder", "GitHub"],
                                              command=self.change_sync_mode)
        self.mode_switch.pack(padx=20, pady=(0, 20), fill="x")
        initial_mode = "GitHub" if self.manager.config.get("sync_mode") == "github" else "Local Folder"
        self.mode_switch.set(initial_mode)

        # Local Sync Settings
        self.local_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.btn_browse = ctk.CTkButton(self.local_frame, text="Browse Cloud Path", command=self.browse_cloud_path)
        self.btn_browse.pack(padx=20, pady=5, fill="x")

        # GitHub Sync Settings
        self.github_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")

        self.entry_repo = self.create_setting_entry(self.github_frame, "Repo URL:", "github_repo_url")
        self.entry_user = self.create_setting_entry(self.github_frame, "Username:", "github_username")
        self.entry_token = self.create_setting_entry(self.github_frame, "Token/PAT:", "github_token", show="*")

        self.update_settings_visibility(initial_mode)

        # Main Content Area
        self.main_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(1, weight=1)

        # Search Bar
        self.search_entry = ctk.CTkEntry(self.main_frame, placeholder_text="Search games by name or ID...")
        self.search_entry.grid(row=0, column=0, padx=(0, 10), pady=(0, 20), sticky="ew")
        self.search_entry.bind("<KeyRelease>", lambda e: self.filter_games())

        self.btn_refresh = ctk.CTkButton(self.main_frame, text="Refresh", width=100, command=self.refresh_games)
        self.btn_refresh.grid(row=0, column=1, padx=0, pady=(0, 20))

        # Games List
        self.games_scroll = ctk.CTkScrollableFrame(self.main_frame, label_text="Detected Games")
        self.games_scroll.grid(row=1, column=0, columnspan=2, sticky="nsew")
        self.games_scroll.grid_columnconfigure(0, weight=1)

        # Status Bar
        self.status_label = ctk.CTkLabel(self, text="Ready", anchor="w")
        self.status_label.grid(row=1, column=1, padx=20, pady=10, sticky="ew")

    def create_setting_entry(self, parent, label_text, config_key, show=None):
        lbl = ctk.CTkLabel(parent, text=label_text, anchor="w")
        lbl.pack(padx=20, pady=(5, 0), fill="x")
        entry = ctk.CTkEntry(parent, show=show)
        entry.insert(0, self.manager.config.get(config_key, ""))
        entry.pack(padx=20, pady=(0, 5), fill="x")
        entry.bind("<FocusOut>", lambda e, k=config_key, ent=entry: self.save_setting(k, ent.get()))
        return entry

    def save_setting(self, key, value):
        self.manager.set_config(key, value)
        self.status_label.configure(text=f"Setting '{key}' saved.")

    def change_sync_mode(self, mode):
        self.update_settings_visibility(mode)
        sync_mode = "github" if mode == "GitHub" else "local"
        self.manager.set_config("sync_mode", sync_mode)
        self.status_label.configure(text=f"Sync mode changed to {mode}")

    def update_settings_visibility(self, mode):
        if mode == "GitHub":
            self.local_frame.pack_forget()
            self.github_frame.pack(fill="x", before=self.sidebar.grid_slaves(row=8)[0] if self.sidebar.grid_slaves(row=8) else None)
        else:
            self.github_frame.pack_forget()
            self.local_frame.pack(fill="x", before=self.sidebar.grid_slaves(row=8)[0] if self.sidebar.grid_slaves(row=8) else None)

    def browse_cloud_path(self):
        path = filedialog.askdirectory()
        if path:
            self.manager.set_cloud_path(path)
            self.status_label.configure(text="Cloud path updated")

    def refresh_games(self):
        self.status_label.configure(text="Scanning for games...")
        self.update()
        self.all_games = self.manager.get_detected_games()
        self.filter_games()
        self.status_label.configure(text=f"Found {len(self.all_games)} games")

    def filter_games(self):
        search_term = self.search_entry.get().lower()

        # Clear existing
        for widget in self.games_scroll.winfo_children():
            widget.destroy()

        filtered = [g for g in self.all_games if search_term in g["name"].lower() or search_term in g["id"].lower()]

        if not filtered:
            label = ctk.CTkLabel(self.games_scroll, text="No games found matching your search.")
            label.grid(row=0, column=0, pady=20)
            return

        for i, game in enumerate(filtered):
            self.create_game_row(game, i)

    def create_game_row(self, game, row_index):
        row_frame = ctk.CTkFrame(self.games_scroll)
        row_frame.grid(row=row_index, column=0, padx=10, pady=5, sticky="ew")
        row_frame.grid_columnconfigure(0, weight=1)

        name_color = "#3498db" if game["is_pokemon"] else "white"
        game_name_label = ctk.CTkLabel(row_frame, text=game["name"], font=("Arial", 13, "bold"), text_color=name_color)
        game_name_label.grid(row=0, column=0, padx=10, pady=(5, 0), sticky="w")

        id_label = ctk.CTkLabel(row_frame, text=f"ID: {game['id']}", font=("Arial", 10), text_color="gray")
        id_label.grid(row=1, column=0, padx=10, pady=(0, 5), sticky="w")

        btn_push = ctk.CTkButton(row_frame, text="Push", width=80,
                                  fg_color="#2ecc71", hover_color="#27ae60",
                                  command=lambda g=game: self.action_push(g))
        btn_push.grid(row=0, column=1, rowspan=2, padx=5, pady=10)

        btn_pull = ctk.CTkButton(row_frame, text="Pull", width=80,
                                  fg_color="#3498db", hover_color="#2980b9",
                                  command=lambda g=game: self.action_pull(g))
        btn_pull.grid(row=0, column=2, rowspan=2, padx=5, pady=10)

    def action_push(self, game):
        self.status_label.configure(text=f"Checking conflicts for {game['name']}...")
        self.update()

        status, msg = self.manager.check_conflict(game)
        if status == "remote_newer":
            confirm = messagebox.askyesno("Conflict Detected", f"The REMOTE save is NEWER than your local save.\n\nRemote: {msg}\n\nAre you sure you want to OVERWRITE the remote save?")
            if not confirm:
                self.status_label.configure(text="Push cancelled by user.")
                return
        elif status == "up_to_date":
            confirm = messagebox.askyesno("Up to Date", "Saves are already synchronized. Push anyway?")
            if not confirm:
                self.status_label.configure(text="Push cancelled.")
                return

        self.status_label.configure(text=f"Pushing {game['name']}...")
        self.update()
        success, message = self.manager.push_save(game)
        if success:
            self.status_label.configure(text=f"Pushed {game['name']} successfully.")
            messagebox.showinfo("Success", message)
        else:
            self.status_label.configure(text="Push failed.")
            messagebox.showerror("Error", message)

    def action_pull(self, game):
        self.status_label.configure(text=f"Checking conflicts for {game['name']}...")
        self.update()

        status, msg = self.manager.check_conflict(game)
        if status == "local_newer":
            confirm = messagebox.askyesno("Conflict Detected", f"Your LOCAL save is NEWER than the remote save.\n\nLocal: {msg}\n\nAre you sure you want to OVERWRITE your local save? (A backup will be created)")
            if not confirm:
                self.status_label.configure(text="Pull cancelled by user.")
                return
        elif status == "up_to_date":
            confirm = messagebox.askyesno("Up to Date", "Saves are already synchronized. Pull anyway?")
            if not confirm:
                self.status_label.configure(text="Pull cancelled.")
                return
        else:
            confirm = messagebox.askyesno("Confirm Pull", f"Overwrite local save for {game['name']}? A backup will be created.")
            if not confirm:
                return

        self.status_label.configure(text=f"Pulling {game['name']}...")
        self.update()
        success, message = self.manager.pull_save(game)
        if success:
            self.status_label.configure(text=f"Pulled {game['name']} successfully.")
            messagebox.showinfo("Success", message)
        else:
            self.status_label.configure(text="Pull failed.")
            messagebox.showerror("Error", message)

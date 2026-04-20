import customtkinter as ctk
from tkinter import filedialog, messagebox
import os

class PokeSyncGUI(ctk.CTk):
    def __init__(self, sync_manager):
        super().__init__()
        self.manager = sync_manager
        
        self.title("PokeSync - Citra Save Cloud Sync")
        self.geometry("700x500")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.setup_ui()
        self.refresh_games()

    def setup_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Header / Config Section
        self.header_frame = ctk.CTkFrame(self)
        self.header_frame.grid(row=0, column=0, padx=20, pady=20, sticky="ew")
        self.header_frame.grid_columnconfigure(1, weight=1)

        self.label_cloud = ctk.CTkLabel(self.header_frame, text="Cloud/Sync Folder:")
        self.label_cloud.grid(row=0, column=0, padx=10, pady=10)

        self.entry_cloud = ctk.CTkEntry(self.header_frame, placeholder_text="Path to your Dropbox/GDrive/OneDrive folder")
        self.entry_cloud.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        self.entry_cloud.insert(0, self.manager.config.get("cloud_path", ""))

        self.btn_browse = ctk.CTkButton(self.header_frame, text="Browse", command=self.browse_cloud_path)
        self.btn_browse.grid(row=0, column=2, padx=10, pady=10)

        # Games List Section
        self.games_frame = ctk.CTkScrollableFrame(self, label_text="Detected Pokemon Games")
        self.games_frame.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="nsew")
        self.games_frame.grid_columnconfigure(0, weight=1)

        # Footer
        self.footer_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.footer_frame.grid(row=2, column=0, padx=20, pady=(0, 20), sticky="ew")
        
        self.btn_refresh = ctk.CTkButton(self.footer_frame, text="Refresh Games", command=self.refresh_games)
        self.btn_refresh.pack(side="left", padx=10)

        self.status_label = ctk.CTkLabel(self.footer_frame, text="Ready")
        self.status_label.pack(side="right", padx=10)

    def browse_cloud_path(self):
        path = filedialog.askdirectory()
        if path:
            self.entry_cloud.delete(0, "end")
            self.entry_cloud.insert(0, path)
            self.manager.set_cloud_path(path)
            self.status_label.configure(text="Cloud path updated")

    def refresh_games(self):
        # Clear existing game rows
        for widget in self.games_frame.winfo_children():
            widget.destroy()

        games = self.manager.get_detected_games()
        if not games:
            label = ctk.CTkLabel(self.games_frame, text="No Pokemon games detected in Citra directory.")
            label.grid(row=0, column=0, pady=20)
            return

        for i, game in enumerate(games):
            self.create_game_row(game, i)

    def create_game_row(self, game, row_index):
        row_frame = ctk.CTkFrame(self.games_frame)
        row_frame.grid(row=row_index, column=0, padx=10, pady=5, sticky="ew")
        row_frame.grid_columnconfigure(0, weight=1)

        game_name_label = ctk.CTkLabel(row_frame, text=game["name"], font=("Arial", 14, "bold"))
        game_name_label.grid(row=0, column=0, padx=10, pady=10, sticky="w")

        btn_push = ctk.CTkButton(row_frame, text="Push to Cloud", 
                                  fg_color="#2ecc71", hover_color="#27ae60",
                                  command=lambda g=game: self.action_push(g))
        btn_push.grid(row=0, column=1, padx=5, pady=10)

        btn_pull = ctk.CTkButton(row_frame, text="Pull from Cloud", 
                                  fg_color="#3498db", hover_color="#2980b9",
                                  command=lambda g=game: self.action_pull(g))
        btn_pull.grid(row=0, column=2, padx=5, pady=10)

    def action_push(self, game):
        if not self.manager.config["cloud_path"]:
            messagebox.showwarning("Warning", "Please select a Cloud/Sync Folder first.")
            return
        
        success, message = self.manager.push_save(game)
        if success:
            self.status_label.configure(text=f"Pushed {game['name']}")
            messagebox.showinfo("Success", message)
        else:
            messagebox.showerror("Error", message)

    def action_pull(self, game):
        if not self.manager.config["cloud_path"]:
            messagebox.showwarning("Warning", "Please select a Cloud/Sync Folder first.")
            return

        # Confirm before pulling as it overwrites
        confirm = messagebox.askyesno("Confirm Pull", f"This will overwrite your local save for {game['name']} with the version from the cloud. A backup will be created. Continue?")
        if not confirm:
            return

        success, message = self.manager.pull_save(game)
        if success:
            self.status_label.configure(text=f"Pulled {game['name']}")
            messagebox.showinfo("Success", message)
        else:
            messagebox.showerror("Error", message)

import customtkinter as ctk
from tkinter import filedialog, messagebox
from datetime import datetime

# Palette: Catppuccin-Mocha-style dark theme with Hyprland-like accent borders
BG = "#11111b"          # desktop background (the "gaps" between windows)
PANEL = "#1e1e2e"       # floating panels
CARD = "#181825"        # rows / inputs inside panels
CARD_HOVER = "#262637"
BORDER = "#313244"
ACCENT = "#89b4fa"      # active window border
ACCENT_2 = "#cba6f7"
TEXT = "#cdd6f4"
SUBTEXT = "#7f849c"
GREEN = "#a6e3a1"
RED = "#f38ba8"
YELLOW = "#f9e2af"

GAP = 12
RADIUS = 14


class PokeSyncGUI(ctk.CTk):
    def __init__(self, sync_manager):
        super().__init__()
        self.manager = sync_manager

        self.title("PokeSync")
        self.geometry("1000x720")
        self.minsize(820, 560)
        self.configure(fg_color=BG)
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.all_games = []
        self.setup_ui()
        self.refresh_games()
        self.tick_clock()

    # ---------- helpers ----------
    def panel(self, parent, active=False, **kw):
        """Rounded floating panel; the active one gets a Hyprland-style accent border."""
        return ctk.CTkFrame(parent, fg_color=PANEL, corner_radius=RADIUS,
                            border_width=2, border_color=ACCENT if active else BORDER, **kw)

    def pill(self, parent, text, color=TEXT, **kw):
        return ctk.CTkLabel(parent, text=text, text_color=color, fg_color=CARD,
                            corner_radius=10, padx=12, pady=4,
                            font=ctk.CTkFont(size=12, weight="bold"), **kw)

    def button(self, parent, text, command, color=ACCENT, **kw):
        kw.setdefault("height", 32)
        return ctk.CTkButton(parent, text=text, command=command, fg_color=color, hover_color=TEXT,
                             text_color=BG, corner_radius=10,
                             font=ctk.CTkFont(size=13, weight="bold"), **kw)

    # ---------- layout ----------
    def setup_ui(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.build_topbar()
        self.build_sidebar()
        self.build_main()
        self.build_statusbar()

    def build_topbar(self):
        """Waybar-style floating bar: title on the left, mode + clock on the right."""
        bar = ctk.CTkFrame(self, fg_color=PANEL, corner_radius=RADIUS, height=40,
                           border_width=1, border_color=BORDER)
        bar.grid(row=0, column=0, columnspan=2, sticky="ew", padx=GAP, pady=(GAP, 0))
        bar.grid_columnconfigure(1, weight=1)

        # macOS-style traffic lights (decorative)
        dots = ctk.CTkFrame(bar, fg_color="transparent")
        dots.grid(row=0, column=0, padx=(14, 8), pady=10)
        for c in (RED, YELLOW, GREEN):
            ctk.CTkLabel(dots, text="", width=12, height=12, fg_color=c, corner_radius=6).pack(side="left", padx=3)

        ctk.CTkLabel(bar, text="PokeSync", text_color=TEXT,
                     font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=1, sticky="w", padx=6)

        self.mode_pill = self.pill(bar, "", ACCENT)
        self.mode_pill.grid(row=0, column=2, padx=6, pady=6)
        self.clock_pill = self.pill(bar, "", SUBTEXT)
        self.clock_pill.grid(row=0, column=3, padx=(0, 10), pady=6)

    def build_sidebar(self):
        self.sidebar = self.panel(self, width=260)
        self.sidebar.grid(row=1, column=0, sticky="nsew", padx=(GAP, 0), pady=GAP)
        self.sidebar.grid_propagate(False)

        ctk.CTkLabel(self.sidebar, text="Settings", text_color=TEXT,
                     font=ctk.CTkFont(size=18, weight="bold"), anchor="w").pack(padx=20, pady=(20, 4), fill="x")
        ctk.CTkLabel(self.sidebar, text="Where your saves sync to", text_color=SUBTEXT,
                     font=ctk.CTkFont(size=12), anchor="w").pack(padx=20, pady=(0, 14), fill="x")

        initial_mode = "GitHub" if self.manager.config.get("sync_mode") == "github" else "Local Folder"
        self.mode_switch = ctk.CTkSegmentedButton(
            self.sidebar, values=["Local Folder", "GitHub"], command=self.change_sync_mode,
            fg_color=CARD, selected_color=ACCENT, selected_hover_color=ACCENT,
            unselected_color=CARD, unselected_hover_color=CARD_HOVER,
            text_color=TEXT, corner_radius=10)
        self.mode_switch.pack(padx=20, pady=(0, 16), fill="x")
        self.mode_switch.set(initial_mode)

        self.local_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.button(self.local_frame, "Browse Cloud Path", self.browse_cloud_path).pack(padx=20, pady=5, fill="x")

        self.github_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.entry_repo = self.create_setting_entry(self.github_frame, "Repo URL", "github_repo_url")
        self.entry_user = self.create_setting_entry(self.github_frame, "Username", "github_username")
        self.entry_token = self.create_setting_entry(self.github_frame, "Token / PAT", "github_token", show="*")

        self.update_settings_visibility(initial_mode)

    def build_main(self):
        self.main_frame = self.panel(self, active=True)
        self.main_frame.grid(row=1, column=1, sticky="nsew", padx=GAP, pady=GAP)
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=18, pady=(18, 10))
        header.grid_columnconfigure(0, weight=1)

        self.search_entry = ctk.CTkEntry(header, placeholder_text="🔍  Search games by name or ID…",
                                         fg_color=CARD, border_color=BORDER, text_color=TEXT,
                                         corner_radius=10, height=36)
        self.search_entry.grid(row=0, column=0, padx=(0, 10), sticky="ew")
        self.search_entry.bind("<KeyRelease>", lambda e: self.filter_games())

        self.button(header, "⟳  Refresh", self.refresh_games, width=110, height=36).grid(row=0, column=1)

        self.games_scroll = ctk.CTkScrollableFrame(self.main_frame, fg_color="transparent",
                                                   scrollbar_button_color=BORDER,
                                                   scrollbar_button_hover_color=SUBTEXT)
        self.games_scroll.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 12))
        self.games_scroll.grid_columnconfigure(0, weight=1)

    def build_statusbar(self):
        bar = ctk.CTkFrame(self, fg_color=PANEL, corner_radius=RADIUS, height=32,
                           border_width=1, border_color=BORDER)
        bar.grid(row=2, column=0, columnspan=2, sticky="ew", padx=GAP, pady=(0, GAP))
        self.status_label = ctk.CTkLabel(bar, text="Ready", text_color=SUBTEXT, anchor="w",
                                         font=ctk.CTkFont(size=12))
        self.status_label.pack(padx=16, pady=6, fill="x")

    def tick_clock(self):
        self.clock_pill.configure(text=datetime.now().strftime("%a %d %b  %H:%M"))
        self.after(15000, self.tick_clock)

    # ---------- settings ----------
    def create_setting_entry(self, parent, label_text, config_key, show=None):
        ctk.CTkLabel(parent, text=label_text, text_color=SUBTEXT, anchor="w",
                     font=ctk.CTkFont(size=12)).pack(padx=20, pady=(6, 0), fill="x")
        entry = ctk.CTkEntry(parent, show=show, fg_color=CARD, border_color=BORDER,
                             text_color=TEXT, corner_radius=10, height=34)
        entry.insert(0, self.manager.config.get(config_key, ""))
        entry.pack(padx=20, pady=(2, 4), fill="x")
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
        self.local_frame.pack_forget()
        self.github_frame.pack_forget()
        if mode == "GitHub":
            self.github_frame.pack(fill="x")
        else:
            self.local_frame.pack(fill="x")
        self.mode_pill.configure(text="  GitHub" if mode == "GitHub" else "  Local")

    def browse_cloud_path(self):
        path = filedialog.askdirectory()
        if path:
            self.manager.set_cloud_path(path)
            self.status_label.configure(text="Cloud path updated")

    # ---------- games list ----------
    def refresh_games(self):
        self.status_label.configure(text="Scanning for games...")
        self.update()
        self.all_games = self.manager.get_detected_games()
        self.filter_games()
        self.status_label.configure(text=f"Found {len(self.all_games)} games")

    def filter_games(self):
        search_term = self.search_entry.get().lower()

        for widget in self.games_scroll.winfo_children():
            widget.destroy()

        filtered = [g for g in self.all_games if search_term in g["name"].lower() or search_term in g["id"].lower()]

        if not filtered:
            ctk.CTkLabel(self.games_scroll, text="No games found matching your search.",
                         text_color=SUBTEXT).grid(row=0, column=0, pady=40)
            return

        for i, game in enumerate(filtered):
            self.create_game_row(game, i)

    def create_game_row(self, game, row_index):
        row_frame = ctk.CTkFrame(self.games_scroll, fg_color=CARD, corner_radius=12,
                                 border_width=1, border_color=BORDER)
        row_frame.grid(row=row_index, column=0, padx=8, pady=5, sticky="ew")
        row_frame.grid_columnconfigure(1, weight=1)

        # Coloured icon tile, like an app icon in a launcher
        tile_color = ACCENT_2 if game["is_pokemon"] else SUBTEXT
        tile = ctk.CTkFrame(row_frame, width=44, height=44, fg_color=tile_color, corner_radius=12)
        tile.grid(row=0, column=0, rowspan=2, padx=(12, 10), pady=12)
        tile.grid_propagate(False)
        ctk.CTkLabel(tile, text=game["name"][:1].upper(), text_color=BG,
                     font=ctk.CTkFont(size=18, weight="bold")).place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(row_frame, text=game["name"], text_color=TEXT if game["is_pokemon"] else SUBTEXT,
                     font=ctk.CTkFont(size=14, weight="bold"), anchor="w").grid(
            row=0, column=1, padx=4, pady=(12, 0), sticky="sw")
        ctk.CTkLabel(row_frame, text=f"ID: {game['id']}", text_color=SUBTEXT,
                     font=ctk.CTkFont(size=11), anchor="w").grid(
            row=1, column=1, padx=4, pady=(0, 12), sticky="nw")

        self.button(row_frame, "↑ Push", lambda g=game: self.action_push(g), color=GREEN, width=84).grid(
            row=0, column=2, rowspan=2, padx=4, pady=12)
        self.button(row_frame, "↓ Pull", lambda g=game: self.action_pull(g), color=ACCENT, width=84).grid(
            row=0, column=3, rowspan=2, padx=(4, 14), pady=12)

        # Hover highlight
        def set_bg(color):
            row_frame.configure(fg_color=color)
        for w in (row_frame, tile):
            w.bind("<Enter>", lambda e: set_bg(CARD_HOVER))
            w.bind("<Leave>", lambda e: set_bg(CARD))

    # ---------- actions (unchanged behaviour) ----------
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

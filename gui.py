import sys
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox

import customtkinter as ctk
from PIL import ImageTk

import glass
from emulators.base import KIND_STATES
from utils import format_time, human_size

ALL_EMULATORS = "All emulators"

# ---- glass theme -------------------------------------------------------------
TEXT = "#eef0ff"
SUBTEXT = "#a6abcb"
MUTED = "#7c82a6"
ACCENT = "#8b7cff"
ACCENT_HOVER = "#a398ff"
GREEN = "#5fe3a6"
AMBER = "#ffcf70"
BLUE = "#6cb6ff"
PINK = "#ff7ab6"
RED = "#ff6b81"
WHITE, BLACK = (255, 255, 255), (0, 0, 0)

GAP = 14          # wallpaper showing between panels
TOP_H = 60
STATUS_H = 40
SIDE_W = 290
INSET = 8         # widgets start this far inside a panel's rounded edge
BAR_RADIUS = 16
PANEL_RADIUS = 20
REF_SIZE = (1100, 760)  # panel tints are sampled from the wallpaper at this size

# check_conflict status -> (label, short label for the summary row, colour)
STATUS_CHIPS = {
    "up_to_date": ("Synced", "synced", GREEN),
    "local_newer": ("Local is newer", "local newer", AMBER),
    "no_remote": ("Not in cloud yet", "not uploaded", BLUE),
    "remote_newer": ("Cloud is newer", "cloud newer", PINK),
    "no_local": ("Only in cloud", "cloud only", PINK),
    "error": ("Can't check", "can't check", RED),
}
TILE_COLOURS = ["#8b7cff", "#ff7ab6", "#5fe3a6", "#6cb6ff", "#ffcf70", "#5ee7f7", "#ff9f6b"]


def layout(width, height):
    """Panel rectangles (x0, y0, x1, y1) for a window of this logical size."""
    body_top, body_bottom = GAP + TOP_H + GAP, height - GAP - STATUS_H - GAP
    return {
        "top": (GAP, GAP, width - GAP, GAP + TOP_H),
        "side": (GAP, body_top, GAP + SIDE_W, body_bottom),
        "main": (GAP + SIDE_W + GAP, body_top, width - GAP, body_bottom),
        "status": (GAP, height - GAP - STATUS_H, width - GAP, height - GAP),
    }


RADII = {"top": BAR_RADIUS, "side": PANEL_RADIUS, "main": PANEL_RADIUS, "status": BAR_RADIUS}


class Palette:
    """Colours derived from one panel's glass tint (widgets inside it must match it)."""

    def __init__(self, fill):
        self.rgb = fill
        self.fill = glass.to_hex(fill)
        self.card = glass.to_hex(glass.mix(fill, WHITE, 0.06))
        self.card_hover = glass.to_hex(glass.mix(fill, WHITE, 0.11))
        self.edge = glass.to_hex(glass.mix(fill, WHITE, 0.14))
        self.input = glass.to_hex(glass.mix(fill, BLACK, 0.30))
        self.ghost = glass.to_hex(glass.mix(fill, WHITE, 0.09))
        self.ghost_hover = glass.to_hex(glass.mix(fill, WHITE, 0.18))


class PokeSyncGUI(ctk.CTk):
    def __init__(self, sync_manager):
        super().__init__()
        self.manager = sync_manager

        self.title("PokeSync - Emulator Save Sync")
        self.geometry("%dx%d" % REF_SIZE)
        self.minsize(900, 600)
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        wall = glass.wallpaper(*REF_SIZE)
        self.pal = {name: Palette(glass.glass_fill(wall, rect)) for name, rect in layout(*REF_SIZE).items()}
        self.configure(fg_color=glass.to_hex(glass.BASE_TOP))

        self.font = {
            "title": ctk.CTkFont(size=18, weight="bold"),
            "h": ctk.CTkFont(size=15, weight="bold"),
            "section": ctk.CTkFont(size=11, weight="bold"),
            "body": ctk.CTkFont(size=13),
            "small": ctk.CTkFont(size=12),
            "button": ctk.CTkFont(size=13, weight="bold"),
        }

        self.all_games = []
        self.remote_only = []
        self.statuses = {}  # game.key -> (status, message), filled on refresh
        self._bg_size = None
        self._bg_job = None

        self.setup_ui()
        self.bind("<Configure>", self._on_configure)
        self._relayout()
        self.refresh_games()

    # ---- glass layout ----------------------------------------------------
    def _on_configure(self, event):
        if event.widget is self:
            self._relayout()

    def _relayout(self):
        scale = self._get_window_scaling()
        width, height = max(1, self.winfo_width()), max(1, self.winfo_height())
        if width < 50:  # not mapped yet
            width, height = (round(v * scale) for v in REF_SIZE)
        rects = layout(width / scale, height / scale)
        for name, holder in self.holders.items():
            x0, y0, x1, y1 = rects[name]
            holder.place(x=round((x0 + INSET) * scale), y=round((y0 + INSET) * scale),
                         width=round((x1 - x0 - 2 * INSET) * scale), height=round((y1 - y0 - 2 * INSET) * scale))
        if (width, height) != self._bg_size:
            if self._bg_job:
                self.after_cancel(self._bg_job)
            self._bg_job = self.after(60, self._paint_backdrop)

    def _paint_backdrop(self):
        self._bg_job = None
        scale = self._get_window_scaling()
        width, height = self.winfo_width(), self.winfo_height()
        rects = layout(width / scale, height / scale)
        panels = [(rects[n], RADII[n], self.pal[n].rgb) for n in rects]
        self._bg_photo = ImageTk.PhotoImage(glass.render(width, height, panels, scale))
        self.backdrop.configure(image=self._bg_photo)
        self._bg_size = (width, height)

    def panel(self, name):
        """Flat content area for one glass panel; its widgets go in the returned frame."""
        pal = self.pal[name]
        holder = tk.Frame(self, bg=pal.fill, bd=0, highlightthickness=0)
        self.holders[name] = holder
        frame = ctk.CTkFrame(holder, fg_color=pal.fill, corner_radius=0)
        frame.pack(fill="both", expand=True)
        return frame

    # ---- widget helpers --------------------------------------------------
    def button(self, parent, pal, text, command, primary=False, colour=None, **kw):
        kw.setdefault("height", 36)
        if primary or colour:
            fg = colour or ACCENT
            return ctk.CTkButton(parent, text=text, command=command, fg_color=fg,
                                 hover_color=ACCENT_HOVER if not colour else glass.to_hex(
                                     glass.mix(tuple(int(fg[i:i + 2], 16) for i in (1, 3, 5)), WHITE, 0.2)),
                                 text_color="#14112b", corner_radius=12, font=self.font["button"], **kw)
        return ctk.CTkButton(parent, text=text, command=command, fg_color=pal.ghost, hover_color=pal.ghost_hover,
                             border_width=1, border_color=pal.edge, text_color=TEXT, corner_radius=12,
                             font=self.font["button"], **kw)

    def entry(self, parent, pal, **kw):
        kw.setdefault("height", 36)
        return ctk.CTkEntry(parent, fg_color=pal.input, border_color=pal.edge, border_width=1, text_color=TEXT,
                            placeholder_text_color=MUTED, corner_radius=12, font=self.font["body"], **kw)

    def section(self, parent, text):
        ctk.CTkLabel(parent, text=text.upper(), text_color=MUTED, font=self.font["section"],
                     anchor="w").pack(padx=16, pady=(18, 6), fill="x")

    def chip(self, parent, text, colour, bg_rgb):
        rgb = tuple(int(colour[i:i + 2], 16) for i in (1, 3, 5))
        return ctk.CTkLabel(parent, text=f"● {text}", text_color=colour, font=self.font["small"],
                            fg_color=glass.to_hex(glass.mix(bg_rgb, rgb, 0.16)), corner_radius=10,
                            height=24, padx=8)

    # ---- layout ----------------------------------------------------------
    def setup_ui(self):
        self.backdrop = tk.Label(self, bd=0, highlightthickness=0, bg=glass.to_hex(glass.BASE_TOP))
        self.backdrop.place(x=0, y=0, relwidth=1, relheight=1)
        self.holders = {}

        self.build_topbar()
        self.build_sidebar()
        self.build_main()
        self.build_statusbar()

        mod = "Command" if sys.platform == "darwin" else "Control"
        self.bind_all(f"<{mod}-f>", lambda e: self.search_entry.focus_set())
        self.bind_all(f"<{mod}-r>", lambda e: self.refresh_games())
        self.search_entry.bind("<Escape>", self.clear_search)

    def clear_search(self, _event=None):
        self.search_entry.delete(0, "end")
        self.focus_set()
        self.search_entry._activate_placeholder()  # CTkEntry only restores it on focus-out otherwise
        self.filter_games()

    def build_topbar(self):
        pal = self.pal["top"]
        bar = self.panel("top")
        bar.grid_columnconfigure(1, weight=1)
        bar.grid_rowconfigure(0, weight=1)

        logo = ctk.CTkLabel(bar, text="⇅", width=34, height=34, corner_radius=10, fg_color=ACCENT,
                            text_color="#14112b", font=ctk.CTkFont(size=18, weight="bold"))
        logo.grid(row=0, column=0, padx=(8, 10))
        titles = ctk.CTkFrame(bar, fg_color="transparent")
        titles.grid(row=0, column=1, sticky="w")
        ctk.CTkLabel(titles, text="PokeSync", text_color=TEXT, font=self.font["title"], anchor="w").pack(anchor="w")
        ctk.CTkLabel(titles, text="Your emulator saves, on every computer", text_color=SUBTEXT,
                     font=self.font["small"], anchor="w", height=14).pack(anchor="w")

        self.mode_pill = ctk.CTkLabel(bar, text="", text_color=TEXT, fg_color=pal.ghost, corner_radius=10,
                                      height=30, padx=12, font=self.font["small"])
        self.mode_pill.grid(row=0, column=2, padx=6)
        self.btn_refresh = self.button(bar, pal, "↻  Refresh", self.refresh_games, width=110)
        self.btn_refresh.grid(row=0, column=3, padx=6)
        self.btn_sync_all = self.button(bar, pal, "↓  Sync All", self.sync_all, primary=True, width=120)
        self.btn_sync_all.grid(row=0, column=4, padx=(6, 8))

    def build_sidebar(self):
        pal = self.pal["side"]
        panel = self.panel("side")
        tips = "⌘F search   ·   ⌘R refresh" if sys.platform == "darwin" else "Ctrl+F search   ·   Ctrl+R refresh"
        ctk.CTkLabel(panel, text=tips, text_color=MUTED, font=self.font["small"]).pack(side="bottom", pady=10)
        # Scrolls when the GitHub fields don't fit a short window
        side = ctk.CTkScrollableFrame(panel, fg_color="transparent", scrollbar_button_color=pal.ghost,
                                      scrollbar_button_hover_color=pal.edge)
        side.pack(fill="both", expand=True)

        self.section(side, "Sync destination")
        initial_mode = "GitHub" if self.manager.config.get("sync_mode") == "github" else "Local Folder"
        self.mode_switch = ctk.CTkSegmentedButton(
            side, values=["Local Folder", "GitHub"], command=self.change_sync_mode, height=34,
            fg_color=pal.input, selected_color=ACCENT, selected_hover_color=ACCENT_HOVER,
            unselected_color=pal.input, unselected_hover_color=pal.ghost, text_color=TEXT,
            corner_radius=12, font=self.font["button"])
        self.mode_switch.pack(padx=16, pady=(0, 10), fill="x")
        self.mode_switch.set(initial_mode)

        self.settings_slot = ctk.CTkFrame(side, fg_color="transparent")
        self.settings_slot.pack(fill="x")

        self.local_frame = ctk.CTkFrame(self.settings_slot, fg_color="transparent")
        self.cloud_path_label = ctk.CTkLabel(self.local_frame, text="", text_color=SUBTEXT, font=self.font["small"],
                                             anchor="w", justify="left", wraplength=SIDE_W - 2 * INSET - 40)
        self.cloud_path_label.pack(padx=16, pady=(0, 6), fill="x")
        self.button(self.local_frame, pal, "📁  Choose Cloud Folder", self.browse_cloud_path).pack(
            padx=16, pady=(0, 4), fill="x")

        self.github_frame = ctk.CTkFrame(self.settings_slot, fg_color="transparent")
        self.entry_repo = self.create_setting_entry(self.github_frame, "Repo URL", "github_repo_url")
        self.entry_user = self.create_setting_entry(self.github_frame, "Username", "github_username")
        self.entry_token = self.create_setting_entry(self.github_frame, "Token / PAT", "github_token", show="•")

        self.section(side, "Finding games")
        self.button(side, pal, "＋  Add Scan Folder", self.add_scan_folder).pack(padx=16, pady=4, fill="x")
        self.button(side, pal, "☰  Manage Scan Folders", self.manage_scan_folders).pack(padx=16, pady=4, fill="x")
        self.scan_info = ctk.CTkLabel(side, text="", text_color=SUBTEXT, font=self.font["small"], anchor="w",
                                      justify="left", wraplength=SIDE_W - 2 * INSET - 40)
        self.scan_info.pack(padx=16, pady=(6, 8), fill="x")
        self.states_switch = ctk.CTkSwitch(side, text="Include save states", command=self.toggle_states,
                                           text_color=TEXT, font=self.font["body"], fg_color=pal.input,
                                           progress_color=ACCENT, button_color=TEXT, button_hover_color="#ffffff")
        if self.manager.config.get("include_savestates"):
            self.states_switch.select()
        self.states_switch.pack(padx=16, pady=(4, 12), anchor="w")

        self.update_settings_visibility(initial_mode)
        self.update_scan_info()
        self.update_cloud_path_label()

    def build_main(self):
        pal = self.pal["main"]
        main = self.panel("main")
        main.grid_columnconfigure(0, weight=1)
        main.grid_rowconfigure(2, weight=1)

        header = ctk.CTkFrame(main, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 6))
        header.grid_columnconfigure(0, weight=1)
        self.search_entry = self.entry(header, pal, placeholder_text="🔍   Search by game, ID or emulator")
        self.search_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self.search_entry.bind("<KeyRelease>", lambda e: self.filter_games())
        self.emulator_filter = ctk.CTkOptionMenu(
            header, values=[ALL_EMULATORS], width=190, height=36, corner_radius=12,
            fg_color=pal.input, button_color=pal.input, button_hover_color=pal.ghost, text_color=TEXT,
            dropdown_fg_color=pal.fill, dropdown_hover_color=pal.ghost_hover, dropdown_text_color=TEXT,
            font=self.font["body"], dropdown_font=self.font["body"], command=lambda _v: self.filter_games())
        self.emulator_filter.grid(row=0, column=1)

        self.summary = ctk.CTkFrame(main, fg_color="transparent")
        self.summary.grid(row=1, column=0, sticky="ew", padx=12, pady=(4, 4))

        self.games_scroll = ctk.CTkScrollableFrame(main, fg_color="transparent", scrollbar_button_color=pal.edge,
                                                   scrollbar_button_hover_color=MUTED)
        self.games_scroll.grid(row=2, column=0, sticky="nsew", padx=4, pady=(0, 6))
        self.games_scroll.grid_columnconfigure(0, weight=1)

    def build_statusbar(self):
        bar = self.panel("status")
        self.status_label = ctk.CTkLabel(bar, text="Ready", text_color=SUBTEXT, anchor="w", font=self.font["small"])
        self.status_label.pack(side="left", padx=10, fill="x", expand=True)
        self.refreshed_label = ctk.CTkLabel(bar, text="", text_color=MUTED, font=self.font["small"])
        self.refreshed_label.pack(side="right", padx=10)

    # ---- settings --------------------------------------------------------
    def create_setting_entry(self, parent, label_text, config_key, show=None):
        ctk.CTkLabel(parent, text=label_text, text_color=SUBTEXT, anchor="w",
                     font=self.font["small"]).pack(padx=16, pady=(4, 2), fill="x")
        entry = self.entry(parent, self.pal["side"], show=show)
        entry.insert(0, self.manager.config.get(config_key, ""))
        entry.pack(padx=16, pady=(0, 4), fill="x")
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
        self.mode_pill.configure(text="●  GitHub" if mode == "GitHub" else "●  Local folder")

    def update_cloud_path_label(self):
        path = self.manager.config.get("cloud_path")
        self.cloud_path_label.configure(text=path or "No cloud folder chosen yet. Pick one in Dropbox, "
                                                     "OneDrive or Google Drive.")

    def browse_cloud_path(self):
        path = filedialog.askdirectory()
        if path:
            self.manager.set_cloud_path(path)
            self.update_cloud_path_label()
            self.status_label.configure(text="Cloud path updated")

    # ---- scan folders and save states ------------------------------------
    def update_scan_info(self):
        count = len(self.manager.config.get("scan_folders", []))
        self.scan_info.configure(
            text=f"{count} scan folder(s). Known emulators are found automatically; add folders "
                 f"that hold your ROMs and saves for the rest.")

    def add_scan_folder(self):
        path = filedialog.askdirectory(title="Folder to scan for games and saves")
        if path:
            self.manager.add_scan_folder(path)
            self.update_scan_info()
            self.refresh_games()

    def manage_scan_folders(self):
        pal = self.pal["side"]
        dialog = ctk.CTkToplevel(self)
        dialog.title("Scan Folders")
        dialog.geometry("580x380")
        dialog.configure(fg_color=pal.fill)
        dialog.transient(self)
        ctk.CTkLabel(dialog, text="Scan folders", text_color=TEXT, font=self.font["h"], anchor="w").pack(
            padx=20, pady=(18, 0), fill="x")
        ctk.CTkLabel(dialog, text="PokeSync looks in these folders for ROMs and the saves next to them.",
                     text_color=SUBTEXT, font=self.font["small"], anchor="w").pack(padx=20, pady=(2, 8), fill="x")
        frame = ctk.CTkScrollableFrame(dialog, fg_color="transparent", scrollbar_button_color=pal.edge)
        frame.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        frame.grid_columnconfigure(0, weight=1)

        def render():
            for widget in frame.winfo_children():
                widget.destroy()
            folders = self.manager.config.get("scan_folders", [])
            if not folders:
                ctk.CTkLabel(frame, text="No scan folders yet.", text_color=SUBTEXT).grid(row=0, column=0, pady=20)
            for i, folder in enumerate(folders):
                card = ctk.CTkFrame(frame, fg_color=pal.card, corner_radius=12, border_width=1, border_color=pal.edge)
                card.grid(row=i, column=0, sticky="ew", padx=6, pady=4)
                card.grid_columnconfigure(0, weight=1)
                ctk.CTkLabel(card, text="📁  " + folder, text_color=TEXT, anchor="w", font=self.font["body"]).grid(
                    row=0, column=0, sticky="ew", padx=12, pady=10)
                self.button(card, pal, "Remove", lambda f=folder: remove(f), colour=RED, width=84, height=30).grid(
                    row=0, column=1, padx=10)

        def remove(folder):
            self.manager.remove_scan_folder(folder)
            self.update_scan_info()
            render()
            self.refresh_games()

        render()
        return dialog

    def toggle_states(self):
        self.manager.set_config("include_savestates", bool(self.states_switch.get()))
        self.refresh_games()

    # ---- game list -------------------------------------------------------
    def refresh_games(self):
        self.status_label.configure(text="Scanning for games...")
        self.update()
        ok, msg = self.manager.refresh_remote()
        self.all_games = self.manager.get_detected_games()
        self.remote_only = self.manager.get_remote_only_entries(self.all_games)
        # Checked once here, not on every keystroke in the search box
        self.statuses = {g.key: self.manager.check_conflict(g) for g in self.all_games}
        self.statuses.update({g.key: ("no_local", "") for g in self.remote_only})

        names = sorted({g.emulator_name for g in self.all_games + self.remote_only})
        current = self.emulator_filter.get()
        self.emulator_filter.configure(values=[ALL_EMULATORS] + names)
        if current not in names:
            self.emulator_filter.set(ALL_EMULATORS)

        self.filter_games()
        status = f"Found {len(self.all_games)} saves"
        if self.remote_only:
            status += f", {len(self.remote_only)} only in the cloud"
        if not ok:
            status += f" (cloud not reachable: {msg})"
        self.status_label.configure(text=status)
        self.refreshed_label.configure(text="Refreshed " + datetime.now().strftime("%H:%M"))

    def render_summary(self):
        for widget in self.summary.winfo_children():
            widget.destroy()
        counts = {}
        for status, _ in self.statuses.values():
            counts[status] = counts.get(status, 0) + 1
        bg = self.pal["main"].rgb
        self.summary.update_idletasks()
        room = self.summary.winfo_width() if self.summary.winfo_width() > 50 else 700
        line, used = None, 0
        for status in ("up_to_date", "local_newer", "remote_newer", "no_remote", "no_local", "error"):
            if not counts.get(status):
                continue
            _, short, colour = STATUS_CHIPS[status]
            text = f"{counts[status]} {short}"
            # Chips aren't drawn yet, so measure the text; a chip is 36 wider than its text, plus the 6 gap
            width = self.font["small"].measure(f"● {text}") + round(42 * ctk.ScalingTracker.get_widget_scaling(self))
            if line is None or used + width > room:  # wrap rather than cut chips off
                line, used = ctk.CTkFrame(self.summary, fg_color="transparent"), 0
                line.pack(fill="x", pady=2)
            self.chip(line, text, colour, bg).pack(side="left", padx=(0, 6))
            used += width

    def filter_games(self):
        search_term = self.search_entry.get().lower().strip()
        wanted = self.emulator_filter.get()

        for widget in self.games_scroll.winfo_children():
            widget.destroy()
        self.render_summary()

        def matches(g):
            if wanted != ALL_EMULATORS and g.emulator_name != wanted:
                return False
            return any(search_term in text.lower() for text in (g.name, g.game_id, g.emulator_name))

        filtered = [g for g in self.all_games + self.remote_only if matches(g)]

        if not filtered:
            empty = ctk.CTkFrame(self.games_scroll, fg_color="transparent")
            empty.grid(row=0, column=0, pady=60)
            ctk.CTkLabel(empty, text="🎮", font=ctk.CTkFont(size=40)).pack()
            ctk.CTkLabel(empty, text="No games found", text_color=TEXT, font=self.font["h"]).pack(pady=(6, 2))
            ctk.CTkLabel(empty, text="Add a scan folder, or run your emulator once so it creates a save.",
                         text_color=SUBTEXT, font=self.font["small"]).pack()
            return

        for i, game in enumerate(filtered):
            self.create_game_row(game, i)

    def describe(self, game):
        parts = [game.emulator_name]
        if game.kind == KIND_STATES:
            parts.append("save states")
        meta = game.metadata
        if meta.get("platform") and meta["platform"] not in game.emulator_name:
            parts.append(meta["platform"])
        if meta.get("region"):
            parts.append(str(meta["region"]))
        if not game.remote_only:
            if meta.get("size") is not None:
                parts.append(human_size(meta["size"]))
            if meta.get("modified"):
                parts.append("modified " + format_time(meta["modified"]))
        return "  ·  ".join(parts)

    def create_game_row(self, game, row_index):
        pal = self.pal["main"]
        card = ctk.CTkFrame(self.games_scroll, fg_color=pal.card, corner_radius=14,
                            border_width=1, border_color=pal.edge)
        card.grid(row=row_index, column=0, padx=8, pady=5, sticky="ew")
        card.grid_columnconfigure(1, weight=1)

        tile_colour = TILE_COLOURS[sum(map(ord, game.emulator)) % len(TILE_COLOURS)]
        tile = ctk.CTkLabel(card, text=game.name[:1].upper(), width=46, height=46, corner_radius=13,
                            fg_color=tile_colour, text_color="#14112b", font=ctk.CTkFont(size=19, weight="bold"))
        tile.grid(row=0, column=0, rowspan=3, padx=(12, 12), pady=12)

        title = ctk.CTkFrame(card, fg_color="transparent")
        title.grid(row=0, column=1, sticky="sw", pady=(10, 0))
        name = game.name + ("  ★" if game.is_pokemon else "")
        ctk.CTkLabel(title, text=name, text_color=TEXT, font=self.font["h"], anchor="w").pack(side="left")
        status, _ = self.statuses.get(game.key, ("error", ""))
        label, _, colour = STATUS_CHIPS.get(status, ("Unknown", "", MUTED))
        self.chip(title, label, colour, glass.mix(pal.rgb, WHITE, 0.06)).pack(side="left", padx=10)
        ctk.CTkLabel(card, text=self.describe(game), text_color=SUBTEXT, font=self.font["small"], anchor="w",
                     height=16).grid(row=1, column=1, sticky="w")

        last_sync = self.manager.last_sync(game) or "Never"
        if last_sync != "Never":
            try:
                last_sync = datetime.fromisoformat(last_sync).strftime("%Y-%m-%d %H:%M")
            except Exception:
                pass
        foot = (f"ID {game.game_id}  ·  restores to {game.dest_dir()}" if game.remote_only
                else f"ID {game.game_id}  ·  last synced {last_sync}")
        ctk.CTkLabel(card, text=foot, text_color=MUTED, font=self.font["small"], anchor="w", height=16).grid(
            row=2, column=1, sticky="nw", pady=(0, 10))

        buttons = ctk.CTkFrame(card, fg_color="transparent")
        buttons.grid(row=0, column=2, rowspan=3, padx=(4, 12))
        if not game.remote_only:
            self.button(buttons, pal, "↑  Push", lambda g=game: self.action_push(g), width=92).pack(
                side="left", padx=4)
        self.button(buttons, pal, "↓  Restore" if game.remote_only else "↓  Pull",
                    lambda g=game: self.action_pull(g), primary=True, width=100).pack(side="left", padx=4)

        def hover(on):
            card.configure(fg_color=pal.card_hover if on else pal.card)
        for widget in (card, tile):
            widget.bind("<Enter>", lambda e: hover(True), add="+")
            widget.bind("<Leave>", lambda e: hover(False), add="+")

    # ---- actions ---------------------------------------------------------
    def action_push(self, game):
        self.status_label.configure(text=f"Checking conflicts for {game.name}...")
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

        self.status_label.configure(text=f"Pushing {game.name}...")
        self.update()
        success, message = self.manager.push_save(game)
        if success:
            self.status_label.configure(text=f"Pushed {game.name} successfully.")
            messagebox.showinfo("Success", message)
            self.refresh_games()
        else:
            self.status_label.configure(text="Push failed.")
            messagebox.showerror("Error", message)

    def action_pull(self, game):
        self.status_label.configure(text=f"Checking conflicts for {game.name}...")
        self.update()

        if game.remote_only:
            where = game.dest_dir()
            confirm = messagebox.askyesno("Restore Save", f"Restore {game.name} from the cloud to:\n\n{where}\n\nContinue?")
            if not confirm:
                return
        else:
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
                confirm = messagebox.askyesno("Confirm Pull", f"Overwrite local save for {game.name}? A backup will be created.")
                if not confirm:
                    return

        self.status_label.configure(text=f"Pulling {game.name}...")
        self.update()
        success, message = self.manager.pull_save(game)
        if success:
            self.status_label.configure(text=f"Pulled {game.name} successfully.")
            messagebox.showinfo("Success", message)
            self.refresh_games()
        else:
            self.status_label.configure(text="Pull failed.")
            messagebox.showerror("Error", message)

    def sync_all(self):
        self.status_label.configure(text="Checking all games for updates...")
        self.update()

        to_pull = []
        for game in self.all_games:
            status, _ = self.manager.check_conflict(game)
            if status in ["remote_newer", "no_local"]:
                to_pull.append(game)

        if not to_pull:
            messagebox.showinfo("Sync All", "All games are already up to date or have local changes.")
            self.status_label.configure(text="Sync All: Nothing to pull.")
            return

        confirm = messagebox.askyesno("Sync All", f"Found {len(to_pull)} games with newer remote saves.\n\nWould you like to PULL all of them now? (Backups will be created)")
        if not confirm:
            return

        success_count = 0
        for game in to_pull:
            self.status_label.configure(text=f"Syncing {game.name}...")
            self.update()
            success, _ = self.manager.pull_save(game)
            if success:
                success_count += 1

        self.refresh_games()
        messagebox.showinfo("Sync All Complete", f"Successfully updated {success_count} of {len(to_pull)} games.")

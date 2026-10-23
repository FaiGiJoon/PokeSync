"""Capture screenshots of the real PokeSync window (macOS) using DemoManager data.

Usage (from repo root):  python tools/screenshots.py [--out docs/screenshots]
"""
import argparse
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))


def pump(widget, ms=400):
    """Run the Tk event loop for ~ms milliseconds without mainloop."""
    end = time.time() + ms / 1000.0
    while time.time() < end:
        widget.update()
        time.sleep(0.01)
    widget.update_idletasks()


def capture(app, out_path):
    """Screenshot the window (incl. title bar) to out_path. Works for CTk and CTkToplevel."""
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    app.update()
    app.lift()
    try:
        app.attributes("-topmost", True)
    except Exception:
        pass
    try:
        app.focus_force()
    except Exception:
        pass
    pump(app, 400)
    try:
        title_h = max(0, app.winfo_rooty() - app.winfo_y())
        x, y = app.winfo_rootx(), app.winfo_rooty() - title_h
        w, h = app.winfo_width(), app.winfo_height() + title_h
        if y < 0:  # window under the menu bar; fall back to client area
            y, h = app.winfo_rooty(), app.winfo_height()
        subprocess.run(["screencapture", "-x", "-R", f"{x},{y},{w},{h}", out_path], check=True)
    finally:
        try:
            app.attributes("-topmost", False)
        except Exception:
            pass
    return out_path


def run(scenes, out_dir, size="1100x700"):
    """scenes: list of (name, setup_fn(app) -> optional widget to capture instead of app)."""
    from gui import PokeSyncGUI
    from demo_manager import DemoManager

    app = PokeSyncGUI(DemoManager())
    try:
        app.geometry(f"{size}+60+40")
        pump(app, 800)
        paths = []
        for name, setup in scenes:
            target = setup(app) or app
            pump(app, 600)
            paths.append(capture(target, os.path.join(out_dir, f"{name}.png")))
    finally:
        try:
            app.destroy()
        except Exception:
            pass
    return paths


def _search(app, text, emulator):
    if text:
        app.search_entry.delete(0, "end")
        app.search_entry.insert(0, text)
    else:
        app.clear_search()
    app.emulator_filter.set(emulator)
    app.filter_games()


def _github_and_states(app):
    _search(app, "", "All emulators")
    app.mode_switch.set("GitHub")
    app.change_sync_mode("GitHub")
    app.states_switch.select()
    app.toggle_states()


# The four screenshots used in the README / PRs
DEFAULT_SCENES = [
    ("1-library", lambda app: None),
    ("2-search-restore", lambda app: _search(app, "pok", "melonDS")),
    ("3-github-savestates", _github_and_states),
    ("4-scan-folders", lambda app: app.manage_scan_folders()),
]


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="docs/screenshots")
    args = ap.parse_args()
    for p in run(DEFAULT_SCENES, args.out):
        print(p)

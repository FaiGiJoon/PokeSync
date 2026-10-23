"""In-memory stand-in for SyncManager, for demos and screenshots (no disk, no network)."""
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from emulators.base import SaveEntry, KIND_SAVE, KIND_STATES  # noqa: E402

_STATUS = {
    "citra/0004000000055D00/save": "up_to_date",
    "citra/000400000011C500/save": "local_newer",
    "citra/00040000001B5100/save": "remote_newer",
    "mgba/BPEE/save": "up_to_date",
    "melonds/CPUE/save": "local_newer",
    "dolphin/GC6E/save": "no_remote",
    "duckstation/SCUS-94900/save": "error",
    "retroarch/BYTE/save": "remote_newer",
}


class DemoManager:
    def __init__(self):
        now = time.time()
        self._now = now
        self.config = {
            "sync_mode": "local",
            "cloud_path": "/Users/demo/Dropbox/PokeSync",
            "github_repo_url": "https://github.com/demo/pokesync-saves.git",
            "github_username": "demo",
            "github_token": "",
            "scan_folders": ["/Users/demo/Games/Emulation", "/Users/demo/Documents/Saves"],
            "include_savestates": False,
            "last_sync": {},
        }
        self._games = self._build(now)
        for i, g in enumerate(self._games):
            if g.kind == KIND_SAVE and _STATUS.get(g.key) not in (None, "no_remote", "error"):
                self.config["last_sync"][g.key] = (
                    datetime.fromtimestamp(now) - timedelta(hours=3 + i * 7)).replace(microsecond=0).isoformat()

    # ---------------------------------------------------------------- data
    @staticmethod
    def _build(now):
        def e(emu, emu_name, gid, name, pk, plat, region, size, ago_h, path, kind=KIND_SAVE):
            return SaveEntry(
                emulator=emu, emulator_name=emu_name, game_id=gid, name=name, kind=kind,
                paths=[path], is_pokemon=pk,
                metadata={"platform": plat, "region": region, "size": size,
                          "modified": now - ago_h * 3600})
        home = "/Users/demo/Library/Application Support"
        return [
            e("citra", "Citra", "0004000000055D00", "Pokémon X", True, "Nintendo 3DS", "EUR", 1048576, 2,
              f"{home}/Citra/sdmc/Nintendo 3DS/00000000000000000000000000000000/00000000000000000000000000000000/title/00040000/00055d00/data/00000001"),
            e("citra", "Citra", "000400000011C500", "Pokémon Alpha Sapphire", True, "Nintendo 3DS", "EUR", 1048576, 5,
              f"{home}/Citra/sdmc/title/00040000/0011c500/data/00000001"),
            e("citra", "Citra", "00040000001B5100", "Pokémon Ultra Moon", True, "Nintendo 3DS", "USA", 1048576, 26,
              f"{home}/Citra/sdmc/title/00040000/001b5100/data/00000001"),
            e("mgba", "mGBA", "BPEE", "Pokémon Emerald", True, "GBA", "USA", 131072, 9,
              "/Users/demo/Games/GBA/Pokemon Emerald.sav"),
            e("melonds", "melonDS", "CPUE", "Pokémon Platinum", True, "NDS", "USA", 524288, 50,
              "/Users/demo/Games/NDS/Pokemon Platinum.sav"),
            e("dolphin", "Dolphin", "GC6E", "Pokémon Colosseum", True, "GameCube", "USA", 524288, 120,
              f"{home}/Dolphin/GC/USA/Card A"),
            e("duckstation", "DuckStation", "SCUS-94900", "Crash Bandicoot", False, "PS1", "USA", 131072, 300,
              "/Users/demo/Documents/DuckStation/memcards/shared_card_1.mcd"),
            e("retroarch", "RetroArch", "BYTE", "Pokémon Crystal", True, "GBC", "USA", 32768, 72,
              "/Users/demo/Games/RetroArch/saves/Pokemon Crystal.srm"),
            e("mgba", "mGBA", "BPEE", "Pokémon Emerald", True, "GBA", "USA", 400000, 9,
              "/Users/demo/Games/GBA/states/Pokemon Emerald.ss1", kind=KIND_STATES),
        ]

    # -------------------------------------------------------------- config
    def set_config(self, key, value):
        self.config[key] = value

    def set_cloud_path(self, path):
        self.set_config("cloud_path", path)

    def add_scan_folder(self, path):
        folders = list(self.config.get("scan_folders", []))
        path = os.path.abspath(path)
        if path not in folders:
            folders.append(path)
            self.config["scan_folders"] = folders

    def remove_scan_folder(self, path):
        self.config["scan_folders"] = [p for p in self.config.get("scan_folders", []) if p != path]

    # ------------------------------------------------------------- listing
    def get_detected_games(self):
        games = list(self._games)
        if not self.config.get("include_savestates"):
            games = [g for g in games if g.kind != KIND_STATES]
        return games

    def get_remote_only_entries(self, local_games):
        entry = SaveEntry(
            emulator="melonds", emulator_name="melonDS", game_id="IPKE", name="Pokémon HeartGold",
            kind=KIND_SAVE, paths=[], is_pokemon=True, remote_only=True,
            metadata={"platform": "NDS", "region": "USA", "size": 524288,
                      "modified": self._now - 6 * 86400},
            dest=Path("/Users/demo/Games/NDS/saves"))
        local_keys = {g.key for g in local_games}
        return [] if entry.key in local_keys else [entry]

    def refresh_remote(self):
        return True, "Up to date."

    # ---------------------------------------------------------------- sync
    def check_conflict(self, game):
        status = _STATUS.get(game.key, "up_to_date")
        msgs = {
            "up_to_date": "Saves are synchronized.",
            "local_newer": "Local save is newer (" + datetime.fromtimestamp(
                game.metadata.get("modified", self._now)).strftime("%Y-%m-%d %H:%M") + ")",
            "remote_newer": "Remote save is newer (" + datetime.fromtimestamp(
                self._now - 3600).strftime("%Y-%m-%d %H:%M") + ")",
            "no_remote": "Remote save does not exist.",
            "error": "Cloud path not set.",
        }
        if getattr(game, "remote_only", False):
            return "no_local", "Local save does not exist."
        return status, msgs[status]

    def push_save(self, game):
        return True, "Demo: nothing was written."

    def pull_save(self, game):
        return True, "Demo: nothing was written."

    def last_sync(self, game):
        return self.config["last_sync"].get(game.key)

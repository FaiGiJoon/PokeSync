"""Citra and its descendants (Azahar, Lime3DS): Nintendo 3DS saves and save states."""
from __future__ import annotations

import os
from pathlib import Path

from utils import is_pokemon_text
from .base import Emulator, SaveEntry, KIND_SAVE, KIND_STATES, unique_id
from .names_3ds import GAME_NAMES

ZERO_ID = "0" * 32
TYPE_FOLDERS = ("00040000", "00040002")

# id, display name, (windows/mac folder name, linux folder name), flatpak id, env override
VARIANTS = [
    ("citra", "Citra", ("Citra", "citra-emu"), "org.citra_emu.citra", "CITRA_PATH"),
    ("azahar", "Azahar", ("Azahar", "azahar-emu"), "org.azahar_emu.Azahar", None),
    ("lime3ds", "Lime3DS", ("Lime3DS", "lime3ds-emu"), "io.github.lime3ds.Lime3DS", None),
]


class CitraFamily(Emulator):
    def __init__(self, emu_id, name, folder_names, flatpak_id, env_var):
        self.id = emu_id
        self.name = name
        self._folders = folder_names
        self._flatpak = flatpak_id
        self._env_var = env_var

    def user_dirs(self, ctx):
        candidates = list(ctx.override_dirs(self.id))
        if self._env_var and ctx.env.get(self._env_var):
            candidates.append(Path(ctx.env[self._env_var]).expanduser())
        win_mac, linux = self._folders
        if ctx.system == "Windows":
            candidates.append(ctx.appdata() / win_mac)
        elif ctx.system == "Darwin":
            candidates.append(ctx.app_support() / win_mac)
            candidates.append(ctx.xdg_data() / linux)  # builds from before 2023
        else:
            candidates.append(ctx.xdg_data() / linux)
            candidates.append(ctx.home / ".var" / "app" / self._flatpak / "data" / linux)
        seen, out = set(), []
        for path in candidates:
            if path.is_dir() and path not in seen:
                seen.add(path)
                out.append(path)
        return out

    @staticmethod
    def _subdirs(path):
        try:
            return sorted(p for p in Path(path).iterdir() if p.is_dir())
        except OSError:
            return []

    def _title_roots(self, base):
        """Every .../sdmc/Nintendo 3DS/<id1>/<id2>/title folder under a user directory."""
        for id1 in self._subdirs(base / "sdmc" / "Nintendo 3DS"):
            for id2 in self._subdirs(id1):
                title = id2 / "title"
                if title.is_dir():
                    yield title

    def find_saves(self, ctx):
        entries, used = [], set()
        for base in self.user_dirs(ctx):
            for title_root in self._title_roots(base):
                for type_folder in TYPE_FOLDERS:
                    for short in self._subdirs(title_root / type_folder):
                        data_dir = short / "data" / "00000001"
                        if not data_dir.is_dir() or not any(p.is_file() for p in data_dir.rglob("*")):
                            continue
                        full_id = (type_folder + short.name).upper()
                        game_id = unique_id(used, full_id)
                        name = GAME_NAMES.get(full_id, f"Unknown Game ({full_id})")
                        entries.append(SaveEntry(
                            emulator=self.id, emulator_name=self.name, game_id=game_id,
                            name=name, kind=KIND_SAVE, paths=[data_dir],
                            is_pokemon=is_pokemon_text(name),
                            metadata={"platform": "Nintendo 3DS", "title_id": full_id},
                            restore_hint=data_dir.relative_to(base).as_posix()))
        return entries

    def find_savestates(self, ctx):
        entries, used = [], set()
        for base in self.user_dirs(ctx):
            state_dir = base / "states"
            if not state_dir.is_dir():
                continue
            groups = {}
            for item in sorted(state_dir.iterdir()):
                if item.is_file() and item.suffix.lower() == ".cst":
                    groups.setdefault(item.name.split(".")[0].upper(), []).append(item)
            for title_id, files in groups.items():
                name = GAME_NAMES.get(title_id, f"Unknown Game ({title_id})")
                entries.append(SaveEntry(
                    emulator=self.id, emulator_name=self.name,
                    game_id=unique_id(used, title_id), name=name, kind=KIND_STATES,
                    paths=files, is_pokemon=is_pokemon_text(name),
                    metadata={"platform": "Nintendo 3DS", "title_id": title_id},
                    restore_hint="states"))
        return entries

    def legacy_dest(self, ctx, game_id):
        """Where a save pushed by the old Citra-only PokeSync should be restored."""
        game_id = game_id.upper()
        base = self.restore_base(ctx)
        if base is None or len(game_id) != 16:
            return None
        title_root = next(iter(self._title_roots(base)), None)
        if title_root is None:
            title_root = base / "sdmc" / "Nintendo 3DS" / ZERO_ID / ZERO_ID / "title"

        def child(parent, wanted):
            # Citra names these folders in lowercase hex; reuse whatever already exists.
            for existing in self._subdirs(parent):
                if existing.name.upper() == wanted.upper():
                    return existing
            return parent / wanted.lower()

        type_dir = child(title_root, game_id[:8])
        return child(type_dir, game_id[8:]) / "data" / "00000001"


def build():
    return [CitraFamily(*variant) for variant in VARIANTS]

"""PlayStation emulators: DuckStation (PS1), PCSX2 (PS2) and PPSSPP (PSP)."""
from __future__ import annotations

import re
from pathlib import Path

from utils import is_pokemon_text, slugify
from .base import Emulator, SaveEntry, KIND_SAVE, KIND_STATES, unique_id
from .metadata import read_param_sfo


class MemcardEmulator(Emulator):
    """Emulators whose saves are memory card image files in one folder."""

    def __init__(self, emu_id, name, platform_name, dirs, card_exts, state_dir, state_exts):
        self.id = emu_id
        self.name = name
        self._platform = platform_name
        self._dirs = dirs  # {system: [path builder(ctx)]}
        self._card_exts = tuple(card_exts)
        self._state_dir = state_dir
        self._state_exts = tuple(state_exts)

    def user_dirs(self, ctx):
        candidates = list(ctx.override_dirs(self.id))
        for build in self._dirs.get(ctx.system, self._dirs["Linux"]):
            candidates.append(build(ctx))
        seen, out = set(), []
        for path in candidates:
            if path.is_dir() and path not in seen:
                seen.add(path)
                out.append(path)
        return out

    def find_saves(self, ctx):
        entries, used = [], set()
        for base in self.user_dirs(ctx):
            cards = base / "memcards"
            if not cards.is_dir():
                continue
            for item in sorted(cards.iterdir()):
                if item.is_file() and item.suffix.lower() in self._card_exts:
                    entries.append(SaveEntry(
                        emulator=self.id, emulator_name=self.name,
                        game_id=unique_id(used, slugify(item.stem)),
                        name=f"Memory card: {item.stem}", kind=KIND_SAVE, paths=[item],
                        metadata={"platform": self._platform},
                        restore_hint="memcards"))
        return entries

    def find_savestates(self, ctx):
        entries, used = [], set()
        for base in self.user_dirs(ctx):
            folder = base / self._state_dir
            if not folder.is_dir():
                continue
            groups = {}
            for item in sorted(folder.iterdir()):
                if item.is_file() and item.suffix.lower() in self._state_exts:
                    groups.setdefault(re.split(r"[_. (]", item.stem)[0], []).append(item)
            for serial, files in groups.items():
                entries.append(SaveEntry(
                    emulator=self.id, emulator_name=self.name,
                    game_id=unique_id(used, slugify(serial)), name=serial, kind=KIND_STATES,
                    paths=files, metadata={"platform": self._platform, "serial": serial},
                    restore_hint=self._state_dir))
        return entries


class PPSSPP(Emulator):
    id = "ppsspp"
    name = "PPSSPP (PSP)"

    def user_dirs(self, ctx):
        candidates = list(ctx.override_dirs(self.id))
        if ctx.system == "Windows":
            candidates.append(ctx.documents() / "PPSSPP")
        elif ctx.system == "Darwin":
            candidates += [ctx.app_support() / "PPSSPP", ctx.home / ".config" / "ppsspp"]
        else:
            candidates += [ctx.xdg_config() / "ppsspp",
                           ctx.home / ".var" / "app" / "org.ppsspp.PPSSPP" / "config" / "ppsspp"]
        seen, out = set(), []
        for path in candidates:
            if path.is_dir() and path not in seen:
                seen.add(path)
                out.append(path)
        return out

    def find_saves(self, ctx):
        entries, used = [], set()
        for base in self.user_dirs(ctx):
            savedata = base / "PSP" / "SAVEDATA"
            if not savedata.is_dir():
                continue
            for folder in sorted(p for p in savedata.iterdir() if p.is_dir()):
                if not any(p.is_file() for p in folder.rglob("*")):
                    continue
                sfo = read_param_sfo(folder / "PARAM.SFO") if (folder / "PARAM.SFO").is_file() else {}
                title = sfo.get("TITLE") or sfo.get("SAVEDATA_TITLE") or folder.name
                detail = sfo.get("SAVEDATA_DETAIL")
                metadata = {"platform": "PlayStation Portable", "save_folder": folder.name}
                if detail:
                    metadata["detail"] = detail
                entries.append(SaveEntry(
                    emulator=self.id, emulator_name=self.name,
                    game_id=unique_id(used, slugify(folder.name)), name=title, kind=KIND_SAVE,
                    paths=[folder], is_pokemon=is_pokemon_text(title), metadata=metadata,
                    restore_hint=folder.relative_to(base).as_posix()))
        return entries

    def find_savestates(self, ctx):
        entries, used = [], set()
        for base in self.user_dirs(ctx):
            folder = base / "PSP" / "PPSSPP_STATE"
            if not folder.is_dir():
                continue
            groups = {}
            for item in sorted(folder.iterdir()):
                if item.is_file() and item.suffix.lower() in (".ppst", ".jpg"):
                    groups.setdefault(item.name.split("_")[0], []).append(item)
            for serial, files in groups.items():
                entries.append(SaveEntry(
                    emulator=self.id, emulator_name=self.name,
                    game_id=unique_id(used, slugify(serial)), name=serial, kind=KIND_STATES,
                    paths=files, metadata={"platform": "PlayStation Portable", "serial": serial},
                    restore_hint="PSP/PPSSPP_STATE"))
        return entries


def build():
    duck_dirs = {
        "Windows": [lambda c: c.documents() / "DuckStation"],
        "Darwin": [lambda c: c.app_support() / "DuckStation"],
        "Linux": [lambda c: c.xdg_data() / "duckstation",
                  lambda c: c.home / ".var" / "app" / "org.duckstation.DuckStation" / "data" / "duckstation"],
    }
    pcsx2_dirs = {
        "Windows": [lambda c: c.documents() / "PCSX2"],
        "Darwin": [lambda c: c.app_support() / "PCSX2"],
        "Linux": [lambda c: c.xdg_config() / "PCSX2",
                  lambda c: c.home / ".var" / "app" / "net.pcsx2.PCSX2" / "config" / "PCSX2"],
    }
    return [
        MemcardEmulator("duckstation", "DuckStation (PlayStation)", "PlayStation", duck_dirs,
                        card_exts=[".mcd", ".mcr", ".mc"], state_dir="savestates", state_exts=[".sav"]),
        MemcardEmulator("pcsx2", "PCSX2 (PlayStation 2)", "PlayStation 2", pcsx2_dirs,
                        card_exts=[".ps2", ".mcd"], state_dir="sstates", state_exts=[".p2s"]),
        PPSSPP(),
    ]

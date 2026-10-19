"""Dolphin: GameCube memory cards, Wii saves and save states."""
from __future__ import annotations

import re
from pathlib import Path

from utils import is_pokemon_text, slugify
from .base import Emulator, SaveEntry, KIND_SAVE, KIND_STATES, unique_id

WII_TYPE_FOLDERS = ("00010000", "00010001", "00010004")
CARD_FILE_RE = re.compile(r"^MemoryCard([AB])\.(\w+)\.(raw|gcp)$", re.I)
STATE_RE = re.compile(r"\.s(0[1-9]|10)$|\.sav$", re.I)


class Dolphin(Emulator):
    id = "dolphin"
    name = "Dolphin (GameCube / Wii)"

    def user_dirs(self, ctx):
        candidates = list(ctx.override_dirs(self.id))
        if ctx.system == "Windows":
            candidates += [ctx.documents() / "Dolphin Emulator", ctx.appdata() / "Dolphin Emulator"]
        elif ctx.system == "Darwin":
            candidates += [ctx.app_support() / "Dolphin"]
        else:
            candidates += [ctx.xdg_data() / "dolphin-emu", ctx.home / ".dolphin-emu",
                           ctx.home / ".var" / "app" / "org.DolphinEmu.dolphin-emu" / "data" / "dolphin-emu"]
        seen, out = set(), []
        for path in candidates:
            if path.is_dir() and path not in seen:
                seen.add(path)
                out.append(path)
        return out

    def find_saves(self, ctx):
        entries, used = [], set()
        for base in self.user_dirs(ctx):
            entries += self._gamecube(base, used)
            entries += self._wii(base, used)
        return entries

    def _gamecube(self, base, used):
        gc = base / "GC"
        out = []
        if not gc.is_dir():
            return out
        for item in sorted(gc.iterdir()):
            match = CARD_FILE_RE.match(item.name) if item.is_file() else None
            if match:
                slot, region = match.group(1).upper(), match.group(2)
                out.append(SaveEntry(
                    emulator=self.id, emulator_name=self.name,
                    game_id=unique_id(used, slugify(f"gc-{item.stem}")),
                    name=f"GameCube Memory Card {slot} ({region})", kind=KIND_SAVE,
                    paths=[item], metadata={"platform": "GameCube", "region": region},
                    restore_hint=item.parent.relative_to(base).as_posix()))
            elif item.is_dir():  # folder mode: GC/<REGION>/Card A/*.gci
                for card in sorted(item.iterdir()):
                    if card.is_dir() and any(p.is_file() for p in card.rglob("*")):
                        out.append(SaveEntry(
                            emulator=self.id, emulator_name=self.name,
                            game_id=unique_id(used, slugify(f"gc-{item.name}-{card.name}")),
                            name=f"GameCube {card.name} ({item.name}, folder)", kind=KIND_SAVE,
                            paths=[card], metadata={"platform": "GameCube", "region": item.name},
                            restore_hint=card.relative_to(base).as_posix()))
        return out

    def _wii(self, base, used):
        out = []
        for type_folder in WII_TYPE_FOLDERS:
            root = base / "Wii" / "title" / type_folder
            if not root.is_dir():
                continue
            for game in sorted(p for p in root.iterdir() if p.is_dir()):
                data = game / "data"
                if not data.is_dir() or not any(p.is_file() for p in data.rglob("*")):
                    continue
                try:
                    code = bytes.fromhex(game.name).decode("ascii")
                    if not code.isprintable():
                        raise ValueError
                except ValueError:
                    code = game.name
                out.append(SaveEntry(
                    emulator=self.id, emulator_name=self.name,
                    game_id=unique_id(used, slugify(f"wii-{code}")),
                    name=f"Wii {code}", kind=KIND_SAVE, paths=[data],
                    is_pokemon=is_pokemon_text(code),
                    metadata={"platform": "Wii", "game_code": code},
                    restore_hint=data.relative_to(base).as_posix()))
        return out

    def find_savestates(self, ctx):
        entries, used = [], set()
        for base in self.user_dirs(ctx):
            state_dir = base / "StateSaves"
            if not state_dir.is_dir():
                continue
            groups = {}
            for item in sorted(state_dir.iterdir()):
                if item.is_file() and STATE_RE.search(item.name):
                    groups.setdefault(STATE_RE.sub("", item.name), []).append(item)
            for stem, files in groups.items():
                entries.append(SaveEntry(
                    emulator=self.id, emulator_name=self.name,
                    game_id=unique_id(used, slugify(stem)), name=stem, kind=KIND_STATES,
                    paths=files, is_pokemon=is_pokemon_text(stem),
                    metadata={"game_code": stem}, restore_hint="StateSaves"))
        return entries


def build():
    return [Dolphin()]

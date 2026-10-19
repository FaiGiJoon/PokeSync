"""Emulators that keep saves and states next to the ROM: mGBA, melonDS, DeSmuME.

These have no fixed save folder, so they are found through the user's scan folders.
"""
from __future__ import annotations

import re
from pathlib import Path

from utils import is_pokemon_text, slugify
from .base import Emulator, SaveEntry, KIND_SAVE, KIND_STATES, unique_id
from .metadata import read_rom_header


class RomAdjacentEmulator(Emulator):
    def __init__(self, emu_id, name, save_exts, rom_exts, state_re, require_rom=True):
        self.id = emu_id
        self.name = name
        self._save_exts = tuple(save_exts)
        self._rom_exts = tuple(rom_exts)
        self._state_re = re.compile(state_re, re.I)
        self._require_rom = require_rom

    def _rom_for(self, ctx, path):
        for sibling in ctx.siblings(path):
            if sibling.suffix.lower() in self._rom_exts:
                return sibling
        return None

    def _describe(self, ctx, path):
        """(display name, game id base, header dict) for a save or state file."""
        rom = self._rom_for(ctx, path)
        header = read_rom_header(rom) if rom else None
        name = rom.stem if rom else path.stem
        game_id = (header or {}).get("game_code") or slugify(path.stem)
        return name, game_id, header or {}, rom

    def find_saves(self, ctx):
        entries, used = [], set()
        for path in ctx.files():
            if path.suffix.lower() not in self._save_exts:
                continue
            name, game_id, header, rom = self._describe(ctx, path)
            if self._require_rom and rom is None:
                continue
            metadata = {k: v for k, v in header.items() if v}
            if rom is not None:
                metadata["rom"] = rom.name
            entries.append(SaveEntry(
                emulator=self.id, emulator_name=self.name,
                game_id=unique_id(used, slugify(game_id)), name=name, kind=KIND_SAVE,
                paths=[path], metadata=metadata,
                is_pokemon=is_pokemon_text(name, header.get("title"))))
        return entries

    def find_savestates(self, ctx):
        groups = {}
        for path in ctx.files():
            match = self._state_re.search(path.name)
            if match:
                groups.setdefault((path.parent, path.name[:match.start()].lower()), []).append(path)
        entries, used = [], set()
        for (_parent, _stem), files in groups.items():
            files.sort()
            name, game_id, header, rom = self._describe(ctx, files[0])
            if rom is None:
                name = self._state_re.sub("", files[0].name)
            metadata = {k: v for k, v in header.items() if v}
            entries.append(SaveEntry(
                emulator=self.id, emulator_name=self.name,
                game_id=unique_id(used, slugify(game_id)), name=name, kind=KIND_STATES,
                paths=files, metadata=metadata,
                is_pokemon=is_pokemon_text(name, header.get("title"))))
        return entries


def build():
    return [
        RomAdjacentEmulator("mgba", "mGBA / VisualBoyAdvance (GB, GBC, GBA)",
                            save_exts=[".sav"], rom_exts=[".gba", ".gbc", ".gb"],
                            state_re=r"\.ss\d$"),
        RomAdjacentEmulator("melonds", "melonDS (Nintendo DS)",
                            save_exts=[".sav"], rom_exts=[".nds"],
                            state_re=r"\.mln\d$"),
        RomAdjacentEmulator("desmume", "DeSmuME (Nintendo DS)",
                            save_exts=[".dsv"], rom_exts=[".nds"],
                            state_re=r"\.ds\d$", require_rom=False),
    ]

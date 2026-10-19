"""Emulator plugins for PokeSync.

To support another emulator, write a subclass of `Emulator` (see base.py), give it a
`build()` function that returns instances, and add that module to `_MODULES` below.
"""
from __future__ import annotations

import logging

from . import citra, dolphin, playstation, retroarch, romadjacent
from .base import Emulator, SaveEntry, ScanContext, KIND_SAVE, KIND_STATES
from .metadata import enrich

log = logging.getLogger("pokesync")

_MODULES = [citra, romadjacent, dolphin, retroarch, playstation]

EMULATORS = {}
for _module in _MODULES:
    for _emulator in _module.build():
        EMULATORS[_emulator.id] = _emulator


def get_emulator(emulator_id):
    return EMULATORS.get(emulator_id)


def emulator_names():
    return {emu.id: emu.name for emu in EMULATORS.values()}


def detect_all(ctx, enabled=None):
    """Find every save (and save state, if enabled) on this machine."""
    entries, claimed = [], set()
    for emulator in EMULATORS.values():
        if enabled is not None and emulator.id not in enabled:
            continue
        try:
            found = list(emulator.find_saves(ctx))
            if ctx.include_states:
                found += list(emulator.find_savestates(ctx))
        except Exception:
            log.exception("Scanning for %s failed", emulator.id)
            continue
        for entry in found:
            files = {str(path) for _, path in entry.files()}
            if not files or files <= claimed:
                continue  # empty, or already found by another emulator
            claimed |= files
            entries.append(enrich(entry))
    entries.sort(key=lambda e: (not e.is_pokemon, e.emulator_name, e.kind != KIND_SAVE, e.name.lower()))
    return entries

"""RetroArch (and any libretro core): battery saves and save states."""
from __future__ import annotations

import re
from pathlib import Path

from utils import is_pokemon_text, slugify
from .base import Emulator, SaveEntry, KIND_SAVE, KIND_STATES, unique_id

SAVE_EXTS = {".srm", ".sav", ".dsv", ".mcr", ".mcd", ".rtc", ".eep", ".fla", ".sra", ".nv"}
STATE_RE = re.compile(r"\.state\d*(\.auto)?(\.png)?$", re.I)


class RetroArch(Emulator):
    id = "retroarch"
    name = "RetroArch"

    def _bases(self, ctx):
        candidates = list(ctx.override_dirs(self.id))
        if ctx.system == "Windows":
            candidates += [ctx.appdata() / "RetroArch", ctx.home / "RetroArch"]
        elif ctx.system == "Darwin":
            candidates += [ctx.app_support() / "RetroArch", ctx.documents() / "RetroArch"]
        else:
            candidates += [ctx.xdg_config() / "retroarch",
                           ctx.home / ".var" / "app" / "org.libretro.RetroArch" / "config" / "retroarch",
                           ctx.home / ".retroarch"]
        seen, out = set(), []
        for path in candidates:
            if path.is_dir() and path not in seen:
                seen.add(path)
                out.append(path)
        return out

    def user_dirs(self, ctx):
        return self._bases(ctx)

    @staticmethod
    def _walk(folder):
        return sorted(p for p in Path(folder).rglob("*") if p.is_file())

    def find_saves(self, ctx):
        files = []
        for base in self._bases(ctx):
            if (base / "saves").is_dir():
                files += [(p, base) for p in self._walk(base / "saves") if p.suffix.lower() in SAVE_EXTS]
        known = {p for p, _ in files}
        # .srm is RetroArch's own extension, so it is safe to pick up from scan folders too
        files += [(p, None) for p in ctx.files() if p.suffix.lower() == ".srm" and p not in known]

        groups = {}
        for path, base in files:
            groups.setdefault((path.parent, path.stem.lower()), []).append((path, base))
        entries, used = [], set()
        for (_parent, _stem), items in groups.items():
            paths = [p for p, _ in items]
            base = items[0][1]
            name = paths[0].stem
            entries.append(SaveEntry(
                emulator=self.id, emulator_name=self.name,
                game_id=unique_id(used, slugify(name)), name=name, kind=KIND_SAVE,
                paths=paths, is_pokemon=is_pokemon_text(name),
                restore_hint=paths[0].parent.relative_to(base).as_posix() if base else None))
        return entries

    def find_savestates(self, ctx):
        groups = {}
        for base in self._bases(ctx):
            if (base / "states").is_dir():
                for path in self._walk(base / "states"):
                    match = STATE_RE.search(path.name)
                    if match:
                        groups.setdefault((path.parent, path.name[:match.start()].lower()), []).append((path, base))
        entries, used = [], set()
        for (_parent, _stem), items in groups.items():
            paths = [p for p, _ in items]
            base = items[0][1]
            name = STATE_RE.sub("", paths[0].name)
            entries.append(SaveEntry(
                emulator=self.id, emulator_name=self.name,
                game_id=unique_id(used, slugify(name)), name=name, kind=KIND_STATES,
                paths=paths, is_pokemon=is_pokemon_text(name),
                restore_hint=paths[0].parent.relative_to(base).as_posix()))
        return entries


def build():
    return [RetroArch()]

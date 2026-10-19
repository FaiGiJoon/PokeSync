"""Reading metadata out of ROM headers and other game files.

`enrich()` runs after detection and fills `SaveEntry.metadata`. To add a smarter
extractor (for example one that reads the in-game location out of a Pokemon save)
append a function to `EXTRACTORS`: it receives the entry and returns a dict of
extra metadata, or an empty dict.
"""
from __future__ import annotations

import struct
from pathlib import Path

REGIONS = {
    "J": "Japan", "E": "USA", "P": "Europe", "D": "Germany", "F": "France",
    "I": "Italy", "S": "Spain", "K": "Korea", "U": "Australia", "O": "International",
}


def _text(raw):
    return raw.split(b"\0")[0].decode("ascii", "replace").strip()


def read_rom_header(path):
    """Parse the header of a GB, GBC, GBA or NDS ROM. Returns a dict or None."""
    path = Path(path)
    ext = path.suffix.lower()
    try:
        with open(path, "rb") as handle:
            head = handle.read(0x200)
    except OSError:
        return None
    if ext == ".gba" and len(head) >= 0xB2:
        code = _text(head[0xAC:0xB0])
        return {"platform": "Game Boy Advance", "title": _text(head[0xA0:0xAC]),
                "game_code": code, "region": REGIONS.get(code[3:4])}
    if ext == ".nds" and len(head) >= 0x10:
        code = _text(head[0x0C:0x10])
        return {"platform": "Nintendo DS", "title": _text(head[0x00:0x0C]),
                "game_code": code, "region": REGIONS.get(code[3:4])}
    if ext in (".gb", ".gbc") and len(head) >= 0x144:
        return {"platform": "Game Boy Color" if ext == ".gbc" else "Game Boy",
                "title": _text(head[0x134:0x144]), "game_code": None, "region": None}
    return None


def read_param_sfo(path):
    """Parse a PSP PARAM.SFO into a dict of its text fields (TITLE, SAVEDATA_TITLE...)."""
    try:
        data = Path(path).read_bytes()
        if data[:4] != b"\0PSF":
            return {}
        key_start, data_start, count = struct.unpack_from("<III", data, 8)
        out = {}
        for i in range(count):
            key_off, fmt, length, _max, data_off = struct.unpack_from("<HHIII", data, 20 + i * 16)
            if fmt not in (0x0004, 0x0204):
                continue
            key_end = data.index(b"\0", key_start + key_off)
            key = data[key_start + key_off:key_end].decode("ascii", "replace")
            raw = data[data_start + data_off:data_start + data_off + length]
            out[key] = raw.split(b"\0")[0].decode("utf-8", "replace")
        return out
    except Exception:
        return {}


def _basic(entry):
    files = entry.files()
    if not files:
        return {}
    mtime = max(path.stat().st_mtime for _, path in files)
    return {"file_count": len(files), "size": sum(path.stat().st_size for _, path in files),
            "modified": mtime}


EXTRACTORS = [_basic]


def enrich(entry):
    for extractor in EXTRACTORS:
        try:
            extra = extractor(entry)
        except Exception:
            extra = {}
        for key, value in (extra or {}).items():
            entry.metadata.setdefault(key, value)
    return entry

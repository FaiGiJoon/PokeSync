"""Small shared helpers for PokeSync."""
import re
import unicodedata
from datetime import datetime
from pathlib import Path


def slugify(value, default="unknown"):
    """Turn arbitrary text into a safe, stable identifier (letters, digits, . _ -)."""
    text = re.sub(r"[^A-Za-z0-9._-]+", "_", str(value)).strip("._-")
    return text or default


def safe_join(base, relative):
    """Join `relative` onto `base`, refusing anything that would escape `base`.

    Remote data (a shared GitHub repo, a cloud folder) is not trusted, so every
    path that comes from it goes through here before a file is written.
    """
    base = Path(base).resolve()
    target = (base / relative).resolve()
    if target != base and base not in target.parents:
        raise ValueError(f"Refusing path outside of {base}: {relative}")
    return target


def human_size(num_bytes):
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{int(size)} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024


def format_time(timestamp):
    return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M")


def is_pokemon_text(*texts):
    """True if any of the given strings looks like a Pokemon title."""
    for text in texts:
        if not text:
            continue
        plain = unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode().lower()
        if "pokemon" in plain or "pikachu" in plain:
            return True
    return False

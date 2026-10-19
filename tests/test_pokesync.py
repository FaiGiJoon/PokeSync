import json
import os
import struct
import time
from pathlib import Path

import pytest

from emulators import ScanContext, detect_all
from emulators.metadata import read_param_sfo, read_rom_header
from sync_manager import SyncManager
from utils import safe_join


def ctx_for(home, system="Linux", **kwargs):
    return ScanContext(home=home, system=system, env={}, **kwargs)


def write(path, data=b"data", mtime=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    if mtime:
        os.utime(path, (mtime, mtime))
    return path


def gba_rom(path, title=b"POKEMON EMER", code=b"BPEE"):
    header = bytearray(0x200)
    header[0xA0:0xA0 + len(title)] = title
    header[0xAC:0xB0] = code
    return write(path, bytes(header))


def nds_rom(path, title=b"POKEMON PLAT", code=b"CPUE"):
    header = bytearray(0x200)
    header[0:len(title)] = title
    header[0x0C:0x10] = code
    return write(path, bytes(header))


def by_emulator(entries, emulator, kind="save"):
    return [e for e in entries if e.emulator == emulator and e.kind == kind]


# ---------------------------------------------------------------- detection
def test_citra_detects_all_games_and_all_files(tmp_path):
    base = tmp_path / ".local/share/citra-emu"
    title = base / "sdmc/Nintendo 3DS" / ("0" * 32) / ("0" * 32) / "title"
    write(title / "00040000/0011c400/data/00000001/main", b"omega ruby")
    write(title / "00040000/00030100/data/00000001/main", b"mk7")
    write(title / "00040000/00030100/data/00000001/extra.bin", b"more")

    entries = by_emulator(detect_all(ctx_for(tmp_path)), "citra")
    names = {e.name: e for e in entries}
    assert set(names) == {"Pokemon Omega Ruby", "Mario Kart 7"}
    assert names["Pokemon Omega Ruby"].is_pokemon
    assert not names["Mario Kart 7"].is_pokemon
    assert {rel for rel, _ in names["Mario Kart 7"].files()} == {"main", "extra.bin"}
    assert entries[0].name == "Pokemon Omega Ruby"  # Pokemon sorts first


def test_citra_savestates_only_when_enabled(tmp_path):
    base = tmp_path / ".local/share/citra-emu"
    write(base / "states/0004000000055D00.01.cst")
    write(base / "states/0004000000055D00.02.cst")
    assert not by_emulator(detect_all(ctx_for(tmp_path)), "citra", "states")
    states = by_emulator(detect_all(ctx_for(tmp_path, include_states=True)), "citra", "states")
    assert len(states) == 1 and len(states[0].files()) == 2 and states[0].name == "Pokemon X"


def test_gba_save_found_via_scan_folder_with_rom_header(tmp_path):
    roms = tmp_path / "roms"
    gba_rom(roms / "Pokemon - Emerald Version (USA).gba")
    write(roms / "Pokemon - Emerald Version (USA).sav", b"x" * 100)
    write(roms / "orphan.sav")  # no ROM next to it: ambiguous, so ignored

    entries = by_emulator(detect_all(ctx_for(tmp_path, scan_folders=[roms])), "mgba")
    assert len(entries) == 1
    entry = entries[0]
    assert entry.game_id == "BPEE" and entry.is_pokemon
    assert entry.metadata["region"] == "USA" and entry.metadata["platform"] == "Game Boy Advance"


def test_nds_melonds_and_desmume(tmp_path):
    roms = tmp_path / "ds"
    nds_rom(roms / "Pokemon Platinum.nds")
    write(roms / "Pokemon Platinum.sav")
    write(roms / "Battery" / "Pokemon Platinum.dsv")  # DeSmuME needs no ROM next to it
    entries = detect_all(ctx_for(tmp_path, scan_folders=[roms]))
    assert len(by_emulator(entries, "melonds")) == 1
    assert len(by_emulator(entries, "desmume")) == 1


def test_rom_adjacent_savestates(tmp_path):
    roms = tmp_path / "roms"
    gba_rom(roms / "Emerald.gba")
    write(roms / "Emerald.ss0")
    write(roms / "Emerald.ss1")
    entries = detect_all(ctx_for(tmp_path, scan_folders=[roms], include_states=True))
    states = by_emulator(entries, "mgba", "states")
    assert len(states) == 1 and len(states[0].files()) == 2


def test_dolphin_gamecube_and_wii(tmp_path):
    base = tmp_path / ".local/share/dolphin-emu"
    write(base / "GC/MemoryCardA.USA.raw")
    write(base / "Wii/title/00010000/52535045/data/banner.bin")
    write(base / "StateSaves/GALE01.s01")
    entries = detect_all(ctx_for(tmp_path, include_states=True))
    saves = by_emulator(entries, "dolphin")
    assert {e.game_id for e in saves} == {"gc-MemoryCardA.USA", "wii-RSPE"}
    assert any(e.name == "GameCube Memory Card A (USA)" for e in saves)
    assert len(by_emulator(entries, "dolphin", "states")) == 1


def test_retroarch_groups_save_files_and_states(tmp_path):
    base = tmp_path / ".config/retroarch"
    write(base / "saves/Zelda.srm")
    write(base / "saves/Zelda.rtc")
    write(base / "states/Zelda.state")
    write(base / "states/Zelda.state1")
    entries = detect_all(ctx_for(tmp_path, include_states=True))
    saves = by_emulator(entries, "retroarch")
    assert len(saves) == 1 and len(saves[0].files()) == 2
    assert len(by_emulator(entries, "retroarch", "states")[0].files()) == 2


def test_ppsspp_reads_title_from_param_sfo(tmp_path):
    key, value = b"TITLE\0", b"Test Game\0"
    header = struct.pack("<4sIIII", b"\0PSF", 0x101, 20 + 16, 20 + 16 + len(key), 1)
    entry = struct.pack("<HHIII", 0, 0x0204, len(value), len(value), 0)
    sfo = write(tmp_path / ".config/ppsspp/PSP/SAVEDATA/ULUS10000DATA00/PARAM.SFO", header + entry + key + value)
    write(sfo.parent / "DATA.BIN")
    assert read_param_sfo(sfo) == {"TITLE": "Test Game"}
    saves = by_emulator(detect_all(ctx_for(tmp_path)), "ppsspp")
    assert saves[0].name == "Test Game" and len(saves[0].files()) == 2


def test_playstation_memory_cards_and_overrides(tmp_path):
    write(tmp_path / ".local/share/duckstation/memcards/shared_card_1.mcd")
    custom = tmp_path / "somewhere/PCSX2"
    write(custom / "memcards/Mcd001.ps2")
    entries = detect_all(ctx_for(tmp_path, overrides={"pcsx2": str(custom)}))
    assert len(by_emulator(entries, "duckstation")) == 1
    assert len(by_emulator(entries, "pcsx2")) == 1


def test_rom_header_parsing(tmp_path):
    assert read_rom_header(gba_rom(tmp_path / "a.gba"))["game_code"] == "BPEE"
    assert read_rom_header(nds_rom(tmp_path / "a.nds"))["platform"] == "Nintendo DS"
    assert read_rom_header(write(tmp_path / "a.txt")) is None


def test_enabled_emulators_filter(tmp_path):
    write(tmp_path / ".config/retroarch/saves/a.srm")
    write(tmp_path / ".local/share/duckstation/memcards/a.mcd")
    entries = detect_all(ctx_for(tmp_path), enabled=["retroarch"])
    assert {e.emulator for e in entries} == {"retroarch"}


# ------------------------------------------------------------------ safety
def test_safe_join_blocks_traversal(tmp_path):
    assert safe_join(tmp_path, "a/b.sav") == (tmp_path / "a/b.sav").resolve()
    with pytest.raises(ValueError):
        safe_join(tmp_path, "../evil")
    with pytest.raises(ValueError):
        safe_join(tmp_path, "/etc/passwd")


# ------------------------------------------------------------------- sync
@pytest.fixture
def manager(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)  # backups/ go in the temp dir
    mgr = SyncManager(config_file=str(tmp_path / "config.json"))
    mgr.set_cloud_path(str(tmp_path / "cloud"))
    (tmp_path / "cloud").mkdir()
    return mgr


def retro_entry(tmp_path, mtime):
    write(tmp_path / ".config/retroarch/saves/Emerald.srm", b"save-v1", mtime)
    return by_emulator(detect_all(ctx_for(tmp_path)), "retroarch")[0]


def test_push_pull_roundtrip_with_metadata_and_backup(tmp_path, manager):
    old = time.time() - 1000
    entry = retro_entry(tmp_path, old)
    assert manager.check_conflict(entry)[0] == "no_remote"

    ok, _ = manager.push_save(entry)
    assert ok
    meta = json.loads((tmp_path / "cloud/retroarch/Emerald/save/.pokesync.json").read_text())
    assert meta["name"] == "Emerald" and meta["files"][0]["rel"] == "Emerald.srm"
    assert len(meta["files"][0]["sha256"]) == 64
    assert manager.check_conflict(entry)[0] == "up_to_date"

    # the local save gets damaged, newer than the cloud copy
    local = entry.paths[0]
    local.write_bytes(b"corrupted")
    os.utime(local, (time.time(), time.time()))
    assert manager.check_conflict(entry)[0] == "local_newer"

    ok, _ = manager.pull_save(entry)
    assert ok and local.read_bytes() == b"save-v1"
    backups = list((tmp_path / "backups/retroarch/Emerald").rglob("Emerald.srm"))
    assert len(backups) == 1 and backups[0].read_bytes() == b"corrupted"


def test_lost_save_shows_up_as_remote_only_and_restores(tmp_path, manager):
    entry = retro_entry(tmp_path, time.time() - 500)
    assert manager.push_save(entry)[0]

    entry.paths[0].unlink()  # the save "randomly disappears"
    local = detect_all(ctx_for(tmp_path))
    assert not by_emulator(local, "retroarch")

    # SyncManager builds its own context from the real home, so point it at the fake one
    manager._context = lambda: ctx_for(tmp_path)
    remote = manager.get_remote_only_entries(local)
    assert len(remote) == 1 and remote[0].remote_only and remote[0].name == "Emerald"

    assert manager.pull_save(remote[0])[0]
    assert (tmp_path / ".config/retroarch/saves/Emerald.srm").read_bytes() == b"save-v1"


def test_legacy_citra_layout_is_still_readable_and_restorable(tmp_path, manager):
    base = tmp_path / ".local/share/citra-emu"
    title = base / "sdmc/Nintendo 3DS" / ("0" * 32) / ("0" * 32) / "title"
    local = write(title / "00040000/0011c400/data/00000001/main", b"local", time.time() - 100)
    entry = by_emulator(detect_all(ctx_for(tmp_path)), "citra")[0]

    # layout written by the old Citra-only PokeSync: <cloud>/<title id>/main
    write(tmp_path / "cloud/000400000011C400/main", b"from-old-version", time.time())
    assert manager.check_conflict(entry)[0] == "remote_newer"
    assert manager.pull_save(entry)[0] and local.read_bytes() == b"from-old-version"

    # and a lost save is found and restored from the legacy layout too
    local.unlink()
    manager._context = lambda: ctx_for(tmp_path)
    remote = manager.get_remote_only_entries(by_emulator(detect_all(ctx_for(tmp_path)), "citra"))
    assert [e.game_id for e in remote] == ["000400000011C400"]
    assert manager.pull_save(remote[0])[0] and local.read_bytes() == b"from-old-version"


def test_pull_refuses_hostile_remote_names(tmp_path, manager):
    entry = retro_entry(tmp_path, time.time() - 500)
    folder = tmp_path / "cloud/retroarch/Emerald/save"
    write(folder / "Emerald.srm", b"ok")
    (folder / ".pokesync.json").write_text(json.dumps({"files": []}))
    # a name that tries to climb out of the destination folder
    (folder / "sub").mkdir()
    entry2 = retro_entry(tmp_path, time.time() - 400)
    entry2.paths = [entry.paths[0]]
    manager._read_remote = lambda root, e: ({"../../escape.txt": folder / "Emerald.srm"}, None)
    ok, msg = manager.pull_save(entry2)
    assert not ok and "outside" in msg
    assert not (tmp_path / "escape.txt").exists()


def test_old_config_files_still_load(tmp_path):
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({"sync_mode": "github", "cloud_path": "/x", "last_sync": {"A": "2024-01-01T00:00:00"}}))
    mgr = SyncManager(config_file=str(cfg))
    assert mgr.config["sync_mode"] == "github"
    assert mgr.config["scan_folders"] == [] and mgr.config["include_savestates"] is False
    assert mgr.config["enabled_emulators"] is None

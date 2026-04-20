import os
import platform

# Expanded list of Pokemon games and some popular 3DS titles
GAME_NAMES = {
    "0004000000055D00": "Pokemon X",
    "0004000000055E00": "Pokemon Y",
    "000400000011C400": "Pokemon Omega Ruby",
    "000400000011C500": "Pokemon Alpha Sapphire",
    "0004000000164100": "Pokemon Sun",
    "0004000000175E00": "Pokemon Moon",
    "00040000001B5000": "Pokemon Ultra Sun",
    "00040000001B5100": "Pokemon Ultra Moon",
    "0004000000116600": "Pokemon Rumble World",
    "000400000011C200": "Pokemon Super Mystery Dungeon",
    "0004000000030700": "Pokemon Mystery Dungeon: Gates to Infinity",
    "0004000000030800": "Pokemon Mystery Dungeon: Gates to Infinity (EU)",
    "0004000000086300": "Pokemon X (Demo)",
    "0004000000086400": "Pokemon Y (Demo)",
    "000400000011C600": "Pokemon Omega Ruby (Demo)",
    "000400000011C700": "Pokemon Alpha Sapphire (Demo)",
    "000400000019C300": "Pokemon Sun (Demo)",
    "000400000019C400": "Pokemon Moon (Demo)",
}

def get_citra_base_path():
    """Returns the base path for Citra user data based on the OS."""
    system = platform.system()
    if system == "Windows":
        return os.path.join(os.environ.get("APPDATA", ""), "Citra")
    elif system == "Darwin":  # macOS
        return os.path.expanduser("~/Library/Application Support/Citra")
    else:
        # Default for Linux/Others
        return os.path.expanduser("~/.local/share/citra-emu")

def get_save_data_root(citra_base_path):
    """
    Returns the path to the 'title' directory where saves are stored.
    Citra path structure: sdmc/Nintendo 3DS/<id1>/<id2>/title/00040000/
    """
    if not citra_base_path or not os.path.exists(citra_base_path):
        return None

    sdmc_path = os.path.join(citra_base_path, "sdmc", "Nintendo 3DS")
    if not os.path.exists(sdmc_path):
        return None
    
    try:
        id1_folders = [f for f in os.listdir(sdmc_path) if os.path.isdir(os.path.join(sdmc_path, f))]
        for id1 in id1_folders:
            id1_path = os.path.join(sdmc_path, id1)
            id2_folders = [f for f in os.listdir(id1_path) if os.path.isdir(os.path.join(id1_path, f))]
            for id2 in id2_folders:
                title_path = os.path.join(id1_path, id2, "title")
                if os.path.exists(title_path):
                    return title_path
    except Exception:
        pass
    
    return None

def find_game_saves(title_root):
    """
    Scans the title_root for ALL 3DS games and identifies known ones.
    """
    found_games = []
    if not title_root or not os.path.exists(title_root):
        return found_games

    # Most 3DS games are under 00040000
    # There are also 00040002 (Demos), 0004008c (Add-on content), etc.
    type_folders = ["00040000", "00040002"]
    
    for type_folder in type_folders:
        base_path = os.path.join(title_root, type_folder)
        if not os.path.exists(base_path):
            continue

        try:
            game_ids = [f for f in os.listdir(base_path) if os.path.isdir(os.path.join(base_path, f))]
            for short_id in game_ids:
                # Reconstruct full ID (approximately, for identification)
                full_id = (type_folder + short_id).upper()
                save_file_path = os.path.join(base_path, short_id, "data", "00000001", "main")

                if os.path.exists(save_file_path):
                    game_name = GAME_NAMES.get(full_id, f"Unknown Game ({full_id})")
                    found_games.append({
                        "name": game_name,
                        "id": full_id,
                        "local_path": save_file_path,
                        "is_pokemon": "Pokemon" in game_name
                    })
        except Exception:
            continue
            
    # Sort: Pokemon games first, then by name
    found_games.sort(key=lambda x: (not x["is_pokemon"], x["name"]))
    return found_games

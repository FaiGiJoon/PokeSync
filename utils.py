import os
import platform

# Expanded list of Pokemon games and some popular 3DS titles
GAME_NAMES = {
    # Pokemon Mainline
    "0004000000055D00": "Pokemon X",
    "0004000000055E00": "Pokemon Y",
    "000400000011C400": "Pokemon Omega Ruby",
    "000400000011C500": "Pokemon Alpha Sapphire",
    "0004000000164100": "Pokemon Sun",
    "0004000000175E00": "Pokemon Moon",
    "00040000001B5000": "Pokemon Ultra Sun",
    "00040000001B5100": "Pokemon Ultra Moon",

    # Pokemon Spin-offs
    "0004000000116600": "Pokemon Rumble World",
    "000400000011C200": "Pokemon Super Mystery Dungeon",
    "0004000000030700": "Pokemon Mystery Dungeon: Gates to Infinity",
    "0004000000030800": "Pokemon Mystery Dungeon: Gates to Infinity (EU)",
    "0004000000121400": "Pokemon Picross",
    "00040000000E3900": "Pokemon Battle Trozei",
    "0004000000126300": "Pokemon Shuffle",
    "000400000017AB00": "Detective Pikachu",

    # Pokemon Demos
    "0004000000086300": "Pokemon X (Demo)",
    "0004000000086400": "Pokemon Y (Demo)",
    "000400000011C600": "Pokemon Omega Ruby (Demo)",
    "000400000011C700": "Pokemon Alpha Sapphire (Demo)",
    "000400000019C300": "Pokemon Sun (Demo)",
    "000400000019C400": "Pokemon Moon (Demo)",

    # Other Popular 3DS Games
    "0004000000030100": "Mario Kart 7",
    "0004000000086B00": "The Legend of Zelda: A Link Between Worlds",
    "0004000000033500": "The Legend of Zelda: Ocarina of Time 3D",
    "0004000000125500": "The Legend of Zelda: Majora's Mask 3D",
    "00040000000A0500": "Animal Crossing: New Leaf",
    "0004000000198100": "Animal Crossing: New Leaf - Welcome amiibo",
    "00040000000EE000": "Super Smash Bros. for Nintendo 3DS",
    "000400000008C300": "Fire Emblem Awakening",
    "000400000012DE00": "Fire Emblem Fates",
    "0004000000030600": "Super Mario 3D Land",
    "000400000007AE00": "New Super Mario Bros. 2",
    "0004000000054000": "Luigi's Mansion: Dark Moon",
    "0004000000191600": "Metroid: Samus Returns",
    "00040000000EDF00": "Monster Hunter 4 Ultimate",
    "0004000000163600": "Monster Hunter Generations",
}

def get_citra_base_path():
    """Returns the base path for Citra user data based on the OS."""
    # Check for environment variable override
    env_path = os.environ.get("CITRA_PATH")
    if env_path:
        return os.path.abspath(env_path)

    system = platform.system()
    if system == "Windows":
        return os.path.join(os.environ.get("APPDATA", ""), "Citra")
    elif system == "Darwin":  # macOS
        return os.path.expanduser("~/Library/Application Support/Citra")
    else:
        return os.path.expanduser("~/.local/share/citra-emu")

def get_save_data_root(citra_base_path):
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
    found_games = []
    if not title_root or not os.path.exists(title_root):
        return found_games

    type_folders = ["00040000", "00040002"]
    
    for type_folder in type_folders:
        base_path = os.path.join(title_root, type_folder)
        if not os.path.exists(base_path):
            continue

        try:
            game_ids = [f for f in os.listdir(base_path) if os.path.isdir(os.path.join(base_path, f))]
            for short_id in game_ids:
                full_id = (type_folder + short_id).upper()
                save_file_path = os.path.join(base_path, short_id, "data", "00000001", "main")

                if os.path.exists(save_file_path):
                    game_name = GAME_NAMES.get(full_id, f"Unknown Game ({full_id})")
                    found_games.append({
                        "name": game_name,
                        "id": full_id,
                        "local_path": save_file_path,
                        "is_pokemon": "Pokemon" in game_name or "Pikachu" in game_name
                    })
        except Exception:
            continue
            
    found_games.sort(key=lambda x: (not x["is_pokemon"], x["name"]))
    return found_games

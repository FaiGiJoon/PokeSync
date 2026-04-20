import os
import platform

POKEMON_GAMES = {
    "Pokemon X": "0004000000055D00",
    "Pokemon Y": "0004000000055E00",
    "Pokemon Omega Ruby": "000400000011C400",
    "Pokemon Alpha Sapphire": "000400000011C500",
}

def get_citra_base_path():
    """Returns the base path for Citra user data based on the OS."""
    system = platform.system()
    if system == "Windows":
        return os.path.join(os.environ.get("APPDATA", ""), "Citra")
    elif system == "Darwin":  # macOS
        return os.path.expanduser("~/Library/Application Support/Citra")
    else:
        # For Linux or other systems, usually ~/.local/share/citra-emu or similar
        # but the user specifically asked for Windows (Alienware) and Mac.
        return os.path.expanduser("~/.local/share/citra-emu")

def get_save_data_root(citra_base_path):
    """
    Returns the path to the 'title' directory where saves are stored.
    Citra path structure: sdmc/Nintendo 3DS/<id1>/<id2>/title/00040000/
    """
    sdmc_path = os.path.join(citra_base_path, "sdmc", "Nintendo 3DS")
    if not os.path.exists(sdmc_path):
        return None
    
    # Nintendo 3DS folder contains a folder with 32 zeros, usually.
    # But it can be different. We'll look for folders.
    try:
        id1_folders = [f for f in os.listdir(sdmc_path) if os.path.isdir(os.path.join(sdmc_path, f))]
        if not id1_folders:
            return None
        
        # Usually there's only one.
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
    Scans the title_root for known Pokemon games.
    Returns a list of dicts with game name and its local save path.
    """
    found_games = []
    if not title_root or not os.path.exists(title_root):
        return found_games

    # Pokemon games are under 00040000
    base_id = "00040000"
    base_path = os.path.join(title_root, base_id)
    
    if not os.path.exists(base_path):
        return found_games

    for game_name, full_id in POKEMON_GAMES.items():
        # The folder name is the last 8 chars of the title ID in Citra's title folder
        # Actually, it's the full title ID but separated. 
        # Wait, Citra uses the lower 8 hex digits as the folder name under 00040000.
        # e.g. 0004000000055D00 -> title/00040000/00055d00/data/00000001/main
        short_id = full_id[8:].lower()
        save_file_path = os.path.join(base_path, short_id, "data", "00000001", "main")
        
        if os.path.exists(save_file_path):
            found_games.append({
                "name": game_name,
                "id": full_id,
                "local_path": save_file_path
            })
            
    return found_games

from sync_manager import SyncManager
from gui import PokeSyncGUI

def main():
    manager = SyncManager()
    app = PokeSyncGUI(manager)
    app.mainloop()

if __name__ == "__main__":
    main()

import subprocess
import sys
import os
import shlex

def sync_data(remote_user, remote_host, remote_port, remote_path, local_path):
    """
    Uses scp to download the latest save file from a remote machine.
    Attempts to find the latest 'main' file if remote_path is a directory (Linux remotes only).
    """
    print(f"Syncing from {remote_user}@{remote_host}:{remote_path}...")

    # Ensure local directory exists
    os.makedirs(os.path.dirname(local_path), exist_ok=True)

    # If the user provided a directory, we try to find the 'main' save file
    # This uses a remote find command via ssh.
    # shlex.quote is used to prevent shell injection.
    remote_target = remote_path
    quoted_remote_path = shlex.quote(remote_path)

    try:
        # This find command is specific to Linux-like remotes.
        find_script = f"find {quoted_remote_path} -name main -type f -printf '%T@ %p\\n' | sort -n | tail -1 | cut -d' ' -f2-"
        find_cmd = [
            "ssh",
            "-p", str(remote_port),
            f"{remote_user}@{remote_host}",
            find_script
        ]
        find_result = subprocess.run(find_cmd, capture_output=True, text=True, timeout=10)
        if find_result.returncode == 0 and find_result.stdout.strip():
            remote_target = find_result.stdout.strip()
            print(f"Found latest save at: {remote_target}")
    except Exception as e:
        # Fallback to the provided path if ssh find fails
        print(f"Could not perform remote search (fallback to provided path): {e}")

    # Construct SCP command
    # -P: port, -p: preserve mtimes
    # We use shlex.quote for the remote source to handle spaces or special characters safely
    quoted_remote_source = f"{remote_user}@{remote_host}:{shlex.quote(remote_target)}"
    cmd = [
        "scp",
        "-P", str(remote_port),
        "-p",
        quoted_remote_source,
        local_path
    ]

    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("Sync complete!")
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"Sync failed with error code {e.returncode}")
        print(e.stderr)
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 6:
        print("Usage: python sync_data.py [user] [host] [port] [remote_save_path] [local_backup_path]")
        print("Example: python sync_data.py user 100.x.y.z 22 /app/saves/main ./local_backup/main")
        sys.exit(1)

    sync_data(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5])

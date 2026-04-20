# Running PokeSync with Docker

If you prefer to run PokeSync in a containerized environment, you can use Docker. Note that since this is a GUI application, you will need an X11 server or similar setup to display the window.

## Prerequisites
- Docker installed.
- (Linux) X11 server running.
- (Windows/macOS) XSrv or XQuartz.

## Building the Image
```bash
docker build -t pokesync .
```

## Running the Container
### Linux
```bash
xhost +local:docker
docker run -it --rm \
    -e DISPLAY=$DISPLAY \
    -v /tmp/.X11-unix:/tmp/.X11-unix \
    -v ~/.local/share/citra-emu:/root/.local/share/citra-emu \
    -v $(pwd):/app \
    pokesync
```

### Windows (using VcXsrv)
1. Start VcXsrv with "Disable access control" checked.
2. Run in PowerShell:
```powershell
docker run -it --rm `
    -e DISPLAY=host.docker.internal:0.0 `
    -v ${HOME}/AppData/Roaming/Citra:/root/.local/share/citra-emu `
    -v ${PWD}:/app `
    pokesync
```

## Notes
- The Dockerfile installs necessary libraries for Tkinter to run inside the container.
- We mount the Citra configuration directory to `/root/.local/share/citra-emu` inside the container so the app can find your saves.

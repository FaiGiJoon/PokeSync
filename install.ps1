# Project Aether-Vault: Orchestration Script (Windows)

Write-Host "Initializing Hardened Infrastructure (Windows)..." -ForegroundColor Cyan

# Check for Virtualization support
$virt = Get-WmiObject -Class Win32_Processor | Select-Object -ExpandProperty VirtualizationFirmwareEnabled
if ($virt) {
    Write-Host "Virtualization support detected." -ForegroundColor Green
} else {
    Write-Host "Warning: Hardware virtualization not enabled in BIOS." -ForegroundColor Yellow
}

# Dependency Checks (simplified for script)
function Check-Command($cmd) {
    return (Get-Command $cmd -ErrorAction SilentlyContinue)
}

if (!(Check-Command "docker")) {
    Write-Host "Docker Desktop not found. Please install it from docker.com" -ForegroundColor Yellow
}
if (!(Check-Command "git")) {
    Write-Host "Git not found. Installing via winget..." -ForegroundColor Yellow
    winget install --id Git.Git -e --source winget
}
if (!(Check-Command "tailscale")) {
    Write-Host "Tailscale not found. Installing via winget..." -ForegroundColor Yellow
    winget install --id Tailscale.Tailscale -e --source winget
}

# Directories
New-Item -ItemType Directory -Force -Path "backups", "save_repo", "logs"

# Service Persistence (Task Scheduler)
$Action = New-ScheduledTaskAction -Execute "docker-compose.exe" -Argument "up -d" -WorkingDirectory $PWD
$Trigger = New-ScheduledTaskTrigger -AtLogOn
Register-ScheduledTask -TaskName "AetherVault-Service" -Action $Action -Trigger $Trigger -Description "Project Aether-Vault Core Service" -Force

Write-Host "Phase 1 complete." -ForegroundColor Green

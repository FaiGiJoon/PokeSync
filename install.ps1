# PokeSync Setup Script for Windows

Write-Host "🚀 Starting PokeSync setup..." -ForegroundColor Cyan

# Check for Python
if (!(Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "❌ Python is not installed. Please install it and try again." -ForegroundColor Red
    exit
}

# Check for Git
if (!(Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Host "❌ Git is not installed. Please install it and try again." -ForegroundColor Red
    exit
}

# Create directories
Write-Host "📁 Creating necessary directories..." -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path "backups"
New-Item -ItemType Directory -Force -Path "save_repo"

# Create config.json if it doesn't exist to prevent Docker volume issues
if (!(Test-Path "config.json")) {
    Write-Host "⚙️ Initializing config.json..." -ForegroundColor Yellow
    "{}" | Out-File -FilePath "config.json" -Encoding ascii
}

# Install dependencies
Write-Host "📦 Installing dependencies..." -ForegroundColor Yellow
python -m pip install -r requirements.txt

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Setup complete! You can now run PokeSync using:" -ForegroundColor Green
    Write-Host "   python main.py"

    # Optional: Register Task Scheduler for auto-run
    $Action = New-ScheduledTaskAction -Execute "python.exe" -Argument "$PWD\main.py" -WorkingDirectory $PWD
    $Trigger = New-ScheduledTaskTrigger -AtLogOn
    $Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
    try {
        Register-ScheduledTask -TaskName "PokeSync" -Action $Action -Trigger $Trigger -Settings $Settings -Description "PokeSync Universal Save Sync" -ErrorAction SilentlyContinue
        Write-Host "⏰ Task Scheduler entry created (Runs at logon)." -ForegroundColor Green
    } catch {
        Write-Host "⚠️ Could not create Task Scheduler entry (may require Admin)." -ForegroundColor Yellow
    }
} else {
    Write-Host "❌ Failed to install dependencies. Please check your internet connection and try again." -ForegroundColor Red
}

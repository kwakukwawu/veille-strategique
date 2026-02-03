<#
Setup script for Veille Strategique
Place this script in the `backend` folder and run it from PowerShell.

Features:
- Check for Python 3.11 (offer to install via winget if available)
- Remove and recreate virtualenv with Python 3.11
- Optionally set ExecutionPolicy for current user to RemoteSigned
- Activate venv, update pip, install requirements
- Optionally start the app and open http://localhost:5000

Usage:
# Run from backend folder in PowerShell
PS> .\setup-python311.ps1
# To install and run the app after install:
PS> .\setup-python311.ps1 -RunApp
# If script execution is blocked, run with:
PS> powershell -ExecutionPolicy Bypass -File .\setup-python311.ps1
#>
param(
    [switch]$RunApp
)

function Write-Info($msg){ Write-Host "[INFO] $msg" -ForegroundColor Cyan }
function Write-Warn($msg){ Write-Host "[WARN] $msg" -ForegroundColor Yellow }
function Write-ErrorMsg($msg){ Write-Host "[ERROR] $msg" -ForegroundColor Red }

# Move to script folder
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

Write-Info "Script started in: $ScriptDir"

# 1) Check for Python 3.11
$py311 = & py -3.11 --version 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Info "Python 3.11 detected: $py311"
} else {
    Write-Warn "Python 3.11 not found."
    $winget = Get-Command winget -ErrorAction SilentlyContinue
    if ($winget) {
        $install = Read-Host "Install Python 3.11 with winget now? (y/N)"
        if ($install -match '^[yY]') {
            Write-Info "Attempting install via winget (admin privileges may be required)..."
            try {
                Start-Process -FilePath "winget" -ArgumentList 'install','--id','Python.Python.3.11','-e' -Wait -NoNewWindow
                Write-Info "Installation done. Verifying..."
                & py -3.11 --version
            } catch {
                Write-ErrorMsg "winget install failed. Please install Python 3.11 from https://python.org"
                exit 1
            }
        } else {
            Write-Warn "User cancelled Python installation. Exiting."
            exit 1
        }
    } else {
        Write-ErrorMsg "winget not found. Please install Python 3.11 from https://python.org"
        exit 1
    }
}

# 2) Remove existing venv and recreate with py -3.11
if (Test-Path .\venv) {
    $confirm = Read-Host "A venv exists. Delete and recreate? (y/N)"
    if ($confirm -notmatch '^[yY]') { Write-Warn "Aborting venv recreation."; exit 1 }
    Write-Info "Removing existing venv..."
    Remove-Item -Recurse -Force .\venv
}

Write-Info "Creating virtualenv with Python 3.11..."
$create = & py -3.11 -m venv .\venv
if ($LASTEXITCODE -ne 0) { Write-ErrorMsg "Failed to create virtualenv with py -3.11. Check Python install."; exit 1 }

# 3) Execution policy suggestion
$currentPolicy = Get-ExecutionPolicy -Scope CurrentUser -ErrorAction SilentlyContinue
if ($currentPolicy -ne 'RemoteSigned') {
    Write-Warn "ExecutionPolicy CurrentUser = $currentPolicy"
    $setPolicy = Read-Host "Set ExecutionPolicy CurrentUser -> RemoteSigned? (y/N)"
    if ($setPolicy -match '^[yY]') {
        try {
            Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser -Force
            Write-Info "ExecutionPolicy updated: $(Get-ExecutionPolicy -Scope CurrentUser)"
        } catch {
            Write-Warn "Failed to change ExecutionPolicy automatically. Run: Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser"
        }
    } else {
        Write-Warn "ExecutionPolicy unchanged. You can activate the venv via CMD if necessary."
    }
} else {
    Write-Info "ExecutionPolicy CurrentUser = RemoteSigned (OK)"
}

# 4) Activate the venv and install dependencies
Write-Info "Activating virtualenv (PowerShell)..."
. .\venv\Scripts\Activate.ps1
if ($?) {
    Write-Info "Virtualenv activated: $(Get-Command python)."
} else {
    Write-ErrorMsg "Could not activate virtualenv via PowerShell. Try: .\\venv\\Scripts\\activate.bat in CMD"; exit 1
}

Write-Info "Updating pip and installing dependencies..."
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { Write-ErrorMsg "Dependency installation failed."; exit 1 }

Write-Info "Dependencies installed"

# 5) Optional: start the app
if ($RunApp) {
    Write-Info "Starting Flask application..."
    Start-Process -FilePath "python" -ArgumentList "app.py" -NoNewWindow
    Start-Sleep -Seconds 2
    Write-Info "Opening http://localhost:5000 in the default browser..."
    Start-Process "http://localhost:5000"
    Write-Info "If the app does not respond, check the port and logs in the console."
} else {
    Write-Info "To start the app now, run: python app.py"
}

Write-Info "Script finished."
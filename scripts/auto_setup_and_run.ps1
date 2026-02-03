<#
Auto setup script for Veille Stratégique (Windows PowerShell)
- Stops python processes
- Installs Python 3.11 via winget if missing
- Creates virtualenv in ./venv using python3.11
- Installs requirements from backend/requirements.txt
- Starts the Flask app in background and writes logs to ./logs/

Run as: PowerShell -ExecutionPolicy Bypass -File .\scripts\auto_setup_and_run.ps1
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

Write-Host "== Veille Stratégique automatic setup ==" -ForegroundColor Cyan

# Allow script execution in this session
try{
    Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned -Force -ErrorAction SilentlyContinue
} catch {
    Write-Warning "Unable to set ExecutionPolicy for this session: $($_.Exception.Message)"
}

function Find-Python311 {
    # Try py launcher
    try{
        $res = & py -3.11 -c "import sys; print(sys.executable)" 2>&1
        if($LASTEXITCODE -eq 0 -and $res){ return $res.Trim() }
    } catch {}

    # Try common commands
    foreach($cmd in @('python3.11','python3','python')){
        try{
            $p = Get-Command $cmd -ErrorAction Stop | Select-Object -First 1 -ExpandProperty Definition
            $v = & $p -c "import sys; print(sys.version_info[:3])" 2>&1
            if($v -match "\(3,\s*11") { return $p }
        } catch{}
    }
    return $null
}

$pythonExe = Find-Python311
if(-not $pythonExe){
    Write-Host "Python 3.11 introuvable. Tentative d'installation via winget..." -ForegroundColor Yellow
    if(Get-Command winget -ErrorAction SilentlyContinue){
        try{
            winget install --id=Python.Python.3.11 -e --source winget --accept-package-agreements --accept-source-agreements -h
        } catch {
            Write-Error "winget install failed: $($_.Exception.Message)"
            exit 1
        }
        # Retry find
        Start-Sleep -Seconds 2
        $pythonExe = Find-Python311
    } else {
        Write-Error "winget introuvable. Impossible d'installer automatiquement Python 3.11. Installez Python3.11 manuellement puis relancez ce script."
        exit 1
    }
}

if(-not $pythonExe){
    Write-Error "Python 3.11 toujours introuvable après tentative d'installation. Abandon."
    exit 1
}

Write-Host "Utilisation de Python: $pythonExe" -ForegroundColor Green

# Stop python processes to avoid file locks
try{
    $procs = Get-Process -Name python -ErrorAction SilentlyContinue
    if($procs){
        Write-Host "Arrêt des processus python en cours..." -ForegroundColor Yellow
        $procs | ForEach-Object { Stop-Process -Id $_.Id -Force }
        Start-Sleep -Milliseconds 500
    }
} catch {
    Write-Warning "Erreur lors de l'arrêt des processus python: $($_.Exception.Message)"
}

# Remove existing venv if present
if(Test-Path .\venv){
    Write-Host "Suppression de .\venv existant..." -ForegroundColor Yellow
    try{ Remove-Item -LiteralPath .\venv -Recurse -Force } catch { Write-Warning "Impossible de supprimer .\venv: $($_.Exception.Message)" }
}

# Create virtualenv
Write-Host "Création du virtualenv avec $pythonExe..." -ForegroundColor Cyan
& $pythonExe -m venv .\venv
if($LASTEXITCODE -ne 0){ Write-Error "Échec création du venv"; exit 1 }

# Upgrade pip and install requirements
Write-Host "Activation du venv et installation des dépendances..." -ForegroundColor Cyan
$venvPython = Join-Path $PWD '.\venv\Scripts\python.exe'
& $venvPython -m pip install --upgrade pip setuptools wheel
& $venvPython -m pip install -r .\backend\requirements.txt

# Ensure logs dir
if(-not (Test-Path .\logs)) { New-Item -ItemType Directory -Path .\logs | Out-Null }

# Start the app in background, redirecting output
Write-Host "Démarrage de l'application Flask en arrière-plan..." -ForegroundColor Cyan
$logFile = Join-Path $PWD '.\logs\app.log'
$errFile = Join-Path $PWD '.\logs\app.err.log'

try{
    # Start process detached
    $proc = Start-Process -FilePath $venvPython -ArgumentList 'backend\app.py' -NoNewWindow -RedirectStandardOutput $logFile -RedirectStandardError $errFile -PassThru
    Start-Sleep -Seconds 2
    if($proc -and $proc.HasExited -eq $false){
        Write-Host "Application démarrée (PID: $($proc.Id)). Logs: $logFile" -ForegroundColor Green
    } else {
        Write-Warning "Le processus s'est terminé rapidement. Consultez $errFile pour les erreurs."
        Get-Content $errFile -Tail 50
    }
} catch {
    Write-Error "Erreur démarrage app: $($_.Exception.Message)"
    exit 1
}

Write-Host "== Vérification endpoints API ==" -ForegroundColor Cyan
try{
    # Wait a bit and call health endpoint
    Start-Sleep -Seconds 3
    $health = Invoke-RestMethod -Uri http://127.0.0.1:5000/health -Method Get -ErrorAction Stop
    Write-Host "Health: $($health.status) - Service: $($health.service)" -ForegroundColor Green
} catch {
    Write-Warning "Impossible d'atteindre le serveur sur http://127.0.0.1:5000 - vérifiez app logs ($logFile / $errFile)"
}

Write-Host "Script terminé. Pour obtenir le token admin :"
Write-Host 'Invoke-RestMethod -Uri http://127.0.0.1:5000/auth/login -Method Post -Body (ConvertTo-Json @{"email"="admin@veille.ci"; "password"="admin123"}) -ContentType "application/json"'
Write-Host 'Run the command above, then get $response.token' -ForegroundColor Yellow

Write-Host "Logs app: $logFile" -ForegroundColor Cyan
Write-Host "Fin du script." -ForegroundColor Cyan

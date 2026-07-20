$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host 'Building FinWise interface...'
Push-Location (Join-Path $root 'frontend')
try {
    npm.cmd run build
} finally {
    Pop-Location
}

$python = $null
$pythonArgs = @()

$activePython = if ($env:VIRTUAL_ENV) { Join-Path $env:VIRTUAL_ENV 'Scripts\python.exe' } else { $null }
if ($activePython -and (Test-Path $activePython)) {
    try {
        & $activePython -c 'import sys' | Out-Null
        $python = $activePython
    } catch {
        $python = $null
    }
}

if (-not $python) {
    $localPython = Join-Path $root '.venv\Scripts\python.exe'
    if (Test-Path $localPython) {
        try {
            & $localPython -c 'import sys' | Out-Null
            $python = $localPython
        } catch {
            $python = $null
        }
    }
}

if (-not $python) {
    $cmd = Get-Command python -ErrorAction SilentlyContinue
    if ($cmd) {
        $python = $cmd.Source
    }
}

if (-not $python) {
    $cmd = Get-Command py -ErrorAction SilentlyContinue
    if ($cmd) {
        $python = $cmd.Source
        $pythonArgs = @('-3')
    }
}

if (-not $python) {
    throw 'FinWise could not find a working Python. Reinstall Python or recreate the virtual environment.'
}

try {
    & $python @pythonArgs -c "import importlib; mods=['flask','flask_cors','mysql.connector','jwt','werkzeug','openpyxl','reportlab','xlrd','pdfplumber']; [importlib.import_module(m) for m in mods]; print('Python dependencies OK')"
    if ($LASTEXITCODE -ne 0) {
        throw 'dependency check failed'
    }
} catch {
    throw "FinWise could not import one or more Python packages. Run: $python $($pythonArgs -join ' ') -m pip install -r backend\requirements.txt"
}

Write-Host 'Starting FinWise at http://127.0.0.1:5000'
Push-Location (Join-Path $root 'backend')
try {
    & $python @pythonArgs app.py
} finally {
    Pop-Location
}

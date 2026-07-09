<#
.SYNOPSIS
    Installs the backend (uvicorn) and frontend (vite dev server) as Windows
    Services via NSSM, so both survive reboot and run without a PowerShell
    window open. Must be run from an elevated ("Run as Administrator") shell.

.NOTES
    Uses uvicorn --reload and `npm run dev`, i.e. still the dev servers, not
    a production build -- picks up code edits automatically. If NSSM loses
    track of uvicorn's reload-watcher subprocess after a crash, restart the
    service (`nssm restart MarketPredictorBackend`) rather than debugging it.
#>

#Requires -RunAsAdministrator
$ErrorActionPreference = 'Stop'

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot '..\..')
$backendDir = Join-Path $repoRoot 'backend'
$frontendDir = Join-Path $repoRoot 'frontend'
$logDir = Join-Path $repoRoot 'logs'
$uvicornExe = Join-Path $backendDir '.venv\Scripts\uvicorn.exe'

if (-not (Test-Path $uvicornExe)) {
    throw "uvicorn.exe not found at $uvicornExe -- run the backend's venv setup first (see README.md)."
}

$npmCommand = Get-Command npm.cmd -ErrorAction SilentlyContinue
if (-not $npmCommand) {
    throw "npm.cmd not found on PATH -- install Node.js first."
}
$npmCmd = $npmCommand.Source

New-Item -ItemType Directory -Force -Path $logDir | Out-Null

if (-not (Get-Command nssm -ErrorAction SilentlyContinue)) {
    if (-not (Get-Command choco -ErrorAction SilentlyContinue)) {
        throw "Neither nssm nor choco found on PATH. Install Chocolatey (https://chocolatey.org/install) or NSSM (https://nssm.cc) manually, then re-run this script."
    }
    Write-Host "Installing NSSM via Chocolatey..."
    choco install nssm -y
    # choco updates PATH for new shells, not this one -- refresh from the registry.
    $env:Path = [System.Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' + [System.Environment]::GetEnvironmentVariable('Path', 'User')
}

function Install-DevService {
    param(
        [string]$Name,
        [string]$Program,
        [string]$Arguments,
        [string]$WorkingDirectory
    )

    $existing = Get-Service -Name $Name -ErrorAction SilentlyContinue
    if ($existing) {
        Write-Host "$Name already exists -- stopping and removing it first."
        nssm stop $Name confirm | Out-Null
        nssm remove $Name confirm | Out-Null
    }

    nssm install $Name $Program
    nssm set $Name AppParameters $Arguments
    nssm set $Name AppDirectory $WorkingDirectory
    nssm set $Name AppStdout (Join-Path $logDir "$Name.out.log")
    nssm set $Name AppStderr (Join-Path $logDir "$Name.err.log")
    nssm set $Name AppRotateFiles 1
    nssm set $Name AppRotateBytes 10485760
    nssm set $Name Start SERVICE_AUTO_START
    nssm set $Name AppStopMethodSkip 0
    nssm set $Name AppStopMethodConsole 1500
    nssm set $Name AppStopMethodWindow 1500

    Write-Host "Installed $Name -- starting it now."
    nssm start $Name
}

Write-Host "`n=== Stop any manually-started backend/frontend in PowerShell first (Ctrl+C) -- both would otherwise fight for ports 8000/80. ===`n"
Read-Host "Press Enter once both manual dev servers are stopped (or if none are running)"

Install-DevService -Name 'MarketPredictorBackend' `
    -Program $uvicornExe `
    -Arguments 'app.main:app --host 127.0.0.1 --port 8000 --reload' `
    -WorkingDirectory $backendDir

# Port 80 (not Vite's default 5173) so http://localhost needs no ":port"
# suffix -- only the service binds it (LocalSystem can bind privileged
# ports); a manually-run `npm run dev` still defaults to 5173.
Install-DevService -Name 'MarketPredictorFrontend' `
    -Program $npmCmd `
    -Arguments 'run dev -- --port 80 --strictPort' `
    -WorkingDirectory $frontendDir

Write-Host "`nDone. Backend: http://localhost:8000/health -- Frontend: http://localhost"
Write-Host "Logs: $logDir"
Write-Host "Manage with: nssm status <name> | nssm restart <name> | nssm stop <name>"
Write-Host "Uninstall with: scripts\windows-service\uninstall-services.ps1"

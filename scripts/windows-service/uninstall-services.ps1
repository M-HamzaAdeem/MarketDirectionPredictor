<#
.SYNOPSIS
    Stops and removes the MarketPredictorBackend / MarketPredictorFrontend
    Windows Services created by install-services.ps1. Must be run elevated.
#>

#Requires -RunAsAdministrator
$ErrorActionPreference = 'Stop'

foreach ($name in @('MarketPredictorBackend', 'MarketPredictorFrontend')) {
    $service = Get-Service -Name $name -ErrorAction SilentlyContinue
    if (-not $service) {
        Write-Host "$name is not installed -- skipping."
        continue
    }
    Write-Host "Stopping and removing $name..."
    nssm stop $name confirm | Out-Null
    nssm remove $name confirm | Out-Null
}

Write-Host "Done."

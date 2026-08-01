# Сборка Quantis (Qt Multimedia) или Quantis-VLC
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("qt", "vlc")]
    [string]$Backend,

    [string]$VlcHome = $env:VLC_HOME
)

$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

if ($Backend -eq "vlc") {
    poetry install --with dev,vlc
    if ($VlcHome) {
        $env:VLC_HOME = $VlcHome
    }
} else {
    poetry install --with dev
}

poetry run python scripts/build_exe.py $Backend

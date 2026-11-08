# SpeakThat Windows Installer
# Usage: irm https://raw.githubusercontent.com/amzmihon/Speak-That-Windows/main/install.ps1 | iex
$ErrorActionPreference = 'Stop'
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  SpeakThat - Windows Text-to-Speech      " -ForegroundColor White
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ">>> Downloading SpeakThat Setup..." -ForegroundColor Yellow

$setupUrl = "https://github.com/amzmihon/Speak-That-Windows/releases/latest/download/SpeakThat-Setup.exe"
$installerPath = "$env:TEMP\SpeakThat-Setup.exe"

[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
Invoke-WebRequest -Uri $setupUrl -OutFile $installerPath -UseBasicParsing

Write-Host ">>> Launching installer..." -ForegroundColor Green
Start-Process -FilePath $installerPath


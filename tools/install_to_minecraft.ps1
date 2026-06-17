# Copy or link this pack into a Minecraft resourcepacks folder.
# Renewed/Legacy need their own Forge profiles — vanilla 1.21+ will not load the LOTR mod.

param(
    [string]$MinecraftDir = "$env:APPDATA\.minecraft",
    [switch]$Link
)

$PackSource = Split-Path -Parent $PSScriptRoot
$PackName = Split-Path -Leaf $PackSource
$Dest = Join-Path $MinecraftDir "resourcepacks\$PackName"

if (-not (Test-Path (Join-Path $MinecraftDir "resourcepacks"))) {
    New-Item -ItemType Directory -Path (Join-Path $MinecraftDir "resourcepacks") -Force | Out-Null
}

if (Test-Path $Dest) {
    Write-Host "Already exists: $Dest"
    exit 0
}

if ($Link) {
    cmd /c mklink /J "$Dest" "$PackSource" | Out-Null
    Write-Host "Junction created: $Dest -> $PackSource"
} else {
    Copy-Item -Path $PackSource -Destination $Dest -Recurse
    Write-Host "Copied pack to: $Dest"
}

Write-Host ""
$TargetFile = Join-Path $PackSource "mod_target.json"
if (Test-Path $TargetFile) {
    $target = Get-Content $TargetFile | ConvertFrom-Json
    Write-Host "Active target: $($target.mod_branch) on Minecraft $($target.minecraft_version)"
}

Write-Host ""
Write-Host "Reminder: Legacy needs Minecraft 1.7.10 + Forge 10.13.4.x (separate instance)."
Write-Host "Your vanilla 26.x install cannot run the LOTR mod — use a 1.7.10 profile or Prism/MultiMC."
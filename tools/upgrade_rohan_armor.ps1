# LOTRO-inspired warm plate grading for Legacy Rohan armour (System.Drawing — no Pillow).
param(
    [switch]$MarshalOnly,
    [switch]$IncludeWeapons
)

$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Drawing

$Root = Split-Path -Parent $PSScriptRoot
$ManifestPath = Join-Path $PSScriptRoot "rohan_armor_manifest.json"
$Manifest = Get-Content $ManifestPath -Raw | ConvertFrom-Json
$SourceDir = Join-Path $Root "source_textures\rohan"
$OutputDir = Join-Path $Root "assets\lotr\textures\items"

if (-not (Test-Path $SourceDir)) {
    python (Join-Path $PSScriptRoot "download_rohan_bases.py")
}

$Targets = @($Manifest.armor)
if ($IncludeWeapons) { $Targets += $Manifest.weapons }
if ($MarshalOnly) { $Targets = $Targets | Where-Object { $_ -match "Marshal" } }

New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

function Apply-LotroRohanStyle {
    param([System.Drawing.Bitmap]$Bmp, [bool]$Marshal)

    $w = $Bmp.Width
    $h = $Bmp.Height

    for ($y = 0; $y -lt $h; $y++) {
        for ($x = 0; $x -lt $w; $x++) {
            $c = $Bmp.GetPixel($x, $y)
            if ($c.A -lt 16) { continue }

            $lum = ($c.R + $c.G + $c.B) / 3.0
            $r = [double]$c.R
            $g = [double]$c.G
            $b = [double]$c.B

            if ($lum -lt 55) {
                $r = [Math]::Min(255, $r * 1.08 + 8)
                $g = [Math]::Min(255, $g * 1.04 + 4)
                $b = [Math]::Max(0,   $b * 0.96)
            }
            elseif ($lum -gt 150) {
                $r = [Math]::Min(255, $r * 1.12)
                $g = [Math]::Min(255, $g * 1.10 + 6)
                $b = [Math]::Max(0,   $b * 0.94)
            }
            else {
                $r = [Math]::Min(255, $r * 1.10)
                $g = [Math]::Min(255, $g * 1.05)
                $b = [Math]::Max(0,   $b * 0.90)
            }

            if ($Marshal -and $lum -gt 90 -and $g -gt $r * 0.85) {
                $r = [Math]::Min(255, $r * 0.92)
                $g = [Math]::Min(255, $g * 1.05)
                $b = [Math]::Min(255, $b * 0.88)
            }

            $Bmp.SetPixel($x, $y, [System.Drawing.Color]::FromArgb($c.A, [int]$r, [int]$g, [int]$b))
        }
    }
    return $Bmp
}

$count = 0
foreach ($name in $Targets) {
    $src = Join-Path $SourceDir $name
    if (-not (Test-Path $src)) {
        Write-Warning "Missing: $src"
        continue
    }

    $marshal = $name -match "Marshal"
    $bmp = [System.Drawing.Bitmap]::FromFile($src)
    $bmp = Apply-LotroRohanStyle -Bmp $bmp -Marshal $marshal
    $dest = Join-Path $OutputDir $name
    $bmp.Save($dest, [System.Drawing.Imaging.ImageFormat]::Png)
    $bmp.Dispose()
    Write-Host "upgraded: $name"
    $count++
}

Write-Host ""
Write-Host "Done - $count Rohan texture(s) -> $OutputDir"
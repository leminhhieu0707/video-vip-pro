# Cài skill Video VIP Pro (Windows). Chạy trong PowerShell:  powershell -ExecutionPolicy Bypass -File setup.ps1
$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
function Need($cmd, $hint) { if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) { Write-Host "THIẾU: $cmd -> $hint" -ForegroundColor Red; $script:missing = $true } }
$missing = $false
Need python "cài Python 3.10+ từ python.org (tick 'Add to PATH') hoặc: winget install Python.Python.3.12"
Need node   "cài Node.js 18+ từ nodejs.org hoặc: winget install OpenJS.NodeJS.LTS"
Need ffmpeg "cài FFmpeg bản đầy đủ: winget install Gyan.FFmpeg  (rồi mở lại PowerShell)"
if ($missing) { Write-Host "Cài xong các mục trên rồi chạy lại setup.ps1" -ForegroundColor Yellow; exit 1 }

Write-Host "1/4 Thư viện Python..." -ForegroundColor Cyan
python -m pip install --upgrade pip | Out-Null
python -m pip install -r "$here\requirements.txt"
python -m pip install onnxruntime-directml
$gpu = (Get-CimInstance Win32_VideoController | Where-Object { $_.Name -match "NVIDIA" })
if ($gpu) { Write-Host "   có card NVIDIA -> thêm thư viện GPU cho Whisper"; python -m pip install nvidia-cublas-cu12 "nvidia-cudnn-cu12>=9,<10" }

Write-Host "2/4 Bộ hiệu ứng chuyển động (Remotion)..." -ForegroundColor Cyan
Push-Location "$here\motion"; npm ci --no-audit --no-fund; Pop-Location

Write-Host "3/4 Font chữ (Be Vietnam Pro, Playfair Display) cho người dùng hiện tại..." -ForegroundColor Cyan
$fontDir = "$env:LOCALAPPDATA\Microsoft\Windows\Fonts"; New-Item -ItemType Directory -Force $fontDir | Out-Null
Get-ChildItem "$here\assets\fonts\*.ttf" | ForEach-Object {
  Copy-Item $_.FullName $fontDir -Force
  New-ItemProperty -Path "HKCU:\Software\Microsoft\Windows NT\CurrentVersion\Fonts" -Name "$($_.BaseName) (TrueType)" -Value "$fontDir\$($_.Name)" -PropertyType String -Force | Out-Null
}

Write-Host "4/4 Âm thanh hiệu ứng + kiểm tra..." -ForegroundColor Cyan
python -X utf8 "$here\scripts\make_sfx.py" | Out-Null
Write-Host "   tải kho âm thanh hot trend (Mixkit, miễn phí dùng thương mại)..."
python -X utf8 "$here\scripts\get_sfx.py"
$hasAss = ffmpeg -hide_banner -filters 2>$null | Select-String " ass "
if (-not $hasAss) { Write-Host "FFmpeg thiếu libass -> cài bản Gyan.FFmpeg (full)" -ForegroundColor Yellow }

$skills = "$env:USERPROFILE\.claude\skills\video-vip-pro"
if (-not (Test-Path $skills) -and ($here -ne $skills)) {
  New-Item -ItemType Directory -Force "$env:USERPROFILE\.claude\skills" | Out-Null
  cmd /c mklink /J "$skills" "$here" | Out-Null
  Write-Host "Đã nối skill vào $skills" -ForegroundColor Green
}
Write-Host "XONG! Mở Claude Code và gõ: dùng skill video-vip-pro edit video <đường dẫn video>" -ForegroundColor Green

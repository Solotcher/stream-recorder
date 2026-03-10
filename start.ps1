# Stream Recorder 서버 시작 스크립트 (PowerShell)
Set-Location $PSScriptRoot

Write-Host "[Stream Recorder] 가상환경을 활성화합니다..." -ForegroundColor Cyan
& ".\.venv\Scripts\Activate.ps1"

Write-Host "[Stream Recorder] 서버를 시작합니다..." -ForegroundColor Green
uvicorn app.main:app --host 0.0.0.0 --port 8000

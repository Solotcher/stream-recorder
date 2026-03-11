@echo off
title Stream Recorder Server
cd /d "%~dp0"

echo [Stream Recorder] 가상환경을 활성화합니다...
call .venv\Scripts\activate.bat

echo [Stream Recorder] 서버를 시작합니다...
uvicorn app.main:app --host 0.0.0.0 --port 8000

pause

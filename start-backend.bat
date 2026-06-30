@echo off
chcp 65001 >nul
set PYTHONUTF8=1
cd /d "%~dp0backend"
echo Starting AI质量平台 Backend...
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

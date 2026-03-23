@echo off
echo Starting XAutomation...
cd /d "%~dp0"
start http://127.0.0.1:5000
.\venv\Scripts\python.exe server.py
pause

@echo off
cd /d "%~dp0"
python web_server.py
if errorlevel 1 pause

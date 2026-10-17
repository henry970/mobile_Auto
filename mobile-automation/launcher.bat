@echo off
REM Double-click to open the Mobile Test Runner window.
cd /d "%~dp0"
if exist .venv\Scripts\pythonw.exe (
  start "" .venv\Scripts\pythonw.exe launcher.py
) else (
  start "" pythonw launcher.py
)

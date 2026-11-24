@echo off
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
  echo Python 3.10+ bulunamadi. Once Python kur.
  pause
  exit /b 1
)
if not exist .venv py -3 -m venv .venv
.venv\Scripts\python.exe -m pip install -q --upgrade pip
.venv\Scripts\python.exe -m pip install -q -r requirements.txt
.venv\Scripts\python.exe app.py

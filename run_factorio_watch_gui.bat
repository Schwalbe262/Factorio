@echo off
setlocal
cd /d "%~dp0"
set PYTHONPATH=src

echo [factorio-ai] Opening a GUI watch client for the current AI world...
echo [factorio-ai] The AI loop is NOT paused in this mode.
echo [factorio-ai] Use run_factorio_review_gui.bat if you want to walk around manually.
python -m factorio_ai.cli watch-gui --window-size 1600x900
if errorlevel 1 (
  echo [factorio-ai] GUI watch failed. Check the printed error above.
  pause
  exit /b 1
)

echo [factorio-ai] GUI watch window closed.

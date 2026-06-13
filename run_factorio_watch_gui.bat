@echo off
setlocal
cd /d "%~dp0"
set PYTHONPATH=src

echo [factorio-ai] Modded multiplayer watch is deferred until the vanilla-compatible executor exists.
echo [factorio-ai] This helper connects to the development mod/RCON server, so it is not public LAN multiplayer
echo [factorio-ai] and it is not achievement-compatible.
if not "%FACTORIO_AI_ALLOW_MODDED_WATCH%"=="1" (
  echo [factorio-ai] Set FACTORIO_AI_ALLOW_MODDED_WATCH=1 only for local development watch mode.
  pause
  exit /b 1
)

echo [factorio-ai] Opening a development GUI watch client for the current AI world...
echo [factorio-ai] The AI loop is NOT paused in this mode.
echo [factorio-ai] Use run_factorio_review_gui.bat if you want to walk around manually.
python -m factorio_ai.cli watch-gui --window-size 1600x900
if errorlevel 1 (
  echo [factorio-ai] GUI watch failed. Check the printed error above.
  pause
  exit /b 1
)

echo [factorio-ai] GUI watch window closed.

@echo off
setlocal
cd /d "%~dp0"
set PYTHONPATH=src

echo [factorio-ai] Launching achievement-compatible vanilla Factorio through Steam...
python -m factorio_ai.cli launch-vanilla-gui || exit /b 1

echo [factorio-ai] This path uses no mods, no RCON, and no Lua commands.
echo [factorio-ai] Future vanilla automation must use normal keyboard and mouse input only.

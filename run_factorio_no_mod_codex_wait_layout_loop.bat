@echo off
setlocal
cd /d "%~dp0"

set PYTHONPATH=src
set FACTORIO_AI_SLURM_ENABLED=1
set FACTORIO_AI_BACKGROUND_LAYOUT_ENABLED=1
set FACTORIO_AI_BACKGROUND_LAYOUT_MODE=attach
set FACTORIO_AI_BACKGROUND_LAYOUT_INTERVAL_SECONDS=20

echo [factorio-ai] Running no-custom-mod Codex wait layout loop.
echo [factorio-ai] This submits simulation-only layout improvement work until runtime\codex-wait.json clears.
python -m factorio_ai.cli run-no-mod-codex-wait-layout-loop --objective launch_rocket_program --cycles 0 --sleep-seconds 20

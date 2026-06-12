# Factorio AI Autoplayer

Layered Factorio AI autoplayer MVP.

The local machine runs Factorio and controls it through RCON. A Factorio Lua mod exposes a small command API:

- `/ai_observe`
- `/ai_action <json>`
- `/ai_wait <ticks>`

Python owns the safety checks, orchestration, logs, and planner loop. Slurm is optional and is used for higher-latency LLM planning or large evaluation jobs, not for directly mutating the Factorio world.

## Current MVP

- Observe player position, inventory, nearby resources, nearby entities, and craftable recipes.
- Execute allowlisted actions only.
- Run a rule-based `produce_iron_plate` skill until at least 10 iron plates exist in inventory or machine outputs.
- Submit planner tasks to a Slurm worker queue when configured, with local rule-based fallback.

## Requirements

- Windows Factorio install. Default path:
  `C:\Program Files (x86)\Steam\steamapps\common\Factorio\bin\x64\factorio.exe`
- Python 3.10+
- Git
- Optional: SSH/SCP access to the Slurm login node.

## Quick Start

Install the project in editable mode:

```powershell
python -m pip install -e .
```

Install the mod into the local runtime mod directory:

```powershell
factorio-ai install-mod
```

Create a save:

```powershell
factorio-ai create-save
```

Start a local Factorio server with RCON:

```powershell
factorio-ai start-server
```

Launch a visible GUI client connected to that local server:

```powershell
factorio-ai launch-gui
```

`launch-gui` calls `factorio.exe` directly with a separate client config under `runtime/client-data`.
This avoids the Steam launch confirmation dialog and lets the dedicated server and GUI client run
at the same time on the local machine.

In another terminal, run the iron plate MVP loop:

```powershell
factorio-ai run-iron-mvp --target 10
```

## Achievement-Compatible Track

The current `factorio-ai` engine is a development and verification track. It uses a mod, RCON,
and Lua commands, so it is not intended for Steam achievement runs.

Achievement-compatible play must run as a separate vanilla track:

- no mods;
- no Lua console commands;
- no RCON world mutation;
- one normal Factorio client controlled through ordinary keyboard and mouse input;
- screen or save-independent perception for inventory, map, entities, and production state.

The planner and skill code should stay portable across both tracks. The mod/RCON track is used to
iterate quickly and prove behavior, then the vanilla track reuses the same high-level decisions with
a different executor.

## Slurm Worker

The remote worker follows the same shape as the reference projects:

- `queue/`
- `running/`
- `results/`
- `failed/`
- `logs/`

Default remote directory: `~/kakao-bot-worker`

Default job name: `AUTO`

When the running job is `AUTO`, planner requests use `srun --jobid=<AUTO_JOB_ID> --overlap`
to execute `factorio_ai.slurm_worker --task ...` inside the existing AUTO allocation. This avoids
submitting another Slurm job and does not require replacing the existing flight worker loop.

Common environment variables:

- `SUPERCOMPUTER_WORKER_SSH_HOST`
- `SUPERCOMPUTER_WORKER_SSH_USER`
- `SUPERCOMPUTER_WORKER_SSH_KEY`
- `SUPERCOMPUTER_WORKER_SSH_PORT`
- `SUPERCOMPUTER_WORKER_REMOTE_DIR`
- `FACTORIO_AI_SLURM_ENABLED=1`
- `FACTORIO_AI_LLM_BASE_URL=http://127.0.0.1:8000/v1`
- `FACTORIO_AI_LLM_MODEL=<model-name>`

Submit a test task:

```powershell
factorio-ai slurm-submit-test
```

## GitHub Workflow

This repository is intended to be committed and pushed by part:

1. Project skeleton.
2. Observation system.
3. Safe action execution.
4. Iron plate MVP.
5. Slurm worker.
6. Research automation expansion.

The current workspace has no GitHub remote configured. Add one before pushing:

```powershell
git remote add origin <github-repo-url>
git push -u origin master
```

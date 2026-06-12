#!/usr/bin/env bash
#SBATCH --job-name=factorio-ai-worker
#SBATCH --output=logs/factorio-ai-worker-%j.out
#SBATCH --error=logs/factorio-ai-worker-%j.err
#SBATCH --time=24:00:00
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=0

set -euo pipefail

ROOT_RAW="${ROOT:-${SUPERCOMPUTER_WORKER_REMOTE_DIR:-$PWD}}"
if [[ "$ROOT_RAW" == "~" ]]; then
  ROOT="$HOME"
elif [[ "$ROOT_RAW" == "~/"* ]]; then
  ROOT="$HOME/${ROOT_RAW:2}"
elif [[ "$ROOT_RAW" == /* ]]; then
  ROOT="$ROOT_RAW"
else
  ROOT="$PWD/$ROOT_RAW"
fi

ENV_NAME="${FACTORIO_AI_SLURM_CONDA_ENV:-factorio-ai}"
POLL_SECONDS="${FACTORIO_AI_WORKER_POLL_SECONDS:-1}"

mkdir -p "$ROOT"/{queue,running,results,failed,logs}
cd "$ROOT/factorio-ai"

if command -v conda >/dev/null 2>&1; then
  eval "$(conda shell.bash hook)"
  if ! conda env list | awk '{print $1}' | grep -qx "$ENV_NAME"; then
    conda create -y -n "$ENV_NAME" python=3.10
  fi
  conda activate "$ENV_NAME"
fi

if [[ -n "${FACTORIO_AI_VLLM_MODEL:-}" ]]; then
  VLLM_PORT="${FACTORIO_AI_VLLM_PORT:-8000}"
  export FACTORIO_AI_LLM_BASE_URL="${FACTORIO_AI_LLM_BASE_URL:-http://127.0.0.1:${VLLM_PORT}/v1}"
  export FACTORIO_AI_LLM_MODEL="${FACTORIO_AI_LLM_MODEL:-$FACTORIO_AI_VLLM_MODEL}"
  if command -v vllm >/dev/null 2>&1; then
    vllm serve "$FACTORIO_AI_VLLM_MODEL" \
      --host 127.0.0.1 \
      --port "$VLLM_PORT" \
      ${FACTORIO_AI_VLLM_ARGS:-} > "$ROOT/logs/vllm-${SLURM_JOB_ID:-local}.out" 2> "$ROOT/logs/vllm-${SLURM_JOB_ID:-local}.err" &
    VLLM_PID="$!"
    trap 'kill "$VLLM_PID" 2>/dev/null || true' EXIT
    sleep "${FACTORIO_AI_VLLM_STARTUP_SECONDS:-30}"
  else
    echo "vllm_not_found=1"
  fi
fi

echo "job_name=${SLURM_JOB_NAME:-factorio-ai-worker}"
echo "job_id=${SLURM_JOB_ID:-local}"
echo "root=$ROOT"
echo "env=$ENV_NAME"
echo "llm_base_url=${FACTORIO_AI_LLM_BASE_URL:-}"
echo "llm_model=${FACTORIO_AI_LLM_MODEL:-}"

python -m factorio_ai.slurm_worker --root "$ROOT" --poll-seconds "$POLL_SECONDS"

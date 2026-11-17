#!/usr/bin/env bash
# Qshift fictional-only Slurm evaluation. Submit through submit_slurm_eval.sh.
set -euo pipefail

: "${QSHIFT_ROOT:?QSHIFT_ROOT was not exported by the submission wrapper}"
: "${QSHIFT_HPC_MODEL:?Set an already-installed model name}"
: "${QSHIFT_HPC_OUTPUT_DIR:?Set an approved scratch/output directory}"

cd "${QSHIFT_ROOT}"
mkdir -p "${QSHIFT_HPC_OUTPUT_DIR}"
metadata="${QSHIFT_HPC_OUTPUT_DIR}/qshift-${SLURM_JOB_ID:-local}-metadata.txt"
result="${QSHIFT_HPC_OUTPUT_DIR}/qshift-${SLURM_JOB_ID:-local}-results.jsonl"
server_pid=""

cleanup() {
  if [[ -n "${server_pid}" ]] && kill -0 "${server_pid}" 2>/dev/null; then
    kill "${server_pid}" 2>/dev/null || true
    wait "${server_pid}" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

{
  date -u
  hostname
  git rev-parse HEAD
  python3 --version
  ollama --version
  echo "model=${QSHIFT_HPC_MODEL}"
  echo "slurm_job_id=${SLURM_JOB_ID:-unknown}"
  echo "slurm_partition=${SLURM_JOB_PARTITION:-unknown}"
  echo "gpu=${CUDA_VISIBLE_DEVICES:-not-exported-by-site}"
  echo "ollama_models_before="
  ollama list
} >"${metadata}"

if ! ollama show "${QSHIFT_HPC_MODEL}" >/dev/null 2>&1; then
  echo "Model ${QSHIFT_HPC_MODEL} is not installed on this node; refusing an automatic download." >&2
  exit 3
fi

if curl --fail --silent --show-error http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
  echo "An Ollama service is already listening on loopback; using it." >>"${metadata}"
else
  OLLAMA_HOST=127.0.0.1:11434 ollama serve >"${QSHIFT_HPC_OUTPUT_DIR}/ollama-${SLURM_JOB_ID:-local}.log" 2>&1 &
  server_pid=$!
  for _ in $(seq 1 30); do
    if curl --fail --silent --show-error http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
      break
    fi
    sleep 1
  done
fi

if ! curl --fail --silent --show-error http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
  echo "Ollama did not become ready on loopback." >&2
  exit 4
fi

QSHIFT_CHANGE_MODEL_PROVIDER=ollama \
QSHIFT_CHANGE_MODEL="${QSHIFT_HPC_MODEL}" \
QSHIFT_EVAL_CONTEXT_MODE=minimal \
QSHIFT_LIVE_EVAL_OUTPUT="${result}" \
make -C "${QSHIFT_ROOT}" eval-live

curl --fail --silent --show-error http://127.0.0.1:11434/api/tags >>"${metadata}"
echo "result=${result}" >>"${metadata}"
echo "Completed fictional-only Qshift evaluation. No model download, public bind or external send occurred."

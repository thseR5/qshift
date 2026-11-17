#!/usr/bin/env bash
set -euo pipefail

# Site-specific values are intentionally required rather than guessed.
: "${QSHIFT_SLURM_PARTITION:?Set the university-approved Slurm partition}"
: "${QSHIFT_SLURM_ACCOUNT:?Set the university-approved Slurm account/project}"
: "${QSHIFT_HPC_MODEL:?Set an already-installed model name; this script never pulls models}"
: "${QSHIFT_HPC_OUTPUT_DIR:?Set an approved scratch/output directory}"
: "${QSHIFT_HPC_AUTHORIZED:?Set QSHIFT_HPC_AUTHORIZED=true only after written site approval}"

if [[ "${QSHIFT_HPC_AUTHORIZED}" != "true" ]]; then
  echo "Refusing submission: university GPU authorization has not been confirmed." >&2
  exit 2
fi

qshift_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
mkdir -p "${QSHIFT_HPC_OUTPUT_DIR}"

exec sbatch \
  --job-name=qshift-forensics \
  --partition="${QSHIFT_SLURM_PARTITION}" \
  --account="${QSHIFT_SLURM_ACCOUNT}" \
  --gres="${QSHIFT_SLURM_GRES:-gpu:1}" \
  --cpus-per-task="${QSHIFT_SLURM_CPUS:-8}" \
  --mem="${QSHIFT_SLURM_MEM:-32G}" \
  --time="${QSHIFT_SLURM_TIME:-00:30:00}" \
  --output="${QSHIFT_HPC_OUTPUT_DIR}/slurm-%j.out" \
  --error="${QSHIFT_HPC_OUTPUT_DIR}/slurm-%j.err" \
  --export="ALL,QSHIFT_ROOT=${qshift_root},QSHIFT_HPC_MODEL=${QSHIFT_HPC_MODEL},QSHIFT_HPC_OUTPUT_DIR=${QSHIFT_HPC_OUTPUT_DIR}" \
  "${qshift_root}/scripts/hpc/qshift_slurm_eval.sbatch"

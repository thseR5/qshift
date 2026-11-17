# University Slurm evaluation preparation

No GPU job has been submitted. The university's authorization for commercial inference,
partition names, account/project, scratch paths, modules and resource limits is not known.

The preparation-only workflow is:

1. Obtain written site approval for fictional-only Qshift evaluation, the approved partition,
   account/project, storage path and software/runtime policy.
2. Ensure the requested model is already installed or supplied through an approved module.
   `scripts/hpc/qshift_slurm_eval.sbatch` refuses to pull a model.
3. Set the site-approved values and `QSHIFT_HPC_AUTHORIZED=true`.
4. Submit with `scripts/hpc/submit_slurm_eval.sh`.

The batch job records Git/model/runtime metadata, binds Ollama to `127.0.0.1`, runs the same
fictional evaluator inside the allocation, writes JSONL output and terminates its local
server through a shell trap. It does not open firewall ports, create tunnels, expose a public
API or process customer data.

Required variables:

```sh
export QSHIFT_SLURM_PARTITION='<site-approved-partition>'
export QSHIFT_SLURM_ACCOUNT='<site-approved-account>'
export QSHIFT_HPC_MODEL='<already-installed-model>'
export QSHIFT_HPC_OUTPUT_DIR='<site-approved-scratch/qshift>'
export QSHIFT_HPC_AUTHORIZED=true
scripts/hpc/submit_slurm_eval.sh
```

Optional resource values default only as placeholders and must be replaced with site-approved
values: `QSHIFT_SLURM_GRES`, `QSHIFT_SLURM_CPUS`, `QSHIFT_SLURM_MEM`, and
`QSHIFT_SLURM_TIME`.

#!/usr/bin/env bash
# Tune threading/affinity for CPU-bound ML workloads
set -e

CORES=${CORES:-$(nproc)}

export OMP_NUM_THREADS=${OMP_NUM_THREADS:-$CORES}
export OPENBLAS_NUM_THREADS=${OPENBLAS_NUM_THREADS:-$CORES}
export MKL_NUM_THREADS=${MKL_NUM_THREADS:-$CORES}
export NUMEXPR_NUM_THREADS=${NUMEXPR_NUM_THREADS:-$CORES}
export PYTORCH_NUM_THREADS=${PYTORCH_NUM_THREADS:-$CORES}

# Better CPU pinning/affinity for OpenMP/Intel MKL
export OMP_PROC_BIND=${OMP_PROC_BIND:-true}
export OMP_PLACES=${OMP_PLACES:-cores}
export KMP_AFFINITY=${KMP_AFFINITY:-granularity=fine,compact,1,0}
export MKL_DYNAMIC=${MKL_DYNAMIC:-FALSE}

echo "[cpu_tune] CORES=$CORES"
echo "[cpu_tune] OMP_NUM_THREADS=$OMP_NUM_THREADS OPENBLAS_NUM_THREADS=$OPENBLAS_NUM_THREADS MKL_NUM_THREADS=$MKL_NUM_THREADS PYTORCH_NUM_THREADS=$PYTORCH_NUM_THREADS"
echo "[cpu_tune] OMP_PROC_BIND=$OMP_PROC_BIND OMP_PLACES=$OMP_PLACES KMP_AFFINITY=$KMP_AFFINITY MKL_DYNAMIC=$MKL_DYNAMIC"

if command -v taskset >/dev/null 2>&1; then
  MASK=$(printf 0x%X $(( (1<<CORES) - 1 )) 2>/dev/null || echo 0)
  echo "[cpu_tune] You can optionally run with: taskset $MASK <command>"
fi

#!/usr/bin/env python3
"""
Script de teste rápido para validar paralelização do joblib com PyTorch.
Simula o comportamento do gridsearch em escala reduzida.
"""

import multiprocessing as mp
import os
import time

import torch
from joblib import Parallel, delayed

# Configurar ambiente
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

print(f"✓ CPUs disponíveis: {mp.cpu_count()}")
print(f"✓ PyTorch threads (main): {torch.get_num_threads()}")


def heavy_task(task_id: int, duration: float = 2.0):
    """Simula trabalho pesado de CPU."""
    # Força 1 thread por worker
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)

    print(f"  Worker {task_id} iniciado [PID={os.getpid()}, threads={torch.get_num_threads()}]")

    # Simular computação PyTorch
    start = time.time()
    x = torch.randn(500, 500)
    for _ in range(100):
        x = torch.mm(x, x.T)
        x = torch.sigmoid(x)

    elapsed = time.time() - start
    print(f"  Worker {task_id} finalizado em {elapsed:.2f}s")
    return {"task_id": task_id, "elapsed": elapsed, "pid": os.getpid()}


if __name__ == "__main__":
    print("\n=== Teste de Paralelização ===")
    n_tasks = 8
    n_jobs = mp.cpu_count()

    print(f"✓ Executando {n_tasks} tarefas em {n_jobs} workers...")
    print("✓ Se paralelização estiver correta, verá múltiplos PIDs diferentes\n")

    start_time = time.time()
    results = Parallel(n_jobs=n_jobs, prefer="processes", verbose=5)(
        delayed(heavy_task)(i) for i in range(n_tasks)
    )
    total_time = time.time() - start_time

    print(f"\n{'='*60}")
    print(f"✓ Teste concluído em {total_time:.2f}s")
    print(f"✓ PIDs únicos utilizados: {len(set(r['pid'] for r in results))}")
    print(f"✓ Speedup estimado: {sum(r['elapsed'] for r in results) / total_time:.1f}x")

    if len(set(r["pid"] for r in results)) > 1:
        print("✅ PARALELIZAÇÃO FUNCIONANDO!")
    else:
        print("❌ PROBLEMA: Apenas 1 PID detectado (sem paralelização)")

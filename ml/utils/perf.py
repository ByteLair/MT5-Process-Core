"""
Utilities to tune CPU-bound training runs (PyTorch and scikit-learn) on CPU servers.

Usage:
- Call tune_environment() early in your script to set sane defaults for BLAS/OpenMP threads.
- For PyTorch heavy workloads, call tune_torch_threads() to set intra/inter-op threads.
- Use fast_read_csv() to leverage pyarrow engine if available.
"""

import multiprocessing
import os
from contextlib import contextmanager

try:
    from threadpoolctl import threadpool_limits  # provided via scikit-learn dependency
except Exception:  # pragma: no cover
    threadpool_limits = None  # type: ignore


def cpu_count() -> int:
    try:
        return len(os.sched_getaffinity(0))  # respects cgroup limits
    except Exception:
        return max(1, multiprocessing.cpu_count())


def tune_environment(default_threads: int | None = None) -> int:
    """Set environment variables for BLAS/OpenMP-based libs to use N threads.

    Order of precedence:
    - If env OMP_NUM_THREADS is set, keep it and return it.
    - Else use provided default_threads or all available CPUs.
    """
    n = int(os.getenv("OMP_NUM_THREADS", "0")) or (default_threads or cpu_count())
    # Set common thread envs for BLAS providers
    os.environ.setdefault("OMP_NUM_THREADS", str(n))
    os.environ.setdefault("OPENBLAS_NUM_THREADS", str(n))
    os.environ.setdefault("MKL_NUM_THREADS", str(n))
    os.environ.setdefault("NUMEXPR_NUM_THREADS", str(n))
    os.environ.setdefault("VECLIB_MAXIMUM_THREADS", str(n))
    os.environ.setdefault("PYTORCH_NUM_THREADS", str(n))
    # Optional: set affinity mask hints for GCC OpenMP
    if "GOMP_CPU_AFFINITY" not in os.environ:
        os.environ["GOMP_CPU_AFFINITY"] = f"0-{max(0, n - 1)}"
    return n


def tune_torch_threads(intra: int | None = None, inter: int | None = None) -> tuple[int, int]:
    """Configure PyTorch intra/inter-op thread counts.

    Returns the (intra, inter) values used.
    """
    try:
        import torch
    except Exception:
        return (0, 0)

    n = cpu_count()
    intra_final = intra or int(os.getenv("PYTORCH_NUM_THREADS", str(n)))
    inter_final = inter or max(1, min(4, n // 4))  # keep inter-op modest on CPU
    try:
        torch.set_num_threads(intra_final)
        torch.set_num_interop_threads(inter_final)
    except Exception:
        pass
    return intra_final, inter_final


@contextmanager
def sklearn_thread_limit(n_threads: int | None = None):
    """Limit scikit-learn (and underlying BLAS) threads inside a context.
    Useful to avoid oversubscription when running torch and sklearn together.
    """
    if threadpool_limits is None:
        yield
        return
    n = n_threads or cpu_count()
    with threadpool_limits(limits=n):
        yield


def fast_read_csv(path: str, **kwargs):
    """Read CSV using pyarrow engine if available, falling back to pandas default.
    Accepts same kwargs as pandas.read_csv.
    """
    import pandas as pd

    engine = kwargs.pop("engine", None)
    if engine is None:
        try:
            import pyarrow  # noqa: F401

            engine = "pyarrow"
        except Exception:
            engine = None
    if engine:
        try:
            return pd.read_csv(path, engine=engine, **kwargs)
        except Exception:
            pass
    return pd.read_csv(path, **kwargs)

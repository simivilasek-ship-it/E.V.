"""
E.V. — Web Dashboard (backward-compatible entrypoint).

Implementation lives in src/api/.
"""
import os
# Prevent PyTorch/OpenMP/loky segfaults when loading SentenceTransformer models
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("LOKY_MAX_CPU_COUNT", "1")
os.environ.setdefault("JOBLIB_MULTIPROCESSING", "0")

from src.api.app import app, run, run_dashboard, run_dashboard_background

__all__ = ["app", "run", "run_dashboard", "run_dashboard_background"]

if __name__ == "__main__":
    from src.api.runner import main

    main()

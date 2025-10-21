"""
Configuração de testes do pacote ML.

Insere a raiz do repositório no sys.path para permitir imports absolutos
como `from ml.worker.train import engine` sem precisar exportar PYTHONPATH.
"""

import os
import sys


def _ensure_repo_root_on_path() -> None:
    tests_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.abspath(os.path.join(tests_dir, os.pardir, os.pardir))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)


_ensure_repo_root_on_path()

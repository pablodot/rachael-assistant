"""
main.py — Punto de entrada del worker de Rachael.

Uso directo:
    python main.py

Equivalente (y forma estándar con arq):
    python -m arq scheduler.WorkerSettings
"""

import logging

from arq import run_worker

from scheduler import WorkerSettings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

if __name__ == "__main__":
    run_worker(WorkerSettings)

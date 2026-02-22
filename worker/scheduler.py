"""
scheduler.py — Configuración del worker arq con cron jobs periódicos.

arq unifica worker y scheduler en un solo proceso:
  - `functions` lista las tareas que se pueden encolar desde fuera.
  - `cron_jobs`  define las tareas periódicas (equivalente a un cron).

Iniciar el worker+scheduler:
    python -m arq scheduler.WorkerSettings
"""

import re

from arq.connections import RedisSettings
from arq.cron import cron

from config import settings
from tasks import browser_task, daily_briefing, health_check, summarize_memory


def _redis_settings() -> RedisSettings:
    """Parsea REDIS_URL y devuelve un RedisSettings para arq."""
    url = settings.redis_url
    # Soporta: redis://host:port, redis://host, redis://:password@host:port
    m = re.match(r"redis://(?:[^@]*@)?([^:/]+)(?::(\d+))?", url)
    if m:
        host = m.group(1)
        port = int(m.group(2)) if m.group(2) else 6379
        return RedisSettings(host=host, port=port)
    # Fallback a defaults
    return RedisSettings()


def _health_check_minutes() -> set[int]:
    """
    Calcula el conjunto de minutos en los que corre health_check.
    HEALTH_CHECK_EVERY_N_MINUTES debe dividir 60; si no, se usa 5.
    """
    n = settings.health_check_every_n_minutes
    if n <= 0 or 60 % n != 0:
        n = 5
    return set(range(0, 60, n))


class WorkerSettings:
    """
    Configuración principal de arq.
    Un solo proceso actúa como worker (procesa colas) y scheduler (cron jobs).
    """

    redis_settings = _redis_settings()

    # Funciones encolables externamente (ej. desde api-core vía arq.create_pool)
    functions = [
        health_check,
        daily_briefing,
        browser_task,
        summarize_memory,
    ]

    # Cron jobs periódicos
    cron_jobs = [
        # health_check cada N minutos (configurable, default 5)
        cron(
            health_check,
            minute=_health_check_minutes(),
            run_at_startup=True,   # ejecutar una vez al arrancar para verificar conectividad
        ),
        # daily_briefing a la hora configurada (default 08:00 UTC)
        cron(
            daily_briefing,
            hour={settings.daily_briefing_hour},
            minute={settings.daily_briefing_minute},
        ),
    ]

    # Límites de concurrencia y timeout
    max_jobs = 10
    job_timeout = 300      # segundos máximo por tarea
    keep_result = 3600     # guardar resultados 1 hora en Redis
    retry_jobs = True
    max_tries = 3

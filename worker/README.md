# rachael-worker

Worker + scheduler del stack Rachael. Implementa la **Misión 4** (SPEC.md §11).

## Qué hace

- **Worker**: procesa tareas encoladas en Redis (por arq o por api-core)
- **Scheduler**: dispara tareas periódicas (health checks, daily briefing)

## Tipos de tarea (SPEC.md §11)

| Tarea | Descripción |
|-------|-------------|
| `health_check` | Ping a api-core, browser-agent y llm-runtime; loguea estado |
| `daily_briefing` | POST `/v1/chat` a api-core con mensaje de buenos días |
| `browser_task` | Encola una tarea de navegador vía api-core |
| `summarize_memory` | Solicita compactación de memoria a api-core |

## Variables de entorno

| Variable | Default | Descripción |
|----------|---------|-------------|
| `REDIS_URL` | `redis://localhost:6379` | URL de Redis |
| `API_CORE_URL` | `http://localhost:8000` | URL base de api-core |
| `BROWSER_AGENT_URL` | `http://localhost:8001` | URL del browser-agent |
| `LLM_RUNTIME_URL` | `http://localhost:11434` | URL del llm-runtime (Ollama) |
| `HEALTH_CHECK_EVERY_N_MINUTES` | `5` | Frecuencia del health-check (debe dividir 60) |
| `DAILY_BRIEFING_HOUR` | `8` | Hora UTC del briefing diario |
| `DAILY_BRIEFING_MINUTE` | `0` | Minuto del briefing diario |

## Arrancar en local

```bash
# Con Redis local corriendo
pip install -r requirements.txt
python main.py
# o equivalente:
python -m arq scheduler.WorkerSettings
```

## Con Docker Compose

```bash
docker compose up -d redis worker
```

## Encolar una tarea manualmente (desde Python)

```python
import asyncio
from arq import create_pool
from arq.connections import RedisSettings

async def main():
    pool = await create_pool(RedisSettings())
    await pool.enqueue_job("browser_task", url="https://example.com", action="screenshot")
    await pool.close()

asyncio.run(main())
```

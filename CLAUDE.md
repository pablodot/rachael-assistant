# Rachael – CLAUDE.md

## Qué es este proyecto

Rachael es una asistente autónoma local-first que funciona como secretaria digital proactiva y operadora de navegador controlada. Lee `SPEC.md` para entender la arquitectura completa antes de tocar código.

## Estructura de servicios

```
api-core/        → Orquestador FastAPI (planificador/ejecutor)
llm-runtime/     → Servidor LLM local (Ollama/vLLM)
memory-db/       → PostgreSQL (memoria estructurada)
vector-store/    → Qdrant (memoria semántica/RAG)
worker/          → Redis + workers (proactividad y background tasks)
browser-agent/   → Playwright en host Linux (fuera de Docker)
```

## Reglas de trabajo en paralelo

- **Cada sesión de Claude Code trabaja en su propio worktree** con rama separada
- **Nunca toques archivos fuera de tu servicio asignado** sin coordinarlo con el orquestador
- **Todo el trabajo va en ramas de feature**, nunca directo a `main`
- **Crea PR cuando termines** un bloque de trabajo para que el orquestador lo revise y mergee

## Nomenclatura de ramas

```
feature/browser-agent-mvp
feature/api-core-planner
feature/memory-db-schema
feature/vector-store-setup
feature/worker-scheduler
```

## Comandos de referencia

```bash
# Levantar servicios Docker (cuando exista docker-compose)
docker compose up -d

# Crear worktree para nueva misión
git worktree add ../rachael-<servicio> -b feature/<servicio>-<descripcion>
```

## Stack técnico

- **Python** para todos los servicios backend
- **FastAPI** para api-core y browser-agent HTTP API
- **Docker + docker-compose** para orquestación de servicios
- **Playwright** para browser-agent (en host, no en Docker)
- **PostgreSQL** para memoria estructurada
- **Qdrant** para memoria vectorial
- **Redis** para cola de tareas
- **Licencia**: MIT o Apache 2.0

## Lo que NO hacer

- No inventar dependencias fuera del stack definido en SPEC.md
- No añadir abstraccciones innecesarias — el código debe ser mínimo y funcional
- No pushear a `main` directamente
- No mezclar responsabilidades entre servicios

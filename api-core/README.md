# api-core – Orquestador de Rachael

Servicio FastAPI que implementa el patrón **Planificador-Ejecutor** de Rachael.

## Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| `POST` | `/v1/chat` | Envía un mensaje; genera plan y lanza ejecución en background |
| `POST` | `/v1/tasks/enqueue` | Encola una tarea sin respuesta conversacional |
| `GET`  | `/v1/tasks/{id}` | Consulta el estado de una tarea |
| `POST` | `/v1/approvals/{id}/ok` | Aprueba un paso que requería `needs_ok=true` |
| `POST` | `/internal/browser/proxy` | Proxy directo al browser-agent (uso interno) |
| `GET`  | `/health` | Health check |

## Flujo principal

```
Usuario → POST /v1/chat
              ↓
         Planner (llm-runtime /v1/chat/completions)
              ↓
         Plan JSON validado
              ↓
         Executor (background)
           ├─ step.needs_ok=false → browser-agent
           └─ step.needs_ok=true  → pausa → POST /v1/approvals/{id}/ok → continúa
```

## Configuración (variables de entorno)

| Variable | Default | Descripción |
|----------|---------|-------------|
| `LLM_BASE_URL` | `http://llm-runtime:11434/v1` | URL del runtime LLM |
| `LLM_MODEL` | `qwen2.5:14b` | Modelo a usar |
| `LLM_TIMEOUT` | `120` | Timeout HTTP en segundos |
| `BROWSER_AGENT_URL` | `http://host.docker.internal:8001` | URL del browser-agent |
| `BROWSER_TIMEOUT` | `60` | Timeout HTTP en segundos |

## Desarrollo local

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## Docker

```bash
docker build -t rachael-api-core .
docker run -p 8000:8000 rachael-api-core
```

## Docs interactivas

Con el servidor corriendo: http://localhost:8000/docs

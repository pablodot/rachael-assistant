# Rachael

Rachael es una asistente autónoma **local-first** que funciona como secretaria digital proactiva y operadora de navegador controlada. Todo corre en tu propia máquina — sin APIs de pago, sin datos que salgan de tu red.

---

## Qué hace

- **Entiende órdenes por voz**: graba audio en el navegador, transcribe con Whisper (en el servidor) y ejecuta la tarea
- **Controla un navegador real**: abre webs, hace clic, escribe, extrae contenido y te resume los resultados en voz
- **Genera planes estructurados**: el LLM local produce un plan JSON paso a paso antes de actuar
- **Pide aprobación** antes de ejecutar acciones irreversibles (pagos, formularios, etc.)
- **Memoria persistente**: guarda conversaciones y tareas en PostgreSQL y búsqueda semántica en Qdrant
- **Comportamiento proactivo**: un worker en segundo plano puede lanzar briefings diarios, health checks y tareas programadas
- **Funciona en LAN/VPN**: la UI es una página web servida por el servidor — accesible desde cualquier dispositivo sin instalar nada

---

## Arquitectura

```
┌─────────────────────────────────────────────────────────┐
│  Navegador del usuario (Chrome/Firefox)                 │
│  UI push-to-talk  ←→  Web Speech TTS                    │
└───────────────────┬─────────────────────────────────────┘
                    │ HTTP
┌───────────────────▼─────────────────────────────────────┐
│  api-core  (FastAPI :8000)                              │
│  • POST /v1/chat        — planificador + ejecutor        │
│  • POST /v1/voice/transcribe  — Whisper STT             │
│  • GET  /v1/tasks/{id}  — polling de estado             │
│  • POST /v1/approvals/{id}/ok  — aprobaciones           │
└──────┬──────────────┬──────────────┬────────────────────┘
       │              │              │
┌──────▼──────┐ ┌─────▼──────┐ ┌────▼────────────────────┐
│ llm-runtime │ │ memory-db  │ │ vector-store             │
│ Ollama      │ │ PostgreSQL │ │ Qdrant                   │
│ :11434      │ │ :5432      │ │ :6333                    │
└─────────────┘ └────────────┘ └─────────────────────────┘
       │
┌──────▼──────────────┐     ┌───────────────────────────┐
│ worker (arq + Redis)│     │ browser-agent  :8001       │
│ • health_check      │     │ Playwright en host Linux   │
│ • daily_briefing    │     │ (fuera de Docker)          │
│ • browser_task      │     └───────────────────────────┘
│ • summarize_memory  │
└─────────────────────┘
```

Todos los servicios excepto `browser-agent` corren en contenedores Docker. El agente de navegador corre en el host para tener acceso al display (real o virtual con Xvfb).

---

## Stack técnico

| Capa | Tecnología |
|------|------------|
| Orquestador | FastAPI (Python) |
| LLM local | Ollama + Qwen 2.5 |
| STT | faster-whisper |
| TTS | Web Speech API (navegador) |
| Navegador | Playwright + Chromium |
| Memoria estructurada | PostgreSQL 16 |
| Memoria semántica | Qdrant + nomic-embed-text |
| Cola de tareas | Redis + arq |
| Contenedores | Docker + Compose |

---

## Requisitos

- Linux (el browser-agent usa el host directamente)
- Docker 24+ con Compose v2
- NVIDIA GPU con drivers y `nvidia-container-toolkit` instalado (recomendado ≥16GB VRAM)
- Python 3.11+ en el host (para browser-agent)
- `xvfb` si el servidor no tiene display físico

### Hardware probado

| Entorno | GPU | Modelo LLM |
|---------|-----|------------|
| Portátil desarrollo | RTX 3060 6GB | `qwen2.5:7b-instruct-q4_K_M` |
| Servidor IA | 2× GTX 1080 Ti + RTX 3060 (34GB) | `qwen2.5:14b-instruct-q8_0` |

---

## Instalación rápida

### 1. Clonar el repo

```bash
git clone https://github.com/pablodot/rachael-assistant.git
cd rachael-assistant
```

### 2. Levantar servicios Docker

```bash
docker compose up -d
```

### 3. Instalar dependencias del browser-agent

```bash
cd browser-agent
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/playwright install chromium --with-deps
cp .env.example .env   # editar si es necesario
```

### 4. Arrancar el browser-agent

```bash
# Con display físico:
source .venv/bin/activate && python main.py

# Sin display (servidor headless):
bash start.sh
```

### 5. Descargar el modelo LLM

```bash
# Portátil / GPU ~6GB:
docker exec rachael-llm-runtime ollama pull qwen2.5:7b-instruct-q4_K_M

# Servidor / GPU ≥16GB:
docker exec rachael-llm-runtime ollama pull qwen2.5:14b-instruct-q8_0

# Modelo de embeddings (necesario para memoria semántica):
docker exec rachael-llm-runtime ollama pull nomic-embed-text
```

### 6. Abrir la interfaz

```
http://localhost:8000
```

> **Nota sobre el micrófono**: los navegadores requieren HTTPS para acceder al micro salvo en `localhost`. Si accedes desde otro dispositivo, configura un proxy HTTPS (Caddy, nginx) o activa el flag de Chrome `chrome://flags/#unsafely-treat-insecure-origin-as-secure`.

---

## Despliegue en servidor remoto

El repo incluye `deploy.sh`, un script que automatiza el despliegue completo en un servidor remoto accesible por SSH:

```bash
./deploy.sh                  # despliegue completo
./deploy.sh --skip-rsync     # saltar sincronización de archivos
./deploy.sh --skip-deps      # saltar instalación de dependencias
./deploy.sh --skip-llm       # saltar descarga del modelo (si ya está)
```

---

## Estado del desarrollo

### Completado ✅

| Módulo | Descripción |
|--------|-------------|
| **browser-agent** | API Playwright completa: open, navigate, click, type, extract, screenshot, close. Allowlist de dominios, stop-points en acciones críticas, perfil Chromium persistente |
| **api-core / planificador** | El LLM genera un plan JSON estructurado a partir de la orden del usuario. El ejecutor recorre los pasos secuencialmente |
| **api-core / ejecutor** | Ejecuta pasos, gestiona aprobaciones (`needs_ok`), almacena resultados |
| **api-core / voz** | Endpoint Whisper STT + UI push-to-talk servida desde el propio servidor |
| **memory-db** | Persistencia real en PostgreSQL (tareas, aprobaciones, sesiones, mensajes) |
| **vector-store** | Cliente Qdrant para guardar y recuperar chunks de conversación por similitud semántica |
| **worker** | Worker arq con scheduler: `health_check` periódico, `daily_briefing`, `browser_task`, `summarize_memory` |
| **despliegue** | Script de despliegue automático con rsync + SSH + Xvfb para servidores sin display |

---

### Pendiente / Work in progress 🔧

| Item | Descripción |
|------|-------------|
| **Tests automatizados** | Suite de tests end-to-end y unitarios (Misión 7 del roadmap) |
| **HTTPS nativo** | Proxy reverso (Caddy/nginx) para acceso seguro desde la LAN sin flags de Chrome |
| **`summarize_memory`** | El worker encola la tarea pero api-core aún no tiene el endpoint de compactación de memoria |
| **Embeddings en el flujo** | El RAG guarda chunks pero el contexto de conversación no se recupera aún en el planner |

---

### Roadmap futuro 🗺️

| Fase | Objetivo |
|------|----------|
| **Fase 2** | Integración de email (IMAP/SMTP) y calendario (CalDAV / Google Calendar) |
| **Fase 3** | Modo supervisor de desarrollo: Rachael puede leer código, abrir terminales y ejecutar comandos con aprobación |

---

## Configuración

El comportamiento se controla mediante variables de entorno. Ver `docker-compose.yml` para los servicios Docker y `browser-agent/.env.example` para el agente de navegador.

Variables principales en `docker-compose.yml`:

| Variable | Servicio | Descripción |
|----------|----------|-------------|
| `LLM_MODEL` | api-core | Modelo Ollama a usar |
| `WHISPER_MODEL` | api-core | Tamaño del modelo Whisper (`tiny`, `base`, `small`) |
| `BROWSER_AGENT_URL` | api-core / worker | URL del browser-agent en el host |

---

## Licencia

Apache 2.0 — ver [LICENSE](LICENSE).

# RACHAEL – AGENTE AUTÓNOMO LOCAL-FIRST
## Especificación Técnica y Estratégica Completa

Rachael es una asistente autónoma local-first diseñada para operar como una secretaria digital proactiva y operadora de navegador controlada. El sistema está diseñado para ser modular, escalable, reproducible y publicable bajo licencia MIT o Apache 2.0.

---

## 1. Visión y Motivación

Rachael no es un chatbot — es una **secretaria digital persistente**. Combina:
- Interacción reactiva con LLM
- Ejecución programada
- Autonomía estructurada y controlada

---

## 2. Principios de Diseño

- **Ejecución local-first**: Todos los servicios principales corren en contenedores Docker locales
- **Control del navegador en el host**: El agente de navegador corre en Linux host, fuera de Docker
- **Aprobación explícita**: Requerida para todas las acciones irreversibles
- **Arquitectura modular**: Permite reemplazar el modelo LLM sin cambiar el resto del sistema
- **Independencia del LLM**: Via API estandarizada compatible con OpenAI
- **Memoria persistente**: Con capas estructurada y semántica
- **Seguridad ante todo**: Política de allowlist de dominios y stop-points en el navegador

---

## 3. Justificación Local-First

- **Privacidad**: Los datos personales nunca salen de la LAN
- **Control de costes**: Sin dependencia de APIs de pago para flujos principales
- **Democratización del hardware**: Funciona en GPUs de 16GB VRAM
- **Flexibilidad**: Capa de modelo reemplazable vía interfaz compatible con OpenAI

---

## 4. Hardware Objetivo

| Componente | Especificación |
|------------|----------------|
| GPU VRAM   | 16GB (línea base) |
| RAM        | 32GB (recomendado) |
| SO         | Linux |

---

## 5. Estrategia de Modelos

Los modelos deben:
- Tener pesos abiertos
- Ofrecer licencia permisiva
- Ser intercambiables

**Familias preferidas:** Qwen (7B–14B cuantizado como default), Mistral

Opcionalmente: modelo especializado en código para tareas de asistente de desarrollo.

---

## 6. Arquitectura del Sistema

El sistema se compone de los siguientes servicios:

| Servicio | Tecnología | Ubicación |
|----------|------------|-----------|
| `api-core` | FastAPI | Contenedor Docker |
| `llm-runtime` | Ollama / vLLM | Contenedor Docker |
| `memory-db` | PostgreSQL | Contenedor Docker |
| `vector-store` | Qdrant | Contenedor Docker |
| `worker + queue` | Redis + workers | Contenedor Docker |
| `browser-agent` | Playwright | Host Linux (fuera de Docker) |

Todos los servicios se comunican por red interna de Docker, excepto `browser-agent`, que expone un endpoint HTTP local seguro.

---

## 7. Servicio A – api-core (FastAPI)

**Rol:** Orquestador central. Gestiona planificación, invocación de herramientas, flujo de aprobaciones, programación de tareas y actualizaciones de memoria.

### Endpoints

```
POST  /v1/chat
POST  /v1/tasks/enqueue
GET   /v1/tasks/{id}
POST  /v1/approvals/{approval_id}/ok
POST  /internal/browser/proxy        (uso interno opcional)
```

### Patrón Planificador-Ejecutor

1. Petición del usuario → el LLM produce un plan JSON estructurado
2. El ejecutor valida el plan
3. Los pasos se ejecutan secuencialmente
4. Si `step.needs_ok == true` → pausa y solicita aprobación al usuario
5. Se almacenan los resultados y las transiciones de estado

---

## 8. Servicio B – llm-runtime

**Rol:** Servir el LLM local con una API compatible con OpenAI.

### Endpoints

```
POST  /v1/chat/completions
POST  /v1/embeddings
```

---

## 9. Servicio C – memory-db (PostgreSQL)

Capa de memoria estructurada que almacena hechos, tareas, aprobaciones y estado a largo plazo.

### Tablas principales

```
sessions
messages
tasks
approvals
entities
browser_runs
```

---

## 10. Servicio D – vector-store (Qdrant)

Memoria semántica para recuperación basada en RAG.

### Colecciones

```
conversation_chunks
notes
web_clips
```

### Política de Chunking

| Parámetro | Valor |
|-----------|-------|
| Tamaño de chunk | 400–800 tokens |
| Solapamiento | 10–20% |
| Metadatos | source, timestamp, tags, session_id |

---

## 11. Servicio E – worker + scheduler

**Rol:** Gestiona el comportamiento proactivo y las comprobaciones en segundo plano. Usa cola Redis + framework de workers.

### Tipos de tareas

```
browser_task
summarize_memory
daily_briefing
health_check
```

---

## 12. Servicio F – browser-agent (Playwright en host)

Corre en el host Linux fuera de Docker. Usa un perfil Chromium dedicado para Rachael. Expone una API HTTP local segura.

### API Contract

```
POST  /v1/browser/open
POST  /v1/browser/navigate
GET   /v1/browser/snapshot
POST  /v1/browser/click
POST  /v1/browser/type
POST  /v1/browser/extract
GET   /v1/browser/screenshot
POST  /v1/browser/close
```

### Políticas de Seguridad

- Allowlist de dominios
- Stop-points en acciones críticas (checkout, pago, envío de formularios)
- Máximo de pasos por tarea
- Detección de campos sensibles

---

## 13. Esquema JSON del Plan (Contrato de Salida del LLM)

```json
{
  "goal": "Buscar hoteles en Valencia",
  "steps": [
    {
      "tool": "browser.open",
      "args": { "url": "https://booking.com" },
      "needs_ok": false
    },
    {
      "tool": "browser.click",
      "args": { "element_id": "search_button" },
      "needs_ok": false
    },
    {
      "tool": "browser.click",
      "args": { "element_id": "checkout_button" },
      "needs_ok": true,
      "ok_prompt": "Entrando al checkout. ¿Confirmar?"
    }
  ]
}
```

---

## 14. Diseño de Memoria (resumen)

Arquitectura de memoria en dos capas:

1. **Almacenamiento relacional estructurado** — PostgreSQL (hechos, tareas, sesiones, aprobaciones)
2. **Almacenamiento vectorial semántico** — Qdrant (recuperación RAG, notas, clips web)

---

## 15. Bucle de Proactividad

- El scheduler dispara evaluaciones periódicas de tareas
- El sistema de colas procesa tareas en segundo plano de forma segura

---

## 16. Roadmap

### Fases estratégicas

| Fase | Objetivo |
|------|----------|
| Fase 1 | Operador browser-first |
| Fase 2 | Integración de email y calendario |
| Fase 3 | Modo supervisor de desarrollo |

### Misiones de desarrollo (paralelas)

| Misión | Descripción | Estado |
|--------|-------------|--------|
| Misión 1 | MVP del browser-agent | ✅ Completada |
| Misión 2 | Planificador/ejecutor de api-core | ✅ Completada |
| Misión 3 | Integración de memoria + vector store | ✅ Completada |
| Misión 4 | Worker en segundo plano + scheduling | Pendiente |
| Misión 5 | Persistencia real en PostgreSQL + Qdrant | Pendiente |
| Misión 6 | Interfaz de voz (STT + TTS) | **Próxima** |
| Misión 7 | Escenarios de demo + tests automatizados | Pendiente |

> Esta especificación está pensada para ser entregada a un agente de código autónomo (Claude Code o similar) para implementar cada servicio de forma independiente y en paralelo.

---

## 17. Interfaz de Voz (Misión 6)

Interacción por voz local mediante push-to-talk. Sin APIs externas, todo corre en local.

### Stack

| Componente | Tecnología | Notas |
|------------|------------|-------|
| STT (voz → texto) | Whisper `base` | ~1GB VRAM, corre en GPU junto al LLM |
| TTS (texto → voz) | Piper | Corre en CPU, muy rápido |
| Interfaz | Python + sounddevice | Captura micrófono con push-to-talk |

### Servicio: `voice-interface`

Corre en el **host** (como el browser-agent), fuera de Docker — necesita acceso al micrófono y altavoces.

### Flujo

```
[usuario mantiene tecla/botón]
        ↓
  graba audio (sounddevice)
        ↓
  Whisper transcribe → texto
        ↓
  POST /v1/chat  →  api-core  →  LLM  →  plan  →  ejecución
        ↓
  respuesta texto
        ↓
  Piper sintetiza → audio
        ↓
  reproduce en altavoces
```

### Modelos Whisper según hardware

| Modelo | VRAM | Velocidad | Calidad |
|--------|------|-----------|---------|
| `tiny` | ~200MB | Muy rápido | Básica |
| `base` | ~500MB | Rápido | **Recomendado** |
| `small` | ~1GB | Medio | Alta |

### Dependencias

```
openai-whisper
sounddevice
piper-tts
numpy
```

### API Contract (interno)

El `voice-interface` no expone API HTTP — es un cliente que consume `/v1/chat` del api-core y reproduce la respuesta. Opcionalmente puede exponer:

```
POST /v1/voice/speak   → sintetiza y reproduce texto arbitrario
GET  /v1/voice/status  → estado del micrófono y modelos cargados
```

---

## 19. Conclusión

Rachael busca cerrar la brecha entre los LLMs reactivos y los agentes autónomos controlados, ofreciendo un sistema que actúa de forma proactiva respetando siempre los límites de aprobación definidos por el usuario.

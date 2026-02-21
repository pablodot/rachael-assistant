"""
POST /v1/chat

Entrada del usuario → planificación → ejecución en background.
Devuelve task_id inmediatamente; el cliente usa GET /v1/tasks/{id} para polling.
"""

import asyncio
import uuid

from fastapi import APIRouter, HTTPException

from app.executor import executor
from app.models import ChatRequest, ChatResponse, TaskRecord, TaskStatus
from app.planner import planner
from app.store import store

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    # Crear registro de tarea
    task = TaskRecord(
        id=str(uuid.uuid4()),
        goal=request.message,
        status=TaskStatus.pending,
    )
    store.save_task(task)

    # Planificar de forma síncrona (el plan suele tardar 1-5 s)
    try:
        plan = await planner.build_plan(request.message)
    except Exception as exc:
        task.status = TaskStatus.failed
        task.error = str(exc)
        store.save_task(task)
        raise HTTPException(status_code=502, detail=f"Error al generar el plan: {exc}")

    task.plan = plan
    task.goal = plan.goal
    store.save_task(task)

    # Lanzar ejecución en background (no bloqueante)
    asyncio.create_task(executor.run(task))

    return ChatResponse(
        task_id=task.id,
        status=task.status,
        message="Plan generado. Ejecución iniciada.",
    )

"""
POST /v1/tasks/enqueue  – encolar una tarea sin esperar respuesta conversacional
GET  /v1/tasks/{id}     – consultar estado de una tarea
"""

import asyncio
import uuid

from fastapi import APIRouter, HTTPException

from app.executor import executor
from app.models import TaskEnqueueRequest, TaskRecord, TaskResponse, TaskStatus
from app.planner import planner
from app.store import store

router = APIRouter()


@router.post("/tasks/enqueue", response_model=TaskResponse, status_code=202)
async def enqueue_task(request: TaskEnqueueRequest) -> TaskResponse:
    task = TaskRecord(
        id=str(uuid.uuid4()),
        goal=request.message,
        status=TaskStatus.pending,
    )
    await store.save_task(task)

    try:
        plan = await planner.build_plan(request.message)
    except Exception as exc:
        task.status = TaskStatus.failed
        task.error = str(exc)
        await store.save_task(task)
        raise HTTPException(status_code=502, detail=f"Error al generar el plan: {exc}")

    task.plan = plan
    task.goal = plan.goal
    await store.save_task(task)

    asyncio.create_task(executor.run(task))

    return _to_response(task)


@router.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str) -> TaskResponse:
    task = await store.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    return _to_response(task)


def _to_response(task: TaskRecord) -> TaskResponse:
    return TaskResponse(
        id=task.id,
        status=task.status,
        goal=task.goal,
        current_step=task.current_step,
        results=task.results,
        pending_approval_id=task.pending_approval_id,
        error=task.error,
        reply=task.reply,
    )

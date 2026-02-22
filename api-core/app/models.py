"""
Modelos Pydantic para el api-core de Rachael.
Cubre: plan JSON (sección 13 de SPEC.md), tasks, approvals y contratos HTTP.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Plan JSON – Contrato de salida del LLM (SPEC.md §13)
# ---------------------------------------------------------------------------

class PlanStep(BaseModel):
    tool: str = Field(..., description="Herramienta a invocar, ej. browser.open")
    args: dict[str, Any] = Field(default_factory=dict)
    needs_ok: bool = Field(False, description="Requiere aprobación explícita del usuario")
    ok_prompt: str | None = Field(None, description="Mensaje mostrado al usuario al solicitar aprobación")


class Plan(BaseModel):
    goal: str
    steps: list[PlanStep]


# ---------------------------------------------------------------------------
# Estado de tareas
# ---------------------------------------------------------------------------

class TaskStatus(str, Enum):
    pending = "pending"
    running = "running"
    paused_for_approval = "paused_for_approval"
    completed = "completed"
    failed = "failed"


class StepResult(BaseModel):
    step_index: int
    tool: str
    args: dict[str, Any]
    status: str  # "ok" | "error" | "skipped"
    output: Any = None
    error: str | None = None


class TaskRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    status: TaskStatus = TaskStatus.pending
    goal: str
    plan: Plan | None = None
    results: list[StepResult] = Field(default_factory=list)
    current_step: int = 0
    error: str | None = None
    reply: str | None = None  # respuesta en lenguaje natural generada por el LLM
    # id de aprobación pendiente (si status == paused_for_approval)
    pending_approval_id: str | None = None


# ---------------------------------------------------------------------------
# Approvals
# ---------------------------------------------------------------------------

class ApprovalRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    task_id: str
    step_index: int
    ok_prompt: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    approved: bool = False
    resolved_at: datetime | None = None


# ---------------------------------------------------------------------------
# Contratos HTTP de entrada
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    message: str = Field(..., description="Mensaje del usuario")
    session_id: str | None = None


class TaskEnqueueRequest(BaseModel):
    message: str = Field(..., description="Descripción de la tarea a ejecutar")
    session_id: str | None = None


# ---------------------------------------------------------------------------
# Contratos HTTP de respuesta
# ---------------------------------------------------------------------------

class ChatResponse(BaseModel):
    task_id: str
    status: TaskStatus
    message: str = "Tarea iniciada"


class TaskResponse(BaseModel):
    id: str
    status: TaskStatus
    goal: str
    current_step: int
    results: list[StepResult]
    pending_approval_id: str | None = None
    error: str | None = None
    reply: str | None = None


class ApprovalResponse(BaseModel):
    approval_id: str
    task_id: str
    ok_prompt: str
    approved: bool

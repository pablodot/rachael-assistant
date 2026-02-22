"""
Store persistente usando PostgreSQL (asyncpg).
Reemplaza el InMemoryStore del MVP.

Tablas usadas (memory-db/init.sql):
  - tasks     → TaskRecord (plan_json almacena plan + results + current_step)
  - approvals → ApprovalRecord

Los asyncio.Event para aprobaciones se mantienen en memoria: son señales
transitorias de proceso y no necesitan persistencia.
"""

from __future__ import annotations

import asyncio
import json
from typing import Optional

import asyncpg

from app.models import ApprovalRecord, Plan, StepResult, TaskRecord, TaskStatus

# ── Mapeo de status modelo ↔ DB ───────────────────────────────────────────────
# El CHECK de tasks en init.sql admite:
#   'pending', 'running', 'waiting_approval', 'done', 'failed', 'cancelled'

_STATUS_TO_DB: dict[TaskStatus, str] = {
    TaskStatus.pending:             "pending",
    TaskStatus.running:             "running",
    TaskStatus.paused_for_approval: "waiting_approval",
    TaskStatus.completed:           "done",
    TaskStatus.failed:              "failed",
}

_STATUS_FROM_DB: dict[str, TaskStatus] = {v: k for k, v in _STATUS_TO_DB.items()}


class PostgreSQLStore:
    """
    Store persistente para TaskRecord y ApprovalRecord.

    Ciclo de vida:
        await store.initialize(database_url)   # en lifespan startup
        ...
        await store.close()                    # en lifespan shutdown
    """

    def __init__(self) -> None:
        self._pool: asyncpg.Pool | None = None
        # Eventos en memoria: se pierden al reiniciar (aceptable en MVP)
        self._approval_events: dict[str, asyncio.Event] = {}

    async def initialize(self, database_url: str) -> None:
        """Crea el pool de conexiones. Llamar desde lifespan de FastAPI."""
        self._pool = await asyncpg.create_pool(database_url, min_size=2, max_size=10)

    async def close(self) -> None:
        if self._pool:
            await self._pool.close()

    @property
    def pool(self) -> asyncpg.Pool:
        assert self._pool is not None, "Store no inicializado. Llama a initialize() primero."
        return self._pool

    # ── Tasks ─────────────────────────────────────────────────────────────────

    async def save_task(self, task: TaskRecord) -> None:
        """Upsert completo del TaskRecord en la tabla tasks."""
        plan_json = json.dumps({
            "plan":                task.plan.model_dump() if task.plan else None,
            "results":             [r.model_dump() for r in task.results],
            "current_step":        task.current_step,
            "pending_approval_id": task.pending_approval_id,
        })
        db_status = _STATUS_TO_DB.get(task.status, "pending")

        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO tasks (id, goal, plan_json, status, error, created_at, updated_at)
                VALUES ($1, $2, $3::jsonb, $4, $5, $6, now())
                ON CONFLICT (id) DO UPDATE SET
                    goal       = EXCLUDED.goal,
                    plan_json  = EXCLUDED.plan_json,
                    status     = EXCLUDED.status,
                    error      = EXCLUDED.error,
                    updated_at = now()
                """,
                task.id,
                task.goal,
                plan_json,
                db_status,
                task.error,
                task.created_at,
            )

    async def get_task(self, task_id: str) -> Optional[TaskRecord]:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT id, goal, plan_json, status, error, created_at, updated_at "
                "FROM tasks WHERE id = $1",
                task_id,
            )
        if not row:
            return None
        return self._row_to_task(row)

    async def list_tasks(self) -> list[TaskRecord]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT id, goal, plan_json, status, error, created_at, updated_at "
                "FROM tasks ORDER BY created_at DESC"
            )
        return [self._row_to_task(r) for r in rows]

    @staticmethod
    def _row_to_task(row: asyncpg.Record) -> TaskRecord:
        data: dict = json.loads(row["plan_json"] or "{}")
        plan_data = data.get("plan")
        plan = Plan.model_validate(plan_data) if plan_data else None
        results = [StepResult.model_validate(r) for r in data.get("results", [])]
        status = _STATUS_FROM_DB.get(row["status"], TaskStatus.pending)

        return TaskRecord(
            id=str(row["id"]),
            goal=row["goal"],
            plan=plan,
            status=status,
            error=row["error"],
            results=results,
            current_step=data.get("current_step", 0),
            pending_approval_id=data.get("pending_approval_id"),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    # ── Approvals ─────────────────────────────────────────────────────────────

    async def save_approval(self, approval: ApprovalRecord) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO approvals (id, task_id, step_index, ok_prompt, status, created_at)
                VALUES ($1, $2, $3, $4, 'pending', $5)
                ON CONFLICT (id) DO NOTHING
                """,
                approval.id,
                approval.task_id,
                approval.step_index,
                approval.ok_prompt,
                approval.created_at,
            )
        # Crear evento en memoria para señalización asíncrona
        if approval.id not in self._approval_events:
            self._approval_events[approval.id] = asyncio.Event()

    async def get_approval(self, approval_id: str) -> Optional[ApprovalRecord]:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT id, task_id, step_index, ok_prompt, status, created_at, resolved_at "
                "FROM approvals WHERE id = $1",
                approval_id,
            )
        if not row:
            return None
        return ApprovalRecord(
            id=str(row["id"]),
            task_id=str(row["task_id"]),
            step_index=row["step_index"],
            ok_prompt=row["ok_prompt"],
            approved=row["status"] == "approved",
            created_at=row["created_at"],
            resolved_at=row["resolved_at"],
        )

    def get_event(self, approval_id: str) -> Optional[asyncio.Event]:
        """Devuelve el asyncio.Event en memoria para la aprobación dada."""
        return self._approval_events.get(approval_id)

    async def resolve_approval(self, approval_id: str) -> bool:
        """Marca la aprobación como aprobada en DB y dispara el evento en memoria."""
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE approvals
                SET status = 'approved', resolved_at = now()
                WHERE id = $1 AND status = 'pending'
                """,
                approval_id,
            )
        # asyncpg devuelve "UPDATE N" como cadena
        updated = int(result.split()[-1])
        if not updated:
            return False

        event = self._approval_events.get(approval_id)
        if event:
            event.set()
        return True


# Singleton compartido por toda la app
store = PostgreSQLStore()

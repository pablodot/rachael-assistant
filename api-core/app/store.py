"""
Store en memoria para tasks y approvals (MVP).
En producción se remplazaría por PostgreSQL (memory-db).
"""

import asyncio
from typing import Optional

from app.models import ApprovalRecord, TaskRecord


class InMemoryStore:
    def __init__(self) -> None:
        self._tasks: dict[str, TaskRecord] = {}
        self._approvals: dict[str, ApprovalRecord] = {}
        # Eventos asyncio para desbloquear el executor cuando llega una aprobación
        self._approval_events: dict[str, asyncio.Event] = {}

    # ------------------------------------------------------------------
    # Tasks
    # ------------------------------------------------------------------

    def save_task(self, task: TaskRecord) -> None:
        from datetime import datetime
        task.updated_at = datetime.utcnow()
        self._tasks[task.id] = task

    def get_task(self, task_id: str) -> Optional[TaskRecord]:
        return self._tasks.get(task_id)

    def list_tasks(self) -> list[TaskRecord]:
        return list(self._tasks.values())

    # ------------------------------------------------------------------
    # Approvals
    # ------------------------------------------------------------------

    def save_approval(self, approval: ApprovalRecord) -> None:
        self._approvals[approval.id] = approval
        if approval.id not in self._approval_events:
            self._approval_events[approval.id] = asyncio.Event()

    def get_approval(self, approval_id: str) -> Optional[ApprovalRecord]:
        return self._approvals.get(approval_id)

    def get_event(self, approval_id: str) -> Optional[asyncio.Event]:
        return self._approval_events.get(approval_id)

    def resolve_approval(self, approval_id: str) -> bool:
        """Marca la aprobación como resuelta y dispara el evento."""
        from datetime import datetime

        approval = self._approvals.get(approval_id)
        if not approval:
            return False

        approval.approved = True
        approval.resolved_at = datetime.utcnow()

        event = self._approval_events.get(approval_id)
        if event:
            event.set()

        return True


# Singleton compartido por toda la app
store = InMemoryStore()

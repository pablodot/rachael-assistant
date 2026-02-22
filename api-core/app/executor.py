"""
Executor: ejecuta los pasos de un Plan de forma secuencial.

Flujo por paso:
  1. Si needs_ok=True → crea aprobación, pausa con asyncio.Event, espera OK.
  2. Despacha la herramienta correcta (browser.* por ahora).
  3. Registra el resultado en el TaskRecord.
  4. Si hay error, marca la tarea como failed y sale.
"""

from __future__ import annotations

import asyncio
import uuid
from typing import Any

from app.clients.browser_client import browser_client
from app.clients.llm_client import llm_client
from app.models import ApprovalRecord, PlanStep, StepResult, TaskRecord, TaskStatus
from app.store import store


class Executor:
    async def run(self, task: TaskRecord) -> None:
        """
        Ejecuta el plan del task en background.
        El task ya debe tener task.plan asignado antes de llamar a este método.
        """
        task.status = TaskStatus.running
        await store.save_task(task)

        plan = task.plan
        assert plan is not None  # garantizado por el caller

        for idx, step in enumerate(plan.steps):
            task.current_step = idx
            await store.save_task(task)

            # 1. Pedir aprobación si es necesario
            if step.needs_ok:
                approved = await self._request_approval(task, idx, step)
                if not approved:
                    # El usuario no aprobó (timeout u otro motivo)
                    await self._record_step(task, idx, step, "skipped", error="Aprobación no recibida")
                    task.status = TaskStatus.failed
                    task.error = f"Paso {idx} requería aprobación pero no se recibió."
                    await store.save_task(task)
                    return

            # 2. Ejecutar la herramienta
            try:
                output = await self._dispatch(step)
                await self._record_step(task, idx, step, "ok", output=output)
            except Exception as exc:
                await self._record_step(task, idx, step, "error", error=str(exc))
                task.status = TaskStatus.failed
                task.error = f"Error en paso {idx} ({step.tool}): {exc}"
                await store.save_task(task)
                return

        task.status = TaskStatus.completed
        try:
            task.reply = await llm_client.generate_reply(
                task.goal,
                [r.model_dump() for r in task.results],
            )
        except Exception:
            task.reply = f"Hecho: {task.goal}"
        await store.save_task(task)

    # ------------------------------------------------------------------
    # Aprobaciones
    # ------------------------------------------------------------------

    async def _request_approval(
        self, task: TaskRecord, step_index: int, step: PlanStep
    ) -> bool:
        approval = ApprovalRecord(
            id=str(uuid.uuid4()),
            task_id=task.id,
            step_index=step_index,
            ok_prompt=step.ok_prompt or f"Aprobar paso {step_index}: {step.tool}?",
        )
        await store.save_approval(approval)

        task.status = TaskStatus.paused_for_approval
        task.pending_approval_id = approval.id
        await store.save_task(task)

        event = store.get_event(approval.id)
        assert event is not None

        # Espera hasta 5 minutos por la aprobación del usuario
        try:
            await asyncio.wait_for(event.wait(), timeout=300)
        except asyncio.TimeoutError:
            return False

        task.status = TaskStatus.running
        task.pending_approval_id = None
        await store.save_task(task)
        return True

    # ------------------------------------------------------------------
    # Dispatch de herramientas
    # ------------------------------------------------------------------

    async def _dispatch(self, step: PlanStep) -> Any:
        service, _, action = step.tool.partition(".")

        if service == "browser":
            return await browser_client.dispatch(action, step.args)

        raise ValueError(f"Servicio desconocido: {service!r}. Solo 'browser' está disponible.")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _record_step(
        self,
        task: TaskRecord,
        idx: int,
        step: PlanStep,
        status: str,
        output: Any = None,
        error: str | None = None,
    ) -> None:
        result = StepResult(
            step_index=idx,
            tool=step.tool,
            args=step.args,
            status=status,
            output=output,
            error=error,
        )
        task.results.append(result)
        await store.save_task(task)


executor = Executor()

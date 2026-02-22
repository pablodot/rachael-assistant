"""
POST /v1/approvals/{approval_id}/ok

El usuario aprueba un paso que requería needs_ok=true.
Dispara el asyncio.Event que desbloquea el Executor.
"""

from fastapi import APIRouter, HTTPException

from app.models import ApprovalResponse
from app.store import store

router = APIRouter()


@router.post("/approvals/{approval_id}/ok", response_model=ApprovalResponse)
async def approve(approval_id: str) -> ApprovalResponse:
    approval = await store.get_approval(approval_id)
    if not approval:
        raise HTTPException(status_code=404, detail="Aprobación no encontrada")

    if approval.approved:
        raise HTTPException(status_code=409, detail="Esta aprobación ya fue procesada")

    resolved = await store.resolve_approval(approval_id)
    if not resolved:
        raise HTTPException(status_code=500, detail="No se pudo resolver la aprobación")

    return ApprovalResponse(
        approval_id=approval.id,
        task_id=approval.task_id,
        ok_prompt=approval.ok_prompt,
        approved=True,
    )

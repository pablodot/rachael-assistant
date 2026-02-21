"""
Planner: llama al LLM y convierte la respuesta JSON en un Plan validado.
"""

from __future__ import annotations

from app.clients.llm_client import llm_client
from app.models import Plan


class Planner:
    async def build_plan(self, user_message: str) -> Plan:
        """
        Envía el mensaje al LLM y parsea el plan JSON resultante.
        Lanza ValueError si el JSON no es un plan válido.
        """
        raw = await llm_client.get_plan_json(user_message)
        try:
            plan = Plan.model_validate(raw)
        except Exception as exc:
            raise ValueError(f"El LLM devolvió un plan inválido: {exc}") from exc

        if not plan.steps:
            raise ValueError("El plan no contiene pasos.")

        return plan


planner = Planner()

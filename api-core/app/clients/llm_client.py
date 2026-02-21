"""
Cliente HTTP para llm-runtime.
Compatible con la API OpenAI /v1/chat/completions.
"""

from __future__ import annotations

import json
from typing import Any

import httpx

from app.config import settings


class LLMClient:
    def __init__(self) -> None:
        self._base_url = settings.llm_base_url
        self._model = settings.llm_model
        self._timeout = settings.llm_timeout

    async def chat_completion(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int = 2048,
        json_mode: bool = True,
    ) -> str:
        """
        Llama a /v1/chat/completions y devuelve el contenido del primer choice.
        Si json_mode=True, solicita respuesta en formato JSON.
        """
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(
                f"{self._base_url}/chat/completions",
                json=payload,
            )
            response.raise_for_status()

        data = response.json()
        content: str = data["choices"][0]["message"]["content"]
        return content

    async def get_plan_json(self, user_message: str) -> dict[str, Any]:
        """
        Solicita al LLM un plan estructurado JSON según el schema de SPEC.md §13.
        """
        system_prompt = (
            "Eres Rachael, una asistente autónoma. "
            "Cuando el usuario te pida una tarea, responde ÚNICAMENTE con un JSON "
            "que siga este esquema exacto:\n"
            "{\n"
            '  "goal": "<descripción breve del objetivo>",\n'
            '  "steps": [\n'
            "    {\n"
            '      "tool": "<nombre.accion>",\n'
            '      "args": { ... },\n'
            '      "needs_ok": false,\n'
            '      "ok_prompt": null\n'
            "    }\n"
            "  ]\n"
            "}\n\n"
            "Herramientas disponibles:\n"
            "- browser.open(url)\n"
            "- browser.navigate(url)\n"
            "- browser.click(element_id)\n"
            "- browser.type(element_id, text)\n"
            "- browser.extract(selector)\n"
            "- browser.screenshot()\n"
            "- browser.close()\n\n"
            "Marca needs_ok=true SÓLO en acciones irreversibles (checkout, envío de formulario, pago). "
            "No incluyas texto fuera del JSON."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]

        raw = await self.chat_completion(messages, json_mode=True)
        return json.loads(raw)


# Singleton
llm_client = LLMClient()

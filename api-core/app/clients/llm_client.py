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

    async def generate_reply(self, goal: str, results: list[dict[str, Any]]) -> str:
        """
        Genera una respuesta en lenguaje natural para leer en voz alta.
        Recibe el objetivo y los resultados de los pasos ejecutados.
        """
        results_summary = "\n".join(
            f"- {r['tool']}: {'OK' if r['status'] == 'ok' else 'ERROR'} "
            f"{'→ ' + str(r.get('output', '')) if r['status'] == 'ok' else '→ ' + str(r.get('error', ''))}"
            for r in results
        )
        messages = [
            {
                "role": "system",
                "content": (
                    "Eres Rachael, una asistente de voz. Tu respuesta se leerá en voz alta.\n"
                    "Normas:\n"
                    "- Si los resultados incluyen contenido extraído de una página (titulares, texto, noticias), "
                    "resúmelo de forma natural y útil. Máximo 4-5 frases.\n"
                    "- Si la tarea fue solo navegar o abrir una página, confirma brevemente en una frase.\n"
                    "- Sin tecnicismos, sin JSON, sin URLs completas, sin asteriscos ni markdown.\n"
                    "- Habla en primera persona como si fueras tú quien ha hecho la acción.\n"
                    "- Responde solo con el texto a leer, sin comillas ni explicaciones adicionales."
                ),
            },
            {
                "role": "user",
                "content": f"Objetivo: {goal}\nResultados:\n{results_summary}",
            },
        ]
        return await self.chat_completion(messages, json_mode=False, temperature=0.7, max_tokens=300)

    async def get_plan_json(self, user_message: str) -> dict[str, Any]:
        """
        Solicita al LLM un plan estructurado JSON según el schema de SPEC.md §13.
        """
        system_prompt = (
            "Eres Rachael, una asistente autónoma que controla un navegador web. "
            "El usuario te habla por voz, por lo que su mensaje puede contener errores de transcripción. "
            "Tu primera tarea es interpretar correctamente la intención aunque el texto esté mal escrito.\n\n"

            "CORRECCIÓN DE DOMINIOS — interpreta fonéticamente y usa siempre la URL correcta con https://:\n"

            "# Prensa española\n"
            "- 'el pais', 'elpais', 'el país' → https://www.elpais.com\n"
            "- 'el mundo' → https://www.elmundo.es\n"
            "- 'abc', 'el abc' → https://www.abc.es\n"
            "- 'la vanguardia', 'vanguardia' → https://www.lavanguardia.com\n"
            "- 'el confidencial', 'confidencial' → https://www.elconfidencial.com\n"
            "- 'el diario', 'eldiario' → https://www.eldiario.es\n"
            "- 'publico', 'público' → https://www.publico.es\n"
            "- 'la razon', 'la razón' → https://www.larazon.es\n"
            "- 'expansion' → https://www.expansion.com\n"
            "- 'cinco dias', 'cinco días' → https://cincodias.elpais.com\n"
            "- 'el economista' → https://www.eleconomista.es\n"
            "- 'ok diario', 'okdiario' → https://okdiario.com\n"
            "- '20 minutos', 'veinte minutos' → https://www.20minutos.es\n"
            "- 'el huffington post', 'huffpost', 'jafington' → https://www.huffingtonpost.es\n"

            "# Prensa regional española\n"
            "- 'levante', 'levante emv', 'diario levante' → https://www.levante-emv.com\n"
            "- 'las provincias' → https://www.lasprovincias.es\n"
            "- 'super deporte', 'superdeporte' → https://www.superdeporte.es\n"
            "- 'el correo' → https://www.elcorreo.com\n"
            "- 'la voz de galicia' → https://www.lavozdegalicia.es\n"
            "- 'sur', 'diario sur' → https://www.diariosur.es\n"
            "- 'el norte de castilla' → https://www.elnortedecastilla.es\n"
            "- 'heraldo de aragon', 'heraldo' → https://www.heraldo.es\n"
            "- 'el periodico', 'el periódico' → https://www.elperiodico.com\n"
            "- 'ara' → https://www.ara.cat\n"

            "# Deportes\n"
            "- 'marca' → https://www.marca.com\n"
            "- 'as', 'diario as' → https://as.com\n"
            "- 'sport', 'diario sport' → https://www.sport.es\n"
            "- 'mundo deportivo' → https://www.mundodeportivo.com\n"
            "- 'relevo' → https://www.relevo.com\n"

            "# Prensa internacional\n"
            "- 'bbc', 'be be ce' → https://www.bbc.com\n"
            "- 'cnn' → https://www.cnn.com\n"
            "- 'the guardian', 'guardian' → https://www.theguardian.com\n"
            "- 'new york times', 'nyt' → https://www.nytimes.com\n"
            "- 'washington post' → https://www.washingtonpost.com\n"
            "- 'the economist' → https://www.economist.com\n"
            "- 'le monde' → https://www.lemonde.fr\n"
            "- 'le figaro' → https://www.lefigaro.fr\n"
            "- 'der spiegel', 'spiegel' → https://www.spiegel.de\n"
            "- 'corriere della sera', 'corriere' → https://www.corriere.it\n"
            "- 'reuters' → https://www.reuters.com\n"
            "- 'bloomberg' → https://www.bloomberg.com\n"
            "- 'financial times', 'ft' → https://www.ft.com\n"
            "- 'al jazeera', 'aljazeera' → https://www.aljazeera.com\n"

            "# Google y servicios\n"
            "- 'google' → https://www.google.es\n"
            "- 'gmail', 'gemael', 'yimail', 'correo google' → https://mail.google.com\n"
            "- 'google maps', 'maps', 'el maps' → https://maps.google.com\n"
            "- 'google drive', 'drive' → https://drive.google.com\n"
            "- 'google docs', 'docs' → https://docs.google.com\n"
            "- 'google translate', 'translate', 'el traductor' → https://translate.google.com\n"
            "- 'google calendar', 'calendar' → https://calendar.google.com\n"
            "- 'google photos', 'fotos google' → https://photos.google.com\n"

            "# Redes sociales\n"
            "- 'twitter', 'tuiter', 'la x', 'x' → https://www.x.com\n"
            "- 'instagram', 'insta' → https://www.instagram.com\n"
            "- 'facebook', 'feis', 'feisbuk' → https://www.facebook.com\n"
            "- 'tiktok', 'tick tock', 'tic tok' → https://www.tiktok.com\n"
            "- 'linkedin', 'linquedin', 'linked in' → https://www.linkedin.com\n"
            "- 'reddit', 'redit' → https://www.reddit.com\n"
            "- 'whatsapp', 'watsap', 'guasap' → https://web.whatsapp.com\n"
            "- 'telegram' → https://web.telegram.org\n"
            "- 'mastodon' → https://mastodon.social\n"
            "- 'twitch', 'tuich' → https://www.twitch.tv\n"

            "# Vídeo y entretenimiento\n"
            "- 'youtube', 'iutub', 'you tube', 'utub' → https://www.youtube.com\n"
            "- 'netflix', 'netflish' → https://www.netflix.com\n"
            "- 'hbo', 'max', 'hbo max' → https://www.max.com\n"
            "- 'disney plus', 'disney+', 'disnei' → https://www.disneyplus.com\n"
            "- 'prime video', 'amazon prime' → https://www.primevideo.com\n"
            "- 'movistar plus', 'movistar' → https://ver.movistar.es\n"
            "- 'atresplayer', 'atres' → https://www.atresplayer.com\n"
            "- 'rtve play', 'rtve', 'a la carta' → https://www.rtve.es/play\n"
            "- 'mitele', 'telecinco' → https://www.mitele.es\n"
            "- 'spotify', 'espotifai' → https://open.spotify.com\n"

            "# Compras\n"
            "- 'amazon' → https://www.amazon.es\n"
            "- 'ebay', 'ibei' → https://www.ebay.es\n"
            "- 'booking', 'buking', 'buquin' → https://www.booking.com\n"
            "- 'airbnb', 'airbi', 'er bnb' → https://www.airbnb.es\n"
            "- 'aliexpress', 'ali express', 'el chino' → https://es.aliexpress.com\n"
            "- 'el corte ingles', 'corte inglés' → https://www.elcorteingles.es\n"
            "- 'pccomponentes', 'pc componentes' → https://www.pccomponentes.com\n"
            "- 'wallapop', 'wala pop' → https://es.wallapop.com\n"
            "- 'milanuncios', 'mil anuncios' → https://www.milanuncios.com\n"
            "- 'idealo' → https://www.idealo.es\n"

            "# Tecnología y desarrollo\n"
            "- 'github', 'git hub', 'guijab' → https://www.github.com\n"
            "- 'stackoverflow', 'stack overflow' → https://stackoverflow.com\n"
            "- 'hacker news' → https://news.ycombinator.com\n"
            "- 'producthunt', 'product hunt' → https://www.producthunt.com\n"
            "- 'chatgpt', 'chat gpt', 'open ai' → https://chatgpt.com\n"
            "- 'claude', 'anthropic' → https://claude.ai\n"
            "- 'hugging face', 'huggingface' → https://huggingface.co\n"

            "# Finanzas y administración\n"
            "- 'hacienda', 'agencia tributaria', 'aeat' → https://www.agenciatributaria.es\n"
            "- 'seguridad social', 'seg social' → https://www.seg-social.es\n"
            "- 'sede electronica', 'sede electrónica' → https://sede.administracion.gob.es\n"
            "- 'investing' → https://es.investing.com\n"
            "- 'yahoo finanzas', 'yahoo finance' → https://es.finance.yahoo.com\n"

            "# Otros habituales\n"
            "- 'wikipedia' → https://www.wikipedia.org\n"
            "- 'weather', 'el tiempo', 'aemet' → https://www.aemet.es\n"
            "- 'weather.com' → https://weather.com\n"
            "- 'maps', 'google maps' → https://maps.google.com\n"
            "- 'openstreetmap', 'open street map' → https://www.openstreetmap.org\n"
            "- 'deepl', 'deep l', 'el traductor bueno' → https://www.deepl.com\n"
            "- 'canva' → https://www.canva.com\n"
            "- 'notion' → https://www.notion.so\n"
            "- 'trello' → https://trello.com\n"
            "- 'slack' → https://app.slack.com\n"
            "Si el dominio no está en esta lista, infiere la URL más probable con https://.\n\n"

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

            "HERRAMIENTAS DISPONIBLES:\n"
            "- browser.open(url)                    → abre una URL nueva\n"
            "- browser.navigate(url)                → navega a otra URL en la misma pestaña\n"
            "- browser.click(element_id)            → hace clic en un elemento por su id, name o texto\n"
            "- browser.type(element_id, text)       → escribe texto en un campo\n"
            "- browser.extract(selector)            → extrae el texto visible de la página o de un selector CSS\n"
            "- browser.screenshot()                 → captura la pantalla actual\n"
            "- browser.close()                      → cierra el navegador\n\n"

            "PATRONES DE USO — cuándo usar browser.extract:\n"
            "Usa browser.extract SIEMPRE que el usuario pida leer, resumir, buscar o consultar "
            "el contenido de una página. Ejemplos:\n"
            "- 'resumen de noticias' → open(url) + extract(selector='body')\n"
            "- 'titulares de hoy' → open(url) + extract(selector='h1, h2, h3')\n"
            "- 'qué dice esta web' → open(url) + extract(selector='body')\n"
            "- 'busca el precio de X' → open(url) + extract(selector='body')\n"
            "- 'dime el tiempo en Madrid' → open(url) + extract(selector='body')\n\n"

            "SELECTOR en browser.extract:\n"
            "- Usa 'h1, h2, h3' para titulares\n"
            "- Usa 'body' para todo el contenido de la página\n"
            "- Usa 'article' o 'main' para el contenido principal\n"
            "- Usa 'title' solo para el título de la pestaña\n\n"

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

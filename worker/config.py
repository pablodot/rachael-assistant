"""
config.py — Configuración del worker via variables de entorno.

Variables de entorno soportadas:
  REDIS_URL                      URL de Redis (default: redis://localhost:6379)
  API_CORE_URL                   URL base de api-core (default: http://localhost:8000)
  BROWSER_AGENT_URL              URL del browser-agent (default: http://localhost:8001)
  LLM_RUNTIME_URL                URL del llm-runtime/Ollama (default: http://localhost:11434)
  HEALTH_CHECK_EVERY_N_MINUTES   Frecuencia del health-check en minutos; debe dividir 60 (default: 5)
  DAILY_BRIEFING_HOUR            Hora UTC del briefing diario (default: 8)
  DAILY_BRIEFING_MINUTE          Minuto del briefing diario (default: 0)
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    redis_url: str = "redis://localhost:6379"
    api_core_url: str = "http://localhost:8000"
    browser_agent_url: str = "http://localhost:8001"
    llm_runtime_url: str = "http://localhost:11434"

    # Scheduling
    health_check_every_n_minutes: int = 5  # debe dividir 60 (1,2,3,4,5,6,10,12,15,20,30,60)
    daily_briefing_hour: int = 8           # hora UTC
    daily_briefing_minute: int = 0

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()

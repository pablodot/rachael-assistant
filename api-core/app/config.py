from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # LLM runtime (compatible con OpenAI)
    llm_base_url: str = "http://llm-runtime:11434/v1"
    llm_timeout: int = 120

    # Modelo activo — cambiar según hardware disponible:
    #
    # LOCAL (6GB VRAM — RTX 3060):
    #   llm_model = "qwen2.5:7b"                  # ~4.5 GB  — default, equilibrado
    #   llm_model = "qwen2.5:7b-instruct-q4_K_M"  # ~4.5 GB  — instruct explícito
    #   llm_model = "mistral:7b-instruct-q4_K_M"  # ~4.1 GB  — alternativa Mistral
    #
    # SERVIDOR IA (34GB VRAM — 2x 1080Ti + 3060):
    #   llm_model = "qwen2.5:32b-instruct-q5_K_M" # ~24 GB   — recomendado servidor
    #   llm_model = "qwen2.5:14b-instruct-q6_K"   # ~12 GB   — opción intermedia
    #   llm_model = "qwen2.5:32b-instruct-q8_0"   # ~34 GB   — máxima calidad
    llm_model: str = "qwen2.5:7b-instruct-q4_K_M"

    # Browser agent (en host Linux)
    browser_agent_url: str = "http://host.docker.internal:8001"
    browser_timeout: int = 60

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

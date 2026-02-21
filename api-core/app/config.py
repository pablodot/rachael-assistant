from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # LLM runtime (compatible con OpenAI)
    llm_base_url: str = "http://llm-runtime:11434/v1"
    llm_model: str = "qwen2.5:7b-q4_K_M"
    llm_timeout: int = 120

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

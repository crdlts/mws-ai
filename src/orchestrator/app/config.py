import os


class Settings:
    """Простые настройки через переменные окружения."""
    PROJECT_NAME: str = "Secrets Orchestrator"
    MODERATOR_URL: str = os.getenv("MODERATOR_URL", "http://localhost:8001")
    # TODO: потом добавим URL для LLM-gateway, RAG и т.п.

    # Флаг, чтобы удобно логировать
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"


settings = Settings()

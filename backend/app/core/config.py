from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    APP_NAME: str = "Missa Hoje API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/missa_hoje"

    SECRET_KEY: str = "change-this-secret-key-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7

    GOOGLE_CLIENT_ID: Optional[str] = None

    PDF_URL: str = "https://www.arqrio.com.br/app/painel/amissa/amissa.pdf"
    PDF_DOWNLOAD_TIMEOUT: int = 30
    PDF_CACHE_DIR: str = "data/pdfs"

    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM: Optional[str] = None

    APP_BASE_URL: str = "http://localhost:3000"

    # Apoio voluntário. Os segredos ficam exclusivamente no ambiente do
    # servidor; o navegador recebe somente a URL hospedada do Checkout Pro.
    APOIOS_ATIVOS: bool = False
    MERCADOPAGO_ACCESS_TOKEN: Optional[str] = None
    MERCADOPAGO_WEBHOOK_SECRET: Optional[str] = None

    CORS_ORIGINS: list[str] = ["*"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        # Ignora env vars não declaradas aqui (ex.: USAR_LLM, ANTHROPIC_API_KEY,
        # ANTHROPIC_MODEL — lidas direto via os.getenv no pipeline LLM). Sem isso,
        # o default extra='forbid' derruba o app ao ver chaves novas no .env.
        extra = "ignore"


settings = Settings()

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str

    # Redis
    redis_url: str = "redis://redis:6379"

    # JWT
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440  # 24 hours

    # Plaid
    plaid_client_id: str = ""
    plaid_secret: str = ""
    plaid_env: str = "sandbox"

    # Encryption key for Plaid access tokens
    encryption_key: str = ""

    # Anthropic (Claude API) — categorization fallback, later the AI chat / NL query feature
    anthropic_api_key: str = ""

    # Google OAuth (login/signup with Google)
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/api/v1/auth/google/callback"
    frontend_url: str = "http://localhost:3000"

    class Config:
        env_file = ".env"


settings = Settings()

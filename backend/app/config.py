from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # "development" or "production" — controls cookie security flags and CORS below
    environment: str = "development"
    # Comma-separated list of origins allowed to call this API with credentials
    cors_origins: str = "http://localhost:3000"

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

    # Anthropic (Claude API) — categorization fallback, and the AI chat / NL query feature
    anthropic_api_key: str = ""

    # Google Places API — chatbot "cheaper places near me" tool
    google_places_api_key: str = ""

    # Google OAuth (login/signup with Google)
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/api/v1/auth/google/callback"
    frontend_url: str = "http://localhost:3000"

    class Config:
        env_file = ".env"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def cookie_samesite(self) -> str:
        # Frontend and backend live on different domains in production (e.g. a
        # Vercel domain calling a Railway domain), which browsers only send
        # cookies across for "none" + secure — "lax" is fine for local dev,
        # where everything's effectively same-site via localhost.
        return "none" if self.is_production else "lax"


settings = Settings()

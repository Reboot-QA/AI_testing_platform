from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "AI质量平台"
    secret_key: str = "dev-secret-key-change-in-production"
    database_url: str = "sqlite:///./ai_testcase.db"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24

    llm_api_base: str = "https://api.openai.com/v1"
    llm_api_key: str = ""
    llm_model: str = "gpt-4o-mini"
    llm_mock_mode: bool = True

    log_dir: str = ""

    grafana_enabled: bool = True
    grafana_url: str = ""
    grafana_port: int = 3000
    grafana_public_url: str = ""
    grafana_embed: bool = True
    loki_url: str = ""
    loki_port: int = 3100
    loki_public_url: str = ""

    class Config:
        env_file = ".env"


settings = Settings()

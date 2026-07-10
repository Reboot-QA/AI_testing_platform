from urllib.parse import quote_plus

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AI质量平台"
    secret_key: str = "dev-secret-key-change-in-production"
    # 可直接设置 DATABASE_URL；留空则使用下方 DB_* 参数拼接 MySQL 连接
    database_url: str = ""
    db_host: str = "127.0.0.1"
    db_port: int = 3306
    db_user: str = "root"
    db_password: str = ""
    db_name: str = "ai_testcase"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24

    llm_api_base: str = "https://api.openai.com/v1"
    llm_api_key: str = ""
    llm_model: str = "gpt-4o-mini"
    llm_mock_mode: bool = True
    ai_generate_batch_size: int = 8
    ai_generate_concurrency: int = 4

    log_dir: str = ""

    grafana_enabled: bool = True
    grafana_url: str = ""
    grafana_port: int = 3000
    grafana_public_url: str = ""
    grafana_embed: bool = True
    grafana_admin_user: str = ""
    grafana_admin_password: str = ""
    loki_url: str = ""
    loki_port: int = 3100
    loki_public_url: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def sqlalchemy_database_url(self) -> str:
        if self.database_url:
            return self.database_url
        password = quote_plus(self.db_password)
        return (
            f"mysql+pymysql://{self.db_user}:{password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}?charset=utf8mb4"
        )


settings = Settings()

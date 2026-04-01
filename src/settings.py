from pathlib import Path
from typing import Literal

import pytz
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

TIMEZONE = "Asia/Yekaterinburg"
timezone = pytz.timezone(TIMEZONE)
BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"
CHROMA_PATH = BASE_DIR / ".chroma"
SQLITE_PATH = BASE_DIR / "checkpoint.sqlite"
INVITATION_EXPIRES_IN_DAYS = 7
TEMPLATES_DIR = BASE_DIR / "templates"
load_dotenv(ENV_PATH)


class PostgresSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="POSTGRES_")

    host: str = "postgres"
    port: int = 5432
    user: str = "<USER>"
    password: str = "<PASSWORD>"
    db: str = "<DB>"
    driver: Literal["asyncpg"] = "asyncpg"

    @property
    def sqlalchemy_url(self) -> str:
        return f"postgresql+{self.driver}://{self.user}:{self.password}@{self.host}:{self.port}/{self.db}"


class GoogleSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="GOOGLE_")

    base_url: str = "https://www.googleapis.com"
    psi_api_key: str = "<API_KEY>"


class RabbitSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="RABBITMQ_")

    user: str = "user"
    password: str = "password"

    @property
    def url(self) -> str:
        return f"amqp://{self.user}:{self.password}@localhost:5672/"


class YandexCloudSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="YANDEX_CLOUD_")

    folder_id: str = ""
    api_key: str = ""


class JWTSettings(BaseSettings):
    access_token_expires_in_minutes: int = 30
    refresh_token_expires_in_days: int = 30


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="APP_")

    name: str = "ДИО-Консалт"
    port: int = 8000

    @property
    def url(self) -> str:
        return f"http://localhost:{self.port}"

    @property
    def api_url(self) -> str:
        return f"{self.url}/api/v1"


class MailSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="MAIL_")

    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_use_tls: bool = False
    smtp_user: str = ""
    smtp_password: str = ""
    default_from_email: str = "diocon@mail.ru"
    support_email: str = "diocon.support@mail.ru"


class Settings(BaseSettings):
    postgres: PostgresSettings = PostgresSettings()
    google: GoogleSettings = GoogleSettings()
    yandexcloud: YandexCloudSettings = YandexCloudSettings()
    rabbit: RabbitSettings = RabbitSettings()
    jwt: JWTSettings = JWTSettings()
    app: AppSettings = AppSettings()
    mail: MailSettings = MailSettings()
    secret_key: str = "<SECRET_KEY>"
    chromium_ws_endpoint: str = "ws://localhost:3000/playwright/chromium"
    frontend_url: str = "http://localhost:3000"


settings = Settings()

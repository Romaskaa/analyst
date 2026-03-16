from pathlib import Path

import pytz
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

TIMEZONE = pytz.timezone("Europe/Moscow")
BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"
CHROMA_PATH = BASE_DIR / ".chroma"

load_dotenv(ENV_PATH)


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

    folder_id: str = "<FOLDER_ID>"
    api_key: str = "<API_KEY>"

class OpenRouterSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="OPENROUTER_")

    base_url: str = "https://openrouter.ai/api/v1"
    api_key: str = ""

class Settings(BaseSettings):
    google: GoogleSettings = GoogleSettings()
    yandexcloud: YandexCloudSettings = YandexCloudSettings()
    rabbit: RabbitSettings = RabbitSettings()
    openrouter: OpenRouterSettings = OpenRouterSettings()

settings = Settings()

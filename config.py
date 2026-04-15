import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass
class Settings:
    bot_token: str


def get_settings() -> Settings:
    load_dotenv()
    token = os.getenv("BOT_TOKEN", "").strip()

    if not token:
        raise ValueError("BOT_TOKEN не найден в .env")

    return Settings(bot_token=token)

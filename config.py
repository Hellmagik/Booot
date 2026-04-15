import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass
class Settings:
    bot_token: str
    admin_id: int


def get_settings() -> Settings:
    load_dotenv()
    token = os.getenv("BOT_TOKEN", "").strip()
    admin_id_raw = os.getenv("ADMIN_ID", "").strip()

    if not token:
        raise ValueError("BOT_TOKEN не найден в .env")

    if not admin_id_raw:
        raise ValueError("ADMIN_ID не найден в .env")

    try:
        admin_id = int(admin_id_raw)
    except ValueError as error:
        raise ValueError("ADMIN_ID должен быть целым числом") from error

    return Settings(bot_token=token, admin_id=admin_id)

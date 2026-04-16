import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass
class Settings:
    bot_token: str
    gigachat_credentials: str
    gigachat_model: str
    gigachat_verify_ssl_certs: bool
    admin_chat_id: int | None


def _to_bool(value: str, default: bool = False) -> bool:
    normalized = (value or "").strip().lower()
    if not normalized:
        return default

    return normalized in {"1", "true", "yes", "y", "on"}


def get_settings() -> Settings:
    base_dir = Path(__file__).resolve().parent
    env_path = base_dir / ".env"

    load_dotenv(dotenv_path=env_path)
    token = os.getenv("BOT_TOKEN", "").strip()
    gigachat_credentials = os.getenv("GIGACHAT_CREDENTIALS", "").strip()
    gigachat_model = os.getenv("GIGACHAT_MODEL", "GigaChat").strip() or "GigaChat"
    gigachat_verify_ssl_certs = _to_bool(
        os.getenv("GIGACHAT_VERIFY_SSL_CERTS", "false"),
        default=False,
    )
    admin_chat_id_raw = os.getenv("ADMIN_CHAT_ID", "").strip()

    if not token:
        raise ValueError(
            "BOT_TOKEN не найден. Создай файл .env в корне проекта и добавь строку: BOT_TOKEN=твой_токен"
        )

    admin_chat_id: int | None = None
    if admin_chat_id_raw:
        try:
            admin_chat_id = int(admin_chat_id_raw)
        except ValueError as error:
            raise ValueError("ADMIN_CHAT_ID должен быть целым числом") from error

    return Settings(
        bot_token=token,
        gigachat_credentials=gigachat_credentials,
        gigachat_model=gigachat_model,
        gigachat_verify_ssl_certs=gigachat_verify_ssl_certs,
        admin_chat_id=admin_chat_id,
    )

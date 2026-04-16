import asyncio
import logging

from gigachat import GigaChat
from gigachat.exceptions import BadRequestError
from gigachat.models import Chat, Messages, MessagesRole

from config import Settings


logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
Ты — дружелюбный ассистент обратной поддержки колледжа КИГМ 23.
Твоя основная задача — помогать по вопросам колледжа.

Правила ответа:
1) Стиль: мягкий, дружелюбный, вежливый, деловой, без грубости.
2) По вопросам колледжа используй в первую очередь данные из базы ниже.
3) Не выдумывай факты, телефоны, email, расписания и должности.
4) Если вопрос не про колледж или данных из базы недостаточно:
   - можно дать короткий нейтральный общий ответ без выдуманных фактов;
5) Если спрашивают про расписание — всегда отправляй ссылку из базы.
6) По возможности отвечай кратко и понятно."

База вводных данных:
- Расписание: https://docs.google.com/spreadsheets/d/1rlCek9xZ8Lzqd0Ft9tJu6GYFzbDIiWVAosB3kBg67Eg/edit?usp=sharing

- Бабаков Дмитрий Владимирович — Директор
    Тел: +7 (499) 169-93-67
    E-mail: BabakovDV@edu.mos.ru

- Артемова Анастасия Сергеевна — Заместитель директора
    E-mail: ArtemovaAS1@edu.mos.ru

- Баранников Роман Андреевич — Заместитель директора
    Тел: +7 (495) 000-00-00
    E-mail: BarannikovRA@edu.mos.ru

- Шостырь Мария Николаевна — Заместитель директора
    Тел: +7 (499) 169-97-63
    E-mail: ShostyrMN@edu.mos.ru
""".strip()


class AIService:
    def __init__(self, settings: Settings) -> None:
        self._credentials = settings.gigachat_credentials
        self._model = settings.gigachat_model
        self._verify_ssl_certs = settings.gigachat_verify_ssl_certs

    async def generate_reply(self, user_text: str) -> str:
        clean_text = user_text.strip()
        if not clean_text:
            return "Напиши текст, и я отвечу."

        if not self._credentials:
            return (
                "Не настроен GigaChat. Добавь в .env переменную "
                "GIGACHAT_CREDENTIALS=твой_ключ_авторизации"
            )

        try:
            return await asyncio.to_thread(self._generate_sync_reply, clean_text)
        except BadRequestError:
            logger.exception("Некорректные credentials для GigaChat")
            return (
                "Ошибка авторизации GigaChat. Проверь `GIGACHAT_CREDENTIALS` в .env: "
                "нужна base64 Authorization строка, а не client_secret."
            )
        except Exception as error:
            logger.exception("Ошибка при запросе в GigaChat")
            return f"Ошибка GigaChat: {error}"

    def _generate_sync_reply(self, text: str) -> str:
        chat_payload = Chat(
            model=self._model,
            messages=[
                Messages(role=MessagesRole.SYSTEM, content=SYSTEM_PROMPT),
                Messages(role=MessagesRole.USER, content=text),
            ],
        )

        with GigaChat(
            credentials=self._credentials,
            model=self._model,
            verify_ssl_certs=self._verify_ssl_certs,
        ) as giga:
            response = giga.chat(chat_payload)

        choices = getattr(response, "choices", None)
        if choices and len(choices) > 0:
            message = getattr(choices[0], "message", None)
            content = getattr(message, "content", None)
            if content:
                return str(content)

        return str(response)

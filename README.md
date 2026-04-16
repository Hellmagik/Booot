# Telegram AI Bot (aiogram)

Базовый каркас Telegram-бота на `aiogram`.

## Текущий этап

- Инициализация бота и polling
- Модульная структура (`handlers`, `services`)
- Команды `/start`, `/help`
- Обработка обычного текста через GigaChat

## 1) Установка

```bash
pip install -r requirements.txt
```

## 2) Настройка переменных окружения

Создай файл `.env` в корне проекта:

```env
BOT_TOKEN=токен_твоего_бота
GIGACHAT_CREDENTIALS=ключ_авторизации_gigachat
GIGACHAT_MODEL=GigaChat
GIGACHAT_VERIFY_SSL_CERTS=false
```

## 3) Запуск

```bash
python main.py
```

После запуска бот отвечает на `/start`.

## Структура

- `main.py` — точка входа
- `config.py` — env-настройки
- `handlers/common.py` — хендлеры Telegram
- `services/ai_service.py` — слой AI-логики


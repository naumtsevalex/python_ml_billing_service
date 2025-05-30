# 🤖 Telegram Joke Bot | @pocket_mate_bot

Бот для работы с анекдотами, который умеет:
- Рассказывать случайные анекдоты
- Озвучивать анекдоты голосом
- Управлять балансом пользователей

<img src="docs/images/tg/01_intro_tg.png" width="400" alt="Начало работы с ботом">


## 📚 Основные артифакты

* Подробное описание архитектуры, стека технологий и структуры проекта находится в [docs/DETAILS.md](docs/DETAILS.md)

* 🍿 Подробные use-case проекта [docs/DEMO.md](docs/DEMO.md)

* Последовательные изменения проекта в [docs/CHANGELOG.md](docs/CHANGELOG.md)


## 🚀 Быстрый старт

1. Клонируйте репозиторий:
```bash
git clone <repository-url>
cd python_ml_billing_service
```

2. Создайте файл `.env` на основе `.env_example`:
```bash
cp .env_example .env
```

3. Запустите проект через Docker Compose:
```bash
docker-compose up -d
```

## 📝 Основные команды бота

- `/start` - Начать работу с ботом
- `/help` - Показать справку
- `/joke` - Получить случайный анекдот
- `/joke_voice` - Получить озвученный анекдот
- `/balance` - Проверить баланс

## 🏗️ Структура проекта

```
python_ml_billing_service/
├── bot/              # Telegram бот
├── worker/           # Асинхронный обработчик задач
├── db/              # Работа с базой данных
├── services/        # Бизнес-логика
├── models/          # Модели данных
├── utils/           # Вспомогательные функции
├── ai_studio/       # AI сервисы (TTS/STT)
└── monitoring/      # Мониторинг (Prometheus + Grafana)
```

## 🔧 Технологии

- Python 3.11+
- PostgreSQL (хранение пользователей, балансов, анекдотов)
- RabbitMQ (асинхронная обработка)
- Docker & Docker Compose
- Prometheus & Grafana
- Yandex SpeechKit (TTS/STT)

## 📚 База данных

База данных содержит следующие основные таблицы:
- `users` - информация о пользователях
- `balances` - балансы пользователей
- `jokes` - коллекция анекдотов
- `tasks` - история задач
- `transactions` - история транзакций

## 🤖 AI Сервисы

Бот использует Yandex SpeechKit для:
- Преобразования текста в речь (TTS)
- Преобразования речи в текст (STT)

## 🤝 Вклад в проект

1. Форкните репозиторий
2. Создайте ветку для новой функциональности
3. Внесите изменения
4. Создайте Pull Request

## 📄 Лицензия

MIT

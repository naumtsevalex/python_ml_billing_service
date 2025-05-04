# python_ml_billing_service

## Промежуточный запуск (этап: эхо-бот Telegram + база)

### 1. Запусти инфраструктуру

```bash
docker-compose up -d
```

### 2. Применить миграции Alembic (если база пустая)

```bash
alembic upgrade head
```

### 3. Установи зависимости для бота

```bash
cd bot
pip install -r requirements.txt
cd ..
```

### 4. Подготовь переменные окружения

- Все параметры (токены, строки подключения) должны быть в файле `envs.sh`:
  ```sh
  export TELEGRAM_TOKEN=... # токен Telegram-бота
  export DB_HOST=localhost
  export DB_PORT=5432
  export DB_NAME=mydb
  export DB_USER=myuser
  export DB_PASSWORD=mypass
  export DATABASE_URL=postgresql+asyncpg://$DB_USER:$DB_PASSWORD@$DB_HOST:$DB_PORT/$DB_NAME
  ```
- Перед запуском бота выполни:
  ```bash
  source envs.sh
  ```

### 5. Запусти Telegram-бота

```bash
python -m bot.main
```

### 6. Проверь работу
- Отправь боту сообщение — он должен ответить "OK" и зарегистрировать пользователя в базе.
- В таблице `logs` фиксируются все действия пользователя (регистрация, старт, сообщения).

---

**Дальнейшие этапы:**
- Интеграция с RabbitMQ (очереди задач)
- Реализация воркера для TTS/STT
- Биллинг и списание кредитов
- Мониторинг через Prometheus и Grafana
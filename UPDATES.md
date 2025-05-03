# UPDATES.md

## 2024-05-XX

- Инициализирован проект.
- Добавлен docker-compose.yml с сервисами: rabbitmq, postgres, prometheus, grafana.
- Создана базовая структура для мониторинга (monitoring/prometheus.yml).
- Описаны модели данных через SQLAlchemy ORM (users, balances, transactions, tasks, logs).
- Настроен Alembic для автоматических миграций.
- Выполнена первая миграция — все таблицы созданы в PostgreSQL.
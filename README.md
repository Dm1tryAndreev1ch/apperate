# Production Quality Control Backend

Полнофункциональный backend на Python (FastAPI) для автоматизации проверок на производстве с REST API, веб-панелями, версионированием чек-листов, генерацией отчётов и интеграцией Bitrix.

## Технологический стек

- **FastAPI** (Python 3.11+)
- **PostgreSQL** с JSONB
- **SQLAlchemy 2.0** (async)
- **Celery** + **Redis** (фоновые задачи)
- **S3/MinIO** (хранилище файлов)
- **WeasyPrint** (генерация PDF)
- **JWT** (аутентификация)
- **Prometheus** + **Grafana** (мониторинг)

## Быстрый старт

### Требования

- Docker и Docker Compose
- Python 3.11+ (для локальной разработки)

### Запуск с Docker Compose

1. Клонируйте репозиторий:
```bash
git clone <repository-url>
cd apperate
```

2. Создайте файл `.env` на основе `.env.example`:
```bash
cp .env.example .env
```

3. Запустите все сервисы:
```bash
docker-compose up -d
```

4. Выполните миграции базы данных:
```bash
docker-compose exec api alembic upgrade head
```

5. Создайте bucket в MinIO:
```bash
# MinIO доступен на http://localhost:9001
# Логин: minioadmin / minioadmin
# Создайте bucket "quality-control"
```

6. API доступен на http://localhost:8000
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc
   - Admin Panel: http://localhost:8000/static/admin.html
   - Worker Panel: http://localhost:8000/static/user.html

### Локальная разработка

1. Установите зависимости:
```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

2. Настройте переменные окружения в `.env`

3. Запустите PostgreSQL и Redis (через Docker или локально)

4. Выполните миграции:
```bash
alembic upgrade head
```

5. Запустите приложение:
```bash
uvicorn app.main:app --reload
```

6. В отдельном терминале запустите Celery worker:
```bash
celery -A app.tasks.celery_app worker --loglevel=info
```

7. В отдельном терминале запустите Celery beat:
```bash
celery -A app.tasks.celery_app beat --loglevel=info
```

## Миграции базы данных

### Создание новой миграции

```bash
alembic revision --autogenerate -m "Description of changes"
```

### Применение миграций

```bash
alembic upgrade head
```

### Откат миграции

```bash
alembic downgrade -1
```

## API Примеры

### Аутентификация

#### Вход
```bash
curl -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "password": "password"
  }'
```

#### Обновление токена
```bash
curl -X POST "http://localhost:8000/api/auth/refresh" \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "your-refresh-token"
  }'
```

### Создание шаблона чек-листа

```bash
curl -X POST "http://localhost:8000/api/templates" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Safety Inspection",
    "description": "Daily safety inspection checklist",
    "schema": {
      "sections": [
        {
          "name": "Equipment",
          "questions": [
            {
              "id": "eq1",
              "type": "boolean",
              "text": "All equipment is in good condition",
              "required": true,
              "meta": {
                "critical": true,
                "requires_ok": true
              }
            }
          ]
        }
      ]
    }
  }'
```

### Создание проверки

```bash
curl -X POST "http://localhost:8000/api/checks" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "template_id": "template-uuid",
    "project_id": "project-123"
  }'
```

### Завершение проверки

```bash
curl -X POST "http://localhost:8000/api/checks/{check_id}/complete" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Получение presigned URL для загрузки файла

```bash
curl -X POST "http://localhost:8000/api/files/presign" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "filename": "photo.jpg",
    "content_type": "image/jpeg",
    "size": 1024000
  }'
```

## Структура проекта

```
apperate/
├── app/
│   ├── api/           # API эндпоинты
│   ├── models/        # SQLAlchemy модели
│   ├── schemas/       # Pydantic схемы
│   ├── crud/          # CRUD операции
│   ├── services/      # Бизнес-логика
│   ├── tasks/         # Celery задачи
│   ├── integrations/  # Внешние интеграции
│   └── utils/         # Утилиты
├── static/            # HTML панели
│   ├── admin.html     # Админ-панель
│   └── user.html      # Панель исполнителя
├── alembic/           # Миграции БД
├── tests/             # Тесты
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

## Веб-панели

Система включает две HTML-панели для взаимодействия с API:

- **Admin Panel** (`/static/admin.html`) - панель администратора для управления:
  - Пользователями и ролями
  - Шаблонами чек-листов
  - Расписаниями
  - Webhook подписками
  - Просмотра журнала аудита

- **Worker Panel** (`/static/user.html`) - панель исполнителя для:
  - Просмотра назначенных проверок
  - Выполнения чек-листов
  - Просмотра и скачивания отчётов

## Мониторинг

- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (admin/admin)
- **Metrics endpoint**: http://localhost:8000/metrics

## Интеграция с Bitrix

По умолчанию используется режим заглушки (stub). Для переключения на реальную интеграцию:

1. Установите `BITRIX_MODE=live` в `.env`
2. Настройте `BITRIX_BASE_URL` и `BITRIX_ACCESS_TOKEN`
3. Все вызовы будут логироваться в таблицу `bitrix_call_logs`

## Тестирование

```bash
pytest
```

С покрытием:
```bash
pytest --cov=app --cov-report=html
```

## Развёртывание

Для production используйте `docker-compose.prod.yml` (создайте на основе `docker-compose.yml` с настройками для production).

## Лицензия

[Укажите лицензию]


<!-- c34cd0e9-3390-43ad-83e1-270b9fef5919 a5475a8f-31cb-417f-9f91-e0aba86a3ef9 -->
# План разработки системы автоматизации проверок на производстве

## Архитектура проекта

Проект будет организован как микросервисная архитектура с использованием Docker Compose для оркестрации сервисов:

- FastAPI приложение (основной API)
- PostgreSQL (база данных)
- Redis (брокер сообщений для Celery)
- Celery Worker (фоновые задачи)
- Celery Beat (планировщик задач)
- MinIO (S3-совместимое хранилище)
- Prometheus (метрики)
- Grafana (визуализация)

## Структура проекта

```
production-quality-control/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # Точка входа FastAPI
│   │   ├── config.py               # Конфигурация приложения
│   │   ├── database.py             # Настройка SQLAlchemy 2.0
│   │   ├── dependencies.py         # FastAPI dependencies (auth, permissions)
│   │   │
│   │   ├── models/                 # SQLAlchemy модели
│   │   │   ├── __init__.py
│   │   │   ├── user.py             # User, Role, Permission
│   │   │   ├── checklist.py        # ChecklistTemplate, CheckInstance
│   │   │   ├── report.py           # Report
│   │   │   ├── schedule.py         # Schedule
│   │   │   ├── audit.py            # AuditLog
│   │   │   └── integration.py      # BitrixSync, TaskLocal
│   │   │
│   │   ├── schemas/                # Pydantic схемы для валидации
│   │   │   ├── __init__.py
│   │   │   ├── user.py
│   │   │   ├── checklist.py
│   │   │   ├── report.py
│   │   │   └── common.py
│   │   │
│   │   ├── api/                    # API эндпоинты
│   │   │   ├── __init__.py
│   │   │   ├── v1/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── auth.py         # /api/v1/auth/ (login, token)
│   │   │   │   ├── templates.py   # /api/v1/templates/
│   │   │   │   ├── checks.py      # /api/v1/checks/
│   │   │   │   ├── reports.py     # /api/v1/reports/
│   │   │   │   ├── users.py       # /api/v1/users/
│   │   │   │   ├── roles.py       # /api/v1/roles/
│   │   │   │   ├── schedules.py   # /api/v1/schedules/
│   │   │   │   └── audit.py       # /api/v1/audit/
│   │   │   └── graphql.py         # /graphql endpoint (Strawberry)
│   │   │
│   │   ├── services/               # Бизнес-логика
│   │   │   ├── __init__.py
│   │   │   ├── auth_service.py    # JWT/OAuth2 логика
│   │   │   ├── checklist_service.py
│   │   │   ├── report_service.py  # Генерация отчётов
│   │   │   ├── storage_service.py # S3/MinIO операции
│   │   │   └── bitrix_service.py  # Интеграция с Bitrix
│   │   │
│   │   ├── tasks/                  # Celery задачи
│   │   │   ├── __init__.py
│   │   │   ├── reports.py         # generate_report task
│   │   │   ├── bitrix.py          # sync_with_bitrix task
│   │   │   ├── schedule.py        # create_scheduled_checks task
│   │   │   └── maintenance.py     # backup, cleanup tasks
│   │   │
│   │   ├── middleware/             # Middleware компоненты
│   │   │   ├── __init__.py
│   │   │   ├── audit.py           # AuditLog middleware
│   │   │   ├── metrics.py         # Prometheus metrics
│   │   │   └── cors.py            # CORS настройки
│   │   │
│   │   ├── utils/                  # Утилиты
│   │   │   ├── __init__.py
│   │   │   ├── security.py        # Password hashing, JWT
│   │   │   ├── permissions.py     # RBAC helpers
│   │   │   └── validators.py
│   │   │
│   │   └── bot/                    # Telegram бот
│   │       ├── __init__.py
│   │       ├── main.py            # Точка входа бота
│   │       ├── handlers/          # Обработчики команд
│   │       │   ├── auth.py        # Авторизация в боте
│   │       │   ├── checks.py      # Работа с проверками
│   │       │   └── common.py
│   │       └── api_client.py      # Клиент для FastAPI
│   │
│   ├── alembic/                    # Миграции БД
│   │   ├── versions/
│   │   ├── env.py
│   │   └── alembic.ini
│   │
│   ├── tests/                      # Тесты (pytest)
│   │   ├── __init__.py
│   │   ├── conftest.py            # Фикстуры
│   │   ├── test_models.py
│   │   ├── test_api.py
│   │   └── factories.py           # FactoryBoy
│   │
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
│
├── docker-compose.yml              # Оркестрация всех сервисов
├── docker-compose.prod.yml         # Продакшн конфигурация
├── .gitignore
├── README.md
└── docs/                           # Документация
    ├── architecture.md
    ├── api.md
    └── deployment.md
```

## Основные компоненты

### 1. Модели данных (SQLAlchemy 2.0)

**User, Role, Permission** ([backend/app/models/user.py](backend/app/models/user.py)):

- User: id, username, email, password_hash, role_id, telegram_id, created_at
- Role: id, name, permissions (JSONB массив строк)
- Permission: предопределённые константы (CREATE_CHECKLIST, VIEW_REPORTS, etc.)

**ChecklistTemplate** ([backend/app/models/checklist.py](backend/app/models/checklist.py)):

- id, name, version, structure (JSONB с sections/questions), status (active/superseded), created_at, created_by
- Версионирование: при изменении создаётся новая версия, старая помечается как superseded

**CheckInstance** ([backend/app/models/checklist.py](backend/app/models/checklist.py)):

- id, template_id, template_version, executor_id, status, answers (JSONB), created_at, completed_at
- answers хранит ответы на вопросы шаблона в формате JSON

**Report** ([backend/app/models/report.py](backend/app/models/report.py)):

- id, check_instance_id, format (PDF/HTML/JSON), file_key (S3), generated_at, parameters (JSONB фильтров)

**Schedule** ([backend/app/models/schedule.py](backend/app/models/schedule.py)):

- id, name, cron_expression, executor_ids (JSONB массив), enabled, created_at

**AuditLog** ([backend/app/models/audit.py](backend/app/models/audit.py)):

- id, user_id, entity_type, entity_id, action, diff (JSONB), timestamp

**BitrixSync, TaskLocal** ([backend/app/models/integration.py](backend/app/models/integration.py)):

- TaskLocal: id, title, description, extern_id (Bitrix), sync_status, last_sync_at

### 2. API эндпоинты (FastAPI)

**REST API** ([backend/app/api/v1/](backend/app/api/v1/)):

- `POST /api/v1/auth/login` - аутентификация, возвращает JWT
- `GET /api/v1/auth/me` - текущий пользователь
- `GET /api/v1/templates/` - список шаблонов
- `POST /api/v1/templates/` - создание шаблона (создаёт новую версию)
- `GET /api/v1/templates/{id}/versions` - история версий
- `GET /api/v1/checks/` - список проверок (с фильтрами)
- `POST /api/v1/checks/` - создание проверки
- `POST /api/v1/checks/{id}/answer` - добавление ответа
- `POST /api/v1/checks/{id}/comment` - комментарий/фото
- `GET /api/v1/checks/{id}` - детали проверки
- `POST /api/v1/reports/generate` - запуск генерации отчёта (Celery)
- `GET /api/v1/reports/{id}` - статус/скачивание отчёта
- `GET /api/v1/users/`, `POST /api/v1/users/` - управление пользователями
- `GET /api/v1/roles/` - роли и права
- `GET /api/v1/schedules/`, `POST /api/v1/schedules/` - расписания
- `GET /api/v1/audit/` - журнал аудита (с фильтрами)
- `GET /health` - health check
- `GET /metrics` - Prometheus метрики

**GraphQL** ([backend/app/api/graphql.py](backend/app/api/graphql.py)):

- `/graphql` endpoint с использованием Strawberry
- Схема для гибких запросов чек-листов, отчётов, пользователей

**OpenAPI/Swagger**:

- Автоматически генерируется FastAPI на `/docs` и `/redoc`

### 3. Аутентификация и безопасность

**JWT/OAuth2** ([backend/app/services/auth_service.py](backend/app/services/auth_service.py)):

- Использование `python-jose` для JWT
- OAuth2PasswordBearer схема FastAPI
- Токены содержат user_id и roles

**RBAC** ([backend/app/dependencies.py](backend/app/dependencies.py)):

- Dependency `get_current_user` - извлечение пользователя из JWT
- Dependency `require_permission(permission)` - проверка прав
- Middleware для автоматической проверки доступа

**Password hashing** ([backend/app/utils/security.py](backend/app/utils/security.py)):

- Использование `bcrypt` или `argon2` для хэширования паролей

### 4. Хранилище файлов (S3/MinIO)

**Storage Service** ([backend/app/services/storage_service.py](backend/app/services/storage_service.py)):

- Генерация presigned URLs для загрузки (PUT) и скачивания (GET)
- Использование `boto3` для работы с S3/MinIO
- Методы: `generate_upload_url()`, `generate_download_url()`, `delete_file()`

### 5. Генерация отчётов (Celery)

**Report Service** ([backend/app/services/report_service.py](backend/app/services/report_service.py)):

- Генерация PDF через WeasyPrint (HTML → PDF)
- Генерация HTML через Jinja2 шаблоны
- JSON - сериализация данных

**Celery Task** ([backend/app/tasks/reports.py](backend/app/tasks/reports.py)):

- `generate_report.delay(check_instance_id, format)` - асинхронная генерация
- Сохранение результата в S3 и создание записи Report в БД

### 6. Telegram бот

**Bot Structure** ([backend/app/bot/](backend/app/bot/)):

- Использование `aiogram` для асинхронного бота
- Webhook режим (через FastAPI endpoint `/webhook/telegram`)
- Авторизация: пользователь генерирует токен в веб-панели, вводит в боте
- Команды: `/start`, `/checks`, `/fill_check`, `/status`
- Обработка фото через Telegram API или presigned URLs

### 7. Интеграция с Bitrix

**Bitrix Service** ([backend/app/services/bitrix_service.py](backend/app/services/bitrix_service.py)):

- Режим заглушки (USE_BITRIX_STUB=true) - возвращает мок-ответы
- Реальный режим - HTTP запросы к Bitrix REST API
- Логирование всех вызовов в таблицу BitrixSync
- Асинхронная синхронизация через Celery задачи

### 8. Фоновые задачи (Celery)

**Tasks** ([backend/app/tasks/](backend/app/tasks/)):

- `generate_report` - генерация отчётов
- `sync_with_bitrix` - синхронизация с Bitrix
- `create_scheduled_checks` - создание проверок по расписанию (Celery Beat)
- `backup_database` - резервное копирование БД
- `cleanup_old_reports` - очистка старых файлов

**Celery Beat**:

- Периодические задачи на основе Schedule моделей
- Создание CheckInstance по cron-выражениям

### 9. Мониторинг

**Prometheus Metrics** ([backend/app/middleware/metrics.py](backend/app/middleware/metrics.py)):

- Использование `prometheus_client`
- Метрики: HTTP запросы (счётчик, гистограмма времени), ошибки, активные проверки
- Endpoint `/metrics` для скраппинга Prometheus

**Grafana**:

- Дашборды для визуализации метрик (в docker-compose)

### 10. Миграции (Alembic)

**Database Migrations** ([backend/alembic/](backend/alembic/)):

- Инициализация Alembic
- Миграции для всех моделей
- Поддержка JSONB полей через SQLAlchemy

### 11. Тестирование

**Tests** ([backend/tests/](backend/tests/)):

- Pytest с async поддержкой
- FactoryBoy для создания тестовых данных
- Тесты моделей, API эндпоинтов, сервисов

### 12. Docker и развёртывание

**Docker Compose** ([docker-compose.yml](docker-compose.yml)):

- Сервисы: api, db, redis, celery-worker, celery-beat, minio, prometheus, grafana
- Переменные окружения через .env файл
- Health checks для всех сервисов

**Dockerfile** ([backend/Dockerfile](backend/Dockerfile)):

- Multi-stage build для оптимизации размера
- Установка зависимостей Python

## Порядок реализации

1. **Базовая структура проекта**: создание директорий, конфигурация, зависимости
2. **База данных**: модели SQLAlchemy, миграции Alembic, настройка подключения
3. **Аутентификация**: JWT/OAuth2, RBAC, зависимости для проверки прав
4. **API эндпоинты**: REST API для всех сущностей, валидация через Pydantic
5. **Хранилище файлов**: интеграция с MinIO/S3, presigned URLs
6. **Генерация отчётов**: сервис генерации, Celery задачи
7. **Telegram бот**: структура бота, обработчики, интеграция с API
8. **Интеграция Bitrix**: сервис с режимом заглушки, Celery задачи синхронизации
9. **Планировщик**: Schedule модели, Celery Beat задачи
10. **Мониторинг**: Prometheus метрики, Grafana дашборды
11. **Audit Log**: middleware для логирования действий
12. **Тестирование**: написание тестов для ключевых компонентов
13. **Docker**: конфигурация всех сервисов, docker-compose
14. **Документация**: README, архитектурная документация, примеры API

## Технологический стек

- **FastAPI** - веб-фреймворк
- **SQLAlchemy 2.0** - ORM с async поддержкой
- **PostgreSQL** - база данных с JSONB
- **Alembic** - миграции БД
- **Celery** - фоновые задачи
- **Redis** - брокер сообщений
- **boto3** - работа с S3/MinIO
- **JWT (python-jose)** - аутентификация
- **WeasyPrint** - генерация PDF
- **Jinja2** - шаблонизация
- **aiogram** - Telegram бот
- **Strawberry** - GraphQL
- **Prometheus Client** - метрики
- **Pytest** - тестирование
- **FactoryBoy** - тестовые данные
- **Docker** - контейнеризация
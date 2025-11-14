# MantaQC

Полнофункциональная система контроля качества на Python (FastAPI) для автоматизации проверок на производстве с REST API, веб-панелями, версионированием чек-листов, автоматической генерацией отчётов в формате Excel, расширенной аналитикой, дашбордами и интеграцией с Bitrix.

## Технологический стек

- **FastAPI** (Python 3.11+)
- **PostgreSQL** с JSONB
- **SQLAlchemy 2.0** (async)
- **Celery** + **Redis** (фоновые задачи)
- **S3/MinIO** (хранилище файлов)
- **OpenPyXL** (генерация Excel отчётов)
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
cd mantaqc
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
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@example.com&password=password"
```

#### Получение текущего пользователя
```bash
curl -X GET "http://localhost:8000/api/v1/auth/me" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Дашборды

#### Админ-дашборд
```bash
curl -X GET "http://localhost:8000/api/v1/dashboards/admin?days=30" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### Пользовательский дашборд
```bash
curl -X GET "http://localhost:8000/api/v1/dashboards/user?days=30" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### Баллы бригад
```bash
curl -X GET "http://localhost:8000/api/v1/dashboards/brigade-scores?days=30&brigade_id=BRIGADE_UUID" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Отчёты

#### Генерация отчёта
```bash
curl -X POST "http://localhost:8000/api/v1/reports/generate/{check_instance_id}" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}'
```

#### Список отчётов с фильтрацией
```bash
curl -X GET "http://localhost:8000/api/v1/reports?status_filter=READY&sort_by=created_at&sort_order=desc&author_id=USER_UUID" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### Скачивание отчёта
```bash
curl -X GET "http://localhost:8000/api/v1/reports/{report_id}/download" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### Аналитика отчётов
```bash
curl -X GET "http://localhost:8000/api/v1/reports/analytics?days=30" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### Периодные сводки
```bash
curl -X GET "http://localhost:8000/api/v1/reports/summaries?granularity=month&period_start=2024-01-01&period_end=2024-01-31" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### Экспорт сводок
```bash
curl -X POST "http://localhost:8000/api/v1/reports/summaries/export" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "granularity": "month",
    "period_start": "2024-01-01",
    "period_end": "2024-01-31"
  }'
```

#### Просмотр логов проверки
```bash
curl -X GET "http://localhost:8000/api/v1/reports/checks/{check_id}/logs" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Чек-листы (Templates)

#### Создание шаблона
```bash
curl -X POST "http://localhost:8000/api/v1/templates" \
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
              "required": true
            }
          ]
        }
      ]
    }
  }'
```

#### Получение по slug
```bash
curl -X GET "http://localhost:8000/api/v1/templates/slug/safety-inspection" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### Клонирование шаблона
```bash
curl -X POST "http://localhost:8000/api/v1/templates/{template_id}/clone?new_name=Cloned Template" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### Версии шаблона
```bash
curl -X GET "http://localhost:8000/api/v1/templates/{template_id}/versions" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

#### Восстановление версии
```bash
curl -X POST "http://localhost:8000/api/v1/templates/{template_id}/versions/{version}/restore" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Проверки

#### Создание проверки
```bash
curl -X POST "http://localhost:8000/api/v1/checks" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "template_id": "template-uuid",
    "project_id": "project-123"
  }'
```

#### Завершение проверки
```bash
curl -X POST "http://localhost:8000/api/v1/checks/{check_id}/complete" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## Структура проекта

```
mantaqc/
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

## Основные возможности

### Отчёты
- **Автоматическая генерация отчётов** в формате Excel (XLSX)
- **Расширенная аналитика** с метриками качества, баллами бригад, сводными данными
- **Периодные сводки** (день, неделя, месяц) с дельтами изменений
- **Графики и визуализация** данных в отчётах
- **Экспорт сводок** через веб-интерфейс

### Дашборды
- **Админ-дашборд** с глобальными KPIs, топ-бригадами, последними отчётами
- **Пользовательский дашборд** с персональными метриками и назначенными проверками
- **Визуализация баллов бригад** с графиками и историей
- **Критические замечания** и задачи Bitrix

### Чек-листы
- **Полный CRUD** для шаблонов чек-листов через веб-интерфейс
- **Версионирование** с историей изменений
- **Клонирование** шаблонов
- **Уникальные slug** для удобной навигации
- **Мягкое удаление** (soft delete)

### Интеграции
- **Bitrix24** - автоматическое создание задач при обнаружении проблем
- **Хранение файлов** в S3/MinIO
- **Фоновые задачи** через Celery

## Веб-панели

Система включает две HTML-панели для взаимодействия с API:

- **Admin Panel** (`/static/admin.html`) - панель администратора:
  - **Дашборд по умолчанию** с KPIs и сводками
  - Управление пользователями и ролями
  - Управление шаблонами чек-листов (CRUD)
  - Просмотр всех отчётов с фильтрацией и сортировкой
  - Просмотр обходов (логов) как веб-страниц
  - Расписания и webhook подписки
  - Журнал аудита
  - Кнопки сброса проекта и демо-версии (в футере)

- **User Panel** (`/static/user.html`) - панель исполнителя:
  - **Персональный дашборд** с собственными метриками
  - Просмотр назначенных проверок
  - Выполнение чек-листов через веб-формы
  - Просмотр и скачивание отчётов (только Excel)
  - Просмотр логов проверок как веб-страниц
  - Баллы бригады (если пользователь в бригаде)
  - Кнопка "Назад" на странице входа

## Мониторинг

- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (admin/admin)
- **Metrics endpoint**: http://localhost:8000/metrics

## Интеграция с Bitrix

MantaQC автоматически создаёт задачи в Bitrix24 при обнаружении критических проблем в отчётах.

### Настройка

По умолчанию используется режим заглушки (stub). Для переключения на реальную интеграцию:

1. Установите `BITRIX_MODE=live` в `.env`
2. Настройте `BITRIX_BASE_URL` и `BITRIX_ACCESS_TOKEN` (или `BITRIX_WEBHOOK_SECRET`)
3. Все вызовы будут логироваться в таблицу `bitrix_call_logs`

### Автоматическое создание задач

При генерации отчёта система:
- Анализирует результаты проверки
- Выявляет критические проблемы и предупреждения
- Автоматически создаёт задачи в Bitrix24
- Сохраняет ID задач в метаданных отчёта
- Дедуплицирует задачи для предотвращения дубликатов

## Тестирование

### Запуск всех тестов
```bash
pytest
```

### Запуск с покрытием
```bash
pytest --cov=app --cov-report=html
```

### Типы тестов

- **Unit тесты** (`tests/test_*.py`) - тестирование отдельных сервисов и функций
- **Integration тесты** (`tests/test_*_api_integration.py`) - тестирование API endpoints
- **E2E тесты** (`tests/test_e2e_workflows.py`) - тестирование полных workflows

### Покрытие тестами

- ✅ Analytics service (баллы бригад, аналитика отчётов, периодные сводки)
- ✅ Report builder (генерация Excel отчётов)
- ✅ Report dispatcher (оркестрация генерации отчётов)
- ✅ Bitrix alert service (интеграция с Bitrix)
- ✅ Reset service (сброс проекта)
- ✅ Checklist CRUD service (управление шаблонами)
- ✅ Reports API (генерация, фильтрация, сортировка, скачивание)
- ✅ Dashboards API (админ, пользователь, баллы бригад)
- ✅ Checklists API (CRUD, клонирование, версионирование)
- ✅ E2E workflows (полные сценарии использования)

## Развёртывание

### Production настройки

1. Создайте `.env` файл с production настройками:
```bash
APP_NAME=MantaQC
DEBUG=False
SECRET_KEY=<generate-strong-secret-key>
DATABASE_URL=postgresql+asyncpg://user:password@db-host:5432/mantaqc
REDIS_URL=redis://redis-host:6379/0
S3_ENDPOINT_URL=https://s3.example.com
S3_ACCESS_KEY_ID=<your-access-key>
S3_SECRET_ACCESS_KEY=<your-secret-key>
S3_BUCKET_NAME=mantaqc-reports
BITRIX_MODE=live
BITRIX_BASE_URL=https://your-domain.bitrix24.com/rest/1/webhook/
BITRIX_WEBHOOK_SECRET=<your-webhook-secret>
```

2. Примените миграции:
```bash
alembic upgrade head
```

3. Создайте bucket в S3/MinIO для хранения отчётов

4. Запустите сервисы:
```bash
docker-compose -f docker-compose.prod.yml up -d
```

### Важные замечания

- **Отчёты только в Excel**: Система генерирует отчёты исключительно в формате XLSX
- **Автоматическая аналитика**: Все отчёты включают расширенную аналитику и метрики
- **Bitrix интеграция**: Настройте интеграцию для автоматического создания задач
- **Резервное копирование**: Настройте регулярное резервное копирование базы данных
- **Мониторинг**: Используйте Prometheus и Grafana для мониторинга системы

## Особенности MantaQC

### Автоматическая генерация отчётов
- Формат Excel (XLSX) с профессиональным оформлением
- Автоматическое построение графиков и диаграмм
- Расширенная аналитика с метриками качества
- Баллы бригад с формулами расчёта
- Периодные сводки с дельтами изменений

### Дашборды
- Админ-дашборд с глобальными KPIs
- Пользовательский дашборд с персональными метриками
- Визуализация данных бригад
- Отслеживание критических замечаний

### Управление чек-листами
- Полный CRUD через веб-интерфейс
- Версионирование с историей изменений
- Клонирование и восстановление версий
- Уникальные slug для удобной навигации

### Интеграции
- Автоматическое создание задач в Bitrix24
- Хранение файлов в S3-совместимом хранилище
- Фоновая обработка через Celery

## Проверка и верификация

После развёртывания выполните проверку системы:

### Автоматическая проверка

```bash
# Linux/Mac
bash scripts/verify_setup.sh

# Windows PowerShell
powershell -ExecutionPolicy Bypass -File scripts/verify_setup.ps1

# Или вручную
pytest
```

### Ручная проверка

См. подробное руководство в [docs/VERIFICATION.md](docs/VERIFICATION.md)

### Чек-лист

- [ ] Все тесты проходят
- [ ] Миграции применены
- [ ] Админ-панель открывается с дашбордом
- [ ] Пользовательская панель показывает персональные данные
- [ ] Отчёты генерируются только в Excel
- [ ] Логи проверок отображаются как веб-страницы
- [ ] Bitrix интеграция работает
- [ ] Периодные сводки генерируются

## Поддержка

Для вопросов и поддержки обращайтесь к документации API на `/docs` или `/redoc`.

## Лицензия

[Укажите лицензию]


"""Utilities for generating demo data for quick test builds."""
from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from io import BytesIO
from typing import Any, Dict, Iterable, List, Tuple

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import ROLE_PERMISSIONS
from app.database import Base
from app.models.brigade import Brigade, BrigadeDailyScore
from app.models.checklist import (
    CheckInstance,
    CheckStatus,
    ChecklistTemplate,
    ChecklistTemplateVersion,
    TemplateStatus,
)
from app.models.report import Report, ReportFormat, ReportStatus
from app.models.user import Role, User
from app.services.auth_service import AuthService
from app.services.storage_service import storage_service


@dataclass
class DemoDataResult:
    """Collection of counters for generated demo data."""

    users_created: int = 0
    brigades_created: int = 0
    templates_created: int = 0
    checks_created: int = 0
    reports_created: int = 0
    scores_created: int = 0

    def as_payload(self) -> Dict[str, Any]:
        """Convert counters to response payload."""
        total = (
            self.users_created
            + self.brigades_created
            + self.templates_created
            + self.checks_created
            + self.reports_created
            + self.scores_created
        )
        status = "skipped" if total == 0 else "created"
        detail = (
            "Демо-данные уже доступны"
            if status == "skipped"
            else "Созданы демонстрационные данные"
        )
        return {
            "status": status,
            "detail": detail,
            "created_users": self.users_created,
            "created_brigades": self.brigades_created,
            "created_templates": self.templates_created,
            "created_checks": self.checks_created,
            "created_reports": self.reports_created,
            "created_scores": self.scores_created,
            "already_populated": status == "skipped",
        }


DEFAULT_ROLE_DESCRIPTIONS = {
    "admin": "Administrator with full access",
    "inspector": "Inspector responsible for performing checks",
    "crew_leader": "Crew leader overseeing brigade performance",
    "viewer": "Read-only access",
}

DEFAULT_ADMIN_EMAIL = "admin@example.com"
DEFAULT_ADMIN_PASSWORD = "admin123"
DEFAULT_ADMIN_NAME = "Administrator"

RESET_IGNORE_TABLES = {"alembic_version"}

DEMO_USERS = [
    {
        "email": "demo.inspector@example.com",
        "full_name": "Демо Инспектор",
        "password": "demo123!",
        "role": "inspector",
    },
    {
        "email": "demo.lead@example.com",
        "full_name": "Демо Руководитель",
        "password": "demo123!",
        "role": "crew_leader",
    },
    {
        "email": "demo.viewer@example.com",
        "full_name": "Демо Наблюдатель",
        "password": "demo123!",
        "role": "viewer",
    },
]

DEMO_BRIGADES = [
        {
            "name": "Demo Brigade Alpha",
            "description": "Команда по монтажу и пуско-наладке",
            "leader": "demo.lead@example.com",
            "members": [
                "demo.lead@example.com",
                "demo.inspector@example.com",
            ],
            "profile": {"project": "Project Phoenix", "shift": "A"},
        },
        {
            "name": "Demo Brigade Beta",
            "description": "Бригада по контролю качества",
            "leader": "demo.inspector@example.com",
            "members": [
                "demo.inspector@example.com",
                "demo.viewer@example.com",
            ],
            "profile": {"project": "Project Atlas", "shift": "B"},
        },
    ]

DEMO_TEMPLATES = [
    {
        "name": "Demo Template: Safety Walk",
        "description": "Контрольный лист для оценки безопасности на объекте.",
        "schema": {
            "sections": [
                {
                    "id": "safety",
                    "title": "Безопасность",
                    "questions": [
                        {
                            "id": "safety-gear",
                            "text": "Все сотрудники используют СИЗ?",
                            "type": "boolean",
                            "required": True,
                        },
                        {
                            "id": "hazards",
                            "text": "Есть ли выявленные опасности?",
                            "type": "text",
                            "required": False,
                            "meta": {"placeholder": "Опишите выявленные риски"},
                        },
                    ],
                },
                {
                    "id": "environment",
                    "title": "Рабочая среда",
                    "questions": [
                        {
                            "id": "cleanliness",
                            "text": "Рабочие зоны содержатся в чистоте?",
                            "type": "boolean",
                            "required": True,
                        },
                        {
                            "id": "equipment",
                            "text": "Оборудование обслужено и исправно?",
                            "type": "choice",
                            "required": True,
                            "meta": {
                                "options": [
                                    {"value": "ok", "label": "Да"},
                                    {"value": "maintenance", "label": "Требует обслуживания"},
                                    {"value": "faulty", "label": "Неисправно"},
                                ]
                            },
                        },
                    ],
                },
            ]
        },
    },
    {
        "name": "Demo Template: Final Inspection",
        "description": "Чек-лист для приемки готового проекта.",
        "schema": {
            "sections": [
                {
                    "id": "visual",
                    "title": "Визуальный осмотр",
                    "questions": [
                        {
                            "id": "finish-quality",
                            "text": "Качество отделки соответствует стандартам?",
                            "type": "boolean",
                            "required": True,
                        },
                        {
                            "id": "photos",
                            "text": "Приложены фото итогового состояния?",
                            "type": "attachment",
                            "required": False,
                        },
                    ],
                },
                {
                    "id": "documentation",
                    "title": "Документация",
                    "questions": [
                        {
                            "id": "reports",
                            "text": "Сформированы итоговые отчеты?",
                            "type": "boolean",
                            "required": True,
                        },
                        {
                            "id": "notes",
                            "text": "Комментарии",
                            "type": "text",
                            "required": False,
                            "meta": {"multiline": True},
                        },
                    ],
                },
            ]
        },
    },
    {
        "name": "Demo Template: Workspace Readiness",
        "description": "Состояние рабочего пространства укладчика-упаковщика и смежных ролей.",
        "schema": {
            "sections": [
                {
                    "id": "workspace-readiness",
                    "title": "Рабочая зона",
                    "questions": [
                        {
                            "id": "floor-cleanliness",
                            "text": "На полу отсутствует пыль и грязь, нет россыпей сырья или красителя.",
                            "type": "boolean",
                            "required": True,
                            "meta": {"critical": True, "requires_ok": True, "points": 2},
                        },
                        {
                            "id": "personal-items-removed",
                            "text": "Личные вещи отсутствуют в рабочей зоне. Работник использует головной убор и перчатки, волосы убраны.",
                            "type": "boolean",
                            "required": True,
                            "meta": {"critical": True, "requires_ok": True, "points": 2},
                        },
                        {
                            "id": "no-foreign-objects",
                            "text": "На оборудовании и рядом нет посторонних предметов, не относящихся к работе.",
                            "type": "boolean",
                            "required": True,
                            "meta": {"points": 1.5},
                        },
                        {
                            "id": "cleaning-tools-ready",
                            "text": "Уборочный инвентарь имеется и аккуратно размещен в установленном месте.",
                            "type": "boolean",
                            "required": True,
                            "meta": {"points": 1},
                        },
                        {
                            "id": "materials-zoned",
                            "text": "Тара, упаковка, поддоны и продукция находятся в разметке идеального рабочего места.",
                            "type": "boolean",
                            "required": True,
                            "meta": {"points": 1.5},
                        },
                        {
                            "id": "passages-clear",
                            "text": "Проходы вокруг оборудования свободны от загромождений.",
                            "type": "boolean",
                            "required": True,
                            "meta": {"critical": True, "requires_ok": True, "points": 2},
                        },
                    ],
                }
            ]
        },
    },
]

DEMO_CHECKS = [
    {
        "project_id": "DEMO-PROJECT-001",
        "template": "Demo Template: Safety Walk",
        "brigade": "Demo Brigade Alpha",
        "inspector": "demo.inspector@example.com",
        "status": CheckStatus.COMPLETED,
        "started_offset": {"days": 5, "hours": 3},
        "duration_hours": 2,
        "answers": {
            "safety-gear": True,
            "hazards": "Выявлены мелкие риски, устранены на месте.",
            "cleanliness": True,
            "equipment": "ok",
        },
        "report_formats": ["json"],
    },
    {
        "project_id": "DEMO-PROJECT-002",
        "template": "Demo Template: Safety Walk",
        "brigade": "Demo Brigade Beta",
        "inspector": "demo.inspector@example.com",
        "status": CheckStatus.IN_PROGRESS,
        "started_offset": {"days": 2, "hours": 6},
        "duration_hours": None,
        "answers": {
            "safety-gear": True,
            "hazards": "",
            "cleanliness": False,
            "equipment": "maintenance",
        },
        "report_formats": [],
    },
    {
        "project_id": "DEMO-PROJECT-003",
        "template": "Demo Template: Final Inspection",
        "brigade": "Demo Brigade Alpha",
        "inspector": "demo.lead@example.com",
        "status": CheckStatus.COMPLETED,
        "started_offset": {"days": 1, "hours": 4},
        "duration_hours": 3,
        "answers": {
            "finish-quality": True,
            "photos": ["minio://quality-control/demo/final/alpha.jpg"],
            "reports": True,
            "notes": "Проект принят без замечаний.",
        },
        "report_formats": ["html", "json"],
    },
    {
        "project_id": "DEMO-PROJECT-004",
        "template": "Demo Template: Workspace Readiness",
        "brigade": "Demo Brigade Beta",
        "inspector": "demo.inspector@example.com",
        "status": CheckStatus.COMPLETED,
        "started_offset": {"days": 3, "hours": 5},
        "duration_hours": 1.5,
        "answers": {
            "floor-cleanliness": True,
            "personal-items-removed": True,
            "no-foreign-objects": False,
            "cleaning-tools-ready": True,
            "materials-zoned": True,
            "passages-clear": False,
        },
        "report_formats": ["json"],
    },
    {
        "project_id": "DEMO-PROJECT-005",
        "template": "Demo Template: Workspace Readiness",
        "brigade": "Demo Brigade Alpha",
        "inspector": "demo.inspector@example.com",
        "status": CheckStatus.IN_PROGRESS,
        "planned_hours_ahead": 36,
        "answers": {},
        "report_formats": [],
    },
]


async def _ensure_roles(
    db: AsyncSession,
    *,
    role_names: Iterable[str],
) -> Dict[str, Role]:
    """Make sure that the required roles exist and return them."""
    created = False
    for role_name in role_names:
        result = await db.execute(select(Role).where(Role.name == role_name))
        role_obj = result.scalar_one_or_none()
        if role_obj:
            continue

        permissions = [
            permission.value
            for permission in ROLE_PERMISSIONS.get(role_name, [])
        ]
        role_obj = Role(
            name=role_name,
            permissions=permissions,
            description=DEFAULT_ROLE_DESCRIPTIONS.get(role_name),
        )
        db.add(role_obj)
        created = True

    if created:
        await db.commit()

    role_map: Dict[str, Role] = {}
    for role_name in role_names:
        result = await db.execute(select(Role).where(Role.name == role_name))
        role = result.scalar_one()
        role_map[role_name] = role
    return role_map


async def _get_or_create_users(
    db: AsyncSession,
    *,
    role_map: Dict[str, Role],
) -> Tuple[Dict[str, User], int]:
    """Create demo users if needed and return user map and created count."""
    user_map: Dict[str, User] = {}
    created_count = 0

    for payload in DEMO_USERS:
        result = await db.execute(
            select(User).where(User.email == payload["email"])
        )
        user_obj = result.scalar_one_or_none()
        if user_obj:
            user_map[payload["email"]] = user_obj
            continue

        user_obj = User(
            email=payload["email"],
            password_hash=AuthService.hash_password(payload["password"]),
            full_name=payload["full_name"],
            is_active=True,
        )
        role = role_map.get(payload["role"])
        if role:
            user_obj.roles = [role]
        db.add(user_obj)
        await db.flush()
        user_map[payload["email"]] = user_obj
        created_count += 1

    if created_count:
        await db.commit()

    return user_map, created_count


async def _create_test_admin_user(
    db: AsyncSession,
    *,
    admin_role: Role,
    email: str = DEFAULT_ADMIN_EMAIL,
    password: str = DEFAULT_ADMIN_PASSWORD,
    full_name: str = DEFAULT_ADMIN_NAME,
) -> User:
    """Create the default test administrator account."""
    if not admin_role:
        raise ValueError("Admin role is required to create the default administrator.")

    admin_user = User(
        email=email,
        password_hash=AuthService.hash_password(password),
        full_name=full_name,
        is_active=True,
    )
    admin_user.roles = [admin_role]
    db.add(admin_user)
    await db.commit()
    await db.refresh(admin_user)
    return admin_user


async def _create_brigades(
    db: AsyncSession,
    *,
    user_map: Dict[str, User],
) -> Tuple[Dict[str, Brigade], int, int]:
    """Create demo brigades when missing and return map plus counters."""
    brigade_map: Dict[str, Brigade] = {}
    brigades_created = 0
    scores_created = 0

    for payload in DEMO_BRIGADES:
        result = await db.execute(
            select(Brigade).where(Brigade.name == payload["name"])
        )
        brigade = result.scalar_one_or_none()
        if brigade:
            brigade_map[payload["name"]] = brigade
            continue

        leader = user_map.get(payload["leader"])
        members = [
            user_map[email]
            for email in payload["members"]
            if email in user_map
        ]

        brigade = Brigade(
            name=payload["name"],
            description=payload["description"],
            leader_id=leader.id if leader else None,
            is_active=True,
            profile=payload.get("profile") or {},
        )
        brigade.members = members
        db.add(brigade)
        await db.flush()

        brigade_map[payload["name"]] = brigade
        brigades_created += 1

        today = date.today()
        for days_ago, score in enumerate(
            [
                Decimal("82.5"),
                Decimal("85.0"),
                Decimal("88.2"),
                Decimal("90.5"),
                Decimal("92.0"),
            ],
            start=1,
        ):
            score_date = today - timedelta(days=days_ago)
            db.add(
                BrigadeDailyScore(
                    brigade_id=brigade.id,
                    score_date=score_date,
                    score=score,
                    details={
                        "productivity": max(0, float(score) - 70),
                        "incidents": 0 if score > Decimal("85.0") else 1,
                    },
                )
            )
            scores_created += 1

    if brigades_created or scores_created:
        await db.commit()

    return brigade_map, brigades_created, scores_created


async def _create_templates(
    db: AsyncSession,
    *,
    current_user: User,
) -> Tuple[Dict[str, ChecklistTemplate], int]:
    """Create demo checklist templates and return them with count."""
    template_map: Dict[str, ChecklistTemplate] = {}
    templates_created = 0

    for payload in DEMO_TEMPLATES:
        result = await db.execute(
            select(ChecklistTemplate).where(ChecklistTemplate.name == payload["name"])
        )
        template = result.scalar_one_or_none()
        if template:
            template_map[payload["name"]] = template
            continue

        template = ChecklistTemplate(
            name=payload["name"],
            description=payload["description"],
            schema=payload["schema"],
            status=TemplateStatus.ACTIVE,
        )
        template.created_by = current_user.id

        db.add(template)
        await db.flush()

        version = ChecklistTemplateVersion(
            template_id=template.id,
            version=template.version,
            schema=payload["schema"],
            diff=None,
            created_by=current_user.id,
        )
        db.add(version)

        template_map[payload["name"]] = template
        templates_created += 1

    if templates_created:
        await db.commit()

    return template_map, templates_created


async def _create_checks_and_reports(
    db: AsyncSession,
    *,
    template_map: Dict[str, ChecklistTemplate],
    brigade_map: Dict[str, Brigade],
    user_map: Dict[str, User],
    current_user: User,
) -> Dict[str, int]:
    """Create demo checks and reports if they are missing."""
    now = datetime.utcnow()
    created_checks = 0
    created_reports = 0

    for payload in DEMO_CHECKS:
        template = template_map.get(payload["template"])
        brigade = brigade_map.get(payload["brigade"])
        inspector = user_map.get(payload["inspector"])
        if not template or not brigade or not inspector:
            continue

        existing_stmt = (
            select(CheckInstance)
            .where(CheckInstance.project_id == payload["project_id"])
            .options(selectinload(CheckInstance.reports))
        )
        result = await db.execute(existing_stmt)
        existing_check = result.scalar_one_or_none()
        if existing_check:
            for report_obj in existing_check.reports:
                try:
                    await _ensure_report_file(report_obj, existing_check)
                except Exception as exc:
                    print(f"[demo] Failed to backfill report {report_obj.id}: {exc}")
            continue

        planned_hours_ahead = payload.get("planned_hours_ahead")
        started_offset = payload.get("started_offset")
        duration_hours = payload.get("duration_hours")

        scheduled_at = None
        started_at = None
        finished_at = None

        if planned_hours_ahead is not None:
            scheduled_at = now + timedelta(hours=planned_hours_ahead)
        elif started_offset is not None:
            started_at = now - timedelta(**started_offset)
            finished_at = (
                started_at + timedelta(hours=duration_hours)
                if duration_hours is not None
                else None
            )
            scheduled_at = started_at - timedelta(hours=12)
        else:
            scheduled_at = now
            started_at = now

        check = CheckInstance(
            template_id=template.id,
            template_version=template.version,
            project_id=payload["project_id"],
            department_id="QA",
            scheduled_at=scheduled_at,
            started_at=started_at,
            finished_at=finished_at,
            inspector_id=inspector.id,
            brigade_id=brigade.id,
            status=payload["status"],
            answers=payload.get("answers", {}),
            comments={"summary": "Generated for demo purposes"},
        )
        db.add(check)
        await db.flush()
        created_checks += 1

        for fmt in payload["report_formats"]:
            report_format = ReportFormat(fmt) if isinstance(fmt, str) else fmt
            report = Report(
                check_instance_id=check.id,
                format=report_format,
                file_key=f"demo/{check.id}/{report_format.value}",
                status=ReportStatus.READY,
                generated_by=current_user.id,
            )
            db.add(report)
            await db.flush()
            created_reports += 1
            try:
                await _ensure_report_file(report, check)
            except Exception as exc:
                # Log silently; demo data generation should not fail due to missing storage
                print(f"[demo] Failed to upload placeholder report {report.id}: {exc}")

    if created_checks or created_reports:
        await db.commit()

    return {
        "checks_created": created_checks,
        "reports_created": created_reports,
    }


async def _ensure_report_file(report_obj: Report, check: CheckInstance) -> None:
    """Upload a placeholder file for demo reports if nothing exists yet."""
    exists = await asyncio.to_thread(storage_service.file_exists, report_obj.file_key)
    if exists:
        return

    content_type = "application/octet-stream"
    payload_bytes = b"Demo report generated for showcase purposes."

    if report_obj.format == ReportFormat.JSON:
        content_type = "application/json"
        payload = {
            "report_id": str(report_obj.id),
            "check_id": str(check.id),
            "project_id": check.project_id,
            "brigade_id": str(check.brigade_id) if check.brigade_id is not None else None,
            "status": check.status.value if isinstance(check.status, CheckStatus) else str(check.status),
            "generated_at": datetime.utcnow().isoformat(),
            "summary": "Автоматически сгенерированный отчет для демо-показа.",
            "answers": check.answers,
        }
        payload_bytes = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    elif report_obj.format == ReportFormat.HTML:
        content_type = "text/html; charset=utf-8"
        answers_html = "".join(
            f"<li><strong>{key}:</strong> {value}</li>"
            for key, value in (check.answers or {}).items()
        )
        payload_bytes = (
            "<!doctype html>"
            "<html lang='ru'><head><meta charset='utf-8'>"
            "<title>Демо отчет</title>"
            "<style>body{font-family:Arial,sans-serif;margin:32px;color:#111}h1{margin-top:0}"
            "ul{padding-left:18px}</style>"
            "</head><body>"
            f"<h1>Демонстрационный отчет {report_obj.id}</h1>"
            f"<p><strong>Проект:</strong> {check.project_id or '—'}</p>"
            f"<p><strong>Статус обхода:</strong> {check.status}</p>"
            "<h2>Ответы</h2>"
            f"<ul>{answers_html or '<li>Ответы отсутствуют</li>'}</ul>"
            "<p style='margin-top:32px;font-size:14px;color:#555'>Этот файл создан автоматически для демонстрации возможности скачивания отчетов.</p>"
            "</body></html>"
        ).encode("utf-8")

    buffer = BytesIO(payload_bytes)
    buffer.seek(0)
    await asyncio.to_thread(
        storage_service.upload_fileobj,
        buffer,
        report_obj.file_key,
        content_type,
    )

async def generate_demo_data(db: AsyncSession, current_user: User) -> Dict[str, Any]:
    """Generate or reuse demo entities for showcasing the system."""
    counters = DemoDataResult()

    required_roles = {"inspector", "crew_leader", "viewer"}
    role_map = await _ensure_roles(db, role_names=required_roles)

    user_map, counters.users_created = await _get_or_create_users(
        db, role_map=role_map
    )

    brigade_map, counters.brigades_created, counters.scores_created = (
        await _create_brigades(db, user_map=user_map)
    )

    template_map, counters.templates_created = await _create_templates(
        db, current_user=current_user
    )

    checks_reports = await _create_checks_and_reports(
        db,
        template_map=template_map,
        brigade_map=brigade_map,
        user_map=user_map,
        current_user=current_user,
    )
    counters.checks_created = checks_reports["checks_created"]
    counters.reports_created = checks_reports["reports_created"]

    return counters.as_payload()


async def reset_project_to_clean_state(db: AsyncSession) -> Dict[str, Any]:
    """Wipe project data and recreate only the default administrator account."""
    total_removed = 0

    for table in reversed(Base.metadata.sorted_tables):
        if table.name in RESET_IGNORE_TABLES:
            continue
        result = await db.execute(table.delete())
        rowcount = getattr(result, "rowcount", None)
        if rowcount is not None and rowcount > 0:
            total_removed += rowcount
    await db.commit()

    role_names = set(ROLE_PERMISSIONS.keys())
    role_map = await _ensure_roles(db, role_names=role_names)
    admin_role = role_map.get("admin")
    if not admin_role:
        raise RuntimeError("Failed to initialize admin role during project reset.")

    admin_user = await _create_test_admin_user(db, admin_role=admin_role)

    return {
        "status": "reset",
        "detail": "Создан чистый проект с тестовым администратором.",
        "records_removed": total_removed,
        "roles_seeded": len(role_map),
        "admin_email": admin_user.email,
        "admin_password": DEFAULT_ADMIN_PASSWORD,
    }


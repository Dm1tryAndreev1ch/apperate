"""Tests for schedule service utilities."""
from datetime import datetime
from uuid import uuid4

import pytest

from app.models.schedule import Schedule
from app.models.brigade import Brigade
from app.models.checklist import CheckStatus
from app.services.schedule_service import schedule_service
from app.services.checklist_service import checklist_service


@pytest.mark.asyncio
async def test_spawn_check_with_forced_assignments(db_session, test_template, test_user):
    """Schedule service should create check with provided inspector and brigade."""
    brigade = Brigade(
        id=uuid4(),
        name="Crew Alpha",
        is_active=True,
    )
    brigade.members = [test_user]
    db_session.add(brigade)
    await db_session.commit()
    await db_session.refresh(brigade)

    schedule = Schedule(
        id=uuid4(),
        name="Daily rotation",
        template_id=test_template.id,
        cron_or_rrule="* * * * *",
        inspector_pool=None,
        brigade_pool=None,
        last_inspector_index=0,
        last_brigade_index=0,
        enabled=True,
    )
    db_session.add(schedule)
    await db_session.commit()
    await db_session.refresh(schedule)

    new_check = await schedule_service.spawn_check(
        db_session,
        schedule,
        force_inspector_id=test_user.id,
        force_brigade_id=brigade.id,
    )

    assert new_check.inspector_id == test_user.id
    assert new_check.brigade_id == brigade.id
    assert new_check.status == CheckStatus.IN_PROGRESS
    assert new_check.template_id == test_template.id


def test_calculate_score_boolean_schema():
    """Score calculation should honour boolean answers with weighting."""
    schema = {
        "sections": [
            {
                "name": "Safety",
                "questions": [
                    {
                        "id": "q1",
                        "type": "boolean",
                        "required": True,
                        "meta": {"points": 2},
                    },
                    {
                        "id": "q2",
                        "type": "boolean",
                        "required": False,
                        "meta": {"points": 1},
                    },
                ],
            }
        ]
    }

    all_ok = checklist_service.calculate_score(schema, {"q1": True, "q2": True})
    assert all_ok == 100.0

    partial = checklist_service.calculate_score(schema, {"q1": True, "q2": False})
    assert partial == pytest.approx(66.67, rel=1e-2)

    none_ok = checklist_service.calculate_score(schema, {"q1": False, "q2": False})
    assert none_ok == 0.0


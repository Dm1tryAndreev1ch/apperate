"""Tests covering brigade-related functionality."""
from datetime import datetime
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.models.brigade import Brigade, BrigadeDailyScore
from app.models.checklist import CheckInstance, CheckStatus
from app.models.report import Report, ReportStatus
from app.tasks.reports import generate_report


@pytest.mark.asyncio
async def test_complete_check_updates_brigade_score(
    client,
    db_session,
    auth_headers,
    test_template,
    test_user,
    monkeypatch,
):
    """Completing a check should update brigade daily score."""
    monkeypatch.setattr(generate_report, "delay", lambda *args, **kwargs: None)
    brigade = Brigade(
        id=uuid4(),
        name="Crew Bravo",
        is_active=True,
    )
    brigade.members = [test_user]
    db_session.add(brigade)
    await db_session.commit()
    await db_session.refresh(brigade)

    check = CheckInstance(
        id=uuid4(),
        template_id=test_template.id,
        template_version=test_template.version,
        inspector_id=test_user.id,
        brigade_id=brigade.id,
        status=CheckStatus.IN_PROGRESS,
        answers={"q1": True},
        started_at=datetime.utcnow(),
    )
    db_session.add(check)
    await db_session.commit()

    response = client.post(f"/api/v1/checks/{check.id}/complete", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["status"] == "COMPLETED"

    result = await db_session.execute(
        select(BrigadeDailyScore).where(BrigadeDailyScore.brigade_id == brigade.id)
    )
    scores = result.scalars().all()
    assert len(scores) == 1
    assert scores[0].score > 0


@pytest.mark.asyncio
async def test_report_analytics_includes_brigade_scores(
    client,
    db_session,
    auth_headers,
    test_template,
    test_user,
    monkeypatch,
):
    """Analytics endpoint should expose brigade score summaries."""
    monkeypatch.setattr(generate_report, "delay", lambda *args, **kwargs: None)
    brigade = Brigade(
        id=uuid4(),
        name="Crew Analytics",
        is_active=True,
    )
    db_session.add(brigade)
    await db_session.commit()
    await db_session.refresh(brigade)

    score_entry = BrigadeDailyScore(
        id=uuid4(),
        brigade_id=brigade.id,
        score_date=datetime.utcnow().date(),
        score=82.5,
        details={"checks": []},
    )
    db_session.add(score_entry)

    completed_check = CheckInstance(
        id=uuid4(),
        template_id=test_template.id,
        template_version=test_template.version,
        inspector_id=test_user.id,
        status=CheckStatus.COMPLETED,
        answers={"q1": True},
        started_at=datetime.utcnow(),
        finished_at=datetime.utcnow(),
    )
    db_session.add(completed_check)

    ready_report = Report(
        id=uuid4(),
        check_instance_id=completed_check.id,
        format="pdf",
        status=ReportStatus.READY,
        generated_by=test_user.id,
    )
    db_session.add(ready_report)
    await db_session.commit()

    response = client.get("/api/v1/reports/analytics", headers=auth_headers)
    assert response.status_code == 200
    payload = response.json()

    assert "brigade_scores" in payload
    assert "charts" in payload
    brigade_labels = [entry["label"] for entry in payload["brigade_scores"]]
    assert brigade.name in brigade_labels
    assert "brigade_scores" in payload["charts"]
    chart_payload = payload["charts"]["brigade_scores"]
    assert chart_payload["kind"] == "bar"
    assert chart_payload["image"].startswith("data:image/png;base64,")


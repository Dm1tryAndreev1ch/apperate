"""Tests for analytics service."""
import pytest
from uuid import uuid4
from datetime import date, datetime, timedelta
from decimal import Decimal

from app.models.checklist import CheckInstance, CheckStatus
from app.models.brigade import Brigade, BrigadeDailyScore
from app.models.user import User
from app.services.analytics_service import analytics_service


@pytest.mark.asyncio
async def test_compute_brigade_score(db_session, test_user):
    """Test computing brigade score from check instances."""
    # Create brigade
    brigade = Brigade(
        id=uuid4(),
        name="Test Brigade",
        is_active=True,
    )
    db_session.add(brigade)
    test_user.brigades.append(brigade)
    await db_session.commit()
    
    # Create template with scoring schema
    from app.models.checklist import ChecklistTemplate, TemplateStatus
    from app.utils.slugify import slugify
    template = ChecklistTemplate(
        id=uuid4(),
        name="Test Template",
        name_slug=slugify("Test Template"),
        schema={
            "sections": [{
                "name": "Section 1",
                "questions": [{
                    "id": "q1",
                    "type": "boolean",
                    "text": "Is OK?",
                    "required": True,
                }]
            }]
        },
        version=1,
        status=TemplateStatus.ACTIVE,
        created_by=test_user.id,
    )
    db_session.add(template)
    await db_session.commit()
    
    # Create completed check with answers
    check = CheckInstance(
        id=uuid4(),
        template_id=template.id,
        template_version=1,
        inspector_id=test_user.id,
        brigade_id=brigade.id,
        status=CheckStatus.COMPLETED,
        answers={"q1": True},
        started_at=datetime.utcnow(),
        finished_at=datetime.utcnow(),
    )
    db_session.add(check)
    await db_session.commit()
    
    # Compute score
    score = await analytics_service.compute_brigade_score(
        db_session,
        brigade_id=brigade.id,
        score_date=date.today(),
    )
    
    assert score is not None
    assert score.brigade_id == brigade.id
    assert score.score_date == date.today()
    assert score.score >= 0
    assert score.score <= 100


@pytest.mark.asyncio
async def test_compute_report_analytics(db_session, test_user):
    """Test computing report analytics."""
    from app.models.checklist import ChecklistTemplate, TemplateStatus
    from app.models.report import Report, ReportStatus, ReportFormatXLSX
    
    # Create template
    from app.utils.slugify import slugify
    template = ChecklistTemplate(
        id=uuid4(),
        name="Test Template",
        name_slug=slugify("Test Template"),
        schema={"sections": []},
        version=1,
        status=TemplateStatus.ACTIVE,
        created_by=test_user.id,
    )
    db_session.add(template)
    await db_session.commit()
    
    # Create check instance
    check = CheckInstance(
        id=uuid4(),
        template_id=template.id,
        template_version=1,
        inspector_id=test_user.id,
        status=CheckStatus.COMPLETED,
        answers={"q1": True},
        started_at=datetime.utcnow(),
        finished_at=datetime.utcnow(),
    )
    db_session.add(check)
    await db_session.commit()
    
    # Create report
    report = Report(
        id=uuid4(),
        check_instance_id=check.id,
        format=ReportFormatXLSX.XLSX,
        status=ReportStatus.READY,
        generated_by=test_user.id,
        author_id=test_user.id,
        metadata_json={},
    )
    db_session.add(report)
    await db_session.commit()
    
    # Compute analytics
    analytics = await analytics_service.compute_report_analytics(
        db_session,
        check_instance_id=check.id,
    )
    
    assert analytics is not None
    assert analytics.check_instance_id == check.id
    assert analytics.total_questions >= 0
    assert analytics.answered_questions >= 0


@pytest.mark.asyncio
async def test_compute_period_summary(db_session, test_user):
    """Test computing period summary."""
    from app.models.reporting import PeriodSummaryGranularity
    
    # Create brigade
    brigade = Brigade(
        id=uuid4(),
        name="Test Brigade",
        is_active=True,
    )
    db_session.add(brigade)
    await db_session.commit()
    
    # Create daily scores
    for i in range(5):
        score_date = date.today() - timedelta(days=i)
        daily_score = BrigadeDailyScore(
            id=uuid4(),
            brigade_id=brigade.id,
            score_date=score_date,
            score=Decimal("85.5"),
            overall_score=Decimal("90.0"),
            formula_version="v1",
        )
        db_session.add(daily_score)
    await db_session.commit()
    
    # Compute period summary
    summary = await analytics_service.compute_period_summary(
        db_session,
        granularity=PeriodSummaryGranularity.DAY,
        period_start=date.today() - timedelta(days=7),
        period_end=date.today(),
        brigade_id=brigade.id,
    )
    
    assert summary is not None
    assert summary.granularity == "day"
    assert len(summary.brigade_scores) > 0
    assert any(bs.brigade_id == brigade.id for bs in summary.brigade_scores)


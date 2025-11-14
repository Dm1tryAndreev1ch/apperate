"""Integration tests for reports API endpoints."""
import pytest
from uuid import uuid4
from datetime import date, datetime, timedelta

from app.models.checklist import CheckInstance, CheckStatus, ChecklistTemplate, TemplateStatus
from app.models.report import Report, ReportStatus, ReportFormatXLSX
from app.models.brigade import Brigade, BrigadeDailyScore
from decimal import Decimal


@pytest.mark.asyncio
async def test_generate_report_endpoint(client, db_session, auth_headers, test_template, test_user, monkeypatch):
    """Test report generation endpoint."""
    # Mock Celery task
    from app.tasks.reports import generate_report
    monkeypatch.setattr(generate_report, "delay", lambda *args, **kwargs: None)
    
    # Create completed check
    check = CheckInstance(
        id=uuid4(),
        template_id=test_template.id,
        template_version=test_template.version,
        inspector_id=test_user.id,
        status=CheckStatus.COMPLETED,
        answers={"q1": True},
        started_at=datetime.utcnow(),
        finished_at=datetime.utcnow(),
    )
    db_session.add(check)
    await db_session.commit()
    
    # Generate report
    response = client.post(
        f"/api/v1/reports/generate/{check.id}",
        headers=auth_headers,
        json={}
    )
    
    assert response.status_code in [200, 201, 202]
    data = response.json()
    assert "report_id" in data or "id" in data


@pytest.mark.asyncio
async def test_list_reports_with_filtering(client, db_session, auth_headers, test_template, test_user):
    """Test listing reports with filtering and sorting."""
    # Create multiple reports
    for i in range(3):
        check = CheckInstance(
            id=uuid4(),
            template_id=test_template.id,
            template_version=1,
            inspector_id=test_user.id,
            status=CheckStatus.COMPLETED,
            answers={},
            started_at=datetime.utcnow() - timedelta(days=i),
            finished_at=datetime.utcnow() - timedelta(days=i),
        )
        db_session.add(check)
        await db_session.flush()
        
        report = Report(
            id=uuid4(),
            check_instance_id=check.id,
            format=ReportFormatXLSX.XLSX,
            status=ReportStatus.READY if i < 2 else ReportStatus.GENERATING,
            generated_by=test_user.id,
            author_id=test_user.id,
            metadata_json={},
            created_at=datetime.utcnow() - timedelta(days=i),
        )
        db_session.add(report)
    
    await db_session.commit()
    
    # Test listing with status filter
    response = client.get(
        "/api/v1/reports?status_filter=READY",
        headers=auth_headers
    )
    assert response.status_code == 200
    reports = response.json()
    assert len(reports) == 2
    assert all(r["status"] == "READY" for r in reports)
    
    # Test sorting by date
    response = client.get(
        "/api/v1/reports?sort_by=created_at&sort_order=desc",
        headers=auth_headers
    )
    assert response.status_code == 200
    reports = response.json()
    if len(reports) > 1:
        dates = [r["created_at"] for r in reports]
        assert dates == sorted(dates, reverse=True)


@pytest.mark.asyncio
async def test_download_report_endpoint(client, db_session, auth_headers, test_template, test_user, monkeypatch):
    """Test report download endpoint."""
    # Mock storage service
    from app.services.storage_service import storage_service
    original_generate = storage_service.generate_download_url
    
    def mock_generate_url(key, expires_in=3600):
        return f"https://storage.example.com/{key}?expires=123456"
    
    monkeypatch.setattr(storage_service, "generate_download_url", mock_generate_url)
    
    check = CheckInstance(
        id=uuid4(),
        template_id=test_template.id,
        template_version=1,
        inspector_id=test_user.id,
        status=CheckStatus.COMPLETED,
        answers={},
        started_at=datetime.utcnow(),
        finished_at=datetime.utcnow(),
    )
    db_session.add(check)
    await db_session.flush()
    
    report = Report(
        id=uuid4(),
        check_instance_id=check.id,
        format=ReportFormatXLSX.XLSX,
        status=ReportStatus.READY,
        file_key="reports/test-report.xlsx",
        generated_by=test_user.id,
        author_id=test_user.id,
        metadata_json={},
    )
    db_session.add(report)
    await db_session.commit()
    
    # Test download endpoint
    response = client.get(
        f"/api/v1/reports/{report.id}/download",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "download_url" in data
    assert "test-report.xlsx" in data["download_url"]


@pytest.mark.asyncio
async def test_report_analytics_endpoint(client, db_session, auth_headers, test_template, test_user):
    """Test report analytics endpoint."""
    # Create reports with metadata
    for i in range(2):
        check = CheckInstance(
            id=uuid4(),
            template_id=test_template.id,
            template_version=1,
            inspector_id=test_user.id,
            status=CheckStatus.COMPLETED,
            answers={"q1": True},
            started_at=datetime.utcnow() - timedelta(days=i),
            finished_at=datetime.utcnow() - timedelta(days=i),
        )
        db_session.add(check)
        await db_session.flush()
        
        report = Report(
            id=uuid4(),
            check_instance_id=check.id,
            format=ReportFormatXLSX.XLSX,
            status=ReportStatus.READY,
            generated_by=test_user.id,
            author_id=test_user.id,
            metadata_json={
                "analytics": {
                    "avg_score": 85.5 + i * 5,
                    "total_questions": 10,
                    "answered_questions": 8,
                }
            },
            created_at=datetime.utcnow() - timedelta(days=i),
        )
        db_session.add(report)
    
    await db_session.commit()
    
    # Get analytics
    response = client.get(
        "/api/v1/reports/analytics?days=30",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "total_reports" in data
    assert "avg_score" in data
    assert data["total_reports"] >= 2


@pytest.mark.asyncio
async def test_period_summaries_endpoint(client, db_session, auth_headers, test_user):
    """Test period summaries endpoint."""
    # Create brigade with scores
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
    
    # Get period summaries
    response = client.get(
        "/api/v1/reports/summaries?granularity=day&period_start="
        f"{(date.today() - timedelta(days=7)).isoformat()}&period_end={date.today().isoformat()}",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    summaries = response.json()
    assert isinstance(summaries, list)
    if len(summaries) > 0:
        assert "granularity" in summaries[0]
        assert "metrics" in summaries[0]


@pytest.mark.asyncio
async def test_check_logs_endpoint(client, db_session, auth_headers, test_template, test_user):
    """Test check logs endpoint."""
    check = CheckInstance(
        id=uuid4(),
        template_id=test_template.id,
        template_version=1,
        inspector_id=test_user.id,
        status=CheckStatus.COMPLETED,
        answers={"q1": True, "q2": False},
        started_at=datetime.utcnow(),
        finished_at=datetime.utcnow(),
    )
    db_session.add(check)
    await db_session.commit()
    
    # Get check logs
    response = client.get(
        f"/api/v1/reports/checks/{check.id}/logs",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    logs = response.json()
    assert "check_id" in logs
    assert logs["check_id"] == str(check.id)
    assert "entries" in logs


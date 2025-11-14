"""Integration tests for dashboards API endpoints."""
import pytest
from uuid import uuid4
from datetime import date, datetime, timedelta
from decimal import Decimal

from app.models.checklist import CheckInstance, CheckStatus, ChecklistTemplate, TemplateStatus
from app.models.report import Report, ReportStatus, ReportFormatXLSX
from app.models.brigade import Brigade, BrigadeDailyScore
from app.models.reporting import RemarkEntry, RemarkSeverity


@pytest.mark.asyncio
async def test_admin_dashboard_endpoint(client, db_session, auth_headers, test_template, test_user):
    """Test admin dashboard endpoint."""
    # Create test data
    brigade = Brigade(
        id=uuid4(),
        name="Test Brigade",
        is_active=True,
    )
    db_session.add(brigade)
    await db_session.commit()
    
    # Create reports
    for i in range(3):
        check = CheckInstance(
            id=uuid4(),
            template_id=test_template.id,
            template_version=1,
            inspector_id=test_user.id,
            brigade_id=brigade.id,
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
            metadata_json={},
            created_at=datetime.utcnow() - timedelta(days=i),
        )
        db_session.add(report)
    
    # Create brigade score
    daily_score = BrigadeDailyScore(
        id=uuid4(),
        brigade_id=brigade.id,
        score_date=date.today(),
        score=Decimal("85.5"),
        overall_score=Decimal("90.0"),
        formula_version="v1",
    )
    db_session.add(daily_score)
    
    # Create critical remark
    remark = RemarkEntry(
        id=uuid4(),
        check_instance_id=check.id,
        severity=RemarkSeverity.CRITICAL,
        message="Critical issue found",
        raised_at=datetime.utcnow(),
    )
    db_session.add(remark)
    await db_session.commit()
    
    # Get admin dashboard
    response = client.get(
        "/api/v1/dashboards/admin?days=30",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    dashboard = response.json()
    
    assert "period" in dashboard
    assert "kpis" in dashboard
    assert "total_reports" in dashboard["kpis"]
    assert "completed_checks" in dashboard["kpis"]
    assert "active_brigades" in dashboard["kpis"]
    assert "critical_remarks" in dashboard["kpis"]
    assert "recent_reports" in dashboard
    assert "top_brigades" in dashboard


@pytest.mark.asyncio
async def test_user_dashboard_endpoint(client, db_session, auth_headers, test_template, test_user):
    """Test user dashboard endpoint."""
    # Create user's reports
    for i in range(2):
        check = CheckInstance(
            id=uuid4(),
            template_id=test_template.id,
            template_version=1,
            inspector_id=test_user.id,
            status=CheckStatus.COMPLETED if i == 0 else CheckStatus.IN_PROGRESS,
            answers={"q1": True} if i == 0 else {},
            started_at=datetime.utcnow() - timedelta(days=i),
            finished_at=datetime.utcnow() - timedelta(days=i) if i == 0 else None,
        )
        db_session.add(check)
        await db_session.flush()
        
        if i == 0:
            report = Report(
                id=uuid4(),
                check_instance_id=check.id,
                format=ReportFormatXLSX.XLSX,
                status=ReportStatus.READY,
                generated_by=test_user.id,
                author_id=test_user.id,
                metadata_json={
                    "analytics": {
                        "avg_score": 85.5,
                    }
                },
                created_at=datetime.utcnow() - timedelta(days=i),
            )
            db_session.add(report)
    
    await db_session.commit()
    
    # Get user dashboard
    response = client.get(
        "/api/v1/dashboards/user?days=30",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    dashboard = response.json()
    
    assert "period" in dashboard
    assert "kpis" in dashboard
    assert "total_reports" in dashboard["kpis"]
    assert "completed_checks" in dashboard["kpis"]
    assert "recent_reports" in dashboard
    assert "assigned_checks" in dashboard


@pytest.mark.asyncio
async def test_brigade_scores_dashboard_endpoint(client, db_session, auth_headers, test_user):
    """Test brigade scores dashboard endpoint."""
    # Create brigade with scores
    brigade = Brigade(
        id=uuid4(),
        name="Test Brigade",
        is_active=True,
    )
    db_session.add(brigade)
    test_user.brigades.append(brigade)
    await db_session.commit()
    
    # Create multiple daily scores
    for i in range(7):
        score_date = date.today() - timedelta(days=i)
        daily_score = BrigadeDailyScore(
            id=uuid4(),
            brigade_id=brigade.id,
            score_date=score_date,
            score=Decimal("80.0") + Decimal(str(i * 2)),
            overall_score=Decimal("85.0") + Decimal(str(i * 2)),
            formula_version="v1",
        )
        db_session.add(daily_score)
    await db_session.commit()
    
    # Get brigade scores
    response = client.get(
        f"/api/v1/dashboards/brigade-scores?days=30&brigade_id={brigade.id}",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert "period" in data
    assert "brigades" in data
    assert len(data["brigades"]) > 0
    brigade_data = data["brigades"][0]
    assert brigade_data["brigade_id"] == str(brigade.id)
    assert "scores" in brigade_data
    assert len(brigade_data["scores"]) > 0


@pytest.mark.asyncio
async def test_dashboard_filters_by_user(client, db_session, auth_headers, test_template, test_user):
    """Test that user dashboard only shows user's own data."""
    # Create another user
    from app.models.user import User
    from app.services.auth_service import AuthService
    other_user = User(
        id=uuid4(),
        email="other@example.com",
        password_hash=AuthService.hash_password("password"),
        full_name="Other User",
        is_active=True,
    )
    db_session.add(other_user)
    await db_session.commit()
    
    # Create reports for both users
    for user, count in [(test_user, 2), (other_user, 1)]:
        for i in range(count):
            check = CheckInstance(
                id=uuid4(),
                template_id=test_template.id,
                template_version=1,
                inspector_id=user.id,
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
                generated_by=user.id,
                author_id=user.id,
                metadata_json={},
                created_at=datetime.utcnow() - timedelta(days=i),
            )
            db_session.add(report)
    
    await db_session.commit()
    
    # Get user dashboard (should only show test_user's reports)
    response = client.get(
        "/api/v1/dashboards/user?days=30",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    dashboard = response.json()
    
    # Should only show test_user's reports (2)
    assert dashboard["kpis"]["total_reports"] == 2
    assert len(dashboard["recent_reports"]) <= 2


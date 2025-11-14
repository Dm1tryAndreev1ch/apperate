"""End-to-end tests for complete workflows."""
import pytest
from uuid import uuid4
from datetime import datetime, timedelta, date
from decimal import Decimal

from app.models.checklist import CheckInstance, CheckStatus, ChecklistTemplate, TemplateStatus
from app.models.report import Report, ReportStatus, ReportFormatXLSX
from app.models.brigade import Brigade, BrigadeDailyScore
from app.models.user import User
from app.services.auth_service import AuthService


@pytest.mark.asyncio
async def test_complete_check_to_report_workflow(
    client, db_session, auth_headers, test_user, monkeypatch
):
    """Test complete workflow: create check -> complete -> generate report -> view in dashboard."""
    # Mock Celery task
    from app.tasks.reports import generate_report
    monkeypatch.setattr(generate_report, "delay", lambda *args, **kwargs: None)
    
    # 1. Create template
    template_data = {
        "name": "E2E Test Template",
        "description": "End-to-end test",
        "schema": {
            "sections": [{
                "name": "Section 1",
                "questions": [{
                    "id": "q1",
                    "type": "boolean",
                    "text": "Is everything OK?",
                    "required": True,
                }]
            }]
        },
    }
    create_response = client.post(
        "/api/v1/templates",
        headers=auth_headers,
        json=template_data
    )
    assert create_response.status_code == 201
    template = create_response.json()
    template_id = template["id"]
    
    # 2. Create check instance
    check_data = {
        "template_id": template_id,
        "project_id": "project-123",
    }
    check_response = client.post(
        "/api/v1/checks",
        headers=auth_headers,
        json=check_data
    )
    assert check_response.status_code == 201
    check = check_response.json()
    check_id = check["id"]
    
    # 3. Add answers to check
    answer_response = client.post(
        f"/api/v1/checks/{check_id}/answer",
        headers=auth_headers,
        json={"question_id": "q1", "value": True}
    )
    assert answer_response.status_code in [200, 201]
    
    # 4. Complete check
    complete_response = client.post(
        f"/api/v1/checks/{check_id}/complete",
        headers=auth_headers
    )
    assert complete_response.status_code == 200
    completed_check = complete_response.json()
    assert completed_check["status"] == "COMPLETED"
    
    # 5. Generate report
    report_response = client.post(
        f"/api/v1/reports/generate/{check_id}",
        headers=auth_headers,
        json={}
    )
    assert report_response.status_code in [200, 201, 202]
    
    # 6. Verify report appears in user dashboard
    dashboard_response = client.get(
        "/api/v1/dashboards/user?days=30",
        headers=auth_headers
    )
    assert dashboard_response.status_code == 200
    dashboard = dashboard_response.json()
    assert dashboard["kpis"]["completed_checks"] >= 1


@pytest.mark.asyncio
async def test_template_crud_workflow(client, db_session, auth_headers):
    """Test complete template CRUD workflow."""
    # 1. Create template
    template_data = {
        "name": "CRUD Test Template",
        "description": "Testing CRUD operations",
        "schema": {
            "sections": [{
                "name": "Section 1",
                "questions": [{
                    "id": "q1",
                    "type": "boolean",
                    "text": "Question 1",
                    "required": True,
                }]
            }]
        },
    }
    create_response = client.post(
        "/api/v1/templates",
        headers=auth_headers,
        json=template_data
    )
    assert create_response.status_code == 201
    template = create_response.json()
    template_id = template["id"]
    original_slug = template["name_slug"]
    
    # 2. Read template
    get_response = client.get(
        f"/api/v1/templates/{template_id}",
        headers=auth_headers
    )
    assert get_response.status_code == 200
    assert get_response.json()["name"] == "CRUD Test Template"
    
    # 3. Get by slug
    slug_response = client.get(
        f"/api/v1/templates/slug/{original_slug}",
        headers=auth_headers
    )
    assert slug_response.status_code == 200
    assert slug_response.json()["id"] == template_id
    
    # 4. Update template
    update_data = {
        "name": "Updated CRUD Template",
        "description": "Updated description",
    }
    update_response = client.put(
        f"/api/v1/templates/{template_id}",
        headers=auth_headers,
        json=update_data
    )
    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated["name"] == "Updated CRUD Template"
    
    # 5. Clone template
    clone_response = client.post(
        f"/api/v1/templates/{template_id}/clone?new_name=Cloned CRUD Template",
        headers=auth_headers
    )
    assert clone_response.status_code == 201
    cloned = clone_response.json()
    assert cloned["name"] == "Cloned CRUD Template"
    assert cloned["id"] != template_id
    
    # 6. List templates (should include both)
    list_response = client.get(
        "/api/v1/templates",
        headers=auth_headers
    )
    assert list_response.status_code == 200
    templates = list_response.json()
    template_names = [t["name"] for t in templates]
    assert "Updated CRUD Template" in template_names
    assert "Cloned CRUD Template" in template_names


@pytest.mark.asyncio
async def test_report_generation_with_analytics_workflow(
    client, db_session, auth_headers, test_template, test_user, monkeypatch
):
    """Test report generation with analytics and brigade scores."""
    # Mock Celery and storage
    from app.tasks.reports import generate_report
    from app.services.storage_service import storage_service
    monkeypatch.setattr(generate_report, "delay", lambda *args, **kwargs: None)
    
    def mock_upload(key, data, content_type):
        return {"key": key, "url": f"https://storage.example.com/{key}"}
    
    monkeypatch.setattr(storage_service, "upload_file", mock_upload)
    
    # Create brigade
    brigade = Brigade(
        id=uuid4(),
        name="E2E Brigade",
        is_active=True,
    )
    db_session.add(brigade)
    test_user.brigades.append(brigade)
    await db_session.commit()
    
    # Create and complete check
    check = CheckInstance(
        id=uuid4(),
        template_id=test_template.id,
        template_version=test_template.version,
        inspector_id=test_user.id,
        brigade_id=brigade.id,
        status=CheckStatus.COMPLETED,
        answers={"q1": True},
        started_at=datetime.utcnow(),
        finished_at=datetime.utcnow(),
    )
    db_session.add(check)
    await db_session.commit()
    
    # Generate report
    report_response = client.post(
        f"/api/v1/reports/generate/{check.id}",
        headers=auth_headers,
        json={}
    )
    assert report_response.status_code in [200, 201, 202]
    
    # Wait a bit for async processing (in real scenario)
    # Here we'll check the report was created
    reports_response = client.get(
        "/api/v1/reports",
        headers=auth_headers
    )
    assert reports_response.status_code == 200
    reports = reports_response.json()
    assert len(reports) > 0
    
    # Check analytics endpoint
    analytics_response = client.get(
        "/api/v1/reports/analytics?days=30",
        headers=auth_headers
    )
    assert analytics_response.status_code == 200
    analytics = analytics_response.json()
    assert "total_reports" in analytics
    assert analytics["total_reports"] >= 1


@pytest.mark.asyncio
async def test_admin_vs_user_dashboard_separation(
    client, db_session, auth_headers, test_template, test_user
):
    """Test that admin and user dashboards show correct data."""
    # Create another user
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
    for user, count in [(test_user, 3), (other_user, 2)]:
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
    
    # Admin dashboard should show all reports
    admin_response = client.get(
        "/api/v1/dashboards/admin?days=30",
        headers=auth_headers
    )
    assert admin_response.status_code == 200
    admin_dashboard = admin_response.json()
    assert admin_dashboard["kpis"]["total_reports"] >= 5  # All reports
    
    # User dashboard should show only user's reports
    user_response = client.get(
        "/api/v1/dashboards/user?days=30",
        headers=auth_headers
    )
    assert user_response.status_code == 200
    user_dashboard = user_response.json()
    assert user_dashboard["kpis"]["total_reports"] == 3  # Only test_user's reports


@pytest.mark.asyncio
async def test_period_summaries_workflow(
    client, db_session, auth_headers, test_template, test_user
):
    """Test period summaries generation and export workflow."""
    # Create brigade with scores over time
    brigade = Brigade(
        id=uuid4(),
        name="Summary Brigade",
        is_active=True,
    )
    db_session.add(brigade)
    await db_session.commit()
    
    # Create daily scores for past week
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
    
    # Get period summaries
    summaries_response = client.get(
        "/api/v1/reports/summaries?granularity=day"
        f"&period_start={(date.today() - timedelta(days=7)).isoformat()}"
        f"&period_end={date.today().isoformat()}",
        headers=auth_headers
    )
    assert summaries_response.status_code == 200
    summaries = summaries_response.json()
    assert isinstance(summaries, list)
    assert len(summaries) > 0
    
    # Test export summaries
    export_response = client.post(
        "/api/v1/reports/summaries/export",
        headers=auth_headers,
        json={
            "granularity": "day",
            "period_start": (date.today() - timedelta(days=7)).isoformat(),
            "period_end": date.today().isoformat(),
        }
    )
    # Export might return file or URL
    assert export_response.status_code in [200, 201, 202]


@pytest.mark.asyncio
async def test_check_logs_viewing_workflow(
    client, db_session, auth_headers, test_template, test_user
):
    """Test viewing check logs workflow."""
    # Create completed check
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
    logs_response = client.get(
        f"/api/v1/reports/checks/{check.id}/logs",
        headers=auth_headers
    )
    assert logs_response.status_code == 200
    logs = logs_response.json()
    assert "check_id" in logs
    assert logs["check_id"] == str(check.id)
    assert "entries" in logs
    assert isinstance(logs["entries"], list)


@pytest.mark.asyncio
async def test_brigade_scores_dashboard_workflow(
    client, db_session, auth_headers, test_user
):
    """Test brigade scores dashboard workflow."""
    # Create brigade
    brigade = Brigade(
        id=uuid4(),
        name="Dashboard Brigade",
        is_active=True,
    )
    db_session.add(brigade)
    test_user.brigades.append(brigade)
    await db_session.commit()
    
    # Create scores over time
    for i in range(10):
        score_date = date.today() - timedelta(days=i)
        daily_score = BrigadeDailyScore(
            id=uuid4(),
            brigade_id=brigade.id,
            score_date=score_date,
            score=Decimal("75.0") + Decimal(str(i)),
            overall_score=Decimal("80.0") + Decimal(str(i)),
            formula_version="v1",
        )
        db_session.add(daily_score)
    await db_session.commit()
    
    # Get brigade scores dashboard
    scores_response = client.get(
        f"/api/v1/dashboards/brigade-scores?days=30&brigade_id={brigade.id}",
        headers=auth_headers
    )
    assert scores_response.status_code == 200
    scores_data = scores_response.json()
    
    assert "period" in scores_data
    assert "brigades" in scores_data
    assert len(scores_data["brigades"]) > 0
    
    brigade_data = scores_data["brigades"][0]
    assert brigade_data["brigade_id"] == str(brigade.id)
    assert "scores" in brigade_data
    assert len(brigade_data["scores"]) >= 10


@pytest.mark.asyncio
async def test_report_filtering_and_sorting_workflow(
    client, db_session, auth_headers, test_template, test_user
):
    """Test report filtering and sorting workflow."""
    # Create reports with different statuses and dates
    statuses = [ReportStatus.READY, ReportStatus.READY, ReportStatus.GENERATING]
    for i, status in enumerate(statuses):
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
            status=status,
            generated_by=test_user.id,
            author_id=test_user.id,
            metadata_json={},
            created_at=datetime.utcnow() - timedelta(days=i),
        )
        db_session.add(report)
    
    await db_session.commit()
    
    # Test filtering by status
    filtered_response = client.get(
        "/api/v1/reports?status_filter=READY",
        headers=auth_headers
    )
    assert filtered_response.status_code == 200
    filtered_reports = filtered_response.json()
    assert all(r["status"] == "READY" for r in filtered_reports)
    
    # Test sorting
    sorted_response = client.get(
        "/api/v1/reports?sort_by=created_at&sort_order=desc",
        headers=auth_headers
    )
    assert sorted_response.status_code == 200
    sorted_reports = sorted_response.json()
    if len(sorted_reports) > 1:
        dates = [r["created_at"] for r in sorted_reports]
        assert dates == sorted(dates, reverse=True)


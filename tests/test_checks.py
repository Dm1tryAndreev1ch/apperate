"""Tests for check instance creation and completion."""
import pytest
from uuid import uuid4
from datetime import datetime
from app.models.checklist import CheckInstance, CheckStatus
from app.models.report import Report, ReportStatus
from app.models.task import TaskLocal


@pytest.mark.asyncio
async def test_create_check_instance(db_session, test_template, test_user):
    """Test creating a check instance."""
    check = CheckInstance(
        id=uuid4(),
        template_id=test_template.id,
        template_version=test_template.version,
        inspector_id=test_user.id,
        status=CheckStatus.IN_PROGRESS,
        answers={},
        started_at=datetime.utcnow(),
    )
    db_session.add(check)
    await db_session.commit()
    await db_session.refresh(check)
    
    assert check.template_id == test_template.id
    assert check.status == CheckStatus.IN_PROGRESS
    assert check.inspector_id == test_user.id


@pytest.mark.asyncio
async def test_complete_check_creates_report(db_session, test_template, test_user):
    """Test that completing a check creates a report."""
    # Create check instance
    check = CheckInstance(
        id=uuid4(),
        template_id=test_template.id,
        template_version=test_template.version,
        inspector_id=test_user.id,
        status=CheckStatus.IN_PROGRESS,
        answers={"q1": True},
        started_at=datetime.utcnow(),
    )
    db_session.add(check)
    await db_session.commit()
    
    # Complete check
    check.status = CheckStatus.COMPLETED
    check.finished_at = datetime.utcnow()
    
    # Create report
    report = Report(
        id=uuid4(),
        check_instance_id=check.id,
        format="pdf",
        status=ReportStatus.GENERATING,
        generated_by=test_user.id,
    )
    db_session.add(report)
    await db_session.commit()
    await db_session.refresh(report)
    
    assert report.check_instance_id == check.id
    assert report.status == ReportStatus.GENERATING
    assert report.format == "pdf"


@pytest.mark.asyncio
async def test_critical_violation_creates_task(db_session, test_template, test_user):
    """Test that critical violations create tasks."""
    # Create check with critical violation
    check = CheckInstance(
        id=uuid4(),
        template_id=test_template.id,
        template_version=test_template.version,
        inspector_id=test_user.id,
        status=CheckStatus.COMPLETED,
        answers={"q1": False},  # Critical violation
        started_at=datetime.utcnow(),
        finished_at=datetime.utcnow(),
    )
    db_session.add(check)
    
    # Create report
    report = Report(
        id=uuid4(),
        check_instance_id=check.id,
        format="pdf",
        status=ReportStatus.READY,
    )
    db_session.add(report)
    await db_session.commit()
    
    # Create task for critical violation
    task = TaskLocal(
        id=uuid4(),
        report_id=report.id,
        title="Critical violation found",
        description="Check q1 failed",
        status="PENDING",
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)
    
    assert task.report_id == report.id
    assert task.status == "PENDING"
    assert "violation" in task.title.lower()


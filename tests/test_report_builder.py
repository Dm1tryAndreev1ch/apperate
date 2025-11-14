"""Tests for report builder service."""
import pytest
from uuid import uuid4
from datetime import datetime

from app.models.checklist import CheckInstance, CheckStatus, ChecklistTemplate, TemplateStatus
from app.models.report import ReportFormatXLSX
from app.services.report_builder import report_builder


@pytest.mark.asyncio
async def test_generate_xlsx_report(db_session, test_user):
    """Test generating XLSX report."""
    # Create template
    template = ChecklistTemplate(
        id=uuid4(),
        name="Test Template",
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
    
    # Generate report
    workbook_bytes = report_builder.generate_xlsx(
        check_instance=check,
        template=template,
        author=test_user,
        analytics={},
        brigade_score=None,
    )
    
    assert workbook_bytes is not None
    assert len(workbook_bytes) > 0
    # Verify it's a valid XLSX file (starts with PK header)
    assert workbook_bytes[:2] == b'PK'


@pytest.mark.asyncio
async def test_generate_xlsx_with_analytics(db_session, test_user):
    """Test generating XLSX report with analytics data."""
    template = ChecklistTemplate(
        id=uuid4(),
        name="Test Template",
        schema={"sections": []},
        version=1,
        status=TemplateStatus.ACTIVE,
        created_by=test_user.id,
    )
    db_session.add(template)
    await db_session.commit()
    
    check = CheckInstance(
        id=uuid4(),
        template_id=template.id,
        template_version=1,
        inspector_id=test_user.id,
        status=CheckStatus.COMPLETED,
        answers={},
        started_at=datetime.utcnow(),
        finished_at=datetime.utcnow(),
    )
    db_session.add(check)
    await db_session.commit()
    
    analytics = {
        "total_questions": 10,
        "answered_questions": 8,
        "avg_score": 85.5,
    }
    
    workbook_bytes = report_builder.generate_xlsx(
        check_instance=check,
        template=template,
        author=test_user,
        analytics=analytics,
        brigade_score=None,
    )
    
    assert workbook_bytes is not None
    assert len(workbook_bytes) > 0


def test_report_builder_only_xlsx():
    """Test that report builder only supports XLSX format."""
    # This is implicit in the service design, but we can verify
    # that the service doesn't have methods for other formats
    assert hasattr(report_builder, 'generate_xlsx')
    # Should not have PDF/HTML/CSV methods
    assert not hasattr(report_builder, 'generate_pdf')
    assert not hasattr(report_builder, 'generate_html')
    assert not hasattr(report_builder, 'generate_csv')


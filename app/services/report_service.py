"""Report generation service."""
import json
import io
from typing import Dict, Any, List
from jinja2 import Template
from weasyprint import HTML
from app.models.report import ReportFormat
from app.models.checklist import CheckInstance
from app.services.storage_service import storage_service


class ReportService:
    """Service for generating reports."""

    HTML_TEMPLATE = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Check Report</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            h1 { color: #333; }
            .section { margin-bottom: 20px; }
            .question { margin-bottom: 10px; padding: 10px; background: #f5f5f5; }
            .answer { font-weight: bold; color: #0066cc; }
            .critical { background: #ffcccc; }
        </style>
    </head>
    <body>
        <h1>Check Report: {{ check.name }}</h1>
        <p><strong>Template:</strong> {{ template.name }}</p>
        <p><strong>Inspector:</strong> {{ inspector.full_name }}</p>
        <p><strong>Date:</strong> {{ check.finished_at }}</p>
        
        {% for section in sections %}
        <div class="section">
            <h2>{{ section.name }}</h2>
            {% for question in section.questions %}
            <div class="question {% if question.critical %}critical{% endif %}">
                <p><strong>{{ question.text }}</strong></p>
                <p class="answer">Answer: {{ answers.get(question.id, 'N/A') }}</p>
            </div>
            {% endfor %}
        </div>
        {% endfor %}
    </body>
    </html>
    """

    @staticmethod
    def generate_json(check_instance: CheckInstance, template_schema: Dict[str, Any]) -> str:
        """Generate JSON report."""
        report_data = {
            "check_id": str(check_instance.id),
            "template_id": str(check_instance.template_id),
            "template_version": check_instance.template_version,
            "inspector_id": str(check_instance.inspector_id) if check_instance.inspector_id else None,
            "status": check_instance.status.value,
            "started_at": check_instance.started_at.isoformat() if check_instance.started_at else None,
            "finished_at": check_instance.finished_at.isoformat() if check_instance.finished_at else None,
            "answers": check_instance.answers,
            "comments": check_instance.comments,
            "schema": template_schema,
        }
        return json.dumps(report_data, indent=2, ensure_ascii=False)

    @staticmethod
    def generate_html(check_instance: CheckInstance, template_schema: Dict[str, Any], inspector_name: str = "Unknown") -> str:
        """Generate HTML report."""
        template = Template(ReportService.HTML_TEMPLATE)
        html_content = template.render(
            check=check_instance,
            template={"name": "Template"},  # Can be enhanced
            inspector={"full_name": inspector_name},
            sections=template_schema.get("sections", []),
            answers=check_instance.answers,
        )
        return html_content

    @staticmethod
    def generate_pdf(html_content: str) -> bytes:
        """Generate PDF from HTML."""
        html = HTML(string=html_content)
        pdf_bytes = html.write_pdf()
        return pdf_bytes

    @staticmethod
    def generate_and_upload(
        check_instance: CheckInstance,
        template_schema: Dict[str, Any],
        format: ReportFormat,
        inspector_name: str = "Unknown",
    ) -> str:
        """Generate report and upload to S3, return S3 key."""
        if format == ReportFormat.JSON:
            content = ReportService.generate_json(check_instance, template_schema)
            file_obj = io.BytesIO(content.encode("utf-8"))
            content_type = "application/json"
        elif format == ReportFormat.HTML:
            content = ReportService.generate_html(check_instance, template_schema, inspector_name)
            file_obj = io.BytesIO(content.encode("utf-8"))
            content_type = "text/html"
        elif format == ReportFormat.PDF:
            html_content = ReportService.generate_html(check_instance, template_schema, inspector_name)
            pdf_bytes = ReportService.generate_pdf(html_content)
            file_obj = io.BytesIO(pdf_bytes)
            content_type = "application/pdf"
        else:
            raise ValueError(f"Unsupported format: {format}")

        # Generate S3 key
        file_extension = format.value
        key = f"reports/{check_instance.id}/{format.value}/{check_instance.id}.{file_extension}"

        # Upload to S3
        file_obj.seek(0)
        storage_service.upload_fileobj(file_obj, key, content_type=content_type)

        return key


report_service = ReportService()


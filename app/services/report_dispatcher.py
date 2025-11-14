"""Report dispatcher service orchestrating analytics -> Excel -> storage -> Bitrix."""
from __future__ import annotations

import io
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.models.checklist import CheckInstance
from app.models.report import Report, ReportFormatXLSX, ReportStatus
from app.models.reporting import ReportGenerationEvent, ReportGenerationEventType, ReportGenerationStatus
from app.models.user import User
from app.services.analytics_service import AnalyticsService, ReportAnalyticsDTO
from app.services.bitrix_alert_service import bitrix_alert_service
from app.services.report_builder import report_builder
from app.services.storage_service import storage_service


class ReportDispatcher:
    """Orchestrates report generation pipeline: analytics -> Excel -> storage -> Bitrix."""

    @staticmethod
    async def generate_and_dispatch_report(
        db: AsyncSession,
        *,
        check_instance: CheckInstance,
        author: User,
        trigger_bitrix: bool = True,
    ) -> Report:
        """Generate report, upload to storage, and optionally trigger Bitrix tickets."""
        # Load relationships
        await db.refresh(check_instance, ["template", "inspector", "brigade"])

        # Create generation event
        event = ReportGenerationEvent(
            check_instance_id=check_instance.id,
            event_type=ReportGenerationEventType.MANUAL,
            status=ReportGenerationStatus.RUNNING,
            triggered_by=author.email,
        )
        db.add(event)
        await db.flush()

        try:
            # Step 1: Compute analytics
            analytics = await AnalyticsService.compute_report_analytics(
                db,
                check_instance=check_instance,
            )

            # Step 2: Build Excel workbook
            inspector_name = check_instance.inspector.full_name if check_instance.inspector else "Unknown"
            template_name = check_instance.template.name if check_instance.template else "Template"
            workbook_bytes = report_builder.build_report_workbook(
                check_instance=check_instance,
                analytics=analytics,
                inspector_name=inspector_name,
                template_name=template_name,
            )

            # Step 3: Upload to storage
            file_key = f"reports/{check_instance.id}/{check_instance.id}.xlsx"
            content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            storage_service.upload_fileobj(
                io.BytesIO(workbook_bytes),
                file_key,
                content_type=content_type,
            )

            # Step 4: Process Bitrix alerts if enabled
            bitrix_tickets: Dict[str, Any] = {}
            if trigger_bitrix and analytics.alerts:
                base_url = settings.EXTERNAL_IP.rstrip("/")
                ticket_results = bitrix_alert_service.process_alerts(
                    analytics.alerts,
                    check_instance_id=check_instance.id,
                    base_url=base_url,
                    deduplicate=True,
                )
                bitrix_tickets = ticket_results

                # Update alert metadata with ticket IDs
                for alert in analytics.alerts:
                    if alert.metadata and "bitrix_ticket_id" in alert.metadata:
                        # Ticket was created, metadata already updated
                        pass

            # Step 5: Create report record
            report = Report(
                check_instance_id=check_instance.id,
                format=ReportFormatXLSX.XLSX,
                file_key=file_key,
                status=ReportStatus.READY,
                generated_by=author.id,
                author_id=author.id,
                metadata_json={
                    "analytics": {
                        "avg_score": float(analytics.avg_score) if analytics.avg_score else None,
                        "remark_count": analytics.remark_count,
                        "critical_violations_count": len(analytics.critical_violations),
                        "alerts_count": len(analytics.alerts),
                    },
                    "brigade_score": {
                        "score": float(analytics.brigade_score.score) if analytics.brigade_score else None,
                        "overall_score": float(analytics.brigade_score.overall_score)
                        if analytics.brigade_score and analytics.brigade_score.overall_score
                        else None,
                        "formula_version": analytics.brigade_score.formula_version if analytics.brigade_score else None,
                    }
                    if analytics.brigade_score
                    else None,
                    "bitrix": {
                        "tickets_created": len([r for r in bitrix_tickets.values() if r.get("ok")]),
                        "tickets": {
                            hash_key: {
                                "external_id": result.get("external_id"),
                                "ok": result.get("ok"),
                            }
                            for hash_key, result in bitrix_tickets.items()
                        },
                    },
                    "generated_at": datetime.utcnow().isoformat(),
                },
            )
            db.add(report)
            await db.flush()

            # Link event to report
            event.report_id = report.id
            event.status = ReportGenerationStatus.SUCCESS
            event.completed_at = datetime.utcnow()
            db.add(event)

            await db.commit()
            await db.refresh(report)

            return report

        except Exception as e:
            # Mark event as failed
            event.status = ReportGenerationStatus.FAILED
            event.error_message = str(e)
            event.completed_at = datetime.utcnow()
            db.add(event)
            await db.commit()
            raise

    @staticmethod
    async def regenerate_report(
        db: AsyncSession,
        *,
        report: Report,
        author: User,
        trigger_bitrix: bool = False,
    ) -> Report:
        """Regenerate an existing report."""
        # Load check instance
        result = await db.execute(
            select(CheckInstance)
            .where(CheckInstance.id == report.check_instance_id)
            .options(selectinload(CheckInstance.template), selectinload(CheckInstance.inspector), selectinload(CheckInstance.brigade))
        )
        check_instance = result.scalar_one_or_none()
        if not check_instance:
            raise ValueError(f"Check instance {report.check_instance_id} not found")

        # Update report status
        report.status = ReportStatus.GENERATING
        db.add(report)

        # Create retry event
        event = ReportGenerationEvent(
            report_id=report.id,
            check_instance_id=check_instance.id,
            event_type=ReportGenerationEventType.RETRY,
            status=ReportGenerationStatus.RUNNING,
            triggered_by=author.email,
        )
        db.add(event)
        await db.flush()

        try:
            # Re-run generation pipeline
            new_report = await ReportDispatcher.generate_and_dispatch_report(
                db,
                check_instance=check_instance,
                author=author,
                trigger_bitrix=trigger_bitrix,
            )

            # Update existing report
            report.file_key = new_report.file_key
            report.status = ReportStatus.READY
            report.metadata_json = new_report.metadata_json
            report.generated_by = author.id
            report.author_id = author.id

            event.status = ReportGenerationStatus.SUCCESS
            event.completed_at = datetime.utcnow()
            db.add(event)

            await db.commit()
            await db.refresh(report)

            return report

        except Exception as e:
            report.status = ReportStatus.FAILED
            event.status = ReportGenerationStatus.FAILED
            event.error_message = str(e)
            event.completed_at = datetime.utcnow()
            db.add(report)
            db.add(event)
            await db.commit()
            raise


report_dispatcher = ReportDispatcher()


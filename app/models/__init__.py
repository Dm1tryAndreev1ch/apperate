"""Model modules."""
from app.models.user import User, Role
from app.models.checklist import ChecklistTemplate, ChecklistTemplateVersion, CheckInstance
from app.models.report import Report
from app.models.task import TaskLocal
from app.models.schedule import Schedule
from app.models.brigade import Brigade, BrigadeDailyScore
from app.models.audit import AuditLog
from app.models.webhook import WebhookSubscription
from app.models.integration import BitrixCallLog
from app.models.inspection import (
    InspectionMeeting,
    MeetingStatus,
    ReferencePhoto,
    ViolationFollowUp,
    InspectionConfirmation,
)
from app.models.notification import (
    Notification,
    NotificationChannel,
    NotificationStatus,
    NotificationType,
    NotificationPreference,
)
from app.models.reporting import (
    CalculationRunStatus,
    CalculationRunType,
    DataCalculationRun,
    DataQualityIssue,
    DataQualityIssueType,
    DataQualitySeverity,
    DailyChecklistMetric,
    DepartmentHistoricalComparison,
    DepartmentMonthlySummary,
    EquipmentRegisterEntry,
    EquipmentStatus,
    EquipmentStatusSnapshot,
    PeriodSummaryGranularity,
    RemarkEntry,
    RemarkSeverity,
    ReportGenerationEvent,
    ReportGenerationStatus,
    ReportGenerationEventType,
    ReportPeriodSummary,
)

__all__ = [
    "User",
    "Role",
    "ChecklistTemplate",
    "ChecklistTemplateVersion",
    "CheckInstance",
    "Report",
    "TaskLocal",
    "Schedule",
    "Brigade",
    "BrigadeDailyScore",
    "AuditLog",
    "WebhookSubscription",
    "BitrixCallLog",
    "CalculationRunStatus",
    "CalculationRunType",
    "DataCalculationRun",
    "DataQualityIssue",
    "DataQualityIssueType",
    "DataQualitySeverity",
    "DailyChecklistMetric",
    "DepartmentHistoricalComparison",
    "DepartmentMonthlySummary",
    "EquipmentRegisterEntry",
    "EquipmentStatus",
    "EquipmentStatusSnapshot",
    "PeriodSummaryGranularity",
    "RemarkEntry",
    "RemarkSeverity",
    "ReportPeriodSummary",
    "ReportGenerationEvent",
    "ReportGenerationEventType",
    "ReportGenerationStatus",
    "InspectionMeeting",
    "MeetingStatus",
    "ReferencePhoto",
    "ViolationFollowUp",
    "InspectionConfirmation",
    "Notification",
    "NotificationChannel",
    "NotificationStatus",
    "NotificationType",
    "NotificationPreference",
]

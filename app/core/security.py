"""Security constants and permissions."""
from enum import Enum


class Permission(str, Enum):
    """Permission constants for RBAC."""

    # Checklist permissions
    CHECKLIST_CREATE = "checklist.create"
    CHECKLIST_VIEW = "checklist.view"
    CHECKLIST_UPDATE = "checklist.update"
    CHECKLIST_DELETE = "checklist.delete"
    CHECKLIST_COMPLETE = "checklist.complete"

    # Template permissions
    TEMPLATE_CREATE = "template.create"
    TEMPLATE_VIEW = "template.view"
    TEMPLATE_UPDATE = "template.update"
    TEMPLATE_DELETE = "template.delete"

    # Report permissions
    REPORT_VIEW = "report.view"
    REPORT_GENERATE = "report.generate"
    REPORT_DOWNLOAD = "report.download"
    REPORT_EXPORT = "report.export"

    # User management
    USER_VIEW = "user.view"
    USER_CREATE = "user.create"
    USER_UPDATE = "user.update"
    USER_DELETE = "user.delete"

    # Role management
    ROLE_VIEW = "role.view"
    ROLE_CREATE = "role.create"
    ROLE_UPDATE = "role.update"
    ROLE_DELETE = "role.delete"

    # Schedule management
    SCHEDULE_VIEW = "schedule.view"
    SCHEDULE_CREATE = "schedule.create"
    SCHEDULE_UPDATE = "schedule.update"
    SCHEDULE_DELETE = "schedule.delete"

    # Webhook management
    WEBHOOK_VIEW = "webhook.view"
    WEBHOOK_CREATE = "webhook.create"
    WEBHOOK_UPDATE = "webhook.update"
    WEBHOOK_DELETE = "webhook.delete"

    # Audit
    AUDIT_VIEW = "audit.view"

    # Integration
    INTEGRATION_VIEW = "integration.view"
    INTEGRATION_MANAGE = "integration.manage"

    # Brigades
    BRIGADE_VIEW = "brigade.view"
    BRIGADE_CREATE = "brigade.create"
    BRIGADE_UPDATE = "brigade.update"
    BRIGADE_DELETE = "brigade.delete"
    BRIGADE_SCORE_VIEW = "brigade.score.view"


# Role definitions with permissions
ROLE_PERMISSIONS = {
    "admin": [
        Permission.CHECKLIST_CREATE,
        Permission.CHECKLIST_VIEW,
        Permission.CHECKLIST_UPDATE,
        Permission.CHECKLIST_DELETE,
        Permission.CHECKLIST_COMPLETE,
        Permission.TEMPLATE_CREATE,
        Permission.TEMPLATE_VIEW,
        Permission.TEMPLATE_UPDATE,
        Permission.TEMPLATE_DELETE,
        Permission.REPORT_VIEW,
        Permission.REPORT_GENERATE,
        Permission.REPORT_DOWNLOAD,
        Permission.REPORT_EXPORT,
        Permission.USER_VIEW,
        Permission.USER_CREATE,
        Permission.USER_UPDATE,
        Permission.USER_DELETE,
        Permission.ROLE_VIEW,
        Permission.ROLE_CREATE,
        Permission.ROLE_UPDATE,
        Permission.ROLE_DELETE,
        Permission.SCHEDULE_VIEW,
        Permission.SCHEDULE_CREATE,
        Permission.SCHEDULE_UPDATE,
        Permission.SCHEDULE_DELETE,
        Permission.WEBHOOK_VIEW,
        Permission.WEBHOOK_CREATE,
        Permission.WEBHOOK_UPDATE,
        Permission.WEBHOOK_DELETE,
        Permission.AUDIT_VIEW,
        Permission.INTEGRATION_VIEW,
        Permission.INTEGRATION_MANAGE,
        Permission.BRIGADE_VIEW,
        Permission.BRIGADE_CREATE,
        Permission.BRIGADE_UPDATE,
        Permission.BRIGADE_DELETE,
        Permission.BRIGADE_SCORE_VIEW,
    ],
    "inspector": [
        Permission.CHECKLIST_VIEW,
        Permission.CHECKLIST_COMPLETE,
        Permission.TEMPLATE_VIEW,
        Permission.REPORT_VIEW,
        Permission.REPORT_DOWNLOAD,
        Permission.SCHEDULE_VIEW,
        Permission.BRIGADE_VIEW,
        Permission.BRIGADE_SCORE_VIEW,
    ],
    "crew_leader": [
        Permission.CHECKLIST_VIEW,
        Permission.TEMPLATE_VIEW,
        Permission.REPORT_VIEW,
        Permission.REPORT_DOWNLOAD,
        Permission.SCHEDULE_VIEW,
        Permission.BRIGADE_VIEW,
        Permission.BRIGADE_SCORE_VIEW,
    ],
    "viewer": [
        Permission.CHECKLIST_VIEW,
        Permission.TEMPLATE_VIEW,
        Permission.REPORT_VIEW,
        Permission.BRIGADE_VIEW,
    ],
}


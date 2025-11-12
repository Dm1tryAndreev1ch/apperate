"""Checklist service for versioning and validation."""
from typing import Any, Dict, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.checklist import ChecklistTemplate, ChecklistTemplateVersion, CheckInstance
from app.models.checklist import CheckStatus
from app.crud.checklist import template, check_instance


class ChecklistService:
    """Service for checklist operations."""

    @staticmethod
    async def create_version(
        db: AsyncSession,
        template_obj: ChecklistTemplate,
        new_schema: Dict[str, Any],
        created_by: str,
    ) -> ChecklistTemplateVersion:
        """Create a new version of a template."""
        # Calculate diff (simplified - can be enhanced)
        old_schema = template_obj.schema
        diff = {"old": old_schema, "new": new_schema}

        # Create version record
        version = ChecklistTemplateVersion(
            template_id=template_obj.id,
            version=template_obj.version + 1,
            schema=new_schema,
            diff=diff,
            created_by=created_by,
        )
        db.add(version)

        # Update template
        template_obj.version = template_obj.version + 1
        template_obj.schema = new_schema
        db.add(template_obj)

        await db.commit()
        await db.refresh(version)
        return version

    @staticmethod
    def validate_answers(template_schema: Dict[str, Any], answers: Dict[str, Any]) -> tuple[bool, List[str]]:
        """Validate answers against template schema."""
        errors = []

        # Extract questions from schema
        questions = {}
        for section in template_schema.get("sections", []):
            for question in section.get("questions", []):
                questions[question.get("id")] = question

        # Validate each answer
        for question_id, answer in answers.items():
            if question_id not in questions:
                errors.append(f"Unknown question ID: {question_id}")
                continue

            question = questions[question_id]
            required = question.get("required", False)
            question_type = question.get("type")

            # Check required
            if required and (answer is None or answer == ""):
                errors.append(f"Required question {question_id} is missing")

            # Type validation (simplified)
            if answer is not None and answer != "":
                if question_type == "number" and not isinstance(answer, (int, float)):
                    errors.append(f"Question {question_id} must be a number")
                elif question_type == "boolean" and not isinstance(answer, bool):
                    errors.append(f"Question {question_id} must be a boolean")

        return len(errors) == 0, errors

    @staticmethod
    def find_critical_violations(template_schema: Dict[str, Any], answers: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Find critical violations in answers."""
        violations = []

        # Extract questions from schema
        questions = {}
        for section in template_schema.get("sections", []):
            for question in section.get("questions", []):
                questions[question.get("id")] = question

        # Check for critical violations
        for question_id, answer in answers.items():
            if question_id not in questions:
                continue

            question = questions[question_id]
            is_critical = question.get("meta", {}).get("critical", False)
            requires_ok = question.get("meta", {}).get("requires_ok", False)

            if is_critical and requires_ok:
                # Check if answer indicates a problem
                if question.get("type") == "boolean" and answer is False:
                    violations.append({
                        "question_id": question_id,
                        "question_text": question.get("text", ""),
                        "answer": answer,
                    })
                elif question.get("type") == "single_choice" and answer == "not_ok":
                    violations.append({
                        "question_id": question_id,
                        "question_text": question.get("text", ""),
                        "answer": answer,
                    })

        return violations


checklist_service = ChecklistService()


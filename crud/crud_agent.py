from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

import models


def create_agent_task(
    db: Session,
    *,
    task_type: str,
    target_type: str | None = None,
    target_id: int | None = None,
    input_data: dict[str, Any] | None = None,
) -> models.AgentTask:
    task = models.AgentTask(
        task_type=task_type,
        status="pending",
        target_type=target_type,
        target_id=target_id,
        input_data=json.dumps(input_data or {}, ensure_ascii=False),
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def get_agent_task(db: Session, task_id: int) -> models.AgentTask | None:
    return db.query(models.AgentTask).filter(models.AgentTask.id == task_id).first()


def list_agent_tasks(db: Session, limit: int = 20) -> list[models.AgentTask]:
    return (
        db.query(models.AgentTask)
        .order_by(models.AgentTask.id.desc())
        .limit(limit)
        .all()
    )


def update_agent_task_status(
    db: Session,
    task: models.AgentTask,
    *,
    status: str,
    result_data: dict[str, Any] | None = None,
    error_message: str | None = None,
) -> models.AgentTask:
    task.status = status
    task.updated_at = datetime.now(timezone.utc)

    if result_data is not None:
        task.result_data = json.dumps(result_data, ensure_ascii=False)

    if error_message is not None:
        task.error_message = error_message

    db.commit()
    db.refresh(task)
    return task


def mark_agent_task_failed(
    db: Session,
    task: models.AgentTask,
    *,
    error_message: str,
) -> models.AgentTask:
    task.status = "failed"
    task.retry_count = int(task.retry_count or 0) + 1
    task.error_message = error_message
    task.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(task)
    return task


def create_agent_draft(
    db: Session,
    *,
    draft_type: str,
    content: str,
    title: str | None = None,
    target_type: str | None = None,
    target_id: int | None = None,
) -> models.AgentDraft:
    draft = models.AgentDraft(
        draft_type=draft_type,
        status="pending_review",
        title=title,
        content=content,
        target_type=target_type,
        target_id=target_id,
        created_by="agent",
    )
    db.add(draft)
    db.commit()
    db.refresh(draft)
    return draft


def get_agent_draft(db: Session, draft_id: int) -> models.AgentDraft | None:
    return db.query(models.AgentDraft).filter(models.AgentDraft.id == draft_id).first()


def list_agent_drafts(db: Session, limit: int = 20) -> list[models.AgentDraft]:
    return (
        db.query(models.AgentDraft)
        .order_by(models.AgentDraft.id.desc())
        .limit(limit)
        .all()
    )


def mark_agent_draft_approved(
    db: Session,
    draft: models.AgentDraft,
    *,
    reviewer: str,
) -> models.AgentDraft:
    draft.status = "approved"
    draft.reviewed_by = reviewer
    draft.reviewed_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(draft)
    return draft


def mark_agent_draft_rejected(
    db: Session,
    draft: models.AgentDraft,
    *,
    reviewer: str,
) -> models.AgentDraft:
    draft.status = "rejected"
    draft.reviewed_by = reviewer
    draft.reviewed_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(draft)
    return draft
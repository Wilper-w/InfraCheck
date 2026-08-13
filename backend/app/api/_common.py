"""Shared API helpers: pagination, 404 lookup, audited writes."""
from __future__ import annotations

from typing import Any, TypeVar

from fastapi import HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Query as OrmQuery

from app.db import Session
from app.models import AuditLog
from app.schemas import Paginated

T = TypeVar("T")


def page_params(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
):
    return {"page": page, "page_size": page_size}


def write_audit(
    db: Session, actor: str, action: str, target_ref: str | None = None, detail: str = ""
) -> None:
    db.add(AuditLog(actor=actor, action=action, target_ref=target_ref, detail=detail))
    db.commit()


def get_or_404(db: Session, model: type[T], pk: Any, label: str, **scope: Any) -> T:
    """Fetch a row by primary key, or raise 404.

    `scope` asserts parent ownership for nested routes, e.g.
    `get_or_404(db, PhysicalNode, node_id, "node", environment_id=env_id)`
    404s when the node exists but belongs to another environment.
    """
    obj = db.get(model, pk)
    if obj is None or any(getattr(obj, k) != v for k, v in scope.items()):
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f"{label} not found")
    return obj


def paginate(q: OrmQuery, page: dict, out_model: type[BaseModel]) -> Paginated:
    """Apply CONTRACT §2 pagination to a query and serialize rows with `out_model`."""
    total = q.count()
    items = q.offset((page["page"] - 1) * page["page_size"]).limit(page["page_size"]).all()
    return Paginated(items=[out_model.model_validate(i) for i in items], total=total, **page)


def save_and_audit(db: Session, obj: T, actor: str, action: str, detail: str) -> T:
    """Persist a new row and record the audit entry.

    `target_ref` is derived from the action verb, so "node.create" audits as "node:<id>".
    """
    db.add(obj)
    db.commit()
    db.refresh(obj)
    write_audit(db, actor, action, f"{action.split('.')[0]}:{obj.id}", detail)
    return obj


def delete_and_audit(db: Session, obj: Any, actor: str, action: str, detail: str) -> None:
    """Delete a row and record the audit entry (id captured before the delete)."""
    target_ref = f"{action.split('.')[0]}:{obj.id}"
    db.delete(obj)
    db.commit()
    write_audit(db, actor, action, target_ref, detail)

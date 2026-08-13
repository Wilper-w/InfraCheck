"""Check item routes (CONTRACT §4 /check-items)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api._common import (
    delete_and_audit,
    get_or_404,
    page_params,
    paginate,
    save_and_audit,
    write_audit,
)
from app.auth import current_account
from app.db import get_db
from app.models import CheckItem
from app.schemas import (
    CheckItemCreate,
    CheckItemOut,
    CheckItemUpdate,
    Paginated,
)

router = APIRouter(prefix="/check-items", tags=["check-items"])


@router.get("", response_model=Paginated)
def list_check_items(
    enabled: bool | None = Query(None),
    target_type: str | None = Query(None),
    page: dict = Depends(page_params),
    db: Session = Depends(get_db),
    _: str = Depends(current_account),
):
    q = db.query(CheckItem)
    if enabled is not None:
        q = q.filter(CheckItem.enabled.is_(enabled))
    if target_type:
        q = q.filter(CheckItem.target_type == target_type)
    return paginate(q.order_by(CheckItem.id), page, CheckItemOut)


@router.post("", response_model=CheckItemOut, status_code=201)
def create_check_item(
    body: CheckItemCreate,
    db: Session = Depends(get_db),
    account: str = Depends(current_account),
):
    item = CheckItem(
        name=body.name,
        target_type=body.target_type,
        os_flavor=body.os_flavor,
        description=body.description,
        enabled=True,
        config=body.config,
    )
    save_and_audit(db, item, account, "check_item.create", f"created {body.name}")
    return CheckItemOut.model_validate(item)


@router.put("/{item_id}", response_model=CheckItemOut)
def update_check_item(
    item_id: int,
    body: CheckItemUpdate,
    db: Session = Depends(get_db),
    account: str = Depends(current_account),
):
    item = get_or_404(db, CheckItem, item_id, "check item")
    data = body.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(item, k, v)
    db.commit()
    db.refresh(item)
    write_audit(db, account, "check_item.update", f"check_item:{item_id}", f"updated fields: {list(data)}")
    return CheckItemOut.model_validate(item)


@router.delete("/{item_id}", status_code=204)
def delete_check_item(
    item_id: int,
    db: Session = Depends(get_db),
    account: str = Depends(current_account),
):
    item = get_or_404(db, CheckItem, item_id, "check item")
    delete_and_audit(db, item, account, "check_item.delete", f"deleted {item.name}")


@router.post("/{item_id}/toggle", response_model=CheckItemOut)
def toggle_check_item(
    item_id: int,
    db: Session = Depends(get_db),
    account: str = Depends(current_account),
):
    item = get_or_404(db, CheckItem, item_id, "check item")
    item.enabled = not item.enabled
    db.commit()
    db.refresh(item)
    write_audit(
        db, account, "check_item.toggle", f"check_item:{item_id}", f"enabled={item.enabled}"
    )
    return CheckItemOut.model_validate(item)

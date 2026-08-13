"""Auth + pagination schemas (CONTRACT §2, §4 /auth)."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel


# ---- auth ----
class LoginRequest(BaseModel):
    account: str


class LoginResponse(BaseModel):
    token: str
    account: str


class MeResponse(BaseModel):
    account: str


# ---- pagination ----
class Page(BaseModel):
    page: int = 1
    page_size: int = 20


class Paginated(BaseModel):
    items: list[Any]
    total: int
    page: int
    page_size: int

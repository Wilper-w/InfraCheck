"""Authentication: JWT issuance + verification (CONTRACT §4 /auth, §6)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app import config

bearer_scheme = HTTPBearer(auto_error=True)


def create_token(account: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": account,
        "account": account,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=config.JWT_EXPIRE_HOURS)).timestamp()),
    }
    return jwt.encode(payload, config.JWT_SECRET, algorithm=config.JWT_ALGORITHM)


def decode_token(token: str) -> str:
    try:
        payload = jwt.decode(token, config.JWT_SECRET, algorithms=[config.JWT_ALGORITHM])
    except jwt.PyJWTError as exc:  # expired, invalid signature, etc.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"invalid or expired token: {exc}",
        )
    account = payload.get("account") or payload.get("sub")
    if not account:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="token missing account")
    return account


def current_account(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> str:
    return decode_token(credentials.credentials)

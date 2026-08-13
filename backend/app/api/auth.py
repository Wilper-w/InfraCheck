"""Auth routes (CONTRACT §4 /auth)."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app import config
from app.auth import create_token, current_account
from app.schemas import LoginRequest, LoginResponse, MeResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest) -> LoginResponse:
    account = body.account.strip()
    if not account:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="account is required")
    # AUTH_MODE=wecom would exchange a Wecom code for the account here;
    # mock mode passes the account through directly (default, runs out-of-box).
    if config.AUTH_MODE == "wecom":
        # Switch point for real Wecom SSO: verify code → resolve account.
        # Left as pass-through so import never breaks without credentials.
        pass
    token = create_token(account)
    return LoginResponse(token=token, account=account)


@router.get("/me", response_model=MeResponse)
def me(account: str = Depends(current_account)) -> MeResponse:
    return MeResponse(account=account)

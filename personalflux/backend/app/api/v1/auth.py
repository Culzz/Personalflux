from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.rate_limit import auth_limiter
from app.core.security import (create_access_token, hash_password, hash_token,
                               new_refresh_token, verify_password)
from app.db.session import get_db
from app.models import RefreshToken, User
from app.schemas.auth import LoginIn, RegisterIn, TokenOut, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])

COOKIE = "refresh_token"


def _cookie_path() -> str:
    return f"{settings.api_v1_prefix}/auth"


def _issue_session(db: Session, user: User, response: Response) -> TokenOut:
    """New access token (in the response body) + rotating refresh token (HttpOnly cookie)."""
    raw, token_hash = new_refresh_token()
    db.add(RefreshToken(
        user_id=user.id, token_hash=token_hash,
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days),
    ))
    db.commit()
    response.set_cookie(
        COOKIE, raw, max_age=settings.refresh_token_expire_days * 86400,
        httponly=True, secure=settings.is_production, samesite="lax", path=_cookie_path(),
    )
    return TokenOut(
        access_token=create_access_token(user.id, user.role),
        expires_in=settings.access_token_expire_minutes * 60,
        user=UserOut.model_validate(user),
    )


@router.post("/register", response_model=TokenOut, status_code=201,
             dependencies=[Depends(auth_limiter)])
def register(payload: RegisterIn, response: Response, db: Session = Depends(get_db)):
    email = payload.email.strip().lower()
    if db.scalar(select(User.id).where(User.email == email)):
        raise HTTPException(status_code=409, detail="An account with this email already exists.")
    user = User(email=email, password_hash=hash_password(payload.password),
                role="customer", tracking_consent=payload.tracking_consent)
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="An account with this email already exists.")
    db.refresh(user)
    return _issue_session(db, user, response)


@router.post("/login", response_model=TokenOut, dependencies=[Depends(auth_limiter)])
def login(payload: LoginIn, response: Response, db: Session = Depends(get_db)):
    email = payload.email.strip().lower()
    user = db.scalar(select(User).where(User.email == email))
    ok = verify_password(user.password_hash if user else None, payload.password)
    if user is None or not ok or not user.is_active:
        raise HTTPException(status_code=401, detail="Incorrect email or password.")
    return _issue_session(db, user, response)


@router.post("/refresh", response_model=TokenOut, dependencies=[Depends(auth_limiter)])
def refresh(request: Request, response: Response, db: Session = Depends(get_db)):
    raw = request.cookies.get(COOKIE)
    if not raw:
        raise HTTPException(status_code=401, detail="No session.")
    row = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == hash_token(raw)))
    if row is None:
        raise HTTPException(status_code=401, detail="Invalid session.")
    now = datetime.now(timezone.utc)
    if row.revoked_at is not None:
        # A rotated token was used again: assume theft and end every session of this user.
        db.execute(update(RefreshToken)
                   .where(RefreshToken.user_id == row.user_id, RefreshToken.revoked_at.is_(None))
                   .values(revoked_at=now))
        db.commit()
        raise HTTPException(status_code=401, detail="Invalid session.")
    if row.expires_at <= now:
        raise HTTPException(status_code=401, detail="Session expired.")
    user = db.get(User, row.user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="Invalid session.")
    row.revoked_at = now            # rotate: each refresh token works once
    return _issue_session(db, user, response)


@router.post("/logout", status_code=204)
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    raw = request.cookies.get(COOKIE)
    if raw:
        row = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == hash_token(raw)))
        if row is not None and row.revoked_at is None:
            row.revoked_at = datetime.now(timezone.utc)
            db.commit()
    response.delete_cookie(COOKIE, path=_cookie_path())


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user

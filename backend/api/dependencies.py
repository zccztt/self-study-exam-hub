# -*- coding: utf-8 -*-
"""Authentication and resource ownership dependencies."""

from fastapi import Depends, HTTPException, status
from typing import Optional

from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.user import User
from backend.utils import decode_access_token, password_token_marker


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")
oauth2_optional_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    payload = decode_access_token(token)
    if payload and payload.get("type", "access") != "access":
        payload = None
    subject = payload.get("sub") if payload else None
    try:
        user_id = int(subject)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="登录状态无效，请重新登录。",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在或已停用，请重新登录。",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if payload.get("pwd") != password_token_marker(user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="登录凭证已失效，请重新登录。",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def require_self(requested_user_id: int, current_user: User) -> None:
    if requested_user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权访问其他用户的数据。")


def get_optional_current_user(
    token: Optional[str] = Depends(oauth2_optional_scheme),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """Return the authenticated user if the token is valid, otherwise None.

    This dependency NEVER raises HTTPException so that endpoints can
    gracefully degrade to guest access when the token is missing, expired,
    or otherwise invalid.
    """
    if not token:
        return None
    payload = decode_access_token(token)
    if not payload:
        return None
    if payload.get("type", "access") != "access":
        return None
    try:
        user_id = int(payload.get("sub"))
    except (TypeError, ValueError):
        return None
    user = db.query(User).filter(User.id == user_id, User.is_active.is_(True)).first()
    if not user:
        return None
    if payload.get("pwd") != password_token_marker(user.hashed_password):
        return None
    return user

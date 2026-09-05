# -*- coding: utf-8 -*-
"""Authentication API routes."""

import logging
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import or_
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.user import User
from backend.api.dependencies import get_current_user
from backend.config import settings
from backend.services.email_service import send_password_reset_email
from backend.utils.rate_limit import client_identifier, rate_limiter
from backend.utils import (
    create_access_token,
    create_password_reset_token,
    create_refresh_token,
    decode_access_token,
    hash_password,
    password_token_marker,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger(__name__)


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50, pattern=r"^[A-Za-z0-9_]+$")
    email: str = Field(min_length=5, max_length=120)
    password: str = Field(min_length=8, max_length=128)
    full_name: Optional[str] = Field(default=None, max_length=100)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if "@" not in normalized or normalized.startswith("@") or normalized.endswith("@"):
            raise ValueError("请输入有效的邮箱地址。")
        return normalized


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=1, max_length=128)


class ProfileUpdateRequest(BaseModel):
    email: Optional[str] = Field(default=None, min_length=5, max_length=120)
    full_name: Optional[str] = Field(default=None, max_length=100)
    current_job: Optional[str] = Field(default=None, max_length=100)
    education_background: Optional[str] = Field(default=None, max_length=100)
    education_major: Optional[str] = Field(default=None, max_length=100)
    skills: Optional[str] = Field(default=None, max_length=500)
    study_hours_per_day: Optional[int] = Field(default=None, ge=0, le=24)
    exam_experience: Optional[str] = Field(default=None, max_length=50)
    learning_preference: Optional[str] = Field(default=None, max_length=50)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        normalized = value.strip().lower()
        if "@" not in normalized or normalized.startswith("@") or normalized.endswith("@"):
            raise ValueError("请输入有效的邮箱地址。")
        return normalized


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(min_length=20)


class ForgotPasswordRequest(BaseModel):
    email: str = Field(min_length=5, max_length=120)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if "@" not in normalized or normalized.startswith("@") or normalized.endswith("@"):
            raise ValueError("请输入有效的邮箱地址。")
        return normalized


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=20)
    new_password: str = Field(min_length=8, max_length=128)


def serialize_user(user: User) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
        "is_active": user.is_active,
        "is_superuser": user.is_superuser,
        "current_job": user.current_job,
        "education_background": user.education_background,
        "education_major": user.education_major,
        "skills": user.skills,
        "study_hours_per_day": user.study_hours_per_day,
        "exam_experience": user.exam_experience,
        "learning_preference": user.learning_preference,
    }


def create_user_tokens(user: User) -> dict:
    payload = {"sub": str(user.id), "username": user.username, "pwd": password_token_marker(user.hashed_password)}
    return {
        "access_token": create_access_token(payload),
        "refresh_token": create_refresh_token(payload),
        "token_type": "bearer",
    }


def _send_password_reset_email_safely(recipient: str, token: str) -> None:
    try:
        send_password_reset_email(recipient, token)
    except Exception:
        logger.exception("Failed to send password reset email.")


@router.post("/register")
async def register(request: RegisterRequest, db: Session = Depends(get_db)):
    existing = (
        db.query(User)
        .filter(or_(User.username == request.username, User.email == request.email))
        .first()
    )
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="用户名或邮箱已被注册。")

    user = User(
        username=request.username,
        email=request.email,
        hashed_password=hash_password(request.password),
        full_name=request.full_name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return {"code": 0, "data": {**create_user_tokens(user), "user": serialize_user(user)}}


@router.post("/login")
async def login(http_request: Request, request: LoginRequest, db: Session = Depends(get_db)):
    rate_limiter.check(
        "login",
        client_identifier(http_request),
        settings.LOGIN_RATE_LIMIT_PER_MINUTE,
    )
    identifier = request.username.strip()
    if "@" in identifier:
        identifier = identifier.lower()
    user = (
        db.query(User)
        .filter(or_(User.username == identifier, User.email == identifier))
        .first()
    )
    if not user or not verify_password(request.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误。")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="该用户已被停用。")

    return {"code": 0, "data": {**create_user_tokens(user), "user": serialize_user(user)}}


@router.post("/forgot-password")
async def forgot_password(
    http_request: Request,
    request: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    rate_limiter.check(
        "password_reset_request",
        client_identifier(http_request),
        settings.PASSWORD_RESET_RATE_LIMIT_PER_MINUTE,
    )
    user = db.query(User).filter(User.email == request.email, User.is_active.is_(True)).first()
    delivery_available = bool(settings.SMTP_HOST)
    if user and delivery_available:
        token = create_password_reset_token(
            {
                "sub": str(user.id),
                "pwd": password_token_marker(user.hashed_password),
            }
        )
        background_tasks.add_task(_send_password_reset_email_safely, user.email, token)
    return {
        "code": 0,
        "data": {
            "accepted": True,
            "delivery_available": delivery_available,
        },
    }


@router.post("/reset-password")
async def reset_password(
    http_request: Request,
    request: ResetPasswordRequest,
    db: Session = Depends(get_db),
):
    rate_limiter.check(
        "password_reset_confirm",
        client_identifier(http_request),
        settings.PASSWORD_RESET_RATE_LIMIT_PER_MINUTE,
    )
    payload = decode_access_token(request.token)
    try:
        user_id = int(payload.get("sub")) if payload and payload.get("type") == "password_reset" else 0
    except (TypeError, ValueError):
        user_id = 0
    user = db.query(User).filter(User.id == user_id, User.is_active.is_(True)).first()
    if not user or not payload or payload.get("pwd") != password_token_marker(user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="密码重置链接无效或已过期。")
    if verify_password(request.new_password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="新密码不能与当前密码相同。")
    user.hashed_password = hash_password(request.new_password)
    db.commit()
    return {"code": 0, "data": {"success": True}}


@router.post("/refresh")
async def refresh_token(request: RefreshTokenRequest, db: Session = Depends(get_db)):
    payload = decode_access_token(request.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="刷新凭证无效或已过期。")
    try:
        user_id = int(payload.get("sub"))
    except (TypeError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="刷新凭证无效或已过期。")
    user = db.query(User).filter(User.id == user_id, User.is_active.is_(True)).first()
    if not user or payload.get("pwd") != password_token_marker(user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="刷新凭证已失效，请重新登录。")
    return {"code": 0, "data": create_user_tokens(user)}


@router.get("/me")
async def me(current_user: User = Depends(get_current_user)):
    return {"code": 0, "data": serialize_user(current_user)}


@router.patch("/profile")
async def update_profile(
    request: ProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if request.email and request.email != current_user.email:
        existing = db.query(User).filter(User.email == request.email, User.id != current_user.id).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="该邮箱已被其他用户使用。")
        current_user.email = request.email
    if request.full_name is not None:
        current_user.full_name = request.full_name.strip() or None
    if request.current_job is not None:
        current_user.current_job = request.current_job.strip() or None
    if request.education_background is not None:
        current_user.education_background = request.education_background.strip() or None
    if request.education_major is not None:
        current_user.education_major = request.education_major.strip() or None
    if request.skills is not None:
        current_user.skills = request.skills.strip() or None
    if request.study_hours_per_day is not None:
        current_user.study_hours_per_day = request.study_hours_per_day
    if request.exam_experience is not None:
        current_user.exam_experience = request.exam_experience.strip() or None
    if request.learning_preference is not None:
        current_user.learning_preference = request.learning_preference.strip() or None
    db.commit()
    db.refresh(current_user)
    return {"code": 0, "data": serialize_user(current_user)}


@router.post("/password")
async def change_password(
    request: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(request.current_password, current_user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="当前密码错误。")
    if verify_password(request.new_password, current_user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="新密码不能与当前密码相同。")
    current_user.hashed_password = hash_password(request.new_password)
    db.commit()
    return {"code": 0, "data": {"success": True}}

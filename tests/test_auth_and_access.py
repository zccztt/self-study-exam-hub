# -*- coding: utf-8 -*-
"""API tests for authentication and per-user data isolation."""

from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.database import get_db
from backend.main import app
from backend.api import auth as auth_api
from backend.config import settings
from backend.models import Base
from backend.models.question import Question
from backend.models.subject import Subject
from backend.services.online_question_provider import TEMP_ONLINE_SOURCE_PREFIX


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSession = sessionmaker(bind=engine)
    Base.metadata.create_all(engine)

    with TestingSession() as db:
        db.add(Subject(id=1, code="03709", name="马克思主义基本原理概论"))
        db.add(Subject(id=2, code="99999", name="临时题课程"))
        db.add(Question(id=1, subject_id=1, content="测试题", question_type="single_choice", answer="A"))
        db.add(Question(id=2, subject_id=2, content="临时题", question_type="single_choice", answer="A", source=f"{TEMP_ONLINE_SOURCE_PREFIX}audit"))
        db.commit()

    def override_get_db():
        with TestingSession() as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def _register(client: TestClient, username: str) -> dict:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "username": username,
            "email": f"{username}@example.com",
            "password": "password123",
        },
    )
    assert response.status_code == 200
    return response.json()["data"]


def test_public_catalog_remains_available_without_login(client: TestClient) -> None:
    response = client.get("/api/v1/subjects")
    assert response.status_code == 200
    assert response.json()["data"][0]["code"] == "03709"
    assert response.json()["data"][0]["question_count"] == 1
    assert response.json()["data"][0]["has_content"] is True
    temporary_subject = next(item for item in response.json()["data"] if item["id"] == 2)
    assert temporary_subject["question_count"] == 0
    assert temporary_subject["has_content"] is False

    overview = client.get("/api/v1/subjects/overview")
    assert overview.status_code == 200
    assert overview.json()["data"]["question_count"] == 1
    assert overview.json()["data"]["subjects_with_questions"] == 1

    readiness = client.get("/api/v1/health/ready")
    assert readiness.status_code == 200
    assert readiness.json() == {"status": "ready", "database": "ok"}


def test_personal_routes_require_login_and_enforce_owner(client: TestClient) -> None:
    first = _register(client, "first_user")
    second = _register(client, "second_user")

    anonymous = client.get(f"/api/v1/exam/history/{first['user']['id']}")
    assert anonymous.status_code == 401

    headers = {"Authorization": f"Bearer {first['access_token']}"}
    own = client.get(f"/api/v1/exam/history/{first['user']['id']}", headers=headers)
    assert own.status_code == 200
    assert own.json()["data"]["items"] == []

    other = client.get(f"/api/v1/exam/history/{second['user']['id']}", headers=headers)
    assert other.status_code == 403
    assert other.json()["detail"] == "无权访问其他用户的数据。"


def test_registration_validates_user_input(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={"username": "x", "email": "invalid", "password": "short"},
    )
    assert response.status_code == 422


def test_user_can_update_profile_and_change_password(client: TestClient) -> None:
    registered = _register(client, "profile_user")
    headers = {"Authorization": f"Bearer {registered['access_token']}"}

    refreshed = client.post("/api/v1/auth/refresh", json={"refresh_token": registered["refresh_token"]})
    assert refreshed.status_code == 200
    assert refreshed.json()["data"]["access_token"] != registered["access_token"]
    refresh_as_access = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {registered['refresh_token']}"},
    )
    assert refresh_as_access.status_code == 401

    profile = client.patch(
        "/api/v1/auth/profile",
        headers=headers,
        json={"email": "new-profile@example.com", "full_name": "学习用户"},
    )
    assert profile.status_code == 200
    assert profile.json()["data"]["email"] == "new-profile@example.com"
    assert profile.json()["data"]["full_name"] == "学习用户"

    wrong_password = client.post(
        "/api/v1/auth/password",
        headers=headers,
        json={"current_password": "incorrect", "new_password": "newpassword123"},
    )
    assert wrong_password.status_code == 400

    changed = client.post(
        "/api/v1/auth/password",
        headers=headers,
        json={"current_password": "password123", "new_password": "newpassword123"},
    )
    assert changed.status_code == 200

    revoked = client.get("/api/v1/auth/me", headers=headers)
    assert revoked.status_code == 401
    revoked_refresh = client.post("/api/v1/auth/refresh", json={"refresh_token": registered["refresh_token"]})
    assert revoked_refresh.status_code == 401

    old_login = client.post("/api/v1/auth/login", json={"username": "profile_user", "password": "password123"})
    new_login = client.post("/api/v1/auth/login", json={"username": "profile_user", "password": "newpassword123"})
    assert old_login.status_code == 401
    assert new_login.status_code == 200


def test_email_login_is_case_insensitive(client: TestClient) -> None:
    _register(client, "email_login")
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "EMAIL_LOGIN@EXAMPLE.COM", "password": "password123"},
    )
    assert response.status_code == 200
    assert response.json()["data"]["user"]["username"] == "email_login"


def test_password_reset_is_private_single_use_and_revokes_old_tokens(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registered = _register(client, "reset_user")
    delivered = []

    monkeypatch.setattr(settings, "SMTP_HOST", "smtp.example.com")
    monkeypatch.setattr(
        auth_api,
        "send_password_reset_email",
        lambda recipient, token: delivered.append((recipient, token)),
    )

    known = client.post("/api/v1/auth/forgot-password", json={"email": "RESET_USER@EXAMPLE.COM"})
    unknown = client.post("/api/v1/auth/forgot-password", json={"email": "missing@example.com"})
    assert known.status_code == 200
    assert unknown.status_code == 200
    assert known.json()["data"] == unknown.json()["data"] == {
        "accepted": True,
        "delivery_available": True,
    }
    assert len(delivered) == 1
    assert delivered[0][0] == "reset_user@example.com"

    token = delivered[0][1]
    reset = client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "new_password": "replacement123"},
    )
    reused = client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "new_password": "another-password123"},
    )
    assert reset.status_code == 200
    assert reused.status_code == 400

    old_access = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {registered['access_token']}"},
    )
    old_login = client.post(
        "/api/v1/auth/login",
        json={"username": "reset_user", "password": "password123"},
    )
    new_login = client.post(
        "/api/v1/auth/login",
        json={"username": "reset_user", "password": "replacement123"},
    )
    assert old_access.status_code == 401
    assert old_login.status_code == 401
    assert new_login.status_code == 200


def test_anonymous_user_cannot_trigger_online_video_import(client: TestClient) -> None:
    response = client.get("/api/v1/videos", params={"keyword": "不存在的视频", "online_search": True})
    assert response.status_code == 401


def test_question_search_is_local_by_default_and_online_search_requires_login(client: TestClient) -> None:
    local = client.get("/api/v1/questions/search")
    assert local.status_code == 200
    assert local.json()["data"]["total"] == 1

    online = client.get("/api/v1/questions/search", params={"online_search": True})
    assert online.status_code == 401


def test_plan_generation_rejects_duplicate_and_unknown_subjects(client: TestClient) -> None:
    registered = _register(client, "planner_validation")
    headers = {"Authorization": f"Bearer {registered['access_token']}"}
    exam_date = (datetime.now() + timedelta(days=30)).isoformat()
    base = {
        "user_id": registered["user"]["id"],
        "exam_date": exam_date,
        "daily_hours": 2,
    }

    duplicate = client.post("/api/v1/planner/generate", headers=headers, json={**base, "subjects": [1, 1]})
    unknown = client.post("/api/v1/planner/generate", headers=headers, json={**base, "subjects": [999]})
    assert duplicate.status_code == 422
    assert unknown.status_code == 422

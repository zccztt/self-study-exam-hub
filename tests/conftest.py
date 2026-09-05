# -*- coding: utf-8 -*-
"""Shared test isolation helpers."""

import pytest

from backend.utils.rate_limit import rate_limiter


@pytest.fixture(autouse=True)
def reset_testclient_rate_limits():
    for scope in (
        "login",
        "password_reset_request",
        "password_reset_confirm",
        "online_question_search",
        "online_video_search",
        "online_exam_generation",
        "ai_analysis",
    ):
        rate_limiter.reset(scope, "testclient")
    yield

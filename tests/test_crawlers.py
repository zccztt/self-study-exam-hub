# -*- coding: utf-8 -*-
"""Tests for the crawler module."""

import pytest

from scripts.crawlers import (
    clean_course_code,
    clean_credits,
    normalize_course_type,
    normalize_level,
    content_hash,
    CrawlResult,
)
from scripts.crawlers.data_importer import DataImporter, PROVINCE_NAMES


class TestCleanCourseCode:
    def test_normal_code(self):
        assert clean_course_code("03708") == "03708"

    def test_strips_whitespace(self):
        assert clean_course_code("  03708  ") == "03708"

    def test_zero_pads_short_code(self):
        assert clean_course_code("708") == "00708"

    def test_longer_prefix(self):
        assert clean_course_code("15043/03708") == "15043"

    def test_empty(self):
        assert clean_course_code("") == ""


class TestCleanCredits:
    def test_normal(self):
        assert clean_credits("4") == 4.0

    def test_float(self):
        assert clean_credits("2.5") == 2.5

    def test_whitespace(self):
        assert clean_credits("  6  ") == 6.0

    def test_empty(self):
        assert clean_credits("") is None

    def test_invalid(self):
        assert clean_credits("abc") is None

    def test_nbsp(self):
        assert clean_credits("\xa0") is None


class TestNormalizeCourseType:
    def test_required_variants(self):
        assert normalize_course_type("必考") == "required"
        assert normalize_course_type("必修") == "required"
        assert normalize_course_type("统考") == "required"
        assert normalize_course_type("公共基础课") == "required"
        assert normalize_course_type("专业核心课") == "required"

    def test_elective_variants(self):
        assert normalize_course_type("选考") == "elective"
        assert normalize_course_type("选修") == "elective"
        assert normalize_course_type("推荐选考课") == "elective"

    def test_additional(self):
        assert normalize_course_type("加考") == "additional"
        assert normalize_course_type("加考课") == "additional"

    def test_fallback(self):
        assert normalize_course_type("未知") == "required"  # default


class TestNormalizeLevel:
    def test_undergraduate(self):
        assert normalize_level("本科") == "bk"
        assert normalize_level("独立本科") == "bk"
        assert normalize_level("专升本") == "bk"

    def test_diploma(self):
        assert normalize_level("专科") == "zk"
        assert normalize_level("基础科") == "zk"

    def test_default(self):
        assert normalize_level("未知") == "bk"


class TestContentHash:
    def test_consistent(self):
        h1 = content_hash("hello")
        h2 = content_hash("hello")
        assert h1 == h2
        assert len(h1) == 12

    def test_different_input(self):
        assert content_hash("a") != content_hash("b")


class TestCrawlResult:
    def test_basic(self):
        result = CrawlResult("13", "zikaosw")
        assert result.province_code == "13"
        assert result.source == "zikaosw"
        assert not result.success

    def test_finish(self):
        result = CrawlResult("13", "zikaosw")
        result.majors_found = 10
        result.courses_found = 50
        result.finish(success=True)
        assert result.success
        assert result.finished_at is not None

    def test_summary(self):
        result = CrawlResult("13", "zikaosw")
        result.schools_found = 5
        result.majors_found = 10
        result.courses_found = 80
        result.finish(success=True)
        summary = result.summary()
        assert "OK" in summary
        assert "province=13" in summary
        assert "schools=5" in summary


class TestProvinceNames:
    def test_hebei(self):
        assert PROVINCE_NAMES["13"] == "河北省"

    def test_coverage(self):
        # Should have all major provinces
        assert len(PROVINCE_NAMES) >= 31
        assert "44" in PROVINCE_NAMES  # Guangdong
        assert "33" in PROVINCE_NAMES  # Zhejiang

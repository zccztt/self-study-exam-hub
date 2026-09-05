# -*- coding: utf-8 -*-
"""Tests for the enrollment module (models, service, API)."""

import pytest
from datetime import date

from backend.database import SessionLocal
from backend.models.enrollment import (
    Major, MajorSubject, Province, School, UserEnrollment, UserSubjectStatus,
)
from backend.models.subject import Subject
from backend.models.user import User
from backend.services.enrollment_service import EnrollmentService
from backend.utils import hash_password


@pytest.fixture
def db():
    session = SessionLocal()
    yield session
    session.rollback()
    session.close()


@pytest.fixture
def test_user(db):
    user = db.query(User).filter(User.username == "test_enrollment_user").first()
    if not user:
        user = User(
            username="test_enrollment_user",
            email="test_enrollment@test.com",
            hashed_password=hash_password("testpass123"),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


@pytest.fixture
def test_province(db):
    province = db.query(Province).filter(Province.code == "99").first()
    if not province:
        province = Province(code="99", name="测试省")
        db.add(province)
        db.commit()
        db.refresh(province)
    return province


@pytest.fixture
def test_school(db, test_province):
    school = db.query(School).filter(
        School.name == "测试大学", School.province_id == test_province.id
    ).first()
    if not school:
        school = School(name="测试大学", province_id=test_province.id, code="99999")
        db.add(school)
        db.commit()
        db.refresh(school)
    return school


@pytest.fixture
def test_major(db, test_province, test_school):
    major = db.query(Major).filter(
        Major.code == "999999", Major.province_id == test_province.id
    ).first()
    if not major:
        major = Major(
            code="999999", name="测试专业", level="bk",
            province_id=test_province.id, school_id=test_school.id,
            total_credits=70,
        )
        db.add(major)
        db.commit()
        db.refresh(major)

        # Add 3 test subjects
        for i in range(1, 4):
            subj = db.query(Subject).filter(Subject.code == f"9900{i}").first()
            if not subj:
                subj = Subject(code=f"9900{i}", name=f"测试课程{i}", category="public")
                db.add(subj)
                db.flush()
            db.add(MajorSubject(
                major_id=major.id, subject_id=subj.id,
                course_type="required", credits=4.0, sort_order=i,
            ))
        db.commit()
    return major


class TestEnrollmentService:
    def test_list_provinces(self, db):
        svc = EnrollmentService(db)
        provinces = svc.list_provinces()
        assert isinstance(provinces, list)
        assert len(provinces) > 0
        assert "code" in provinces[0]
        assert "name" in provinces[0]

    def test_create_enrollment(self, db, test_user, test_major):
        svc = EnrollmentService(db)
        result = svc.create_enrollment(
            user_id=test_user.id,
            major_id=test_major.id,
            target_date=date(2027, 6, 1),
        )
        assert result["major_id"] == test_major.id
        assert result["is_active"] is True

    def test_create_enrollment_duplicate(self, db, test_user, test_major):
        svc = EnrollmentService(db)
        # Ensure enrollment exists (may already exist from previous test)
        existing = db.query(UserEnrollment).filter(
            UserEnrollment.user_id == test_user.id,
            UserEnrollment.major_id == test_major.id,
            UserEnrollment.is_active.is_(True),
        ).first()
        if not existing:
            svc.create_enrollment(user_id=test_user.id, major_id=test_major.id)
        # Try again - should raise
        with pytest.raises(ValueError, match="已经报考"):
            svc.create_enrollment(user_id=test_user.id, major_id=test_major.id)

    def test_list_enrollments(self, db, test_user, test_major):
        svc = EnrollmentService(db)
        # Ensure at least one exists
        try:
            svc.create_enrollment(user_id=test_user.id, major_id=test_major.id)
        except ValueError:
            pass
        enrollments = svc.list_enrollments(test_user.id)
        assert len(enrollments) >= 1
        assert "progress" in enrollments[0]

    def test_get_enrollment_subjects(self, db, test_user, test_major):
        svc = EnrollmentService(db)
        try:
            svc.create_enrollment(user_id=test_user.id, major_id=test_major.id)
        except ValueError:
            pass
        enrollment = db.query(UserEnrollment).filter(
            UserEnrollment.user_id == test_user.id,
            UserEnrollment.major_id == test_major.id,
        ).first()

        data = svc.get_enrollment_subjects(test_user.id, enrollment.id)
        assert "subjects" in data
        assert "progress" in data
        assert data["progress"]["total"] == 3

    def test_update_subject_status(self, db, test_user, test_major):
        svc = EnrollmentService(db)
        try:
            svc.create_enrollment(user_id=test_user.id, major_id=test_major.id)
        except ValueError:
            pass
        enrollment = db.query(UserEnrollment).filter(
            UserEnrollment.user_id == test_user.id,
            UserEnrollment.major_id == test_major.id,
        ).first()

        subject = db.query(Subject).filter(Subject.code == "99001").first()
        result = svc.update_subject_status(
            user_id=test_user.id,
            enrollment_id=enrollment.id,
            subject_id=subject.id,
            status="passed",
            score=78.0,
            exam_date=date(2026, 4, 12),
        )
        assert result["status"] == "passed"
        assert result["score"] == 78.0
        assert result["attempt_count"] == 1

    def test_update_subject_status_invalid(self, db, test_user, test_major):
        svc = EnrollmentService(db)
        try:
            svc.create_enrollment(user_id=test_user.id, major_id=test_major.id)
        except ValueError:
            pass
        enrollment = db.query(UserEnrollment).filter(
            UserEnrollment.user_id == test_user.id,
            UserEnrollment.major_id == test_major.id,
        ).first()
        subject = db.query(Subject).filter(Subject.code == "99001").first()

        with pytest.raises(ValueError, match="状态值无效"):
            svc.update_subject_status(
                user_id=test_user.id, enrollment_id=enrollment.id,
                subject_id=subject.id, status="invalid",
            )

    def test_update_subject_status_score_range(self, db, test_user, test_major):
        svc = EnrollmentService(db)
        try:
            svc.create_enrollment(user_id=test_user.id, major_id=test_major.id)
        except ValueError:
            pass
        enrollment = db.query(UserEnrollment).filter(
            UserEnrollment.user_id == test_user.id,
            UserEnrollment.major_id == test_major.id,
        ).first()
        subject = db.query(Subject).filter(Subject.code == "99002").first()

        with pytest.raises(ValueError, match="分数范围"):
            svc.update_subject_status(
                user_id=test_user.id, enrollment_id=enrollment.id,
                subject_id=subject.id, status="passed", score=150.0,
            )

    def test_get_remaining_subjects(self, db, test_user, test_major):
        svc = EnrollmentService(db)
        try:
            svc.create_enrollment(user_id=test_user.id, major_id=test_major.id)
        except ValueError:
            pass
        enrollment = db.query(UserEnrollment).filter(
            UserEnrollment.user_id == test_user.id,
            UserEnrollment.major_id == test_major.id,
        ).first()

        remaining = svc.get_remaining_subjects(test_user.id, enrollment.id)
        assert isinstance(remaining, list)
        # Should have at least some not-passed subjects
        assert len(remaining) >= 1

    def test_delete_enrollment(self, db, test_user, test_major):
        svc = EnrollmentService(db)
        try:
            svc.create_enrollment(user_id=test_user.id, major_id=test_major.id)
        except ValueError:
            pass
        enrollment = db.query(UserEnrollment).filter(
            UserEnrollment.user_id == test_user.id,
            UserEnrollment.major_id == test_major.id,
        ).first()

        svc.delete_enrollment(test_user.id, enrollment.id)
        # Should be soft-deleted
        refreshed = db.query(UserEnrollment).filter(UserEnrollment.id == enrollment.id).first()
        assert refreshed.is_active is False

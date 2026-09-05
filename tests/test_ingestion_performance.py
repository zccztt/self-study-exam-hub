# -*- coding: utf-8 -*-
"""Regression tests for bounded and batched question/document ingestion."""

import csv
import io
from types import SimpleNamespace

from fastapi import UploadFile
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from backend.api import admin as admin_api
from backend.api import upload as upload_api
from backend.models import Base
from backend.models.knowledge import UserDocument
from backend.models.question import Question
from backend.models.subject import Subject
from backend.services.exam_engine import ExamEngine


def _session():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    return engine, Session(engine)


def test_question_csv_import_uses_bounded_executemany_batches() -> None:
    engine, db = _session()
    db.add(Subject(id=1, code="TEST", name="Test subject"))
    db.commit()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "subject_id",
            "content",
            "question_type",
            "options",
            "answer",
            "explanation",
            "year",
            "month",
            "chapter_id",
            "difficulty",
            "score",
        ]
    )
    for index in range(1_200):
        writer.writerow([1, f"Question {index}", "short_answer", "", "answer", "", "", "", "", "medium", 2])

    insert_batches = 0

    @event.listens_for(engine, "before_cursor_execute")
    def count_question_inserts(conn, cursor, statement, parameters, context, executemany):
        nonlocal insert_batches
        normalized = statement.lstrip().upper().replace('"', "")
        if normalized.startswith("INSERT INTO QUESTIONS"):
            insert_batches += 1

    upload = UploadFile(filename="questions.csv", file=io.BytesIO(output.getvalue().encode("utf-8")))
    result = admin_api.import_questions(upload, db, SimpleNamespace(is_superuser=True))

    assert result["data"]["imported"] == 1_200
    assert result["data"]["errors"] == []
    assert db.query(Question).count() == 1_200
    assert insert_batches == 3

    db.close()
    engine.dispose()


def test_document_upload_streams_and_bounds_extracted_text(monkeypatch, tmp_path) -> None:
    engine, db = _session()
    monkeypatch.setattr(upload_api, "UPLOAD_DIR", tmp_path)

    class TrackingBytesIO(io.BytesIO):
        requested_sizes = []

        def read(self, size=-1):
            self.requested_sizes.append(size)
            return super().read(size)

    payload = (b"a" * 50_000) + (b"tail" * 10_000)
    source = TrackingBytesIO(payload)
    upload = UploadFile(filename="notes.txt", file=source)
    result = upload_api.upload_file(upload, None, db, SimpleNamespace(id=7))

    assert result["size"] == len(payload)
    assert result["extracted_length"] == upload_api.MAX_EXTRACTED_TEXT_LENGTH
    assert max(TrackingBytesIO.requested_sizes) <= upload_api.UPLOAD_CHUNK_SIZE
    assert -1 not in TrackingBytesIO.requested_sizes
    saved_path = next(tmp_path.glob("7_*"))
    assert saved_path.read_bytes() == payload
    assert db.query(UserDocument).count() == 1

    db.close()
    engine.dispose()


def test_extracted_questions_are_deduplicated_with_one_lookup() -> None:
    engine, db = _session()
    subject = Subject(id=1, code="TEST", name="Test subject")
    db.add(subject)
    db.commit()

    selects = 0

    @event.listens_for(engine, "before_cursor_execute")
    def count_question_selects(conn, cursor, statement, parameters, context, executemany):
        nonlocal selects
        normalized = statement.lstrip().upper()
        if normalized.startswith("SELECT") and "FROM QUESTIONS" in normalized:
            selects += 1

    existing = Question(
        subject_id=1,
        content="Existing extracted question",
        question_type="short_answer",
        answer="answer",
        source="在线临时题源：页面抽取",
        frequency=0,
    )
    db.add(existing)
    db.commit()

    service = ExamEngine(db)
    result = service._save_extracted_questions(
        subject,
        [
            {"content": "Existing extracted question", "source_url": "https://example.com/a"},
            {"content": "A new extracted question", "source_url": "https://example.com/b"},
        ],
        True,
        {},
    )

    assert len(result) == 2
    assert result[0].id == existing.id
    assert result[1].id is not None
    assert existing.source.startswith("线上题源")
    assert selects == 1
    assert db.query(Question).count() == 2

    db.close()
    engine.dispose()

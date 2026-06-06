# -*- coding: utf-8 -*-
"""Video API routes."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.services.video_service import VideoService

router = APIRouter(prefix="/videos", tags=["videos"])


class AddVideoFavoriteRequest(BaseModel):
    user_id: int = 1
    video_id: int
    note: Optional[str] = None


def _split_ints(value: Optional[str]):
    if not value:
        return None
    return [int(item) for item in value.split(",") if item.strip()]


@router.get("")
async def search_videos(
    keyword: Optional[str] = None,
    subject_id: Optional[int] = None,
    chapter_ids: Optional[str] = None,
    source: Optional[str] = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    service = VideoService(db)
    return {
        "code": 0,
        "data": service.search_videos(
            keyword=keyword,
            subject_id=subject_id,
            chapter_ids=_split_ints(chapter_ids),
            source=source,
            page=page,
            page_size=page_size,
        ),
    }


@router.post("/favorites")
async def add_to_favorites(request: AddVideoFavoriteRequest, db: Session = Depends(get_db)):
    service = VideoService(db)
    success = service.add_to_favorites(request.user_id, request.video_id, request.note)
    if not success:
        raise HTTPException(status_code=404, detail="Video not found.")
    return {"code": 0, "data": {"success": True}}


@router.get("/favorites/{user_id}")
async def get_favorites(
    user_id: int,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    service = VideoService(db)
    return {"code": 0, "data": service.get_favorites(user_id, page, page_size)}


@router.delete("/favorites/{user_id}/{video_id}")
async def remove_from_favorites(user_id: int, video_id: int, db: Session = Depends(get_db)):
    service = VideoService(db)
    success = service.remove_from_favorites(user_id, video_id)
    if not success:
        raise HTTPException(status_code=404, detail="Favorite not found.")
    return {"code": 0, "data": {"success": True}}


@router.get("/{video_id}")
async def get_video_detail(video_id: int, db: Session = Depends(get_db)):
    service = VideoService(db)
    result = service.get_video_detail(video_id)
    if not result:
        raise HTTPException(status_code=404, detail="Video not found.")
    return {"code": 0, "data": result}

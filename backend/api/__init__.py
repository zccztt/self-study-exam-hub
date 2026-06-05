# -*- coding: utf-8 -*-
"""
API路由模块
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "ok", "message": "Service is running"}


# TODO: 导入其他路由模块
# from .exam import router as exam_router
# from .question import router as question_router
# from .video import router as video_router
# from .analysis import router as analysis_router
# from .planner import router as planner_router

# router.include_router(exam_router, prefix="/exam", tags=["考试"])
# router.include_router(question_router, prefix="/question", tags=["题库"])
# router.include_router(video_router, prefix="/video", tags=["视频"])
# router.include_router(analysis_router, prefix="/analysis", tags=["分析"])
# router.include_router(planner_router, prefix="/planner", tags=["规划"])

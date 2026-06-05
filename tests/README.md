# 自考真题系统测试

本目录包含后端和前端的测试代码。

## 后端测试

```bash
# 运行所有测试
pytest

# 运行指定模块测试
pytest tests/test_exam_engine.py

# 生成覆盖率报告
pytest --cov=backend --cov-report=html
```

## 前端测试

```bash
cd frontend
npm test
```

## 测试结构

```
tests/
├── backend/
│   ├── test_exam_engine.py      # 考试引擎测试
│   ├── test_question_service.py # 题库服务测试
│   ├── test_video_service.py    # 视频服务测试
│   ├── test_analysis_service.py # 分析服务测试
│   └── test_planner_service.py  # 规划服务测试
└── frontend/
    ├── components/              # 组件测试
    └── integration/             # 集成测试
```

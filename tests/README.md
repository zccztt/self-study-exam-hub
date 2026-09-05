# 自考真题系统测试

本目录包含后端和前端的测试代码。

## 后端测试

```bash
# 运行所有测试
pytest

# 运行认证和用户数据隔离测试
pytest tests/test_auth_and_access.py

# 生成覆盖率报告
pytest --cov=backend --cov-report=html
```

## 前端检查

```bash
cd frontend
npm run lint
npx tsc --noEmit
```

## 测试结构

```
tests/
├── test_algorithms.py               # 组卷、趋势、复习与试卷解析算法
├── test_auth_and_access.py          # 注册登录、密码重置、就绪探针和用户数据隔离
├── test_search_and_score_trends.py  # 题库搜索、成绩趋势和错题导出
└── test_video_service.py            # 在线视频源归一化和保存
```

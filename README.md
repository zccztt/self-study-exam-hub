# 自考真题模拟与学习系统

> 一站式自学考试备考平台：智能题库 × 真题模拟 × AI 规划 × 高频考点 × 报考管理 × 闪卡记忆

系统围绕 **数据采集 → 题库检索 → 模拟考试 → 错题沉淀 → 考点分析 → AI 智能规划** 形成完整备考闭环。平台通过题库频次、错题记录和掌握度数据识别高频考点与个人薄弱环节，结合艾宾浩斯遗忘曲线和 AI 建议生成每日任务，帮助自考生更高效地安排复习节奏。

---

## 演示地址

[自考真题模拟演示](https://replace-indicator-order-separately.trycloudflare.com/)

## 演示视频

[![点击播放视频](封面图链接)](https://github.com/user-attachments/assets/ceef0ecb-0b2e-4e90-b234-8133fc330551)

---

## 🚀 快速开始

### 环境要求

- Python 3.9+
- Node.js 18+（推荐 Node.js 20）
- PostgreSQL 13+、Redis 6+、Elasticsearch 8+（可选；默认 SQLite 可直接运行）

### 安装部署

在线题源搜索使用 Tavily SDK，可通过后端配置自建地址。设置 `TAVILY_API_URL` 为 SDK 的 `base_url`（不包含 `/search` 路径）、`TAVILY_API_KEY` 为服务端密钥；两者必须同时配置才会启用。未配置时使用 Bing RSS 和 360 搜索回退。

```bash
# 1. 克隆仓库
git clone https://github.com/zccztt/self-study-exam-hub.git
cd self-study-exam-hub

# 2. 安装后端依赖
pip install -r requirements.txt

# 3. 配置环境变量（可选；不配置时使用项目根目录的 SQLite）
cp .env.example .env  # Windows PowerShell 使用 Copy-Item .env.example .env
# 如需零依赖本地运行，将 DATABASE_URL 改为 sqlite:///./exam_hub.db

# 4. 建表并导入课程、题库、视频和演示账号
python -m backend.init_db

# 5. 启动后端服务
uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload

# 6. 安装前端依赖（另开终端）
cd frontend
npm ci

# 7. 启动前端开发服务器
npm run dev
```

访问 `http://localhost:3000` 开始使用。

也可以运行 `docker compose up --build` 启动 PostgreSQL、Redis、Elasticsearch、MinIO、后端和前端。Docker 启动前必须在 `.env` 中将 `SECRET_KEY` 替换为至少 32 位的随机值，可运行 `python -c "import secrets; print(secrets.token_urlsafe(48))"` 生成。后端容器会自动完成首次建表、迁移和演示数据初始化。

### 数据库迁移与备份

Alembic 基线可直接在空数据库创建完整表结构：

```bash
alembic upgrade head
python -m backend.init_db  # 可选：导入课程目录和演示数据
```

生产环境升级前应先停止写入并创建备份：

```bash
python scripts/backup_db.py --output-dir backups
python scripts/restore_db.py backups/exam_hub_YYYYMMDD_HHMMSS.db --confirm
```

PostgreSQL 备份与恢复需要系统中可用的 `pg_dump` 和 `pg_restore`。恢复操作会替换当前数据，执行前必须停止后端服务。

### 安全与限流

- 登录、密码重置、AI 分析和线上资源搜索默认启用每分钟限流，可通过 `.env` 中的 `LOGIN_RATE_LIMIT_PER_MINUTE`、`PASSWORD_RESET_RATE_LIMIT_PER_MINUTE`、`EXTERNAL_SEARCH_RATE_LIMIT_PER_MINUTE` 和 `AI_RATE_LIMIT_PER_MINUTE` 调整。
- 找回密码需要配置 `SMTP_HOST`、`SMTP_USERNAME`、`SMTP_PASSWORD` 和 `SMTP_FROM_EMAIL`。重置链接默认 15 分钟失效，成功重置后旧访问令牌、刷新令牌和旧重置链接会同时失效。
- 服务存活检查为 `/api/v1/health`，包含数据库、Elasticsearch、MinIO 状态的就绪探针为 `/api/v1/health/ready`。
- AI 提供商 API 密钥使用 Fernet 对称加密存储在数据库中，不以明文存储。

---

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          前端展示层 (Frontend)                          │
│  React 18 + TypeScript + Tailwind CSS + Ant Design + ECharts + PWA     │
│                                                                         │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌──────────┐  │
│  │模拟考试│ │题库搜索│ │视频中心│ │考点分析│ │学习规划│ │报考管理  │  │
│  └───┬────┘ └───┬────┘ └───┬────┘ └───┬────┘ └───┬────┘ └────┬─────┘  │
│      │          │          │          │          │           │         │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐              │
│  │闪卡记忆│ │真题归档│ │考试日历│ │管理后台│ │个人中心│              │
│  └───┬────┘ └───┬────┘ └───┬────┘ └───┬────┘ └───┬────┘              │
└──────┼──────────┼──────────┼──────────┼──────────┼────────────────────┘
       │          │          │          │          │
  ─────▼──────────▼──────────▼──────────▼──────────▼────────────────────
       │                  Vite API Proxy (/api → backend)               │
  ─────┼────────────────────────────────────────────────────────────────
       │
┌──────▼────────────────────────────────────────────────────────────────┐
│                         后端服务层 (Backend)                          │
│                     Python 3.9+ / FastAPI / SQLAlchemy                │
│                                                                       │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────────┐ │
│  │  考试引擎   │ │  题库服务   │ │  视频服务   │ │  考点分析服务   │ │
│  │ • 智能组卷  │ │ • ES 全文检 │ │ • 分类索引  │ │ • 知识树       │ │
│  │ • 计时控制  │ │   索 + SQL  │ │ • 收藏管理  │ │ • 词云/热力图  │ │
│  │ • 自动评分  │ │   回退      │ │             │ │ • 趋势/预测    │ │
│  │ • AI 阅卷   │ │ • 多维筛选  │ │             │ │ • AI 热点分析  │ │
│  │ • 错题管理  │ │ • 收藏管理  │ │             │ │ • 网络图谱     │ │
│  └──────┬──────┘ └──────┬──────┘ └──────┬──────┘ └───────┬─────────┘ │
│         │               │               │                │           │
│  ┌──────▼───────────────▼───────────────▼────────────────▼─────────┐ │
│  │  学习规划引擎          │ 报考管理服务  │ AI 提供商池             │ │
│  │  • 艾宾浩斯复习排期   │ • 省/校/专业  │ • 加权轮询 + 故障切换   │ │
│  │  • 薄弱点识别         │ • 科目状态    │ • 角色路由 (阅卷/规划)  │ │
│  │  • AI 个性化建议      │ • 进度追踪    │ • 密钥加密存储          │ │
│  │  • 每日任务生成       │ • 课程推荐    │ • 健康检查 + 自动恢复   │ │
│  └────────────────────────────────────────────────────────────────┘ │
└───────────────────────────────┬────────────────────────────────────┘
                                │
┌───────────────────────────────▼────────────────────────────────────┐
│                          数据存储层 (Data)                          │
│                                                                     │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────┐  ┌──────────┐ │
│  │  PostgreSQL  │  │ Elasticsearch│  │    Redis     │  │  MinIO   │ │
│  │  (或 SQLite) │  │  (可选)      │  │  (可选)      │  │ (可选)   │ │
│  │ • 全部业务   │  │ • 题目全文   │  │ • 会话缓存  │  │ • 上传   │ │
│  │   数据       │  │   索引       │  │ • 限流计数  │  │   文件   │ │
│  │ • 用户/报考  │  │ • 考点词云   │  │ • 考试计时  │  │ • OCR    │ │
│  │ • AI 配置    │  │              │  │             │  │   文档   │ │
│  └─────────────┘  └──────────────┘  └─────────────┘  └──────────┘ │
│                                                                     │
│  注：ES、Redis、MinIO 均为可选；缺失时系统自动降级到 SQL 查询       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## ✨ 核心功能

### 📝 模块一：真题模拟考试系统

还原真实考试场景，支持计时、评分、AI 阅卷。

```
选择科目 ──→ 选择模式 ──→ 开始考试 ──→ 提交试卷 ──→ 结果分析
               │                                    │
          ┌────┴────┐                          ┌────┴────┐
          │• 真题卷  │                          │• 自动评分│
          │  (按年)  │                          │• AI 阅卷 │
          │• 随机组卷│                          │  (主观题)│
          │• 章节练习│                          │• 答案解析│
          │• 错题重做│                          │• 错题归档│
          └─────────┘                          │• 成绩趋势│
                                               └─────────┘
```

| 功能 | 说明 |
|------|------|
| 年份真题 | 按已导入年份筛选并生成试卷 |
| 智能组卷 | 按章节 / 题型 / 难度随机抽题组卷 |
| 考试计时 | 倒计时 + 超时自动提交 |
| 答题卡 | 可视化答题进度，支持标记 / 跳转 |
| 自动评分 | 客观题自动评分 |
| AI 阅卷 | 主观题（简答、论述、案例分析）由 AI 评分并给出评语，支持用户反馈纠正 |
| 错题本 | 自动归档错题，支持标签分类、重做、导出 |
| 薄弱点分析 | 按科目 / 章节 / 题型维度定位薄弱知识点 |
| 成绩趋势 | 多次模考成绩折线图，追踪进步轨迹 |

---

### 🔍 模块二：题库筛选搜索引擎

快速定位目标题目，支持多维度筛选和全文搜索。

- **Elasticsearch 全文搜索**：支持分词和语义匹配，ES 不可用时自动降级到 SQL LIKE
- **多维度组合筛选**：科目、年份、题型、难度、章节
- **高频考点标记**：快速定位重点题目
- **题目收藏**：收藏管理，统一在「我的收藏」页面查看
- **在线题源**：本地题库无结果时自动从 Tavily / SearXNG / Bing RSS / 360 搜索在线题源

---

### 🎬 模块三：视频资源聚合中心

关联题目与视频讲解，快速定位学习资源。

- 聚合主流平台视频资源（B站、网易公开课、腾讯课堂等）
- 视频与科目、章节、知识点、题目智能关联
- 视频收藏管理
- 按科目 / 来源 / 关键词筛选

---

### 📊 模块四：高频考点大纲与可视化分析

数据化呈现考试重点，指导复习方向。8 种可视化图表一览掌握考试全貌。

| 图表 | 说明 |
|------|------|
| 🌳 知识树 | 交互式考试大纲树形图，标注每个知识点的出题频次 |
| 📊 高频柱状图 | Top N 高频考点排行 |
| 🔵 知识网络图 | 力导向图展示知识点关联关系 |
| 📈 趋势折线图 | 考点年度出题趋势 |
| ☁️ 词云 | 考点关键词词云 |
| 🗺️ 章节热力图 | 颜色深浅表示章节出题密度 |
| 🥧 题型分布饼图 | 各题型占比 |
| 🔮 出题预测 | 基于历史趋势预测下次考试重点 |
| 🤖 AI 热点分析 | AI 驱动的考试热点深度分析 |
| 📋 答题模板 | 按题型提供标准答题模板和得分要点 |
| 📑 冲刺报告 | 考前冲刺专项报告，聚焦高频 + 薄弱点 |

---

### 🗓️ 模块五：智能学习规划 + AI 建议

基于个人薄弱点和考试时间，生成个性化学习计划，并可获取 AI 一对一备考建议。

```
输入                          处理                          输出
────                          ────                          ────
┌──────────────┐        ┌───────────────────┐        ┌──────────────┐
│• 考试日期    │        │    规划算法引擎    │        │  每日任务    │
│• 报考科目    │───────▶│                   │───────▶│  清单        │
│• 每日可用时长│        │ • 薄弱点权重计算  │        ├──────────────┤
│• 个人情况描述│        │ • 时间分配优化    │        │  AI 个性化   │
│  (可选)      │        │ • 艾宾浩斯复习    │        │  备考建议    │
│• 模考成绩    │        │   排期            │        │ • 总体评估   │
│• 错题分布    │        │ • AI 个性化建议   │        │ • 学习策略   │
└──────────────┘        │   生成            │        │ • 科目建议   │
                        └───────────────────┘        │ • 每日安排   │
                                                     │ • 风险警告   │
                                                     │ • 激励寄语   │
                                                     └──────────────┘
```

**核心能力**：

1. **薄弱点识别** — 基于模考成绩和错题分布计算知识点掌握度
2. **时间分配优化** — 根据考试倒计时和每日可用时长动态分配学习任务
3. **艾宾浩斯遗忘曲线** — 基于遗忘曲线安排复习节点，到期自动提醒
4. **进度自适应调整** — 根据实际完成情况动态调整后续计划
5. **AI 个性化建议** — 用户可输入个人情况（基础、在职/全职、目标），AI 生成六维度备考建议：总体评估、学习策略、各科建议、每日安排、风险警告、激励寄语
6. **多计划管理** — 支持创建多个学习计划，激活 / 归档切换

---

### 🎓 模块六：报考管理与课程推荐

管理自考报名信息，追踪各科目状态，获取智能选课建议。

| 功能 | 说明 |
|------|------|
| 省份 / 院校 / 专业 | 多省份自考院校及专业目录，数据来源官方采集 |
| 报考登记 | 选择省份 → 院校 → 专业，创建报考记录 |
| 科目状态 | 每科标记：未考 / 已过 / 未过，自动计算学分进度 |
| 进度总览 | 已修学分 / 总学分、已过科目数 / 总科目数、预计毕业时间 |
| 课程替代 | 查看新旧课程替代映射关系 |
| 智能推荐 | 综合难度估计和学分/学时比推荐下一批报考科目 |

---

### 🃏 模块七：闪卡记忆 (SM-2 间隔重复)

基于 SM-2 算法的间隔重复系统，从知识点和题目自动生成闪卡。

- **自动生成**：从章节知识点、高频题目自动提取生成闪卡
- **手动创建**：支持自定义闪卡内容
- **SM-2 调度**：根据每次回顾的评分（难度）自动计算下次复习时间
- **到期提醒**：每日显示到期待复习闪卡数量
- **暂停 / 删除**：暂时挂起或永久移除不需要的闪卡
- **统计面板**：总卡数、待复习、平均难度因子

---

### 📅 模块八：考试日历

自考报名和考试时间一目了然。

- 各省自考时间表（从官方渠道采集 + 静态数据兜底）
- 距离下次考试倒计时
- 考前学习计划建议

---

### 📄 模块九：真题归档浏览

历年真题按科目 / 年份 / 月份 / 省份 / 类型检索，一键进入模考。

---

### 📚 模块十：个人知识库

上传个人学习资料（PDF / TXT / MD / DOCX），系统自动提取文本，可关联到题目或真题来源。支持 OCR 识别图片中的文字。

---

### ⚙️ 管理后台

管理员（`is_superuser`）可通过后台管理：

| 功能 | 说明 |
|------|------|
| 用户管理 | 用户列表、启用 / 禁用 |
| 科目管理 | 科目 CRUD、章节 / 知识点维护 |
| 题库管理 | 题目 CRUD、批量导入 |
| 视频管理 | 视频 CRUD |
| AI 提供商 | 添加 / 编辑 / 测试 AI API（密钥加密存储），加权轮询池管理 |
| 搜索提供商 | 配置 Tavily、SearXNG 或自定义搜索 API |
| 采集管理 | 查看采集日志、触发采集任务、数据校验 |
| 仪表盘 | 系统概览统计 |

用户也可自行配置 AI / 搜索提供商（BYOK — Bring Your Own Key），个人配置优先于系统默认。

---

## 🛠️ 技术栈

### 后端

| 类别 | 技术 |
|------|------|
| 框架 | FastAPI + Uvicorn |
| ORM | SQLAlchemy 2.x + Alembic 迁移 |
| 数据校验 | Pydantic v2 |
| 数据库 | PostgreSQL 13（生产）/ SQLite（开发） |
| 缓存 | Redis 6 |
| 全文搜索 | Elasticsearch 8.11 |
| 对象存储 | MinIO |
| AI 能力 | OpenAI SDK（兼容 API），支持多提供商池化管理 |
| 搜索引擎 | Tavily SDK / SearXNG / Bing RSS / 360 搜索 |
| OCR | PyPDF / Pillow / pytesseract |
| 爬虫 | httpx / aiohttp / BeautifulSoup4 / Playwright |
| 安全 | JWT (PyJWT) + Fernet 密钥加密 + bcrypt 密码哈希 |

### 前端

| 类别 | 技术 |
|------|------|
| 框架 | React 18 |
| 语言 | TypeScript |
| 构建 | Vite 5 |
| UI 库 | Ant Design 5 + @ant-design/icons |
| 样式 | Tailwind CSS 3 |
| 状态管理 | Zustand |
| 数据可视化 | ECharts 5 (echarts-for-react) |
| HTTP | Axios（JWT 自动刷新拦截器）|
| 路由 | React Router 6 |
| 日期 | dayjs |
| PWA | vite-plugin-pwa（离线缓存 + 安装提示）|

### 部署

| 类别 | 技术 |
|------|------|
| 容器化 | Docker + Docker Compose（6 个服务） |
| 开发代理 | Vite API Proxy |
| 数据库迁移 | Alembic（12+ 迁移版本） |
| 备份恢复 | 内置脚本（SQLite + PostgreSQL）|

---

## 📂 项目结构

```
self-study-exam-hub/
├── backend/                    # 后端服务
│   ├── api/                    # API 路由 (21 个模块)
│   │   ├── __init__.py         # 路由注册 + 健康检查
│   │   ├── auth.py             # 认证：注册/登录/密码重置/JWT刷新
│   │   ├── exam.py             # 考试：组卷/作答/评分/AI阅卷/错题
│   │   ├── question.py         # 题库：搜索/高频/收藏
│   │   ├── subject.py          # 科目：目录/概览/学习资源
│   │   ├── video.py            # 视频：列表/筛选/收藏
│   │   ├── analysis.py         # 分析：知识树/词云/热力图/趋势/预测
│   │   ├── planner.py          # 规划：生成计划/AI建议/每日任务
│   │   ├── enrollment.py       # 报考：省校专业/登记/进度/推荐
│   │   ├── flashcard.py        # 闪卡：SM-2调度/生成/复习
│   │   ├── past_paper.py       # 真题：归档浏览/按条件筛选
│   │   ├── exam_calendar.py    # 日历：考试时间/倒计时
│   │   ├── feedback.py         # 反馈：AI阅卷纠正
│   │   ├── upload.py           # 上传：个人知识库
│   │   ├── resource.py         # 资源：上传/链接/OCR/关联
│   │   ├── admin.py            # 管理：仪表盘/CRUD/批量导入
│   │   ├── admin_crawl.py      # 采集：日志/触发/校验
│   │   ├── ai_provider.py      # AI提供商：CRUD/测试/池管理
│   │   ├── search_provider.py  # 搜索提供商：CRUD/测试
│   │   ├── user_provider.py    # 用户BYOK：个人提供商配置
│   │   └── dependencies.py     # 依赖注入：认证/权限
│   ├── services/               # 业务逻辑 (23 个服务)
│   │   ├── exam_engine.py      # 考试引擎
│   │   ├── question_service.py # 题库服务
│   │   ├── video_service.py    # 视频服务
│   │   ├── analysis_service.py # 考点分析
│   │   ├── planner_service.py  # 学习规划 + AI 建议
│   │   ├── enrollment_service.py # 报考管理
│   │   ├── flashcard_service.py # 闪卡 SM-2
│   │   ├── past_paper_service.py # 真题归档
│   │   ├── email_service.py    # 邮件发送
│   │   ├── knowledge_service.py # 知识库
│   │   ├── ocr_service.py      # OCR 文本提取
│   │   ├── search_client.py    # 统一搜索客户端
│   │   ├── online_question_provider.py # 在线题源
│   │   ├── ai_provider_pool.py # AI 提供商池
│   │   ├── ai_provider_service.py # AI 提供商管理
│   │   ├── search_provider_service.py # 搜索提供商管理
│   │   ├── recommendation_service.py # 课程推荐
│   │   ├── answer_template_service.py # 答题模板
│   │   ├── sprint_report_service.py # 冲刺报告
│   │   └── ...                 # 其他服务
│   ├── models/                 # SQLAlchemy 数据模型 (19 个)
│   ├── config/                 # 配置 (Settings + AI 配置)
│   ├── utils/                  # 工具 (密码哈希/限流/加密)
│   ├── data/                   # 种子数据
│   ├── init_db.py              # 数据库初始化
│   └── main.py                 # FastAPI 入口
├── frontend/                   # 前端应用
│   ├── src/
│   │   ├── pages/              # 页面 (18 个)
│   │   ├── components/         # UI 组件 + 业务组件
│   │   │   └── ui/             # 通用 UI 组件库
│   │   ├── api/                # API 调用模块 (18 个)
│   │   ├── App.tsx             # 路由配置
│   │   └── main.tsx            # 入口
│   ├── public/                 # 静态资源
│   ├── package.json
│   ├── vite.config.ts          # Vite + PWA 配置
│   └── tailwind.config.js      # Tailwind 配置
├── alembic/                    # 数据库迁移 (12+ 版本)
├── scripts/                    # 脚本工具 (40+)
│   ├── seed_*.py               # 种子数据导入
│   ├── crawl_*.py              # 官方数据采集
│   ├── fix_*.py                # 数据质量修复
│   ├── migrate_*.py            # 数据迁移
│   ├── backup_db.py            # 数据库备份
│   ├── restore_db.py           # 数据库恢复
│   └── ...                     # 其他脚本
├── tests/                      # 测试 (13 个测试文件)
├── docs/                       # 文档
│   └── DEPLOYMENT.md           # 部署文档
├── docker-compose.yml          # 容器编排 (6 个服务)
├── requirements.txt            # Python 依赖
├── .env.example                # 环境变量示例
└── README.md
```

---

## 🔑 核心配置

编辑 `.env` 文件，配置以下关键参数：

```bash
# ── 数据库（不配置时使用 SQLite） ──
DATABASE_URL=postgresql://user:password@localhost:5432/exam_hub

# ── Redis（可选） ──
REDIS_URL=redis://localhost:6379/0

# ── Elasticsearch（可选） ──
ELASTICSEARCH_URL=http://localhost:9200

# ── MinIO（可选） ──
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=your_access_key
MINIO_SECRET_KEY=your_secret_key

# ── JWT ──
SECRET_KEY=your_secret_key_here  # 生产环境必须替换

# ── AI 提供商（也可在管理后台配置） ──
# 支持任意 OpenAI 兼容 API
AI_API_BASE_URL=https://api.example.com/v1
AI_API_KEY=your_api_key
AI_MODEL=claude-sonnet-4-6

# ── 在线搜索（可选） ──
TAVILY_API_URL=https://api.tavily.com
TAVILY_API_KEY=your_tavily_key

# ── 邮件（密码重置） ──
SMTP_HOST=smtp.example.com
SMTP_USERNAME=your_email
SMTP_PASSWORD=your_password
SMTP_FROM_EMAIL=noreply@example.com

# ── 限流 ──
LOGIN_RATE_LIMIT_PER_MINUTE=10
PASSWORD_RESET_RATE_LIMIT_PER_MINUTE=3
EXTERNAL_SEARCH_RATE_LIMIT_PER_MINUTE=20
AI_RATE_LIMIT_PER_MINUTE=10
```

---

## 🐳 Docker 部署

```bash
# 生成密钥
python -c "import secrets; print(secrets.token_urlsafe(48))"

# 编辑 .env，设置 SECRET_KEY

# 一键启动全部服务
docker compose up --build
```

`docker-compose.yml` 包含 6 个服务：

| 服务 | 端口 | 说明 |
|------|------|------|
| postgres | 5432 | PostgreSQL 13 主数据库 |
| redis | 6379 | Redis 6 缓存 |
| elasticsearch | 9200 | Elasticsearch 8.11 全文搜索 |
| minio | 9000/9001 | MinIO 对象存储 |
| backend | 8000 | FastAPI 后端 |
| frontend | 3000 | Vite 前端 |

---

## 📊 数据导入

```bash
# 初始化建表 + 导入课程目录和演示数据
python -m backend.init_db

# 导入题库数据（支持 JSON/CSV）
python scripts/data_import.py --type questions --source data/questions/

# 批量导入真题试卷
python scripts/seed_past_papers_batch.py

# 导入多省份报考数据
python scripts/seed_multi_province_data.py

# 从官方渠道采集专业目录
python scripts/crawl_majors.py

# 从网络搜索导入真题
python scripts/multi_search_with_answers.py
```

---

## ✅ 测试

```bash
# 运行全部测试
python -m pytest tests/

# 运行单个测试
python -m pytest tests/test_algorithms.py -v
```

测试覆盖：认证与访问控制、算法、备份恢复、搜索客户端、在线题源、AI 提供商池、爬虫、报考管理、评分趋势、视频服务、数据导入性能、真题来源。

---

## 🤝 参与贡献

欢迎提交 Issue 和 Pull Request！

1. Fork 项目并创建特性分支 (`git checkout -b feature/AmazingFeature`)
2. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
3. 推送到分支 (`git push origin feature/AmazingFeature`)
4. 提交 Pull Request

---

## 📄 开源协议

本项目采用 MIT 协议开源 - 查看 [LICENSE](LICENSE) 文件了解详情。

---

## 📞 联系方式

- 项目主页: https://github.com/zccztt/self-study-exam-hub
- 问题反馈: https://github.com/zccztt/self-study-exam-hub/issues

---

## 🙏 致谢

- 感谢所有贡献者的辛勤付出
- 感谢开源社区提供的优秀工具和框架

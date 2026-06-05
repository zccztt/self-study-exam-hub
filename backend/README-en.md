# Self-Study Exam Hub

> All-in-one Self-Study Examination Prep Platform: Mock Exams × Question Bank Search × Video Resources × High-Frequency Topics × Smart Study Planning

A complete closed-loop learning platform built for self-study exam candidates — covering the entire journey from **practice → search → watch → focus → plan**. Say goodbye to fragmented study sessions; let data drive your learning direction and intelligent planning boost your pass rate.

---

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- PostgreSQL 13+
- Redis 6+
- Elasticsearch 8+ (optional, for full-text search)
- Node.js 16+ (frontend development)

### Installation & Deployment

```bash
# 1. Clone the repository
git clone https://github.com/zccztt/self-study-exam-hub.git
cd self-study-exam-hub

# 2. Install backend dependencies
pip install -r requirements.txt

# 3. Configure environment variables
cp .env.example .env
# Edit .env to configure database connections, API keys, etc.

# 4. Initialize the database
python manage.py migrate
python manage.py load_initial_data  # Import initial question bank data

# 5. Start the backend server
python manage.py runserver

# 6. Install frontend dependencies (open a new terminal)
cd frontend
npm install

# 7. Start the frontend development server
npm run dev
```

Visit `http://localhost:3000` to get started.

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                      Frontend Presentation Layer                     │
│  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌──────────┐ ┌────────┐ │
│  │   Mock     │ │ Question  │ │  Video    │ │  Topic   │ │ Study  │ │
│  │   Exam     │ │  Bank     │ │  Center   │ │ Outline  │ │Planner │ │
│  │  Module    │ │  Module   │ │  Module   │ │  Module  │ │ Module │ │
│  └─────┬─────┘ └─────┬─────┘ └────┬──────┘ └────┬─────┘ └───┬────┘ │
│        │             │            │             │           │      │
│  React / Vue3 + TypeScript + Tailwind CSS + ECharts / D3.js       │
└────────┼─────────────┼────────────┼─────────────┼───────────┼──────┘
         │             │            │             │           │
    ─────▼─────────────▼────────────▼─────────────▼───────────▼──────
         │          API Gateway (Nginx / Kong)                │
    ─────┼───────────────────────────────────────────────────┼──────
         │                                                     │
┌────────▼─────────────────────────────────────────────────────▼──────┐
│                        Backend Service Layer                         │
│                     Python (FastAPI / Django)                        │
│                                                                      │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌────────────┐  │
│  │  Exam Engine │ │  Question    │ │  Video       │ │  Topic     │  │
│  │  Service     │ │  Bank Service│ │  Service     │ │  Analysis  │  │
│  │ ─────────── │ │ ─────────── │ │ ─────────── │ │ ────────── │  │
│  │• Paper Gen  │ │• Full-text   │ │• Link Mgmt  │ │• Frequency │  │
│  │• Timer Ctrl │ │  Search      │ │• Category   │ │  Stats     │  │
│  │• Auto Grade │ │• Multi-dim   │ │  Index      │ │• Topic     │  │
│  │• Wrong Q    │ │  Filter      │ │• Recommend  │ │  Extraction│  │
│  │  Archive    │ │• Favorites   │ │• Link Check │ │• Trend     │  │
│  │             │ │  & Export    │ │             │ │  Analysis  │  │
│  │             │ │              │ │             │ │• Knowledge │  │
│  │             │ │              │ │             │ │  Graph     │  │
│  └──────┬───────┘ └──────┬───────┘ └──────┬───────┘ └─────┬──────┘  │
│         │                │                │               │         │
│  ┌──────▼────────────────▼────────────────▼───────────────▼──────┐  │
│  │                    Study Planning Engine                       │  │
│  │  • Weakness Detection  • Time Allocation  • Personalized Path │  │
│  │  • Progress Tracking   • Adaptive Adjustments                 │  │
│  └──────────────────────────┬────────────────────────────────────┘  │
└─────────────────────────────┼──────────────────────────────────────┘
                              │
┌─────────────────────────────▼──────────────────────────────────────┐
│                         Data Storage Layer                          │
│                                                                      │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────┐  ┌──────────┐  │
│  │  PostgreSQL  │  │Elasticsearch │  │    Redis     │  │  MinIO   │  │
│  │  ──────────  │  │  ──────────  │  │  ─────────  │  │ ──────── │  │
│  │ • User data  │  │ • Full-text  │  │ • Session   │  │ • Images │  │
│  │ • Question   │  │   index      │  │   cache     │  │ • Attach │  │
│  │   bank       │  │ • Topic word │  │ • Leader-   │  │   -ments │  │
│  │ • Exam       │  │   cloud      │  │   board     │  │ • Export │  │
│  │   records    │  │              │  │ • Exam      │  │   files  │  │
│  │ • Video      │  │              │  │   timer     │  │          │  │
│  │   metadata   │  │              │  │             │  │          │  │
│  └─────────────┘  └──────────────┘  └─────────────┘  └──────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## ✨ Core Features

### 📝 Module 1: Mock Exam System

Recreate a realistic exam environment with timing, auto-grading, and intelligent answer analysis.

```
┌─────────────────────────────────────────────────────────┐
│                    Mock Exam Workflow                     │
│                                                           │
│  Select    ──→  Select  ──→  Start   ──→   Submit        │
│  Subject        Mode         Exam          Paper         │
│     │             │            │              │           │
│     ▼             ▼            ▼              ▼           │
│  ┌──────┐   ┌─────────┐  ┌──────────┐  ┌───────────┐   │
│  │Subject│   │• Past    │  │• Q-by-Q  │  │• Auto     │   │
│  │  List │   │  Papers  │  │  Answer  │  │  Grading  │   │
│  │       │   │  (by yr) │  │• Count-  │  │• Answer   │   │
│  │• Gen  │   │• Random  │  │  down    │  │  Analysis │   │
│  │  Ed   │   │  Paper   │  │• Mark &  │  │• Wrong Q  │   │
│  │• Major│   │• Chapter │  │  Skip    │  │  Archive  │   │
│  │  -    │   │  Drill   │  │• Answer  │  │• Score    │   │
│  │  spec │   │• Redo    │  │  Sheet   │  │  Trend    │   │
│  │       │   │  Wrong Q │  │          │  │  Charts   │   │
│  └──────┘   └─────────┘  └──────────┘  └───────────┘   │
└─────────────────────────────────────────────────────────┘
```

**Feature List**:

| Feature | Description |
|---------|-------------|
| Past Exam Papers | Fully restored exam papers by year (2019–2024) |
| Smart Paper Generation | Randomly assemble papers by chapter / question type / difficulty |
| Exam Timer | Countdown timer with auto-submission on timeout |
| Answer Sheet | Visual progress tracker with mark / jump support |
| Auto Grading | Automatic grading for objective questions; reference answers for subjective ones |
| Wrong Question Book | Auto-archive wrong answers with tag-based classification and redo |
| Score Analysis | Score-rate trends by subject / chapter / question type |

---

### 🔍 Module 2: Question Bank Search Engine

Quickly locate target questions with multi-dimensional filtering and full-text search.

```
┌──────────────────────────────────────────────────────┐
│                Question Bank Search                    │
│                                                        │
│  ┌─────────────────────────────────────────────────┐  │
│  │          Search Bar (Natural Language)            │  │
│  │  🔍 Enter keywords, question content, topics...  │  │
│  └──────────────────┬──────────────────────────────┘  │
│                     │                                  │
│          ┌──────────▼──────────┐                       │
│          │    Filter Panel      │                       │
│          │                      │                       │
│          │  ☐ Subject  [Select] │                       │
│          │  ☐ Year     [Multi]  │                       │
│          │  ☐ Type     [Multi]  │                       │
│          │    • Single Choice   │                       │
│          │    • Multiple Choice │                       │
│          │    • Fill-in-blank   │                       │
│          │    • Short Answer    │                       │
│          │    • Essay  • Case   │                       │
│          │  ☐ Difficulty[Slider]│                       │
│          │  ☐ Chapter  [Tree]   │                       │
│          │  ☐ High-Freq[Toggle] │                       │
│          └──────────┬──────────┘                       │
│                     │                                  │
│          ┌──────────▼──────────┐                       │
│          │   Search Results     │                       │
│          │                      │                       │
│          │  📋 Question Card    │                       │
│          │  ├─ Content (HL)     │                       │
│          │  ├─ Source: Oct 2023 │                       │
│          │  ├─ Type: Single     │                       │
│          │  ├─ Appeared: 3x     │                       │
│          │  ├─ [View Answer]    │                       │
│          │  ├─ [Add to Fav]     │                       │
│          │  └─ [Add to Wrong Q] │                       │
│          └──────────────────────┘                       │
└──────────────────────────────────────────────────────┘
```

**Highlights**:
- Elasticsearch-powered full-text search with tokenization and semantic matching
- Multi-dimensional combined filtering (subject, year, type, difficulty, chapter)
- High-frequency topic markers for quickly spotting key questions
- Question bookmarking and custom tag management

---

### 🎬 Module 3: Video Resource Hub

Link questions to video explanations and quickly locate learning resources.

```
┌───────────────────────────────────────────────────────────┐
│                   Video Resource Architecture               │
│                                                              │
│  ┌──────────────┐    ┌───────────────┐    ┌──────────────┐  │
│  │ Video Sources │    │ Linking Engine │    │ Display Layer│  │
│  │              │    │               │    │              │  │
│  │ • Bilibili   │───▶│ • By Subject  │───▶│ • List View  │  │
│  │ • NetEase    │    │ • By Chapter  │    │ • Card View  │  │
│  │   Open Course│    │ • By Topic    │    │ • Embedded   │  │
│  │ • Tencent    │    │ • By Question │    │   Player     │  │
│  │   Classroom  │    │               │    │              │  │
│  │ • Self-hosted│    │               │    │              │  │
│  │ • YouTube    │    │               │    │              │  │
│  └──────────────┘    └───────────────┘    └──────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │               Video Resource Card Example             │   │
│  │  ┌────────────────────────────────────────────────┐  │   │
│  │  │ 📹 Intro to Marxism - Ch.3 Materialist         │  │   │
│  │  │    Dialectics                                   │  │   │
│  │  │ ──────────────────────────────────────────────  │  │   │
│  │  │ Source: Bilibili - XX Education                 │  │   │
│  │  │ Duration: 45:20       Views: 123K               │  │   │
│  │  │ Related Topic: Universality & Particularity     │  │   │
│  │  │               of Contradictions                 │  │   │
│  │  │ Related Questions: 12                           │  │   │
│  │  │ [▶ Play] [🔗 Link] [⭐ Favorite] [📋 Notes]   │  │   │
│  │  └────────────────────────────────────────────────┘  │   │
│  └──────────────────────────────────────────────────────┘   │
└───────────────────────────────────────────────────────────┘
```

**Highlights**:
- Aggregated video resources from mainstream platforms (Bilibili, NetEase Open Course, Tencent Classroom, etc.)
- Smart linking between videos, questions, and exam topics
- Video bookmarking and study notes
- Automatic external link validation

---

### 📊 Module 4: High-Frequency Topic Outline & Visual Analytics

Data-driven visualization of exam focus areas to guide your review strategy.

```
┌────────────────────────────────────────────────────────────────┐
│              High-Frequency Topic Analysis System               │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                 Data Collection & Analysis                 │   │
│  │                                                            │   │
│  │  Past Papers ──→ Topic Tagging ──→ Frequency ──→ Trend    │   │
│  │       │               │           Stats │     Analysis │   │   │
│  │       ▼               ▼                ▼            ▼      │   │
│  │   ┌───────┐    ┌──────────┐    ┌──────────┐  ┌─────────┐ │   │
│  │   │Q Bank │    │Topic     │    │Frequency │  │Predict  │ │   │
│  │   │       │    │Taxonomy  │    │Matrix    │  │Model    │ │   │
│  │   │2019~  │    │(tree)    │    │(subject ×│  │(next    │ │   │
│  │   │2024   │    │          │    │ topic)   │  │ exam    │ │   │
│  │   └───────┘    │chapter   │    └──────────┘  │forecast)│ │   │
│  │                │ └─section │                  └─────────┘ │   │
│  │                │   └─point │                               │   │
│  │                └──────────┘                                │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                  Visualization Dashboard                   │   │
│  │                                                            │   │
│  │  ┌─ Exam Outline Tree ────────────────────────────────┐   │   │
│  │  │                                                     │   │   │
│  │  │  Introduction to Marxist Philosophy                 │   │   │
│  │  │  ├── Ch.1 What is Marxism (Weight: ★★★☆☆)         │   │   │
│  │  │  │   ├── 1.1 Origin & Development (3 appearances)  │   │   │
│  │  │  │   ├── 1.2 Key Characteristics (5 appearances) 🔥│   │   │
│  │  │  │   └── 1.3 Contemporary Value (2 appearances)    │   │   │
│  │  │  ├── Ch.2 Materiality of the World                 │   │   │
│  │  │  │       (Weight: ★★★★☆)                           │   │   │
│  │  │  │   ├── 2.1 Matter & Consciousness (8x) 🔥🔥      │   │   │
│  │  │  │   └── ...                                       │   │   │
│  │  │  └── ...                                           │   │   │
│  │  └────────────────────────────────────────────────────┘   │   │
│  │                                                            │   │
│  │  ┌─ Additional Visualizations ────────────────────────┐   │   │
│  │  │  • 📊 Top 20 High-Frequency Topic Bar Chart        │   │   │
│  │  │  • 🔵 Topic Correlation Network (Force-directed)   │   │   │
│  │  │  • 📈 Annual Topic Trend Line Chart                │   │   │
│  │  │  • ☁️  Topic Word Cloud                             │   │   │
│  │  │  • 🗺️  Chapter Heatmap (darker = higher frequency) │   │   │
│  │  │  • 🥧  Question Type Distribution Pie Chart        │   │   │
│  │  └────────────────────────────────────────────────────┘   │   │
│  └──────────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────────┘
```

**Highlights**:
- Knowledge point frequency analysis based on historical exam papers
- Interactive exam outline tree with high-frequency topic annotations
- Multi-dimensional data visualization (bar chart, network graph, heatmap, word cloud, etc.)
- Topic trend analysis and next-exam predictions

---

### 🗓️ Module 5: Smart Study Planner

Generate a personalized study plan based on individual weaknesses and exam schedule.

```
┌───────────────────────────────────────────────────────────┐
│                   Study Planning Engine                     │
│                                                             │
│  INPUT                 PROCESSING              OUTPUT       │
│  ─────                 ──────────              ──────       │
│                                                             │
│  ┌──────────┐      ┌───────────────┐      ┌────────────┐  │
│  │• Exam    │      │               │      │ Daily Study│  │
│  │  Date    │      │   Planning    │      │ Task List  │  │
│  │• Enrolled│      │   Algorithm   │      │            │  │
│  │  Subjects│─────▶│   Engine      │─────▶│ ┌────────┐ │  │
│  │• Daily   │      │               │      │ │Day 1   │ │  │
│  │  Avail.  │      │ ┌───────────┐ │      │ │ 9:00   │ │  │
│  │  Hours   │      │ │Weakness   │ │      │ │ Ch.3   │ │  │
│  │• Mock    │      │ │Weight     │ │      │ │ 20 Qs  │ │  │
│  │  Scores  │      │ │Calculation│ │      │ │ 2 Vids │ │  │
│  │• Wrong Q │      │ ├───────────┤ │      │ ├────────┤ │  │
│  │  Distrib.│      │ │Time Alloc │ │      │ │Day 2   │ │  │
│  │• Learning│      │ │Optimization│ │     │ │ ...    │ │  │
│  │  Prefs   │      │ ├───────────┤ │      │ └────────┘ │  │
│  └──────────┘      │ │Forgetting │ │      │            │  │
│                    │ │Curve      │ │      │ 📊 Gantt   │  │
│                    │ │Scheduling │ │      │    Chart   │  │
│                    │ ├───────────┤ │      │ 📈 Progress│  │
│                    │ │Adaptive   │ │      │    Bar     │  │
│                    │ │Progress   │ │      │            │  │
│                    │ │Adjustment │ │      │            │  │
│                    │ └───────────┘ │      └────────────┘  │
│                    └───────────────┘                       │
└───────────────────────────────────────────────────────────┘
```

**Core Algorithms**:
1. **Weakness Detection**: Calculates topic mastery based on mock exam scores and wrong-question distribution
2. **Time Allocation Optimization**: Dynamically allocates study tasks based on exam countdown and daily available hours
3. **Forgetting Curve Scheduling**: Arranges review sessions based on the Ebbinghaus forgetting curve
4. **Adaptive Progress Adjustment**: Dynamically adjusts future plans based on actual completion rates

**Outputs**:
- Daily study task lists (chapters, question count, video count)
- Visual Gantt chart and progress bars
- Estimated pass rate and weakness alerts

---

## 🛠️ Tech Stack

### Backend
- **Framework**: FastAPI / Django REST Framework
- **Database**: PostgreSQL (primary data store)
- **Cache**: Redis (sessions, leaderboards, exam timers)
- **Search Engine**: Elasticsearch (full-text search)
- **Object Storage**: MinIO (images, attachments, export files)
- **AI Capabilities**: Unity2.ai API (Codex, Claude models — powering intelligent analysis and planning)

### Frontend
- **Framework**: React / Vue 3
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **Visualization**: ECharts / D3.js
- **State Management**: Redux / Pinia

### DevOps & Deployment
- **Containerization**: Docker + Docker Compose
- **API Gateway**: Nginx / Kong
- **Monitoring**: Prometheus + Grafana
- **Logging**: ELK Stack (Elasticsearch + Logstash + Kibana)

---

## 📂 Project Structure

```
self-study-exam-hub/
├── backend/                  # Backend services
│   ├── api/                  # API routes
│   ├── services/             # Business logic
│   │   ├── exam_engine.py           # Mock exam engine
│   │   ├── question_service.py      # Question bank service
│   │   ├── video_service.py         # Video resource service
│   │   ├── analysis_service.py      # Topic analysis service
│   │   └── planner_service.py       # Study planning service
│   ├── models/               # Data models / ORM
│   ├── utils/                # Utility functions
│   └── config/               # Configuration files
├── frontend/                 # Frontend application
│   ├── src/
│   │   ├── components/       # Reusable UI components
│   │   ├── pages/            # Page-level views
│   │   ├── store/            # State management
│   │   └── api/              # API client layer
│   └── public/               # Static assets
├── data/                     # Data files
│   ├── questions/            # Question bank data
│   ├── videos/               # Video metadata
│   └── knowledge_base/       # Knowledge point taxonomy
├── scripts/                  # Utility scripts
│   ├── data_import.py        # Data import tool
│   └── crawler/              # Web scrapers
├── docker/                   # Docker configuration
├── docs/                     # Documentation
├── tests/                    # Test suites
├── requirements.txt          # Python dependencies
├── docker-compose.yml        # Container orchestration
├── .env.example              # Environment variable template
└── README.md                 # Project documentation
```

---

## 🔑 Configuration

Edit the `.env` file to set the following key parameters:

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/exam_hub

# Redis
REDIS_URL=redis://localhost:6379/0

# Elasticsearch
ELASTICSEARCH_URL=http://localhost:9200

# MinIO (Object Storage)
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=your_access_key
MINIO_SECRET_KEY=your_secret_key

# Unity2.ai API (for AI-powered features)
UNITY2_API_KEY=your_unity2_api_key
UNITY2_MODEL=claude-sonnet-4-6  # or codex

# JWT Secret
SECRET_KEY=your_secret_key_here

# Frontend URL (for CORS)
FRONTEND_URL=http://localhost:3000
```

---

## 📊 Data Import

Initialize the question bank and video data:

```bash
# Import question bank data (supports JSON / CSV formats)
python scripts/data_import.py --type questions --source data/questions/

# Import video metadata
python scripts/data_import.py --type videos --source data/videos/

# Import knowledge point taxonomy
python scripts/data_import.py --type knowledge --source data/knowledge_base/
```

---

## 🤝 Contributing

Issues and Pull Requests are welcome! Please follow these guidelines:

1. Fork the repo and create a feature branch (`git checkout -b feature/AmazingFeature`)
2. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
3. Push to the branch (`git push origin feature/AmazingFeature`)
4. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

## 📞 Contact

- **Project Homepage**: [https://github.com/zccztt/self-study-exam-hub](https://github.com/zccztt/self-study-exam-hub)
- **Issue Tracker**: [https://github.com/zccztt/self-study-exam-hub/issues](https://github.com/zccztt/self-study-exam-hub/issues)

---

## 🙏 Acknowledgments

- Thanks to all contributors for their hard work and dedication
- Thanks to the open-source community for providing excellent tools and frameworks
- Thanks to Unity2.ai for powering the AI capabilities in this project
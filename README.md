# 🚀 Sprintly — Enterprise Agile Project Management Platform

> **Next-Generation Agile Planning, AI Workload Optimization, Real-Time Collaboration & Cryptographic Security.**

Sprintly is a full-stack, enterprise-grade project management system engineered for high-velocity engineering teams. It combines modern Kanban boards, live-updating Gantt chart roadmaps, backlogs, team communication channels, and deeply integrated AI copilot capabilities with multi-layer cyber threat defense.

---

## 🌟 Key Features

### 1. 📊 Agile Project Lifecycle & Roadmaps
- **Interactive Kanban Boards**: Real-time drag-and-drop workflow (`Backlog`, `To Do`, `In Progress`, `In Review`, `Blocked`, `Done`).
- **Live Gantt Chart Roadmap**: Interactive Gantt timeline visualization with real progress bars, epic hierarchy, and auto-syncing updates.
- **Sprint Management**: Planning, starting, and completing sprints with automated velocity metrics, burndown indicators, and rollover handling.
- **Product Backlog**: Effortless backlog grooming, priority tagging, and 1-click sprint assignment.

### 2. 👥 Dual Task Allocation Engine
- **Option A: ✨ AI Smart Work Allocation**:
  - Automatically assesses each team member's role (Developer, QA Engineer, Designer, Architect), weekly capacity (hours/story points), and current assigned workload.
  - Distributes unassigned tasks with optimal load balancing and human-readable reasoning.
  - 1-click **Apply All Allocations** to commit updates across the workspace.
- **Option B: Manual Task Allocation**:
  - Interactive teammate assignment with role badges and capacity indicators directly from the Team and Backlog views.

### 3. 💬 Real-Time Team Communication Chat App
- **Project Team Channels**: Dedicated communication streams (`#general`, `#dev-team`, `#sprint-planning`).
- **Direct Messaging (DMs)**: Private 1-on-1 chats between teammates with live online status indicators.
- **Live Synchronized Stream**: Auto-refreshing message stream with member badges, avatar colors, and timestamps.

### 4. 🧠 Sprintly AI Copilot (Live Telemetry Engine)
- **Live Workspace Intelligence**: AI has direct live access to workspace metrics, pending/active project counts, and bottlenecks.
- **Automated Sprint Planning**: Generates optimal scope proposals with confidence ratings and 1-click application.
- **Sprint Risk & Health Diagnostics**: Identifies scope creep, blockers, and capacity bottlenecks.
- **Subtask Breakdown & Acceptance Criteria**: Generates testing criteria and task breakdowns from issue descriptions.
- **Daily Work Recommender**: Ranks daily priorities for individual engineers.

### 5. 🛡️ Enterprise Security & DDoS Mitigation Suite
- **Email OTP 2-Factor Authentication**: 6-digit cryptographic OTP codes for secure Signup and Login verification.
- **DDoS & Route Rate Limiting**: Sliding-window IP rate limiting (20 req/min for auth routes, 120 req/min for APIs).
- **Anti-Injection Firewall**: Proactive scanning and sanitization preventing SQLi (`UNION SELECT`, `DROP TABLE`), NoSQLi (`$where`, `$gt`, `$ne`), and XSS (`<script>`, `onerror=`).
- **Cryptographic Hardening**: AES-256-GCM data encryption, SHA-256 HMAC integrity, strict CSP, and HSTS headers.

---

## 🛠️ Technology Stack

| Layer | Technology |
|---|---|
| **Backend Framework** | Django 5.2.17 + Django REST Framework |
| **Language** | Python 3.10+ |
| **Relational Database** | SQLite / PostgreSQL (Structured entities: Projects, Sprints, Issues, Users) |
| **NoSQL Engine** | MongoDB (High-velocity telemetry, audit logs, and event streams) |
| **AI / LLM Engine** | Groq API (`llama-3.3-70b-versatile`) |
| **Frontend UI** | HTML5, Modern Vanilla CSS Design System, Lucide Icons, Chart.js |
| **Security Layer** | Custom Firewall Middleware, AES-256-GCM, SHA-256, Django Session Security |

---

## 📁 Project Directory Structure

```
Sprintly/
├── accounts/               # User authentication, profiles, 6-digit OTP engine & email dispatch
├── ai_assistant/           # Sprintly AI service, prompt engineering & action executors
├── config/                 # Django settings, security middleware & crypto utilities
├── dashboard/              # Workspace metrics, activity feeds & telemetry overview
├── issues/                 # Issues, tasks, bugs, subtasks & audit log tracking
├── mongodb_engine/         # MongoDB dual-write synchronization & audit persistence
├── notifications/          # Notifications inbox, Team Chat app & room messaging API
├── projects/               # Projects, team memberships, Gantt roadmap & analytics
├── sprints/                # Sprints lifecycle, velocity & health tracking
├── static/                 # CSS styles, JavaScript controllers (sprintly.js) & assets
├── templates/              # Jinja/Django HTML templates (Glassmorphic dark/light UI)
├── .env                    # Environment secrets & credentials
├── manage.py               # Django management CLI
└── requirements.txt        # Python package dependencies
```

---

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.10 or higher
- MongoDB (Optional for local development; gracefully falls back if offline)
- Git

### 2. Clone and Setup Environment
```bash
# Clone repository
git clone <repository-url>
cd Sprintly

# Create and activate virtual environment (Windows)
python -m venv venv
.\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Configuration (`.env`)
Create or edit your `.env` file with the following configuration:
```env
DEBUG=True
SECRET_KEY=your-django-secret-key
DATABASE_URL=sqlite:///db.sqlite3

# Email Service (Gmail App Password)
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=Sprintly Platform <your-email@gmail.com>

# AI Engine (Groq API)
GROQ_API_KEY=your-groq-api-key
GROQ_MODEL=openai/gpt-oss-120b

# MongoDB Connection
MONGO_URI=mongodb://localhost:27017
MONGO_DB_NAME=sprintly_db
```

### 4. Database Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

### 5. Run the Application
```bash
python manage.py runserver
```
Visit **`http://127.0.0.1:8000`** in your browser.

---

## 🧪 Running Automated Tests

Run the full automated test suite (Authentication, AI Engine, Gantt Chart, Security Firewall, Team Chat):
```bash
python manage.py test
```
All **24 test suites** run in under 30 seconds with 100% test coverage.

---

## 📡 Key API Endpoints

### AI Assistant Endpoints
- `POST /api/ai/chat/` — Live workspace natural language Q&A.
- `POST /api/ai/plan-sprint/` — Generates sprint scope recommendations.
- `POST /api/ai/allocate-work/` — Generates role & capacity balanced workload assignments.
- `POST /api/ai/apply-action/` — 1-click execution of AI plans, allocations, and subtasks.
- `POST /api/ai/analyze-sprint/` — Sprint risk and velocity diagnostics.

### Team Communication & Notifications
- `GET /chat/` — Team Chat UI with Channels & DMs.
- `GET /api/notifications/chat/rooms/<id>/messages/` — Fetch recent room chat messages.
- `POST /api/notifications/chat/rooms/<id>/messages/` — Post a new message to a channel.
- `GET /api/notifications/api/` — Navbar live notification badge & list.

### Projects, Sprints & Issues
- `GET /api/projects/<id>/roadmap/gantt/` — Real-time Gantt roadmap data stream.
- `POST /api/issues/` — Create new issues and tickets.
- `GET /api/issues/<id>/` — Fetch issue details, comments, and subtasks.

---

## 🔒 Security & Compliance
- **OWASP Top 10 Compliant**: Built-in protection against SQL Injection, NoSQL Injection, XSS, and CSRF.
- **Zero Raw Secret Exposure**: Sensitive keys and tokens encrypted at rest via AES-256-GCM.
- **Session Protection**: `HttpOnly`, `SameSite=Lax`, and `Secure` cookie flags enabled.

---

## 📄 License
This project is licensed under the MIT License.

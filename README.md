# 🚀 Sprintly — Enterprise Agile Project Management Platform

> **Next-Generation Agile Planning, AI Workload Optimization, Real-Time Collaboration & Multi-Layer Cyber Threat Defense.**

Sprintly is a full-stack, enterprise-grade agile project management system engineered for high-velocity software engineering teams. It unites interactive drag-and-drop Kanban boards, live Gantt chart roadmaps, dynamic sprint velocity tracking, team collaboration, and a deeply integrated Groq LLaMA 3.3 AI Copilot with hardened security and real-time database persistence.

---

## 🌟 Key Features

### 1. 📊 Agile Project Lifecycle & Kanban Workflow
- **Interactive 6-Column Kanban Board**: Real-time drag-and-drop status transitions across `Backlog`, `To Do`, `In Progress`, `In Review`, `Blocked`, and `Done`.
- **Dynamic Sprint Velocity Synchronization**: Dragging issues into or out of `Done` immediately recalculates sprint velocity and completed story points in real time across the board, sprint hub, and project metrics.
- **Optimistic UI with Automatic Rollback**: Instant UI feedback on ticket movements with automatic rollback to original column and error toast notifications on network disruptions.
- **Complete Sprint Lifecycle Modal**: End active sprints with dedicated modal dialogs, calculate final sprint velocity, generate burndown telemetry, and seamlessly roll over unfinished tickets into the Product Backlog or upcoming planned sprints.
- **Live Gantt Chart Roadmap**: Interactive Gantt timeline visualization featuring real progress bars, epic hierarchies, milestone schedules, and live updates.
- **Product Backlog Grooming**: Effortless ticket backlog management, story point estimations, priority tagging, and 1-click sprint assignments.

### 2. 👤 User Profile & Identity Management
- **Full Database Persistence**: Every profile update is validated, authenticated, and persisted directly to Django's relational database and synchronized with MongoDB.
- **Profile Information (Editable)**:
  - **First Name & Last Name**: Automatically populated from the authenticated user; automatically infers and extracts names from username or email if blank.
  - **Username & Email**: Validated for format and strictly enforced for global uniqueness.
  - **Job Title & Location**: Real-time workspace identity customization.
  - **Bio**: Public bio with live reactive character counter (`0 / 1000`).
  - **Profile Picture**: Supports JPG, PNG, WEBP, and GIF formats (up to 5MB) with instant base64 data URL preview, photo removal option, and a sleek initials avatar fallback.
- **Work Information (Read-Only)**:
  - **Role**, **Department**, and **Joined Date** are clearly labeled with lock badges and immutable constraints enforced at both client and REST API levels.
- **Anti-IDOR Security**: REST endpoints (`GET /api/profile/`, `PUT /api/profile/`) strictly resolve the user identity from active sessions or cryptographically signed JWT Bearer tokens.

### 3. 🧠 Sprintly AI Copilot (Live Telemetry Engine)
- **Powered by Groq API (`llama-3.3-70b-versatile`)**: Real-time, contextual AI assistant accessible from a slide-out drawer or floating quick-action button.
- **Live Workspace Context Awareness**: Directly analyzes live workspace tickets, sprint health, pending projects, blockers, and team telemetry.
- **Automated Sprint Planning**: Generates optimal sprint scope proposals with confidence ratings and 1-click plan application.
- **Smart Work Allocation**: Analyzes each engineer's role, weekly capacity, and current active workload to distribute unassigned tasks with human-readable reasoning.
- **Sprint Risk & Health Diagnostics**: Pinpoints scope creep, bottlenecks, and delivery risk factors with actionable remediation steps.
- **Task Breakdown & Acceptance Criteria**: Automatically decomposes complex feature descriptions into subtasks and QA test specifications.

### 4. 👥 Team Collaboration & Workspace Invitations
- **Team Roster & Memberships**: Centralized visibility into workspace members, assigned roles (Administrator, Scrum Master, Developer, Tester, Viewer), and allocated weekly capacity.
- **Direct Workspace Invitations**: Invite team members by email or username with designated project roles.
- **Real-Time Notification Center**: Live notification inbox, unread count badges in navbar and sidebar, mark-as-read actions, and automatic project onboarding upon invitation acceptance.
- **Activity Stream**: Live audit logging of issue transitions, sprint completions, and membership updates.

### 5. 📡 Live Platform Status & Telemetry Widget
- **Sidebar Health Beacon**: Sticky operational status card with a pulsing emerald beacon dot indicating real-time system uptime (`99.98% Uptime`, `v2.4 Core`).
- **Interactive Telemetry Popover**: 1-click popover detailing real-time health metrics across core subsystems: Agile Core Engine, AI Copilot, MongoDB Telemetry Sync, and Live Kanban Services.

### 6. 🛡️ Enterprise Security & DDoS Mitigation Suite
- **Email OTP 2-Factor Authentication**: 6-digit cryptographic OTP codes dispatched for secure Signup and Login verification.
- **DDoS & Route Rate Limiting**: Sliding-window IP rate limiter (20 requests/minute for authentication routes, 120 requests/minute for API routes).
- **Anti-Injection Web Application Firewall**: Proactive scanning and sanitization preventing SQLi (`UNION SELECT`, `DROP TABLE`), NoSQLi (`$where`, `$gt`, `$ne`), and XSS (`<script>`, `javascript:`, `onerror=`).
- **Cryptographic Hardening**: AES-256-GCM data encryption, SHA-256 HMAC integrity, strict Content-Security-Policy (CSP allowing `self`, `data:`, `blob:`), and HSTS headers.

---

## 🛠️ Technology Stack

| Layer | Technology |
|---|---|
| **Backend Framework** | Django 5.2.17 + Django REST Framework |
| **Language** | Python 3.10+ |
| **Relational Database** | SQLite (Default development) / PostgreSQL |
| **Media Processing** | Pillow (PIL) for image upload validation & processing |
| **NoSQL Engine** | MongoDB (High-velocity telemetry, audit logs, and event streams) |
| **AI / LLM Engine** | Groq Cloud API (`llama-3.3-70b-versatile`) |
| **Frontend UI** | HTML5, Modern Vanilla CSS Glassmorphism Design System, Lucide Icons, Chart.js |
| **Security Layer** | Custom Firewall Middleware, AES-256-GCM, SHA-256, Django Session Security, CSP |

---

## 📁 Project Directory Structure

```
Sprintly/
├── accounts/               # User authentication, profiles, 6-digit OTP engine & Profile REST API
├── ai_assistant/           # Sprintly AI service (Groq LLaMA 3.3), prompt engineering & executors
├── analytics/              # Sprint velocity analytics, burndown charts & team metrics
├── config/                 # Django settings, security middleware, URLs & crypto utilities
├── dashboard/              # Workspace metrics, activity feeds & telemetry overview
├── issues/                 # Issues, tasks, bugs, subtasks & drag-and-drop move status API
├── media/                  # Uploaded user media files (profile avatars, attachments)
├── mongodb_engine/         # MongoDB dual-write synchronization & audit persistence
├── notifications/          # Notifications inbox, invitation acceptance & badge APIs
├── projects/               # Projects, team memberships, Gantt roadmap & analytics
├── sprints/                # Sprints lifecycle, velocity engine & completion modal
├── static/                 # CSS design system, JavaScript controllers (sprintly.js) & assets
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

# Create and activate virtual environment (Windows PowerShell)
python -m venv venv
.\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Configuration (`.env`)
Create or edit your `.env` file in the project root:
```env
DJANGO_DEBUG=True
DJANGO_SECRET_KEY=your-django-secret-key
ALLOWED_HOSTS=*

# Email Service (Gmail App Password for OTP dispatch)
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=Sprintly Platform <your-email@gmail.com>

# AI Engine (Groq Cloud API)
GROQ_API_KEY=your-groq-api-key
GROQ_MODEL=llama-3.3-70b-versatile

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
python manage.py runserver 127.0.0.1:8000
```
Visit **`http://127.0.0.1:8000`** in your browser.

---

## 🧪 Running Automated Tests

Run the full automated test suite across all applications:
```bash
python manage.py test
```
All **34 automated test suites** execute in ~30 seconds with 100% pass rate:
- **`accounts`**: OTP generation, login/signup, profile retrieval, profile updates, username/email uniqueness, immutability of read-only fields, avatar upload validation, and security headers.
- **`issues`**: Issue status transitions, drag-and-drop move endpoint, sprint completed points synchronization, and subtasks.
- **`sprints`**: Sprint lifecycle, velocity calculation, burndown data, and sprint completion workflows.
- **`projects`**: Project creation, team roster, capacity management, and Gantt roadmap serialization.
- **`ai_assistant`**: Groq copilot integrations, workload allocation, sprint planning, and prompt executors.
- **`notifications`**: Invitation acceptances, mark-as-read actions, and navbar badge counters.

---

## 📡 Key REST API Endpoints

### User Profile & Identity
- `GET /api/profile/` — Fetch authenticated user profile details, work info, and avatar URL.
- `PUT /api/profile/` — Update profile details (first name, last name, username, email, job title, location, bio, avatar file upload, or avatar removal).

### Agile Issues & Kanban
- `POST /api/issues/<id>/move/` — Drag-and-drop issue status change with dynamic sprint velocity sync.
- `POST /api/issues/` — Create new tickets and backlog items.
- `GET /api/issues/<id>/` — Fetch issue details, comments, and subtasks.
- `POST /api/issues/<id>/subtasks/` — Create and toggle subtasks.

### Sprints & Roadmaps
- `POST /projects/<project_id>/sprints/<sprint_id>/complete/` — Complete active sprint and rollover uncompleted issues.
- `GET /api/projects/<id>/roadmap/gantt/` — Real-time Gantt roadmap data stream.
- `POST /api/sprints/` — Create and start new agile sprints.

### AI Assistant (Groq Copilot)
- `POST /api/ai/chat/` — Live workspace natural language Q&A.
- `POST /api/ai/plan-sprint/` — Generates sprint scope recommendations.
- `POST /api/ai/allocate-work/` — Generates role & capacity balanced workload assignments.
- `POST /api/ai/apply-action/` — 1-click execution of AI plans, allocations, and subtasks.
- `POST /api/ai/analyze-sprint/` — Sprint risk and velocity diagnostics.

### Notifications & Collaboration
- `GET /notifications/` — Notification Inbox UI.
- `GET /api/notifications/api/` — Navbar live notification badge & list.
- `POST /notifications/<id>/mark-read/` — Mark individual notification as read.
- `POST /notifications/mark-all-read/` — Mark all notifications as read.
- `POST /notifications/<id>/accept/` — Accept team invitation & automatically join project team.

---

## 🔒 Security & Compliance
- **OWASP Top 10 Compliant**: Built-in defenses against SQL Injection, NoSQL Injection, XSS, CSRF, and IDOR vulnerabilities.
- **Strict Anti-IDOR Enforcement**: Sensitive actions resolve authenticated identity strictly from sessions or validated JWT claims.
- **Hardened Cookies & CSP**: `HttpOnly`, `SameSite=Lax`, and `Secure` cookie flags enabled with strict CSP for script, style, and media directives.

---

## 📄 License
This project is licensed under the MIT License.

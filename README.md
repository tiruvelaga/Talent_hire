# TalentHire – Modern Django Online Exam & Recruitment Portal

**A clean, professional online examination system for recruitment.** Features a modern glassmorphism UI with light-orange accents, candidate self-registration with admin approval, per-exam configuration, robust bulk operations, fixed filters, profile management, and stable Docker deployment.

**Recent major updates include:** simplified admin forms/settings (checkbox multi-select with live search), blurred small delete modals, single orange password toggle, no hardcoded defaults (admin sets Passing %), fixed Selected/Not-Selected filters and profile queries, improved navbar/profile flow, cache-clearing entrypoint for reliable reloads, and removal of cutoff threshold/mixed questions/subject distribution.

---

## 🚀 Key Features

### 👨‍💼 Admin Portal
- **Clean Dashboard**: Stats cards, recent attempts, quick links.
- **Candidate Management**: Multi-select checkboxes (live search, Select All/Clear, count), bulk Excel import/export (with dummy samples), self-registration approval workflow (`PendingRegistration` model).
- **Exam Management**: Per-exam settings (Passing % set by admin — no defaults), multi-select questions/candidates, simplified creation flow (redirects to settings after create).
- **Question Bank**: Bulk import from Excel, category support.
- **Results & Analytics**: Robust filters (`Selected`/`Not Selected`/`All` — no more mixed data), export to Excel, publish/unpublish controls.
- **UI/UX**: Glassmorphism cards, light orange theme (`#f59e0b` accents — "not too orange"), small blurred-background delete popups (compact, softer red), responsive Bootstrap 5.
- **Other**: Notifications, support queries, load testing ready (`locustfile.py`).

### 🎓 Candidate Portal
- **Self-Registration**: New candidates register (Registration ID becomes initial password); admin approves.
- **Modern Login**: Centered card, single orange eye toggle (no duplicate icons), clear info box with register link.
- **My Profile**: Stats (attempts, selected count), change password, light-orange styling; accessible via navbar icon.
- **Dashboard**: Active exams, history, notifications (no duplicate "View Profile" buttons).
- **Exam Experience**: Rules page, pre-exam check, timed interface, automatic submit.
- **Results**: Detailed view when published.

**All previous bugs fixed**: filters, `date_taken` ordering (no more `attempted_at` FieldError), modal sizing/color, Docker reloads/cache, login eye icons.

---

## 📁 Project Structure

```
Talent_Hire/
├── manage.py                    # Django entrypoint
├── README.md                    # This file (updated with all changes)
├── requirements.txt             # Python deps (Django, openpyxl, celery, redis, gunicorn, pytz)
├── docker-compose.yml           # Services: Postgres, Redis, Celery, 4x Gunicorn web, Nginx
├── Dockerfile                   # Python 3.11 + deps
├── entrypoint.sh                # DB wait, migrations, sample data, cache clear, start app
├── db.sqlite3                   # Local SQLite (Docker uses Postgres)
├── locustfile.py                # Load testing
├── test.py                      # Quick tests
│
├── talent_hire/                 # Main Django project
│   ├── __init__.py
│   ├── settings.py              # Config (DB routers, Celery, static, templates)
│   ├── urls.py                  # Root + admin + exam URLs
│   ├── wsgi.py
│   └── celery.py
│
├── exam/                        # Main app (all business logic)
│   ├── __init__.py
│   ├── models.py                # Candidate, Exam, Question, ExamAttempt, PendingRegistration, Notification, SupportQuery
│   ├── views.py                 # All views (profile, results filters, bulk, register/approve, admin CRUD)
│   ├── admin.py
│   ├── tasks.py                 # Celery tasks
│   ├── urls.py
│   ├── management/commands/load_sample_data.py  # Generates dummy Excel + loads data
│   ├── migrations/              # Up to 0010+ (PendingRegistration, exam relations, is_activated, etc.)
│   └── templates/exam/          # All HTML (Bootstrap 5 + custom CSS/JS)
│       ├── base.html            # Shared layout
│       ├── admin_base.html      # Admin layout + reusable small blurred delete modal + JS
│       ├── login.html           # Modern centered login with single orange eye toggle
│       ├── register.html        # Self-registration (light orange)
│       ├── candidate_profile.html  # Stats + password change (light orange glass cards)
│       ├── admin_exam_form.html / admin_exam_settings.html  # Clean checkbox multi-selects
│       ├── admin_results.html   # Fixed status filters
│       ├── candidate_dashboard.html
│       ├── admin_dashboard.html
│       ├── result.html / candidate_results.html
│       ├── exam.html / exam_rules.html / pre_exam_check.html
│       ├── notifications.html / help_support.html / admin_queries.html
│       └── partials/...
│
├── nginx/                       # nginx.conf (reverse proxy)
├── static/                      # Admin static + custom CSS/JS
├── scratch/                     # Test scripts (verify_login, reset_passwords)
└── .venv/                       # Local virtual environment
```

**Note**: Docker mounts the entire project for live reloads (cache cleared automatically).

---

## 🛠️ Setup & Installation

### Preferred: Docker (Production-like, includes Postgres + Redis + Celery + Nginx)
```bash
# 1. Clone / navigate to project
cd Talent_Hire

# 2. Build and start (first time takes ~30-60s)
docker-compose up --build -d

# 3. Wait for "Migrations done" and healthy containers
# Check logs:
docker-compose logs -f web1
```

**Default Credentials**
- **Admin**: `http://localhost/portal/login/` → `root` / `9999`
- **Sample Candidates**: Use `python manage.py load_sample_data` (or via Docker exec) — generates dummy Excel files in project root.
- **Self-Register**: Visit `/register/` as candidate → Admin approves in Pending Registrations.

### Local Development (venv)
```bash
# Create/activate venv (Python 3.11+)
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt

# Configure environment
python -m configure_python_environment  # or manual
python manage.py migrate
python manage.py load_sample_data
python manage.py createsuperuser  # root/9999 recommended
python manage.py runserver
```

**Access**
- Candidate Login: `http://localhost/login/`
- Admin: `http://localhost/portal/`
- Profile: Click navbar icon or `/profile/`

**Load Testing**: `locust -f locustfile.py`

---

## 🌐 Key URLs

| Role | Page | URL |
|------|------|-----|
| **Public** | Home / Register | `/` or `/register/` |
| **Candidate** | Login / Dashboard / Profile / Results | `/login/`, `/dashboard/`, `/profile/`, `/result/<id>/` |
| **Admin** | Login / Portal / Results / Settings / Pending | `/portal/login/`, `/portal/`, `/portal/results/`, `/portal/exam-settings/`, `/portal/pending-registrations/` |

---

## 🧪 Tech Stack (Updated)
- **Backend**: Django 4.2.7, Celery (Redis broker), Gunicorn
- **Database**: SQLite (dev), PostgreSQL (Docker)
- **Frontend**: Bootstrap 5 + custom glassmorphism CSS/JS (light orange `#f59e0b`/`#fb923c` gradients, blurred backdrops, clean checkboxes with live search)
- **Excel**: openpyxl (bulk import/export + sample generator)
- **Deployment**: Docker Compose (multi-container: db, redis, celery, web x4, nginx), Nginx reverse proxy
- **Other**: Bootstrap Icons, pytz, management commands for samples

**Key Improvements in this version**:
- **UI**: Simple/clean — no cluttered native selects, small compact modals with blur, single orange password eye, light-orange profile/dashboard, softer confirmation colors.
- **Features**: Self-registration + approval, per-exam Passing % (admin configurable, no 70% default), fixed Selected filter (uses `data-status` + `__iexact`), profile with `date_taken` stats/ordering, navbar-driven profile.
- **Reliability**: Docker entrypoint now clears cache on every start (fixes reload/stale bytecode bugs), no more FieldErrors, robust filters/export, smaller modals.
- **Removed**: Global cutoff/threshold, question mixing/subject distribution, duplicate UI elements, heavy reds.

**Dummy Data**: Run management command — creates Excel templates for candidates/questions with proper headers.

---

*Updated May 2026 — All bugs fixed, UI modernized, ready for production/demo. Built with ❤️ for TalentHire.*

# SaaS Boilerplate 🚀

Production-grade FastAPI SaaS platform with JWT auth, Stripe billing, Celery background jobs, multi-tenancy, uploads, realtime notifications, analytics, API keys, and a lightweight Next.js frontend scaffold.

## Stack

| Layer | Tech |
|-------|------|
| Framework | FastAPI |
| Database | PostgreSQL or SQLite + SQLAlchemy (async) |
| Migrations | Alembic |
| Auth | JWT, refresh tokens, email verification, password reset, TOTP 2FA |
| Billing | Stripe + invoices + usage tracking |
| Jobs | Celery + Redis + webhook delivery |
| Multi-tenancy | Organizations + memberships |
| Files | S3-compatible presigned uploads |
| Realtime | WebSockets + in-app notifications |
| Tests | Pytest |
| Deploy | Docker + GitHub Actions + Next.js frontend scaffold |

## Week Roadmap

| Day | Feature |
|-----|---------|
| Day 1 ✅ | Project setup, PostgreSQL, SQLAlchemy, Alembic |
| Day 2 | Auth — Register, Login, JWT tokens |
| Day 3 | RBAC, Middleware, Rate limiting |
| Day 4 | Stripe billing, Subscriptions, Webhooks |
| Day 5 | Celery jobs, Email verification, Password reset |
| Day 6 | Pytest, Docker Compose, GitHub Actions CI |
| Day 7 | Admin routes, Logging, Health checks, Deploy |
| Phase 2 | Organizations, presigned uploads, WebSockets, plan rate limiting |
| Phase 3 | Audit logs, 2FA, API keys, notifications, webhooks, analytics, invoice generation |

## Quickstart

```bash
# Clone
git clone https://github.com/yash752-stack/SaaSboilerplate
cd SaaSboilerplate

# Setup env
cp .env.example .env
# Edit .env with your values

# Run with Docker
docker-compose up --build

# OR run locally
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Database Migrations

```bash
# Create migration
alembic revision --autogenerate -m "your message"

# Run migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

## Project Structure

```
SaaSboilerplate/
├── app/
│   ├── api/v1/endpoints/   # Route handlers
│   ├── core/               # Config, security, permissions, rate limits
│   ├── db/                 # DB engine, session
│   ├── models/             # SQLAlchemy models (users, orgs, audit, invoices, webhooks)
│   ├── schemas/            # Pydantic schemas
│   ├── services/           # Business logic
│   ├── websocket/          # Realtime connection manager
│   └── utils/              # Helpers
├── frontend/               # Next.js starter app
├── alembic/                # DB migrations
├── tests/                  # Pytest tests
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

## API Docs

Run the server and visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

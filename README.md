# SaaS Boilerplate 🚀

Production-grade FastAPI SaaS backend with PostgreSQL, JWT auth, Stripe billing, Celery background jobs, and Docker.

## Stack

| Layer | Tech |
|-------|------|
| Framework | FastAPI |
| Database | PostgreSQL + SQLAlchemy (async) |
| Migrations | Alembic |
| Auth | JWT (access + refresh tokens) |
| Billing | Stripe |
| Jobs | Celery + Redis |
| Tests | Pytest |
| Deploy | Docker + GitHub Actions |

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
│   ├── core/               # Config, security
│   ├── db/                 # DB engine, session
│   ├── models/             # SQLAlchemy models
│   ├── schemas/            # Pydantic schemas
│   ├── services/           # Business logic
│   └── utils/              # Helpers
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

.PHONY: install api worker beat test up down migrate frontend-install frontend-dev

install:
	pip install -r requirements.txt

api:
	uvicorn app.main:app --reload

worker:
	celery -A app.core.celery_app worker --loglevel=info -Q default,email,webhooks

beat:
	celery -A app.core.celery_app beat --loglevel=info

test:
	pytest

up:
	docker-compose up --build

down:
	docker-compose down

migrate:
	alembic upgrade head

frontend-install:
	cd frontend && npm install

frontend-dev:
	cd frontend && npm run dev

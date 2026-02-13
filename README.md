# USDA Market Report Monitor

Containerized FastAPI + worker/scheduler system that polls USDA AMS/MPR JSON reports, stores history in Postgres, and emails summaries via AWS SES.

## Requirements
- Docker + Docker Compose
- AWS SES configured with verified sender and recipients

## Quick Start (Local)
1. Copy env:
   - `cp .env.example .env`
2. Start services:
   - `docker-compose up --build`
3. Run migrations:
   - `docker-compose exec app alembic upgrade head`
4. Health check:
   - `curl http://localhost:8000/health`
5. UI:
   - `http://localhost:5173`

## Smoke Test
Run a single report once:
- `docker-compose exec app python -m app.smoke --report-id PK600_MORNING_CASH`

Optionally specify a date:
- `docker-compose exec app python -m app.smoke --report-id PK600_MORNING_CASH --report-date 2026-01-15`

## Endpoints
- `GET /health`
- `GET /reports`
- `GET /reports/{id}`
- `POST /run/{id}` (trigger a run immediately)
- `GET /api/health`
- `GET /api/reports`
- `GET /api/reports/{id}/runs`
- `GET /api/reports/{id}/latest`
- `POST /api/reports/{id}/run`
- `GET /api/logs`
- `GET /api/alerts`
- `GET /api/markets/contracts`
- `GET /api/markets/quote-symbols`
- `GET /api/markets/quotes`
- `GET /api/markets/history`
- `POST /api/markets/backfill/cost`
- `POST /api/markets/backfill/run`
- `GET /api/markets/backfill/jobs`

## AWS SES on EC2
- Do not set AWS keys in `.env` on EC2.
- Attach an IAM role to the instance with SES SendEmail permissions.
- Set `SES_REGION` and `SES_SENDER` env vars in the container.

## Configuration
Registry and schedules live in `app/registry.py`. It defines:
- Report ids, names, endpoints
- Time windows and cadence
- Whether prior day lookup is needed
- Recipient subscriptions

Market data services require:
- `DATABENTO_APIKEY` for historical OHLCV-1d backfill
- `API_NINJA_APIKEY` for current contract quotes

## Tests
Run tests locally:
- `docker-compose exec app pytest -q`

## Notes
- The system stores a full audit trail in Postgres.
- Runs are guarded by per-report advisory locks.
- Only `published_new` triggers email delivery.

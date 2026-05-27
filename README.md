# LeadFlow CRM

LeadFlow is a secure Flask + PostgreSQL CRM dashboard built for a polished student-friendly demo today and a real production path later. It keeps the dark, premium dashboard feel of your ledger app while focusing on lead capture, pipeline visibility, reminders, and future AI workflow automation.

## What ships now

- Secure registration and login with hardened session cookies, CSRF protection, rate limiting, and strong server-side validation
- Lead capture and editing with sanitized inputs, toast-based validation feedback, and ownership checks on every record mutation
- Pipeline dashboard with list and Kanban views, value tracking, stale lead reminders, overdue follow-up alerts, and lightweight AI stub actions
- PostgreSQL-first schema with SQLite fallback for free local testing and CI
- Docker, GitHub Actions, and a deployment shape that can grow into AWS, ECS, App Runner, or Render/Railway

## Planned AI workflow automations

The app already includes API hooks and storage fields for future workflow automations such as:

- Sponsorship email categorization
- Guest application scoring
- Customer inquiry routing
- Meeting note summarization
- Automated CRM enrichment
- Reporting generation

Those features are intentionally stubbed today so the contracts, UI, and tests are ready without forcing LLM spend yet.

## Stack

- Backend: Flask 3.1, psycopg2, Flask-Limiter
- Database: PostgreSQL in production, SQLite fallback for tests and quick local spins
- Security: bcrypt, bleach, email-validator, strict cookie/session settings
- Frontend: server-rendered HTML, modern CSS, vanilla JavaScript
- Ops: Gunicorn, Docker, GitHub Actions

## Local setup

1. Create a virtual environment and install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Copy the environment template:

```bash
cp .env.example .env
```

3. Set at minimum:

- `SECRET_KEY`
- `DATABASE_URL`

4. Run the app:

```bash
python run.py
```

5. Open [http://127.0.0.1:5000](http://127.0.0.1:5000)

The schema auto-initializes on startup for demo convenience.

## Docker

Run the app with Postgres locally:

```bash
docker compose up --build
```

Services:

- App: [http://127.0.0.1:5000](http://127.0.0.1:5000)
- Postgres: `localhost:5432`

## Testing

Run the full verification suite:

```bash
pytest
```

The tests use SQLite so CI stays fast and free-tier friendly.

## Security notes

- `HttpOnly` session cookie with `SameSite=Strict`
- `Secure` cookie support for production deployments
- CSRF double-submit protection for every mutating request
- Content Security Policy and strict response headers
- Rate limiting on auth and write-heavy endpoints
- Server-side sanitization for all lead and auth inputs
- No unsafe HTML rendering of user content in the frontend

## Deployment path

The current shape is suitable for a staged rollout:

1. Local Docker demo
2. GitHub Actions CI
3. Container deploy to Render/Railway/App Runner
4. Move to ECS Fargate + RDS when needed
5. Add real AI automations behind provider keys and spend controls

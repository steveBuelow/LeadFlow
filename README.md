# LeadFlow

A lightweight, self-contained CRM for small businesses. Manage leads, track pipeline, set follow-ups, and leverage AI-powered scoring — all in one secure, minimalist app.

**Live:** https://www.tryleadflow.io/

---

## See it in action

### Desktop App Shell — Sidebar + Analytics
<video controls width="100%" muted loop style="margin-bottom: 2rem; border-radius: 8px;">
  <source src="/static/videos/demo-desktop-app-shell.mp4" type="video/mp4">
  Your browser does not support the video tag.
</video>

<!-- TODO: Add desktop app shell demo MP4 (1920×1080 or 1280×720, 15–30 sec) showing:
  - Fixed sidebar (260px zinc-950) with nav
  - Main workspace with analytics cards (scrollable independently)
  - Open mobile hamburger drawer to show responsive behavior
-->

### Mobile Responsive Flow
<video controls width="100%" muted loop style="margin-bottom: 2rem; border-radius: 8px;">
  <source src="/static/videos/demo-mobile-responsive.mp4" type="video/mp4">
  Your browser does not support the video tag.
</video>

<!-- TODO: Add mobile responsive demo MP4 (375px viewport or similar, 15–30 sec) showing:
  - Full-screen mobile layout
  - Hamburger menu open/close
  - Form interaction and touch responsiveness
-->

### Lead Capture Flow
<video controls width="100%" muted loop style="margin-bottom: 2rem; border-radius: 8px;">
  <source src="/static/videos/demo-lead-capture.mp4" type="video/mp4">
  Your browser does not support the video tag.
</video>

<!-- TODO: Add lead capture demo MP4 (1920×1080, 15–30 sec) showing:
  - Fill out a new lead form
  - Submit and see validation/feedback
  - Toast notification
  - Lead appears in list/pipeline
-->

### Kanban Pipeline View
<video controls width="100%" muted loop style="margin-bottom: 2rem; border-radius: 8px;">
  <source src="/static/videos/demo-kanban-pipeline.mp4" type="video/mp4">
  Your browser does not support the video tag.
</video>

<!-- TODO: Add Kanban demo MP4 (1920×1080, 15–30 sec) showing:
  - Drag lead card between pipeline columns
  - Status updates in real-time
  - Filter or search interaction
-->

---

## What ships now

- **Lead management**: Create, edit, delete leads with rich fields (name, company, email, phone, value, custom notes)
- **Pipeline tracking**: Kanban-style drag-and-drop board; filter by status (New, Contacted, Qualified, Proposal, Closed-Won, Closed-Lost)
- **Follow-up scheduling**: Set next-followup dates, see overdue alerts on the dashboard
- **AI-powered insights** (opt-in): Auto-score leads, generate summaries, and categorize inbound via OpenAI/Anthropic
- **App Shell framework**: Fixed zinc-950 sidebar (260px), independently-scrolling workspace, mobile-responsive hamburger drawer
- **Analytics at a glance**: Pipeline total, won rate, new leads this week, overdue followups
- **One-click password reset**: Secure token-based flow with 1-hour expiry
- **Rate limiting & CSRF protection**: Built-in defense against abuse
- **Security headers**: Strict CSP, X-Frame-Options: DENY, HTTPS-only in production
- **Dark-mode UI**: Premium zinc and slate palette, accessible sans-serif typography

---

## Tech stack

- **Backend**: Flask 3.1 + Gunicorn
- **Database**: PostgreSQL (Supabase on Render) or SQLite (local dev)
- **Authentication**: Bcrypt (cost 13) password hashing, session-based with secure httponly cookies
- **Frontend**: Server-rendered HTML, premium CSS (App Shell, dark zinc/slate palette), vanilla JavaScript (no frameworks)
- **AI integration**: OpenAI / Anthropic APIs (optional, for lead scoring & summaries)
- **Infrastructure**: Deployed on Render with PostgreSQL; local development on SQLite
- **Rate limiting**: Flask-Limiter with configurable storage (memory or Redis)

---

## Local setup

### Requirements
- Python 3.9+
- PostgreSQL (for production) or SQLite (for development)
- Optional: OpenAI / Anthropic API key (for AI features)

### Installation

1. **Clone & enter the directory:**
   ```bash
   git clone https://github.com/yourusername/leadflow.git
   cd leadflow
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env with your DATABASE_URL, SECRET_KEY, and API keys
   ```

5. **Initialize the schema:**
   ```bash
   python -c "from db import init_schema; init_schema()"
   ```

6. **Run the development server:**
   ```bash
   python run.py
   ```
   Visit `http://localhost:5000` in your browser.

### Environment variables

| Variable | Example | Notes |
|----------|---------|-------|
| `FLASK_ENV` | `development` or `production` | Controls debug mode and security headers |
| `DATABASE_URL` | `postgresql://user:pass@host/dbname` | PostgreSQL or SQLite URL |
| `SECRET_KEY` | (random string) | **Required in production** |
| `SESSION_LIFETIME_DAYS` | `7` | Session expiry (default: 7) |
| `OPENAI_API_KEY` | (your key) | Optional; enables AI lead scoring |
| `ANTHROPIC_API_KEY` | (your key) | Optional; alternative to OpenAI |
| `RATELIMIT_STORAGE_URL` | `redis://localhost:6379` | Rate limit backend (default: in-memory) |

---

## Deployment

### Docker

Build and run:
```bash
docker build -t leadflow .
docker run -p 5000:5000 \
  -e FLASK_ENV=production \
  -e DATABASE_URL=postgresql://... \
  -e SECRET_KEY=your-secret-key \
  leadflow
```

### Render (Production)

1. Connect your GitHub repo to Render.
2. Create a PostgreSQL database and set `DATABASE_URL`.
3. Set environment variables in Render's dashboard.
4. Deploy with:
   ```bash
   gunicorn -w 4 -b 0.0.0.0:5000 "run:app"
   ```

---

## Project structure

```
leadflow/
├── app.py              # Flask app factory, routes registration, security headers
├── db.py               # Database abstraction (PostgreSQL + SQLite fallback)
├── models.py           # ORM-like data layer (users, leads, password resets)
├── extensions.py       # Flask extensions (rate limiter)
├── run.py              # Development entry point
├── requirements.txt    # Python dependencies
├── templates/          # Server-rendered HTML (app shell, forms, legal pages)
├── static/             # CSS, JavaScript, images
│   ├── css/
│   ├── js/
│   └── videos/         # Demo MP4 files (populated once ready)
├── schema.sql          # PostgreSQL schema and migrations
├── Dockerfile          # Container definition
├── .env.example        # Environment template
└── README.md           # This file
```

---

## Features in detail

### Lead Management
- Create leads with auto-generated timestamps
- Rich metadata: company, email, phone, deal value, source
- Custom notes and AI-generated summaries (if enabled)
- Soft-delete via CASCADE on user deletion

### Pipeline & Status
- Six predefined statuses: New, Contacted, Qualified, Proposal, Closed-Won, Closed-Lost
- Kanban board with drag-and-drop
- Status-based filtering and sorting
- Real-time updates with form validation

### Follow-up Tracking
- Set `next_followup` date per lead
- Dashboard alerts for overdue followups
- Stale lead detection (leads older than 7 days in "New" status)

### AI Integration (Optional)
- Send lead data to OpenAI or Anthropic for scoring (0–100)
- Auto-generate summaries (key info snapshot)
- Categorize leads by type or quality
- All AI requests are single-request (no storage on provider side)

### Security
- Bcrypt password hashing (cost 13)
- Session-based auth with secure httponly cookies
- CSRF protection on all state-changing requests
- Rate limiting (300 req/day, 60 req/hour by default)
- Strict CSP, X-Frame-Options: DENY, X-Content-Type-Options: nosniff
- HTTPS enforced in production (Strict-Transport-Security header)

### Responsive Design
- App Shell layout: fixed sidebar on desktop, hamburger drawer on mobile
- Touch-friendly forms and buttons
- Dark-mode theme (zinc-950 sidebar, slate accents)
- Accessible typography and color contrast

---

## Testing

Run the test suite:
```bash
pytest
```

Run with coverage:
```bash
pytest --cov=. --cov-report=html
```

Tests cover:
- User authentication and session management
- Lead CRUD operations
- Password reset flow
- Rate limiting
- Database pool management

---

## Security considerations

1. **Passwords**: Never stored as plaintext. Bcrypt ensures slow, salted hashing.
2. **Sessions**: HttpOnly, SameSite=Strict, Secure in production.
3. **CSRF tokens**: Generated per request, validated on POST/PUT/DELETE.
4. **Database queries**: Parameterized to prevent SQL injection.
5. **Rate limiting**: Applied to authentication endpoints to block brute-force.
6. **Content Security Policy**: Restricts inline scripts, external resource loading.
7. **Password resets**: Token-based with 1-hour expiry and single-use guarantee.

---

## Support

- **General support**: [leadflow.app1@gmail.com](mailto:leadflow.app1@gmail.com)
- **Privacy requests**: [Privacy request](mailto:leadflow.app1@gmail.com?subject=Privacy%20Request)
- **Security disclosure**: [Security disclosure](mailto:leadflow.app1@gmail.com?subject=Security%20Disclosure)

See `terms.html` and `privacy.html` for full legal details.

---

## License

TBD. Proprietary until otherwise specified.

---

**Built as a solo SaaS by Steve. Early-stage, feedback welcome.**
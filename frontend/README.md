## LeadFlow — Simple Lead & Messages Tracking Dashboard

## [Live Demo 🔗](https://leadflow-6avi.onrender.com/)

LeadFlow is a lightweight workflow tool designed to help small businesses organize and automate follow-up messages from platforms like Facebook Messenger and email.

It replaces scattered conversations with a simple, structured pipeline so no leads or customer requests slip through.

## Core Features

### Lead Capture (Manual Input)
* Add new leads from Facebook Messenger or email
* Store customer name, message, and source
* Simple, fast input designed for real-world use
* In-app follow-up reminders after >7 days

### Kanban Workflow System
* Organize leads into stages:
```
- New
- Contacted
- Qualified
- Closed
```
* Move leads between stages to track progress
* Light React/Vite kanban board UI (drag-and-drop workflow)

### Lead Management
* Attach notes to each lead
* Track follow-ups and ongoing conversations
* Maintain visibility across all customer interactions
* Optimistic UI updates (reverts on API failure)
* Better error surfacing for failed deletes/updates

### Auth + Sessions
* Create account + log in / log out
* Session persistence endpoint (`/me`) to keep you signed in

### Follow-ups
* Follow-up reminder list for “New” leads older than 7 days
* One-click follow-up message generator (simple templates)

## Tech stack
* **Backend:** Python, Flask
* **Database:** PostgreSQL
* **Frontend:** React + Vite (plus lightweight HTML/CSS/JS where useful)
* **Deployment:** Render

## Tests
Basic route tests included with `pytest` (auth guardrails, session behavior, add/delete flows).

## Future Improvements
* [ ] Automated message ingestion (Facebook / email APIs)
* [x] Notifications for follow-ups
* [x] Multi-user support
* [x] Analytics dashboard
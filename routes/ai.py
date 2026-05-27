from __future__ import annotations

import os

from flask import Blueprint, session

from extensions import limiter
from models import get_lead, update_ai_fields
from utils.security import clean, err, login_required, ok, require_csrf, SUMMARY_MAX


ai_bp = Blueprint("ai", __name__)
AI_CONFIGURED = bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("OPENAI_API_KEY"))


def _uid() -> int:
    return int(session["user_id"])


def _lead_or_error(lead_id: int):
    lead = get_lead(lead_id, _uid())
    if not lead:
        return None, err("Lead not found.", 404)
    return lead, None


@ai_bp.post("/leads/<int:lead_id>/score")
@login_required
@require_csrf
@limiter.limit("30 per hour")
def score_lead(lead_id: int):
    lead, error = _lead_or_error(lead_id)
    if error:
        return error

    score = 42 if AI_CONFIGURED else None
    if score is not None:
        update_ai_fields(lead_id, _uid(), score=score)
    return ok({
        "score": score,
        "stub": True,
        "message": "AI scoring is stubbed for now. Wire your LLM client here later.",
    })


@ai_bp.post("/leads/<int:lead_id>/categorize")
@login_required
@require_csrf
@limiter.limit("30 per hour")
def categorize(lead_id: int):
    lead, error = _lead_or_error(lead_id)
    if error:
        return error

    source = clean(lead.get("source") or "", 80).lower()
    message = clean(lead.get("message") or "", 240).lower()

    if "sponsor" in source or "sponsor" in message:
        category = "Sponsorship"
    elif "guest" in source or "guest" in message or "podcast" in message:
        category = "Guest Application"
    elif "support" in source or "help" in message:
        category = "Support Inquiry"
    else:
        category = "General Inquiry"

    update_ai_fields(lead_id, _uid(), category=category)
    return ok({
        "category": category,
        "stub": True,
        "message": "Lead categorized using the current stub workflow.",
    })


@ai_bp.post("/leads/<int:lead_id>/followup")
@login_required
@require_csrf
@limiter.limit("20 per hour")
def generate_followup(lead_id: int):
    lead, error = _lead_or_error(lead_id)
    if error:
        return error

    followup = (
        f"Hi {lead['name']},\n\n"
        f"Thanks for reaching out via {lead.get('source') or 'our CRM'}."
        " I wanted to follow up and see if you would be open to a quick conversation this week.\n\n"
        "Let me know what works best for you.\n\n"
        "Best,\n[Your Name]"
    )
    return ok({"followup_text": followup, "stub": True})


@ai_bp.post("/leads/<int:lead_id>/summarize")
@login_required
@require_csrf
@limiter.limit("20 per hour")
def summarize(lead_id: int):
    lead, error = _lead_or_error(lead_id)
    if error:
        return error
    message = lead.get("message") or ""
    notes = lead.get("notes") or ""
    if not message and not notes:
        return err("No message content to summarize.")

    source_text = message or notes
    summary = clean(source_text, SUMMARY_MAX)
    if len(summary) > 200:
        summary = f"{summary[:197]}..."
    update_ai_fields(lead_id, _uid(), summary=summary)
    return ok({"summary": summary, "stub": True})


@ai_bp.post("/leads/<int:lead_id>/route")
@login_required
@require_csrf
@limiter.limit("20 per hour")
def route_lead(lead_id: int):
    lead, error = _lead_or_error(lead_id)
    if error:
        return error

    suggestion = "Suggested owner: Partnerships queue" if (lead.get("source") or "").lower() == "sponsorship" else "Suggested owner: General CRM queue"
    return ok({"route": suggestion, "stub": True})

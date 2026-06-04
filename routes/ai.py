from __future__ import annotations

import logging
import os

from flask import Blueprint, session

from extensions import limiter
from models import get_lead, update_ai_fields
from utils.security import clean, err, login_required, ok, require_csrf, SUMMARY_MAX


ai_bp = Blueprint("ai", __name__)
logger = logging.getLogger(__name__)

# ── OpenAI client (optional) ───────────────────────────────────────────────
# Gracefully degrades to a stub if openai is not installed or key not set.
_openai_client = None
try:
    from openai import OpenAI as _OpenAI  # type: ignore
    _api_key = os.environ.get("OPENAI_API_KEY")
    if _api_key:
        _openai_client = _OpenAI(api_key=_api_key)
        logger.info("OpenAI client ready")
    else:
        logger.info("OPENAI_API_KEY not set — AI routes will use stubs")
except ImportError:
    logger.info("openai package not installed — AI routes will use stubs")

AI_CONFIGURED = _openai_client is not None

# ── Safety constants ───────────────────────────────────────────────────────
_AI_MODEL       = "gpt-4.1"
_AI_MAX_TOKENS  = 300   # maps to max_output_tokens in the Responses API
_CTX_CHAR_LIMIT = 2_000   # max chars of lead context sent to OpenAI


def _uid() -> int:
    return int(session["user_id"])


def _lead_or_error(lead_id: int):
    lead = get_lead(lead_id, _uid())
    if not lead:
        return None, err("Lead not found.", 404)
    return lead, None


def _build_lead_context(lead: dict) -> str:
    """Build a plain-text context string from lead fields, capped at _CTX_CHAR_LIMIT."""
    parts: list[str] = []
    if lead.get("name"):     parts.append(f"Contact: {lead['name']}")
    if lead.get("company"):  parts.append(f"Company: {lead['company']}")
    if lead.get("source"):   parts.append(f"Source: {lead['source']}")
    if lead.get("status"):   parts.append(f"Pipeline stage: {lead['status']}")
    if lead.get("message"):  parts.append(f"Initial message: {lead['message']}")
    if lead.get("notes"):    parts.append(f"Notes: {lead['notes']}")
    # clean() strips HTML/control chars; hard cap at 2 000 chars
    return clean("\n".join(parts), _CTX_CHAR_LIMIT)


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
        "stub": not AI_CONFIGURED,
        "message": "AI scoring stub — wire your LLM here." if not AI_CONFIGURED else "Lead scored.",
    })


@ai_bp.post("/leads/<int:lead_id>/categorize")
@login_required
@require_csrf
@limiter.limit("30 per hour")
def categorize(lead_id: int):
    lead, error = _lead_or_error(lead_id)
    if error:
        return error

    source  = clean(lead.get("source")  or "", 80).lower()
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
    return ok({"category": category, "stub": True})


@ai_bp.post("/leads/<int:lead_id>/followup")
@login_required
@require_csrf
@limiter.limit("20 per hour")
def generate_followup(lead_id: int):
    lead, error = _lead_or_error(lead_id)
    if error:
        return error

    if _openai_client:
        # ── Real OpenAI path ───────────────────────────────────────────────
        context = _build_lead_context(lead)

        prompt = (
            "You are a professional business development assistant.\n"
            "Write a brief, warm, personalized follow-up message for the lead below.\n"
            "Requirements:\n"
            "- Under 120 words\n"
            "- Professional yet friendly tone\n"
            "- One clear call-to-action (e.g. schedule a call, reply with interest)\n"
            "- Do NOT include a subject line — write only the message body\n\n"
            f"Lead context:\n{context}"
        )

        try:
            response = _openai_client.responses.create(
                model=_AI_MODEL,
                input=prompt,
                max_output_tokens=_AI_MAX_TOKENS,
                store=True,
            )
            followup_text = response.output_text.strip()
        except Exception:
            logger.exception("OpenAI API error generating follow-up for lead %s", lead_id)
            return err("AI service is temporarily unavailable. Please try again shortly.", 503)

        return ok({"followup_text": followup_text, "stub": False})

    # ── Stub fallback (no API key) ─────────────────────────────────────────
    followup_text = (
        f"Hi {lead['name']},\n\n"
        f"Thanks for reaching out via {lead.get('source') or 'our CRM'}. "
        "I wanted to follow up and see if you'd be open to a quick conversation this week.\n\n"
        "Let me know what works best for you.\n\n"
        "Best,\n[Your Name]"
    )
    return ok({"followup_text": followup_text, "stub": True})


@ai_bp.post("/leads/<int:lead_id>/summarize")
@login_required
@require_csrf
@limiter.limit("20 per hour")
def summarize(lead_id: int):
    lead, error = _lead_or_error(lead_id)
    if error:
        return error
    message = lead.get("message") or ""
    notes   = lead.get("notes")   or ""
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

    src = (lead.get("source") or "").lower()
    suggestion = (
        "Suggested owner: Partnerships queue"
        if "sponsor" in src
        else "Suggested owner: General CRM queue"
    )
    return ok({"route": suggestion, "stub": True})

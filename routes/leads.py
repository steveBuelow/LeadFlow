from __future__ import annotations

import logging

from flask import Blueprint, request, session

from extensions import limiter
from models import (
    create_lead,
    delete_lead,
    get_lead,
    lead_stats,
    list_leads,
    overdue_followups,
    stale_leads,
    update_lead,
    update_lead_status,
)
from utils.security import clean_status, err, login_required, ok, require_csrf, validate_lead


leads_bp = Blueprint("leads", __name__)
logger = logging.getLogger(__name__)


def _uid() -> int:
    return int(session["user_id"])


@leads_bp.get("/")
@login_required
def list_all():
    status = request.args.get("status")
    return ok({"leads": list_leads(_uid(), status=status)})


@leads_bp.get("/stats")
@login_required
def stats():
    return ok({"stats": lead_stats(_uid())})


@leads_bp.get("/reminders")
@login_required
def reminders():
    return ok({"stale": stale_leads(_uid(), days=7), "overdue": overdue_followups(_uid())})


@leads_bp.post("/")
@login_required
@require_csrf
@limiter.limit("60 per hour")
def create():
    cleaned, errors = validate_lead(request.get_json(silent=True) or {})
    if errors:
        return err(errors[0])
    try:
        lead_id = create_lead(cleaned, _uid())
    except Exception:
        logger.exception("Lead creation failed")
        return err("Could not save lead. Please try again.", 500)
    return ok({"id": lead_id, "message": "Lead added!"}, 201)


@leads_bp.get("/<int:lead_id>")
@login_required
def get_one(lead_id: int):
    lead = get_lead(lead_id, _uid())
    if not lead:
        return err("Lead not found.", 404)
    return ok({"lead": lead})


@leads_bp.put("/<int:lead_id>")
@login_required
@require_csrf
def update(lead_id: int):
    cleaned, errors = validate_lead(request.get_json(silent=True) or {})
    if errors:
        return err(errors[0])
    if not update_lead(lead_id, _uid(), cleaned):
        return err("Lead not found or you don't own it.", 404)
    return ok({"message": "Lead updated."})


@leads_bp.patch("/<int:lead_id>/status")
@login_required
@require_csrf
@limiter.limit("120 per hour")
def patch_status(lead_id: int):
    status = clean_status((request.get_json(silent=True) or {}).get("status", ""))
    if not status:
        return err("Invalid status value.")
    if not update_lead_status(lead_id, _uid(), status):
        return err("Lead not found.", 404)
    return ok({"message": f"Moved to {status}.", "status": status})


@leads_bp.delete("/<int:lead_id>")
@login_required
@require_csrf
def delete(lead_id: int):
    if not delete_lead(lead_id, _uid()):
        return err("Lead not found.", 404)
    return ok({"message": "Lead deleted."})

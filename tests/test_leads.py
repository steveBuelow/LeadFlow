from __future__ import annotations

from datetime import timedelta

from conftest import issue_csrf, register_and_login
from models import execute_write, utc_now


def test_create_validation_and_listing(client):
    register_and_login(client)
    csrf = issue_csrf(client)

    invalid = client.post(
        "/leads/",
        json={"name": "A", "email": "not-an-email", "value": "-50"},
        headers={"X-CSRF-Token": csrf},
    )
    assert invalid.status_code == 400

    valid = client.post(
        "/leads/",
        json={
            "name": "Taylor Brooks",
            "company": "Northwind Media",
            "email": "taylor@example.com",
            "phone": "555-0101",
            "source": "Sponsorship",
            "status": "New",
            "priority": "high",
            "value": "1500.00",
            "next_followup": "2026-05-28",
            "message": "<b>Interested</b> in sponsorship packages.",
            "notes": "<script>alert(1)</script>High intent lead.",
        },
        headers={"X-CSRF-Token": csrf},
    )
    assert valid.status_code == 201

    listing = client.get("/leads/")
    payload = listing.get_json()
    assert listing.status_code == 200
    assert len(payload["leads"]) == 1
    lead = payload["leads"][0]
    assert lead["name"] == "Taylor Brooks"
    assert lead["message"] == "Interested in sponsorship packages."
    assert "script" not in (lead["notes"] or "").lower()


def test_update_delete_and_ownership_boundaries(client):
    register_and_login(client)
    csrf = issue_csrf(client)

    created = client.post(
        "/leads/",
        json={"name": "Alex Rivera", "status": "New", "priority": "medium"},
        headers={"X-CSRF-Token": csrf},
    )
    lead_id = created.get_json()["id"]

    updated = client.put(
        f"/leads/{lead_id}",
        json={
            "name": "Alex Rivera",
            "company": "Launch Labs",
            "email": "alex@launchlabs.io",
            "phone": "555-2121",
            "source": "Website",
            "status": "Qualified",
            "priority": "high",
            "value": "4200",
            "next_followup": "2026-06-01",
            "message": "Asked for pricing",
            "notes": "Warm lead",
        },
        headers={"X-CSRF-Token": csrf},
    )
    assert updated.status_code == 200

    other = client.application.test_client()
    register_and_login(other, username="other_user", email="other@example.com")
    other_csrf = issue_csrf(other)

    blocked = other.put(
        f"/leads/{lead_id}",
        json={"name": "Intrusion attempt", "status": "Closed-Won", "priority": "low"},
        headers={"X-CSRF-Token": other_csrf},
    )
    assert blocked.status_code == 404

    deleted = client.delete(f"/leads/{lead_id}", headers={"X-CSRF-Token": csrf})
    assert deleted.status_code == 200

    missing = client.get(f"/leads/{lead_id}")
    assert missing.status_code == 404


def test_status_patch_stats_and_reminders(client):
    register_and_login(client)
    csrf = issue_csrf(client)

    first = client.post(
        "/leads/",
        json={
            "name": "Jordan Lee",
            "source": "Sponsorship",
            "status": "New",
            "priority": "high",
            "value": "3000",
            "next_followup": "2026-05-20",
        },
        headers={"X-CSRF-Token": csrf},
    )
    first_id = first.get_json()["id"]

    second = client.post(
        "/leads/",
        json={
            "name": "Morgan Reed",
            "status": "Proposal",
            "priority": "medium",
            "value": "1800",
            "next_followup": "2026-05-27",
        },
        headers={"X-CSRF-Token": csrf},
    )
    second_id = second.get_json()["id"]

    stale_timestamp = (utc_now() - timedelta(days=10)).isoformat().replace("+00:00", "Z")
    execute_write("UPDATE leads SET created_at = %s, updated_at = %s WHERE id = %s", (stale_timestamp, stale_timestamp, first_id))

    patched = client.patch(
        f"/leads/{second_id}/status",
        json={"status": "Closed-Won"},
        headers={"X-CSRF-Token": csrf},
    )
    assert patched.status_code == 200
    assert patched.get_json()["status"] == "Closed-Won"

    stats = client.get("/leads/stats").get_json()["stats"]
    assert stats["total"] == 2
    assert stats["new_count"] == 1
    assert stats["closed_won"] == 1
    assert stats["pipeline_total"] == 4800.0
    assert stats["pipeline_won"] == 1800.0
    assert stats["overdue_followups"] == 1

    reminders = client.get("/leads/reminders").get_json()
    assert len(reminders["stale"]) == 1
    assert reminders["stale"][0]["name"] == "Jordan Lee"
    assert len(reminders["overdue"]) == 1


def test_ai_stub_endpoints(client):
    register_and_login(client)
    csrf = issue_csrf(client)

    created = client.post(
        "/leads/",
        json={
            "name": "Cameron Tate",
            "source": "Sponsorship",
            "status": "New",
            "priority": "medium",
            "message": "Interested in sponsoring three episodes and wants a media kit.",
        },
        headers={"X-CSRF-Token": csrf},
    )
    lead_id = created.get_json()["id"]

    categorize = client.post(f"/ai/leads/{lead_id}/categorize", headers={"X-CSRF-Token": csrf})
    assert categorize.status_code == 200
    assert categorize.get_json()["category"] == "Sponsorship"

    score = client.post(f"/ai/leads/{lead_id}/score", headers={"X-CSRF-Token": csrf})
    assert score.status_code == 200
    assert "score" in score.get_json()

    followup = client.post(f"/ai/leads/{lead_id}/followup", headers={"X-CSRF-Token": csrf})
    assert followup.status_code == 200
    assert "followup_text" in followup.get_json()

    summary = client.post(f"/ai/leads/{lead_id}/summarize", headers={"X-CSRF-Token": csrf})
    assert summary.status_code == 200
    assert "summary" in summary.get_json()

    route = client.post(f"/ai/leads/{lead_id}/route", headers={"X-CSRF-Token": csrf})
    assert route.status_code == 200
    assert "Suggested owner" in route.get_json()["route"]

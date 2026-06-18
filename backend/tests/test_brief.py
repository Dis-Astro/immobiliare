"""
Tests for Brief AI endpoints (iteration_6).
Covers: GET /brief/config, PUT /brief/config, POST /brief/preview, POST /brief/send-now.
SMTP is NOT configured in dev: send-now must return status='error' and persist last_status.
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8001").rstrip("/")
API = f"{BASE_URL}/api/v1"

ADMIN_EMAIL = "r.disante@impresacingoli.it"
ADMIN_PWD = "Cinguli26!!"


@pytest.fixture(scope="module")
def token():
    r = requests.post(
        f"{API}/auth/login",
        data={"username": ADMIN_EMAIL, "password": ADMIN_PWD},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=15,
    )
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module", autouse=True)
def reset_brief_config(auth_headers):
    """Ensure clean state at start and at end (recipients=[], enabled=False)."""
    requests.put(
        f"{API}/brief/config",
        json={"enabled": False, "recipients": []},
        headers=auth_headers,
        timeout=15,
    )
    yield
    requests.put(
        f"{API}/brief/config",
        json={"enabled": False, "recipients": []},
        headers=auth_headers,
        timeout=15,
    )


# ---- GET /brief/config ----
def test_get_config_default(auth_headers):
    r = requests.get(f"{API}/brief/config", headers=auth_headers, timeout=15)
    assert r.status_code == 200
    body = r.json()
    assert body["enabled"] is False
    assert isinstance(body["recipients"], list)
    assert body["include_rate"] is True
    assert body["include_ape"] is True
    assert body["include_contratti"] is True
    assert body["include_interventi"] is True
    assert "cron_hour" in body and "cron_minute" in body
    # 'key' must be stripped
    assert "key" not in body


# ---- PUT /brief/config ----
def test_put_config_updates_and_persists(auth_headers):
    payload = {
        "enabled": True,
        "cron_hour": 9,
        "cron_minute": 15,
        "recipients": ["test1@example.com", "test2@example.com"],
        "include_rate": False,
        "include_ape": True,
        "include_contratti": True,
        "include_interventi": False,
    }
    r = requests.put(f"{API}/brief/config", json=payload, headers=auth_headers, timeout=15)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["enabled"] is True
    assert body["cron_hour"] == 9
    assert body["cron_minute"] == 15
    assert "test1@example.com" in body["recipients"]
    assert body["include_rate"] is False
    assert body["include_interventi"] is False

    # Persistence: GET again
    g = requests.get(f"{API}/brief/config", headers=auth_headers, timeout=15)
    assert g.status_code == 200
    gbody = g.json()
    assert gbody["cron_hour"] == 9
    assert "test1@example.com" in gbody["recipients"]


def test_put_config_partial_update(auth_headers):
    # Only update enabled
    r = requests.put(f"{API}/brief/config", json={"enabled": False}, headers=auth_headers, timeout=15)
    assert r.status_code == 200
    body = r.json()
    assert body["enabled"] is False
    # cron_hour previously set to 9 should be preserved
    assert body["cron_hour"] == 9


def test_put_config_invalid_email(auth_headers):
    r = requests.put(
        f"{API}/brief/config",
        json={"recipients": ["not-an-email"]},
        headers=auth_headers,
        timeout=15,
    )
    # pydantic EmailStr should reject => 422
    assert r.status_code == 422


# ---- POST /brief/preview ----
def test_preview_returns_html_text_stats(auth_headers):
    r = requests.post(f"{API}/brief/preview", headers=auth_headers, timeout=60)
    assert r.status_code == 200, r.text
    body = r.json()
    assert "summary_html" in body
    assert "summary_text" in body
    assert "stats" in body
    assert isinstance(body["summary_html"], str)
    assert len(body["summary_html"]) > 100  # non-empty
    assert "<html>" in body["summary_html"].lower() or "<!doctype" in body["summary_html"].lower()
    stats = body["stats"]
    for k in ("rate_in_ritardo", "ape_in_scadenza", "contratti_in_scadenza", "interventi_aperti"):
        assert k in stats
        assert isinstance(stats[k], int)


# ---- POST /brief/send-now ----
def test_send_now_no_recipients_returns_400(auth_headers):
    # Reset to empty recipients
    requests.put(
        f"{API}/brief/config",
        json={"recipients": []},
        headers=auth_headers,
        timeout=15,
    )
    r = requests.post(f"{API}/brief/send-now", headers=auth_headers, timeout=60)
    assert r.status_code == 400
    body = r.json()
    assert "destinatari" in (body.get("detail", "") or "").lower()


def test_send_now_smtp_not_configured_returns_error_status(auth_headers):
    # Configure recipients
    requests.put(
        f"{API}/brief/config",
        json={"recipients": ["sample@example.com"]},
        headers=auth_headers,
        timeout=15,
    )
    r = requests.post(f"{API}/brief/send-now", headers=auth_headers, timeout=120)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "error"
    assert body["sent_count"] == 0
    assert body["total_recipients"] == 1
    assert isinstance(body.get("errors"), list) and len(body["errors"]) >= 1
    # error message should reference SMTP non configurato
    err = body["errors"][0].lower()
    assert "smtp" in err

    # Verify last_sent_at / last_status persisted
    g = requests.get(f"{API}/brief/config", headers=auth_headers, timeout=15)
    gb = g.json()
    assert gb.get("last_status") == "error"
    assert gb.get("last_sent_at") is not None
    assert gb.get("last_error") is not None


# ---- Celery task importability ----
def test_celery_task_registered():
    """Ensure tasks.brief.send_morning_brief is importable and registered."""
    import sys
    sys.path.insert(0, "/app/backend")
    from tasks.brief import send_morning_brief  # noqa: F401
    from celery_app import celery_app
    assert "tasks.brief.send_morning_brief" in celery_app.tasks
    assert "send-morning-brief-hourly-check" in celery_app.conf.beat_schedule


# ---- Regression: existing endpoints still work ----
@pytest.mark.parametrize("path", [
    "/auth/me",
    "/immobili",
    "/contratti",
    "/soggetti",
    "/ape",
    "/audit",
    "/reports/executive",
])
def test_regression_existing_endpoints(auth_headers, path):
    r = requests.get(f"{API}{path}", headers=auth_headers, timeout=30)
    assert r.status_code == 200, f"{path} returned {r.status_code}: {r.text[:200]}"

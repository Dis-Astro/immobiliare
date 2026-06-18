"""
EstateWise P1 Features tests:
- Reports: status, contratto/verbale PDF generation (WeasyPrint real)
- Notifications: trigger-check ape, check_ape_scadenza task callable
- Beat schedule includes check-ape-scadenza-daily
"""
import os
import pytest
import requests
from datetime import date, timedelta

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8001").rstrip("/")
API = f"{BASE_URL}/api/v1"


@pytest.fixture(scope="module")
def token():
    r = requests.post(
        f"{API}/auth/login",
        data={"username": "admin@estatewise.it", "password": "admin123"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=20,
    )
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


# ---- Reports ----
class TestReports:
    def test_reports_status_pdf_available(self, auth_headers):
        r = requests.get(f"{API}/reports/status", headers=auth_headers, timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["pdf_available"] is True

    def test_contratto_pdf_generation(self, auth_headers):
        rl = requests.get(f"{API}/contratti", headers=auth_headers, timeout=15)
        assert rl.status_code == 200
        contratti = rl.json()
        if not contratti:
            pytest.skip("No contratti in DB")
        cid = contratti[0]["id"]
        r = requests.get(f"{API}/reports/contratto/{cid}/pdf", headers=auth_headers, timeout=60)
        assert r.status_code == 200, f"Status {r.status_code}: {r.text[:300]}"
        assert r.headers.get("content-type", "").startswith("application/pdf")
        # PDF magic header
        assert r.content[:4] == b"%PDF", "Response is not a real PDF"
        assert len(r.content) > 1000, "PDF too small to be valid"

    def test_verbale_pdf_generation(self, auth_headers):
        rl = requests.get(f"{API}/verbali", headers=auth_headers, timeout=15)
        if rl.status_code != 200:
            pytest.skip("verbali endpoint not accessible")
        verbali = rl.json()
        if not verbali:
            pytest.skip("No verbali in DB")
        vid = verbali[0]["id"]
        r = requests.get(f"{API}/reports/verbale/{vid}/pdf", headers=auth_headers, timeout=60)
        assert r.status_code == 200, r.text[:300]
        assert r.content[:4] == b"%PDF"


# ---- APE Celery task ----
class TestApeCheckTask:
    def test_check_ape_scadenza_callable(self):
        """Direct call (sync) of the celery task function."""
        import sys
        sys.path.insert(0, "/app/backend")
        from tasks.notifications import check_ape_scadenza
        result = check_ape_scadenza()
        assert "APE scadenze controllate" in result or "notifiche" in result

    def test_beat_schedule_has_ape(self):
        import sys
        sys.path.insert(0, "/app/backend")
        from celery_app import celery_app
        sched = celery_app.conf.beat_schedule
        assert "check-ape-scadenza-daily" in sched
        entry = sched["check-ape-scadenza-daily"]
        assert entry["task"] == "tasks.notifications.check_ape_scadenza"

    def test_check_ape_marks_expired(self, auth_headers):
        """Create an APE expired in the past, run task, check stato updated to 'scaduto'."""
        # Need a unita
        ru = requests.get(f"{API}/unita", headers=auth_headers, timeout=15)
        if ru.status_code != 200 or not ru.json():
            pytest.skip("No unita to attach APE")
        unita_id = ru.json()[0]["id"]

        scaduto_iso = (date.today() - timedelta(days=10)).isoformat()
        emiss_iso = (date.today() - timedelta(days=20)).isoformat()
        payload = {
            "unita_id": unita_id,
            "classe_energetica": "C",
            "zona_climatica": "E",
            "data_emissione": emiss_iso,
            "data_scadenza": scaduto_iso,
            "certificatore_nome": "TEST_certificatore",
            "epgl_nren": 100.0,
            "superficie_utile": 80.0,
            "note": "TEST_p1",
        }
        rc = requests.post(f"{API}/ape", headers=auth_headers, json=payload, timeout=20)
        assert rc.status_code in (200, 201), rc.text
        ape_id = rc.json()["id"]

        try:
            # Trigger task synchronously
            import sys
            sys.path.insert(0, "/app/backend")
            from tasks.notifications import check_ape_scadenza
            check_ape_scadenza()

            # Verify stato is now 'scaduto'
            rg = requests.get(f"{API}/ape/{ape_id}", headers=auth_headers, timeout=15)
            assert rg.status_code == 200
            assert rg.json()["stato"] == "scaduto"

            # Verify a notification exists with idempotency_key for ape_scaduto
            from pymongo import MongoClient
            mongo = MongoClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))
            db = mongo[os.environ.get("DB_NAME", "test_database")]
            notif = db.notifiche.find_one({"ref_id": ape_id, "tipo": "ape_scaduto"})
            assert notif is not None, "No notification created for expired APE"
            assert notif.get("idempotency_key", "").startswith("ape_scaduto:")
        finally:
            requests.delete(f"{API}/ape/{ape_id}", headers=auth_headers, timeout=15)


# ---- Trigger-check endpoint ----
class TestTriggerCheck:
    def test_trigger_check_ape(self, auth_headers):
        r = requests.post(f"{API}/notifiche/trigger-check?check_type=ape", headers=auth_headers, timeout=30)
        assert r.status_code == 200, r.text
        body = r.json()
        assert "Check" in body.get("message", "") or "triggerato" in body.get("message", "")

    def test_trigger_check_all(self, auth_headers):
        r = requests.post(f"{API}/notifiche/trigger-check?check_type=all", headers=auth_headers, timeout=60)
        assert r.status_code == 200, r.text


# ---- Regression endpoints used by new frontend pages ----
class TestRegressionEndpoints:
    @pytest.mark.parametrize("path", [
        "/verbali", "/documenti", "/interventi",
        "/immobili", "/unita", "/soggetti", "/contratti", "/notifiche",
        "/ape", "/ai/config",
    ])
    def test_get_endpoint_ok(self, auth_headers, path):
        r = requests.get(f"{API}{path}", headers=auth_headers, timeout=20)
        assert r.status_code == 200, f"{path}: {r.status_code} {r.text[:200]}"

    def test_documenti_in_scadenza_filter(self, auth_headers):
        r = requests.get(f"{API}/documenti/in-scadenza?giorni=90", headers=auth_headers, timeout=15)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

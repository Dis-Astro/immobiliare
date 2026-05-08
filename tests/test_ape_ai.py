"""
Test suite for EstateWise APE + AI integration (iteration 3).
Backend: /api/v1/ape/* and /api/v1/ai/*
Credentials: admin@estatewise.it / admin123
"""
import os
import io
import time
import pytest
import requests
from datetime import date, timedelta

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://energy-audit-demo-1.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api/v1"

# ---------- fixtures ----------
@pytest.fixture(scope="session")
def token():
    r = requests.post(
        f"{API}/auth/login",
        data={"username": "admin@estatewise.it", "password": "admin123"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=20,
    )
    assert r.status_code == 200, f"login failed {r.status_code} {r.text}"
    return r.json()["access_token"]


@pytest.fixture(scope="session")
def H(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="session")
def unita_id(H):
    r = requests.get(f"{API}/unita", headers=H, timeout=15)
    assert r.status_code == 200
    items = r.json()
    assert len(items) > 0, "Need at least one unita to run APE tests"
    return items[0]["id"]


# ============== APE TESTS ==============
class TestApe:
    created_id = None

    def test_01_list_ape(self, H):
        r = requests.get(f"{API}/ape", headers=H, timeout=15)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_02_stats_dashboard(self, H):
        r = requests.get(f"{API}/ape/stats/dashboard", headers=H, timeout=15)
        assert r.status_code == 200
        d = r.json()
        for k in ("total", "validi", "in_scadenza", "scaduti", "by_classe"):
            assert k in d
        assert isinstance(d["by_classe"], dict)

    def test_03_create_ape(self, H, unita_id):
        payload = {
            "unita_id": unita_id,
            "classe_energetica": "B",
            "data_emissione": date.today().isoformat(),
            "data_scadenza": (date.today() + timedelta(days=365 * 10)).isoformat(),
            "certificatore_nome": "TEST_Mario Rossi",
            "certificatore_albo": "ALBO123",
            "zona_climatica": "E",
            "epgl_nren": 75.5,
            "superficie_utile_mq": 90.0,
            "note": "TEST APE",
        }
        r = requests.post(f"{API}/ape", json=payload, headers=H, timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["classe_energetica"] == "B"
        assert d["unita_id"] == unita_id
        assert d["stato"] in ("valido", "in_scadenza")
        assert "id" in d
        TestApe.created_id = d["id"]

    def test_04_get_ape(self, H):
        assert TestApe.created_id
        r = requests.get(f"{API}/ape/{TestApe.created_id}", headers=H, timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d["id"] == TestApe.created_id
        assert "giorni_alla_scadenza" in d

    def test_05_update_ape(self, H):
        assert TestApe.created_id
        r = requests.put(
            f"{API}/ape/{TestApe.created_id}",
            json={"note": "TEST aggiornata", "classe_energetica": "A1"},
            headers=H, timeout=15,
        )
        assert r.status_code == 200, r.text
        assert r.json()["classe_energetica"] == "A1"
        assert r.json()["note"] == "TEST aggiornata"

    def test_06_rimanda_scadenza(self, H):
        assert TestApe.created_id
        new_date = (date.today() + timedelta(days=365 * 11)).isoformat()
        r = requests.put(
            f"{API}/ape/{TestApe.created_id}/scadenza",
            json={"nuova_scadenza": new_date, "motivazione": "TEST proroga"},
            headers=H, timeout=15,
        )
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["data_scadenza"][:10] == new_date
        assert len(d.get("storico_modifiche", [])) >= 1
        last = d["storico_modifiche"][-1]
        assert last["azione"] == "rimando_scadenza"
        assert last["motivazione"] == "TEST proroga"

    def test_07_in_scadenza(self, H):
        r = requests.get(f"{API}/ape/in-scadenza?giorni=90", headers=H, timeout=15)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_08_scaduti(self, H):
        r = requests.get(f"{API}/ape/scaduti", headers=H, timeout=15)
        assert r.status_code == 200

    def test_09_by_unita(self, H, unita_id):
        r = requests.get(f"{API}/ape/by-unita/{unita_id}", headers=H, timeout=15)
        assert r.status_code == 200
        assert any(a["id"] == TestApe.created_id for a in r.json())

    def test_10_upload_ape_file(self, H, unita_id):
        """Crea APE con upload file -> verifica che marchi precedente come sostituito."""
        pdf_bytes = b"%PDF-1.4\n1 0 obj<<>>endobj\n%%EOF\n"
        files = {"file": ("test_ape.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
        data = {
            "unita_id": unita_id,
            "classe_energetica": "C",
            "data_emissione": date.today().isoformat(),
            "data_scadenza": (date.today() + timedelta(days=365 * 10)).isoformat(),
            "certificatore_nome": "TEST_Cert Upload",
            "zona_climatica": "E",
        }
        r = requests.post(f"{API}/ape/upload", files=files, data=data, headers=H, timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["file_name"] == "test_ape.pdf"
        assert d["file_size_bytes"] > 0
        new_id = d["id"]

        # Old APE should be marked sostituito
        r2 = requests.get(f"{API}/ape/{TestApe.created_id}", headers=H, timeout=15)
        assert r2.status_code == 200
        # The "by_unita" returns all incl. sostituito; the previously created one should now be sostituito
        assert r2.json()["stato"] == "sostituito"

        TestApe.created_id = new_id  # for replace-file test below

    def test_11_replace_file(self, H):
        assert TestApe.created_id
        new_pdf = b"%PDF-1.5\n%new content\n%%EOF\n"
        files = {"file": ("replaced.pdf", io.BytesIO(new_pdf), "application/pdf")}
        data = {"motivazione": "TEST sostituzione file"}
        r = requests.put(
            f"{API}/ape/{TestApe.created_id}/file",
            files=files, data=data, headers=H, timeout=30,
        )
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["file_name"] == "replaced.pdf"
        assert any(s["azione"] == "sostituzione_file" for s in d.get("storico_modifiche", []))

    def test_99_delete_ape(self, H):
        if TestApe.created_id:
            r = requests.delete(f"{API}/ape/{TestApe.created_id}", headers=H, timeout=15)
            assert r.status_code == 200


# ============== AI TESTS ==============
class TestAi:
    session_id = None

    def test_01_get_config(self, H):
        r = requests.get(f"{API}/ai/config", headers=H, timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert "provider" in d
        assert "available_external_models" in d
        assert isinstance(d["available_external_models"], list)
        assert len(d["available_external_models"]) > 0

    def test_02_update_config_to_openai(self, H):
        """Cambia provider a openai per poter testare le chiamate AI."""
        r = requests.put(
            f"{API}/ai/config",
            json={"provider": "openai", "external_model": "gpt-5.2", "enabled": True},
            headers=H, timeout=15,
        )
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["provider"] == "openai"
        assert d["external_model"] == "gpt-5.2"

    def test_03_test_connection(self, H):
        r = requests.post(f"{API}/ai/test-connection", headers=H, timeout=60)
        assert r.status_code == 200
        d = r.json()
        # potrebbe fallire se key invalida; segnaliamo ma non blocchiamo se è connection issue
        if not d.get("success"):
            pytest.skip(f"AI test-connection failed: {d.get('error')}")
        assert d["provider"] in ("openai", "anthropic", "gemini")
        assert "latency_ms" in d

    def test_04_chat_new_session(self, H):
        r = requests.post(
            f"{API}/ai/chat",
            json={"session_id": None, "message": "Ciao, rispondi solo: PONG", "include_context": False},
            headers=H, timeout=90,
        )
        assert r.status_code == 200, r.text
        d = r.json()
        assert "session_id" in d
        assert "assistant_message" in d
        assert d["assistant_message"]["content"]
        assert "metadata" in d["assistant_message"]
        TestAi.session_id = d["session_id"]

    def test_05_chat_multi_turn(self, H):
        assert TestAi.session_id
        r = requests.post(
            f"{API}/ai/chat",
            json={"session_id": TestAi.session_id, "message": "Ricordi cosa ti ho appena chiesto?", "include_context": False},
            headers=H, timeout=90,
        )
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["session_id"] == TestAi.session_id

    def test_06_list_sessions(self, H):
        r = requests.get(f"{API}/ai/sessions", headers=H, timeout=15)
        assert r.status_code == 200
        sessions = r.json()
        assert any(s["id"] == TestAi.session_id for s in sessions)

    def test_07_session_messages(self, H):
        assert TestAi.session_id
        r = requests.get(f"{API}/ai/sessions/{TestAi.session_id}/messages", headers=H, timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert "session" in d and "messages" in d
        # 2 turni = 4 messaggi minimo
        assert len(d["messages"]) >= 4

    def test_08_chat_with_context(self, H):
        r = requests.post(
            f"{API}/ai/chat",
            json={"session_id": None, "message": "Quanti immobili ci sono nell'app?", "include_context": True},
            headers=H, timeout=90,
        )
        assert r.status_code == 200, r.text

    def test_09_generate_email_sollecito(self, H):
        r = requests.post(
            f"{API}/ai/generate",
            json={"tipo": "email_sollecito", "contesto": {"inquilino": "Mario", "importo": "500"}},
            headers=H, timeout=90,
        )
        assert r.status_code == 200, r.text
        d = r.json()
        assert d.get("content")

    def test_10_suggest_globale(self, H):
        r = requests.post(
            f"{API}/ai/suggest",
            json={"entita_tipo": "globale"},
            headers=H, timeout=90,
        )
        assert r.status_code == 200, r.text

    def test_11_delete_session(self, H):
        if TestAi.session_id:
            r = requests.delete(f"{API}/ai/sessions/{TestAi.session_id}", headers=H, timeout=15)
            assert r.status_code == 200

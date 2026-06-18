"""Iteration 5 tests - new auth endpoints (PUT /auth/me + change-password regression)."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8001").rstrip("/")
API = f"{BASE_URL}/api/v1"


@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(
        f"{API}/auth/login",
        data={"username": "admin@estatewise.it", "password": "admin123"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=30,
    )
    assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def auth_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


# Backend: GET /auth/me works (regression baseline)
def test_get_me_baseline(auth_headers):
    r = requests.get(f"{API}/auth/me", headers=auth_headers, timeout=15)
    assert r.status_code == 200
    data = r.json()
    assert data["email"] == "admin@estatewise.it"
    assert data["ruolo"] == "supervisore"
    assert "nome" in data


# Backend: PUT /auth/me updates nome and persists
def test_put_me_update_nome(auth_headers):
    # Read current nome
    me0 = requests.get(f"{API}/auth/me", headers=auth_headers, timeout=15).json()
    original_nome = me0["nome"]

    new_nome = "TEST_Updated_Admin"
    r = requests.put(f"{API}/auth/me", json={"nome": new_nome}, headers=auth_headers, timeout=15)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["nome"] == new_nome
    # password_hash must NOT be returned
    assert "password_hash" not in body
    assert "_id" not in body

    # Verify persistence via GET
    me1 = requests.get(f"{API}/auth/me", headers=auth_headers, timeout=15).json()
    assert me1["nome"] == new_nome

    # Restore
    requests.put(f"{API}/auth/me", json={"nome": original_nome}, headers=auth_headers, timeout=15)


# Backend: PUT /auth/me - email already in use should return 400
def test_put_me_email_already_in_use(auth_headers):
    # Need a second user. Create via /utenti if endpoint exists; otherwise skip
    # Try fetching list of users
    r = requests.get(f"{API}/utenti", headers=auth_headers, timeout=15)
    if r.status_code != 200:
        pytest.skip(f"No /utenti endpoint to find a second user (got {r.status_code})")
    users = r.json()
    other = next((u for u in users if u.get("email") and u["email"] != "admin@estatewise.it"), None)
    if not other:
        # try to create one
        create = requests.post(
            f"{API}/utenti",
            json={"nome": "TEST_Other", "email": "TEST_other@estatewise.it",
                  "password": "TempPass123!", "ruolo": "operatore"},
            headers=auth_headers, timeout=15,
        )
        if create.status_code not in (200, 201):
            pytest.skip(f"Cannot create second user: {create.status_code} {create.text}")
        other_email = "TEST_other@estatewise.it"
        other_id = create.json().get("id")
    else:
        other_email = other["email"]
        other_id = other.get("id")

    r = requests.put(f"{API}/auth/me", json={"email": other_email}, headers=auth_headers, timeout=15)
    assert r.status_code == 400, f"Expected 400, got {r.status_code}: {r.text}"
    assert "in uso" in r.json().get("detail", "").lower() or "email" in r.json().get("detail", "").lower()

    # Cleanup created test user
    if other_id and other_email.startswith("TEST_"):
        requests.delete(f"{API}/utenti/{other_id}", headers=auth_headers, timeout=15)


# Backend: PUT /auth/me - same email is allowed (no change)
def test_put_me_same_email_ok(auth_headers):
    r = requests.put(f"{API}/auth/me", json={"email": "admin@estatewise.it"}, headers=auth_headers, timeout=15)
    assert r.status_code == 200


# Backend: change-password regression with wrong current password
def test_change_password_wrong_current(auth_headers):
    r = requests.post(
        f"{API}/auth/change-password",
        json={"current_password": "WRONG_pwd_xyz", "new_password": "Whatever123!"},
        headers=auth_headers, timeout=15,
    )
    assert r.status_code == 400
    assert "non corretta" in r.json().get("detail", "").lower()


# Backend: change-password full happy path with restore
def test_change_password_happy_path(auth_headers):
    temp = "TempPass123!"
    # Change to temp
    r = requests.post(
        f"{API}/auth/change-password",
        json={"current_password": "admin123", "new_password": temp},
        headers=auth_headers, timeout=15,
    )
    assert r.status_code == 200, r.text
    assert "successo" in r.json().get("message", "").lower()

    # Verify new password works
    login_r = requests.post(
        f"{API}/auth/login",
        data={"username": "admin@estatewise.it", "password": temp},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=15,
    )
    assert login_r.status_code == 200, "Login with new password failed"
    new_token = login_r.json()["access_token"]

    # Restore admin123
    r2 = requests.post(
        f"{API}/auth/change-password",
        json={"current_password": temp, "new_password": "admin123"},
        headers={"Authorization": f"Bearer {new_token}"}, timeout=15,
    )
    assert r2.status_code == 200, f"Restore failed! {r2.text}"

    # Verify admin123 works again
    final = requests.post(
        f"{API}/auth/login",
        data={"username": "admin@estatewise.it", "password": "admin123"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=15,
    )
    assert final.status_code == 200, "FATAL: admin123 restore failed"


# Backend: report endpoints (CSV/Excel/PDF) for /report frontend testing prerequisites
def test_report_pagamenti_csv(auth_headers):
    r = requests.get(f"{API}/reports/pagamenti?formato=csv", headers=auth_headers, timeout=30)
    if r.status_code == 404:
        pytest.skip("No /reports/pagamenti endpoint")
    assert r.status_code == 200, r.text


def test_report_executive(auth_headers):
    r = requests.get(f"{API}/reports/executive", headers=auth_headers, timeout=30)
    if r.status_code == 404:
        pytest.skip("No /reports/executive endpoint")
    assert r.status_code == 200, r.text
    data = r.json()
    # Should contain some KPI structure
    assert isinstance(data, dict)


# Backend: audit-log endpoint
def test_audit_log_list(auth_headers):
    r = requests.get(f"{API}/audit-log", headers=auth_headers, timeout=15)
    if r.status_code == 404:
        # try alternative path
        r = requests.get(f"{API}/audit", headers=auth_headers, timeout=15)
    assert r.status_code == 200, f"Audit log not accessible: {r.status_code} {r.text[:200]}"


# Backend: soggetti endpoints
def test_soggetti_list(auth_headers):
    r = requests.get(f"{API}/soggetti", headers=auth_headers, timeout=15)
    assert r.status_code == 200


def test_contratti_list(auth_headers):
    r = requests.get(f"{API}/contratti", headers=auth_headers, timeout=15)
    assert r.status_code == 200


# Backend: contratto detail (enriched) for ContrattoDetailPage
def test_contratto_detail(auth_headers):
    contratti = requests.get(f"{API}/contratti", headers=auth_headers, timeout=15).json()
    if not contratti:
        pytest.skip("No contratti in DB")
    cid = contratti[0]["id"]
    r = requests.get(f"{API}/contratti/{cid}", headers=auth_headers, timeout=15)
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == cid


# Backend: soggetto detail
def test_soggetto_detail(auth_headers):
    soggetti = requests.get(f"{API}/soggetti", headers=auth_headers, timeout=15).json()
    if not soggetti:
        pytest.skip("No soggetti in DB")
    sid = soggetti[0]["id"]
    r = requests.get(f"{API}/soggetti/{sid}", headers=auth_headers, timeout=15)
    assert r.status_code == 200

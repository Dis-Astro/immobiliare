#!/usr/bin/env python3
"""
EstateWise P0 Features Backend Tests
Tests for:
- P0-1: Sistema Notifiche con Celery+Redis+Beat e deduplicazione
- P0-2: Mappa con fitBounds automatico
- P0-3: Wizard Contratto multi-step con generazione rate automatiche
- Pagamenti: Rate con funzione Incassa
"""

import pytest
import requests
import os
from datetime import date, datetime
from dateutil.relativedelta import relativedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'http://localhost:8001').rstrip('/')


class TestHealthAndAuth:
    """Health check and authentication tests"""
    
    @pytest.fixture(scope="class")
    def session(self):
        """Create a requests session"""
        return requests.Session()
    
    @pytest.fixture(scope="class")
    def auth_token(self, session):
        """Get authentication token"""
        response = session.post(
            f"{BASE_URL}/api/v1/auth/login",
            data={
                "username": "r.disante@impresacingoli.it",
                "password": "Cinguli26!!"
            }
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "access_token" in data, "No access_token in response"
        return data["access_token"]
    
    def test_health_check(self, session):
        """Test health endpoint"""
        response = session.get(f"{BASE_URL}/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"
        print(f"✅ Health check passed: {data}")
    
    def test_login_success(self, session):
        """Test login with valid credentials"""
        response = session.post(
            f"{BASE_URL}/api/v1/auth/login",
            data={
                "username": "r.disante@impresacingoli.it",
                "password": "Cinguli26!!"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data.get("user", {}).get("ruolo") == "supervisore"
        print(f"✅ Login successful: {data.get('user', {}).get('email')}")
    
    def test_login_invalid_credentials(self, session):
        """Test login with invalid credentials"""
        response = session.post(
            f"{BASE_URL}/api/v1/auth/login",
            data={
                "username": "wrong@email.com",
                "password": "wrongpassword"
            }
        )
        assert response.status_code == 401
        print("✅ Invalid login correctly rejected")


class TestNotificheP0:
    """P0-1: Sistema Notifiche tests"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers"""
        session = requests.Session()
        response = session.post(
            f"{BASE_URL}/api/v1/auth/login",
            data={
                "username": "r.disante@impresacingoli.it",
                "password": "Cinguli26!!"
            }
        )
        token = response.json().get("access_token")
        return {"Authorization": f"Bearer {token}"}
    
    def test_trigger_notification_check(self, auth_headers):
        """Test POST /api/v1/notifiche/trigger-check?check_type=all creates notifications"""
        response = requests.post(
            f"{BASE_URL}/api/v1/notifiche/trigger-check",
            params={"check_type": "all"},
            headers=auth_headers
        )
        assert response.status_code == 200, f"Trigger check failed: {response.text}"
        data = response.json()
        assert "message" in data
        # Can be either queued (Celery) or completed (sync fallback)
        assert data.get("status") in ["queued", "completed"]
        print(f"✅ Notification trigger check: {data}")
    
    def test_get_notifiche_list(self, auth_headers):
        """Test GET /api/v1/notifiche returns notifications list"""
        response = requests.get(
            f"{BASE_URL}/api/v1/notifiche",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✅ Notifiche list: {len(data)} notifications")
        
        # Check notification structure if any exist
        if data:
            notifica = data[0]
            assert "id" in notifica
            assert "tipo" in notifica
            assert "stato" in notifica
            assert "titolo" in notifica
            print(f"   Sample notification: {notifica.get('tipo')} - {notifica.get('stato')}")
    
    def test_get_notifiche_stats(self, auth_headers):
        """Test GET /api/v1/notifiche/stats returns statistics"""
        response = requests.get(
            f"{BASE_URL}/api/v1/notifiche/stats",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "by_stato" in data
        assert "by_tipo" in data
        print(f"✅ Notifiche stats: total={data.get('total')}, by_stato={data.get('by_stato')}")
    
    def test_notifiche_filter_by_stato(self, auth_headers):
        """Test filtering notifications by stato"""
        for stato in ["pending", "sent", "failed"]:
            response = requests.get(
                f"{BASE_URL}/api/v1/notifiche",
                params={"stato": stato},
                headers=auth_headers
            )
            assert response.status_code == 200
            data = response.json()
            # All returned notifications should have the requested stato
            for n in data:
                assert n.get("stato") == stato, f"Expected stato={stato}, got {n.get('stato')}"
            print(f"✅ Filter by stato={stato}: {len(data)} notifications")


class TestMappaP0:
    """P0-2: Mappa con fitBounds tests"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers"""
        session = requests.Session()
        response = session.post(
            f"{BASE_URL}/api/v1/auth/login",
            data={
                "username": "r.disante@impresacingoli.it",
                "password": "Cinguli26!!"
            }
        )
        token = response.json().get("access_token")
        return {"Authorization": f"Bearer {token}"}
    
    def test_get_map_markers(self, auth_headers):
        """Test GET /api/v1/mappa/markers returns markers with coordinates"""
        response = requests.get(
            f"{BASE_URL}/api/v1/mappa/markers",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "markers" in data
        markers = data.get("markers", [])
        print(f"✅ Map markers: {len(markers)} markers found")
        
        # Check marker structure
        for marker in markers:
            assert "lat" in marker, "Marker missing lat"
            assert "lon" in marker, "Marker missing lon"
            assert marker["lat"] is not None, "Marker lat is None"
            assert marker["lon"] is not None, "Marker lon is None"
            print(f"   Marker: lat={marker['lat']}, lon={marker['lon']}, status={marker.get('status')}")
        
        # Check status breakdown
        if "by_status" in data:
            print(f"   Status breakdown: {data['by_status']}")
    
    def test_get_map_bounds(self, auth_headers):
        """Test GET /api/v1/mappa/bounds returns bounds for fitBounds"""
        response = requests.get(
            f"{BASE_URL}/api/v1/mappa/bounds",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Should have bounds or center
        if data.get("bounds"):
            bounds = data["bounds"]
            assert "north" in bounds or "sw" in bounds
            print(f"✅ Map bounds: {bounds}")
        elif data.get("center"):
            print(f"✅ Map center: {data['center']}")
        else:
            print(f"✅ Map bounds response: {data}")
    
    def test_markers_have_different_coordinates(self, auth_headers):
        """Test that markers have different coordinates (for fitBounds to work)"""
        response = requests.get(
            f"{BASE_URL}/api/v1/mappa/markers",
            headers=auth_headers
        )
        assert response.status_code == 200
        markers = response.json().get("markers", [])
        
        if len(markers) > 1:
            coords = set()
            for m in markers:
                coord = (m.get("lat"), m.get("lon"))
                coords.add(coord)
            
            # Should have multiple unique coordinates for fitBounds to be meaningful
            print(f"✅ Unique coordinates: {len(coords)} out of {len(markers)} markers")
            assert len(coords) > 1, "All markers have same coordinates - fitBounds won't work properly"


class TestContrattoWizardP0:
    """P0-3: Wizard Contratto multi-step tests"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers"""
        session = requests.Session()
        response = session.post(
            f"{BASE_URL}/api/v1/auth/login",
            data={
                "username": "r.disante@impresacingoli.it",
                "password": "Cinguli26!!"
            }
        )
        token = response.json().get("access_token")
        return {"Authorization": f"Bearer {token}"}
    
    def test_get_unita_disponibili(self, auth_headers):
        """Test getting available units for wizard step 1"""
        response = requests.get(
            f"{BASE_URL}/api/v1/unita",
            params={"stato": "libera"},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        print(f"✅ Available units: {len(data)} units")
        return data
    
    def test_get_soggetti(self, auth_headers):
        """Test getting soggetti for wizard steps 2-3"""
        response = requests.get(
            f"{BASE_URL}/api/v1/soggetti",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✅ Soggetti: {len(data)} subjects")
        
        # Check for locatori and affittuari
        locatori = [s for s in data if s.get("tipo") in ["proprietario", "locatore"]]
        affittuari = [s for s in data if s.get("tipo") in ["affittuario", "inquilino"]]
        print(f"   Locatori: {len(locatori)}, Affittuari: {len(affittuari)}")
        return data
    
    def test_get_contratti_list(self, auth_headers):
        """Test getting contracts list"""
        response = requests.get(
            f"{BASE_URL}/api/v1/contratti",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✅ Contratti: {len(data)} contracts")
        
        # Check for active contracts
        attivi = [c for c in data if c.get("stato") == "attivo"]
        print(f"   Active contracts: {len(attivi)}")
        return data
    
    def test_get_contratto_rate(self, auth_headers):
        """Test getting rate for a contract (verifies rate generation)"""
        # First get contracts
        response = requests.get(
            f"{BASE_URL}/api/v1/contratti",
            headers=auth_headers
        )
        contratti = response.json()
        
        if contratti:
            contratto_id = contratti[0].get("id")
            response = requests.get(
                f"{BASE_URL}/api/v1/contratti/{contratto_id}/rate",
                headers=auth_headers
            )
            assert response.status_code == 200
            rate = response.json()
            print(f"✅ Contract {contratto_id} has {len(rate)} rate")
            
            # Verify rate structure
            if rate:
                rata = rate[0]
                assert "importo" in rata
                assert "periodo" in rata
                assert "stato" in rata
                print(f"   Sample rata: periodo={rata.get('periodo')}, importo={rata.get('importo')}, stato={rata.get('stato')}")
        else:
            print("⚠️ No contracts found to test rate")


class TestPagamentiP0:
    """Pagamenti: Rate con funzione Incassa tests"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers"""
        session = requests.Session()
        response = session.post(
            f"{BASE_URL}/api/v1/auth/login",
            data={
                "username": "r.disante@impresacingoli.it",
                "password": "Cinguli26!!"
            }
        )
        token = response.json().get("access_token")
        return {"Authorization": f"Bearer {token}"}
    
    def test_get_rate_list(self, auth_headers):
        """Test GET /api/v1/rate returns rate list"""
        response = requests.get(
            f"{BASE_URL}/api/v1/rate",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✅ Rate list: {len(data)} rate")
        
        # Check rate structure
        if data:
            rata = data[0]
            assert "id" in rata
            assert "importo" in rata
            assert "stato" in rata
            print(f"   Sample rata: {rata.get('periodo')} - €{rata.get('importo')} - {rata.get('stato')}")
        return data
    
    def test_get_rate_stats(self, auth_headers):
        """Test GET /api/v1/rate/stats returns statistics"""
        response = requests.get(
            f"{BASE_URL}/api/v1/rate/stats",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "totale" in data
        assert "incassato" in data
        assert "da_incassare" in data
        print(f"✅ Rate stats: totale=€{data.get('totale')}, incassato=€{data.get('incassato')}, da_incassare=€{data.get('da_incassare')}")
    
    def test_incassa_rata(self, auth_headers):
        """Test POST /api/v1/rate/{rata_id}/incassa marks rata as paid"""
        # First get rate that are not yet incassato
        response = requests.get(
            f"{BASE_URL}/api/v1/rate",
            params={"stato": "da_incassare"},
            headers=auth_headers
        )
        rate = response.json()
        
        if rate:
            rata_id = rate[0].get("id")
            original_stato = rate[0].get("stato")
            
            # Incassa the rata
            response = requests.post(
                f"{BASE_URL}/api/v1/rate/{rata_id}/incassa",
                headers=auth_headers
            )
            assert response.status_code == 200
            data = response.json()
            assert "message" in data
            assert data.get("data_incasso") is not None
            print(f"✅ Rata {rata_id} incassata: {data}")
            
            # Verify the rata is now incassato
            response = requests.get(
                f"{BASE_URL}/api/v1/rate",
                headers=auth_headers
            )
            updated_rate = response.json()
            updated_rata = next((r for r in updated_rate if r.get("id") == rata_id), None)
            if updated_rata:
                assert updated_rata.get("stato") == "incassato", f"Expected stato=incassato, got {updated_rata.get('stato')}"
                print(f"✅ Verified rata stato changed to 'incassato'")
        else:
            print("⚠️ No rate with stato=da_incassare found to test incassa")
    
    def test_filter_rate_by_stato(self, auth_headers):
        """Test filtering rate by stato"""
        for stato in ["da_incassare", "incassato", "in_ritardo"]:
            response = requests.get(
                f"{BASE_URL}/api/v1/rate",
                params={"stato": stato},
                headers=auth_headers
            )
            assert response.status_code == 200
            data = response.json()
            print(f"✅ Filter by stato={stato}: {len(data)} rate")


class TestDashboardAPIs:
    """Dashboard API tests"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers"""
        session = requests.Session()
        response = session.post(
            f"{BASE_URL}/api/v1/auth/login",
            data={
                "username": "r.disante@impresacingoli.it",
                "password": "Cinguli26!!"
            }
        )
        token = response.json().get("access_token")
        return {"Authorization": f"Bearer {token}"}
    
    def test_dashboard_overview(self, auth_headers):
        """Test dashboard overview endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/v1/dashboard/overview",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "kpi" in data
        kpi = data["kpi"]
        print(f"✅ Dashboard KPI: immobili={kpi.get('immobili')}, unita_locate={kpi.get('unita_locate')}/{kpi.get('unita_totali')}")
    
    def test_dashboard_rate_ritardo(self, auth_headers):
        """Test rate in ritardo endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/v1/dashboard/rate-ritardo",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        print(f"✅ Rate in ritardo: {len(data)} rate")


class TestImmobiliAPIs:
    """Immobili API tests"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get auth headers"""
        session = requests.Session()
        response = session.post(
            f"{BASE_URL}/api/v1/auth/login",
            data={
                "username": "r.disante@impresacingoli.it",
                "password": "Cinguli26!!"
            }
        )
        token = response.json().get("access_token")
        return {"Authorization": f"Bearer {token}"}
    
    def test_get_immobili(self, auth_headers):
        """Test getting immobili list"""
        response = requests.get(
            f"{BASE_URL}/api/v1/immobili",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✅ Immobili: {len(data)} properties")
        
        # Check immobile structure
        if data:
            immobile = data[0]
            assert "id" in immobile
            assert "titolo" in immobile
            print(f"   Sample: {immobile.get('titolo')} - {immobile.get('indirizzo')}")
    
    def test_get_unita(self, auth_headers):
        """Test getting unita list"""
        response = requests.get(
            f"{BASE_URL}/api/v1/unita",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✅ Unita: {len(data)} units")
        
        # Check for locata units
        locate = [u for u in data if u.get("stato") == "locata"]
        libere = [u for u in data if u.get("stato") == "libera"]
        print(f"   Locate: {len(locate)}, Libere: {len(libere)}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

#!/usr/bin/env python3
"""
EstateWise Backend API Testing Suite
Tests all critical endpoints for the property management system
"""

import requests
import sys
import json
from datetime import datetime
from typing import Dict, Any, Optional

class EstateWiseAPITester:
    def __init__(self, base_url="https://energy-audit-demo-1.preview.emergentagent.com"):
        self.base_url = base_url
        self.token = None
        self.tests_run = 0
        self.tests_passed = 0
        self.failed_tests = []
        self.session = requests.Session()
        
    def log(self, message: str, level: str = "INFO"):
        """Log test messages with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")
        
    def run_test(self, name: str, method: str, endpoint: str, expected_status: int, 
                 data: Optional[Dict] = None, headers: Optional[Dict] = None) -> tuple[bool, Dict]:
        """Run a single API test"""
        url = f"{self.base_url}/api/v1/{endpoint}"
        test_headers = {'Content-Type': 'application/json'}
        
        if self.token:
            test_headers['Authorization'] = f'Bearer {self.token}'
        if headers:
            test_headers.update(headers)

        self.tests_run += 1
        self.log(f"Testing {name}... ({method} {endpoint})")
        
        try:
            if method == 'GET':
                response = self.session.get(url, headers=test_headers)
            elif method == 'POST':
                response = self.session.post(url, json=data, headers=test_headers)
            elif method == 'PUT':
                response = self.session.put(url, json=data, headers=test_headers)
            elif method == 'DELETE':
                response = self.session.delete(url, headers=test_headers)
            else:
                raise ValueError(f"Unsupported method: {method}")

            success = response.status_code == expected_status
            
            if success:
                self.tests_passed += 1
                self.log(f"✅ PASSED - Status: {response.status_code}")
                try:
                    return True, response.json()
                except:
                    return True, {"message": "Success (no JSON response)"}
            else:
                self.log(f"❌ FAILED - Expected {expected_status}, got {response.status_code}")
                self.log(f"   Response: {response.text[:200]}...")
                self.failed_tests.append({
                    "test": name,
                    "expected": expected_status,
                    "actual": response.status_code,
                    "response": response.text[:500]
                })
                try:
                    return False, response.json()
                except:
                    return False, {"error": response.text}

        except Exception as e:
            self.log(f"❌ FAILED - Exception: {str(e)}", "ERROR")
            self.failed_tests.append({
                "test": name,
                "error": str(e)
            })
            return False, {"error": str(e)}

    def test_health_check(self):
        """Test health check endpoint"""
        self.log("=== TESTING HEALTH CHECK ===")
        success, response = self.run_test(
            "Health Check",
            "GET",
            "health",
            200
        )
        
        if success and response.get("status") == "healthy":
            self.log("✅ Health check passed - System is healthy")
            return True
        else:
            self.log("❌ Health check failed - System may be unhealthy")
            return False

    def test_authentication(self):
        """Test authentication with admin credentials"""
        self.log("=== TESTING AUTHENTICATION ===")
        
        # Test login with admin credentials using form data
        url = f"{self.base_url}/api/v1/auth/login"
        login_data = {
            "username": "admin@estatewise.it",
            "password": "admin123"
        }
        
        self.tests_run += 1
        self.log("Testing Admin Login... (POST auth/login)")
        
        try:
            response = self.session.post(url, data=login_data)
            success = response.status_code == 200
            
            if success:
                self.tests_passed += 1
                self.log(f"✅ PASSED - Status: {response.status_code}")
                response_data = response.json()
            else:
                self.log(f"❌ FAILED - Expected 200, got {response.status_code}")
                self.log(f"   Response: {response.text[:200]}...")
                self.failed_tests.append({
                    "test": "Admin Login",
                    "expected": 200,
                    "actual": response.status_code,
                    "response": response.text[:500]
                })
                try:
                    response_data = response.json()
                except:
                    response_data = {"error": response.text}
        except Exception as e:
            self.log(f"❌ FAILED - Exception: {str(e)}", "ERROR")
            self.failed_tests.append({
                "test": "Admin Login",
                "error": str(e)
            })
            success = False
            response_data = {"error": str(e)}
        
        if success and 'access_token' in response_data:
            self.token = response_data['access_token']
            self.log(f"✅ Login successful - Token obtained")
            self.log(f"   User: {response_data.get('user', {}).get('email', 'N/A')}")
            self.log(f"   Role: {response_data.get('user', {}).get('ruolo', 'N/A')}")
            self.log(f"   Must change password: {response_data.get('user', {}).get('must_change_password', 'N/A')}")
            return True
        else:
            self.log("❌ Login failed - Cannot proceed with authenticated tests")
            return False

    def test_user_profile(self):
        """Test user profile endpoint"""
        self.log("=== TESTING USER PROFILE ===")
        
        success, response = self.run_test(
            "Get User Profile",
            "GET",
            "auth/me",
            200
        )
        
        if success:
            self.log(f"✅ Profile retrieved - User: {response.get('email', 'N/A')}")
            return True
        return False

    def test_dashboard_apis(self):
        """Test dashboard-related APIs"""
        self.log("=== TESTING DASHBOARD APIs ===")
        
        # Test dashboard overview
        success, response = self.run_test(
            "Dashboard Overview",
            "GET",
            "dashboard/overview",
            200
        )
        
        if success:
            kpi = response.get('kpi', {})
            self.log(f"✅ Dashboard overview retrieved")
            self.log(f"   Immobili: {kpi.get('immobili', 0)}")
            self.log(f"   Unità locate: {kpi.get('unita_locate', 0)}/{kpi.get('unita_totali', 0)}")
            self.log(f"   Rate in ritardo: {kpi.get('rate_in_ritardo', 0)}")
            self.log(f"   Incassi mese: €{kpi.get('incassi_mese', 0)}")
            
        # Test other dashboard endpoints
        endpoints = [
            ("Rate in Ritardo", "dashboard/rate-ritardo"),
            ("Eventi Critici", "dashboard/eventi-critici"),
            ("Contratti in Scadenza", "dashboard/contratti-scadenza"),
        ]
        
        for name, endpoint in endpoints:
            self.run_test(name, "GET", endpoint, 200)
        
        return success

    def test_mappa_apis(self):
        """Test map-related APIs"""
        self.log("=== TESTING MAPPA APIs ===")
        
        # Test map markers
        success1, response = self.run_test(
            "Map Markers",
            "GET",
            "mappa/markers",
            200
        )
        
        if success1:
            markers = response.get('markers', [])
            stats = response.get('by_status', {})
            self.log(f"✅ Map markers retrieved - {len(markers)} markers")
            self.log(f"   Status breakdown: Rosso:{stats.get('rosso',0)}, Giallo:{stats.get('giallo',0)}, Verde:{stats.get('verde',0)}, Grigio:{stats.get('grigio',0)}")
        
        # Test map bounds
        success2, response = self.run_test(
            "Map Bounds",
            "GET",
            "mappa/bounds",
            200
        )
        
        return success1 and success2

    def test_immobili_apis(self):
        """Test property-related APIs"""
        self.log("=== TESTING IMMOBILI APIs ===")
        
        # Test get immobili list
        success, response = self.run_test(
            "Get Immobili List",
            "GET",
            "immobili",
            200
        )
        
        if success:
            immobili = response if isinstance(response, list) else response.get('immobili', [])
            self.log(f"✅ Immobili list retrieved - {len(immobili)} properties")
        
        return success

    def test_contratti_apis(self):
        """Test contract-related APIs"""
        self.log("=== TESTING CONTRATTI APIs ===")
        
        success, response = self.run_test(
            "Get Contratti List",
            "GET",
            "contratti",
            200
        )
        
        if success:
            contratti = response if isinstance(response, list) else response.get('contratti', [])
            self.log(f"✅ Contratti list retrieved - {len(contratti)} contracts")
        
        return success

    def test_soggetti_apis(self):
        """Test subjects/tenants APIs"""
        self.log("=== TESTING SOGGETTI APIs ===")
        
        success, response = self.run_test(
            "Get Soggetti List",
            "GET",
            "soggetti",
            200
        )
        
        if success:
            soggetti = response if isinstance(response, list) else response.get('soggetti', [])
            self.log(f"✅ Soggetti list retrieved - {len(soggetti)} subjects")
        
        return success

    def test_pagamenti_apis(self):
        """Test payments-related APIs"""
        self.log("=== TESTING PAGAMENTI APIs ===")
        
        success, response = self.run_test(
            "Get Rate List",
            "GET",
            "rate",
            200
        )
        
        if success:
            rate = response if isinstance(response, list) else response.get('rate', [])
            self.log(f"✅ Rate list retrieved - {len(rate)} payments")
        
        return success

    def test_geocoding_api(self):
        """Test geocoding functionality"""
        self.log("=== TESTING GEOCODING API ===")
        
        test_address = "Via Roma 1, Milano, Italy"
        success, response = self.run_test(
            "Geocode Address",
            "POST",
            "geocode",
            200,
            data={"address": test_address}
        )
        
        if success and 'lat' in response and 'lon' in response:
            self.log(f"✅ Geocoding successful - Lat: {response['lat']}, Lon: {response['lon']}")
            return True
        else:
            self.log("❌ Geocoding failed or returned invalid coordinates")
            return False

    def test_global_search(self):
        """Test global search functionality"""
        self.log("=== TESTING GLOBAL SEARCH ===")
        
        success, response = self.run_test(
            "Global Search",
            "GET",
            "search?q=test",
            200
        )
        
        if success:
            results = response
            self.log(f"✅ Global search completed")
            self.log(f"   Immobili: {len(results.get('immobili', []))}")
            self.log(f"   Contratti: {len(results.get('contratti', []))}")
            self.log(f"   Soggetti: {len(results.get('soggetti', []))}")
            return True
        
        return False

    def run_all_tests(self):
        """Run all test suites"""
        self.log("🚀 Starting EstateWise API Test Suite")
        self.log(f"   Base URL: {self.base_url}")
        
        # Critical tests first
        health_ok = self.test_health_check()
        if not health_ok:
            self.log("❌ CRITICAL: Health check failed - stopping tests", "ERROR")
            return False
            
        auth_ok = self.test_authentication()
        if not auth_ok:
            self.log("❌ CRITICAL: Authentication failed - stopping tests", "ERROR")
            return False
        
        # Continue with other tests
        self.test_user_profile()
        self.test_dashboard_apis()
        self.test_mappa_apis()
        self.test_immobili_apis()
        self.test_contratti_apis()
        self.test_soggetti_apis()
        self.test_pagamenti_apis()
        self.test_geocoding_api()
        self.test_global_search()
        
        return True

    def print_summary(self):
        """Print test summary"""
        self.log("=" * 50)
        self.log("📊 TEST SUMMARY")
        self.log(f"   Total tests: {self.tests_run}")
        self.log(f"   Passed: {self.tests_passed}")
        self.log(f"   Failed: {len(self.failed_tests)}")
        self.log(f"   Success rate: {(self.tests_passed/self.tests_run*100):.1f}%" if self.tests_run > 0 else "0%")
        
        if self.failed_tests:
            self.log("\n❌ FAILED TESTS:")
            for i, test in enumerate(self.failed_tests, 1):
                self.log(f"   {i}. {test['test']}")
                if 'expected' in test:
                    self.log(f"      Expected: {test['expected']}, Got: {test['actual']}")
                if 'error' in test:
                    self.log(f"      Error: {test['error']}")
        
        return len(self.failed_tests) == 0


def main():
    """Main test execution"""
    tester = EstateWiseAPITester()
    
    try:
        success = tester.run_all_tests()
        all_passed = tester.print_summary()
        
        # Return appropriate exit code
        if not success:
            return 2  # Critical failure
        elif not all_passed:
            return 1  # Some tests failed
        else:
            return 0  # All tests passed
            
    except KeyboardInterrupt:
        tester.log("\n⚠️  Tests interrupted by user", "WARNING")
        return 130
    except Exception as e:
        tester.log(f"\n💥 Unexpected error: {e}", "ERROR")
        return 1


if __name__ == "__main__":
    sys.exit(main())
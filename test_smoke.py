import re
import unittest

import app as foodlink


class FoodLinkSmokeTests(unittest.TestCase):
    def setUp(self):
        self.client = foodlink.app.test_client()

    def login(self, email):
        page = self.client.get("/login")
        token = re.search(rb'name="csrf-token" content="([^"]+)"', page.data).group(1).decode()
        return self.client.post("/login", data={
            "csrf_token": token,
            "email": email,
            "password": "FoodLink123!",
        })

    def test_public_pages_and_seeded_api(self):
        self.assertEqual(self.client.get("/").status_code, 200)
        self.assertEqual(self.client.get("/food").status_code, 200)
        self.assertEqual(self.client.get("/food/1").status_code, 200)
        response = self.client.get("/api/food")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json), 3)
        self.assertIn("priority", response.json[0])

    def test_donor_dashboard_and_role_restriction(self):
        self.assertEqual(self.login("donor@foodlink.demo").status_code, 302)
        self.assertEqual(self.client.get("/dashboard").status_code, 200)
        response = self.client.get("/add-food")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Add food", self.client.get("/dashboard").data)
        self.assertEqual(self.client.get("/admin").status_code, 403)

    def test_restaurant_donate_entry_and_ngo_receiving_role(self):
        response = self.client.get("/donate-food")
        self.assertEqual(response.status_code, 302)
        self.assertIn("role=donor", response.location)

        self.assertEqual(self.login("ngo@foodlink.demo").status_code, 302)
        self.assertEqual(self.client.get("/add-food").status_code, 403)
        dashboard = self.client.get("/dashboard")
        self.assertIn(b"Emergency request", dashboard.data)
        self.assertNotIn(b"Add food", dashboard.data)

    def test_admin_dashboard(self):
        self.assertEqual(self.login("admin@foodlink.demo").status_code, 302)
        self.assertEqual(self.client.get("/admin").status_code, 200)

    def test_analytics_and_verified_ngo_emergency_page(self):
        self.assertEqual(self.login("ngo@foodlink.demo").status_code, 302)
        self.assertEqual(self.client.get("/analytics").status_code, 200)
        self.assertEqual(self.client.get("/notifications").status_code, 200)
        self.assertEqual(self.client.get("/emergency-request").status_code, 200)


if __name__ == "__main__":
    unittest.main()

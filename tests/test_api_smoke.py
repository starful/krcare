import unittest

from app import app


class ApiSmokeTest(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()

    def test_api_items_returns_list(self):
        response = self.client.get("/api/items?lang=en")
        self.assertEqual(response.status_code, 200)

        payload = response.get_json()
        self.assertIsInstance(payload, dict)

        list_key = next((k for k, v in payload.items() if isinstance(v, list)), None)
        self.assertIsNotNone(list_key)
        self.assertIn("last_updated", payload)

    def test_robots_and_sitemap_exist(self):
        robots = self.client.get("/robots.txt")
        self.assertEqual(robots.status_code, 200)
        self.assertIn("Sitemap:", robots.get_data(as_text=True))

        sitemap = self.client.get("/sitemap.xml")
        self.assertEqual(sitemap.status_code, 200)
        body = sitemap.get_data(as_text=True)
        self.assertIn("<urlset", body)
        self.assertIn("<loc>", body)
        self.assertIn("xhtml:link", body)

    def test_ads_txt(self):
        ads = self.client.get("/ads.txt")
        self.assertEqual(ads.status_code, 200)
        self.assertIn(
            "google.com, pub-8780435268193938, DIRECT, f08c47fec0942fa0",
            ads.get_data(as_text=True),
        )

    def test_favicon_and_manifest_routes_exist(self):
        favicon = self.client.get("/favicon.ico")
        self.assertIn(favicon.status_code, (200, 302))

        manifest = self.client.get("/site.webmanifest")
        self.assertEqual(manifest.status_code, 200)
        self.assertIn("icons", manifest.get_data(as_text=True))

    def test_reactions_api_returns_counts(self):
        response = self.client.get("/api/reactions/smoke-test-slug")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertIn("likes", payload)
        self.assertIn("dislikes", payload)

    def test_item_detail_has_reaction_panel(self):
        items_resp = self.client.get("/api/items?lang=en")
        payload = items_resp.get_json()
        items = payload.get("items") or []
        self.assertTrue(items)
        item_id = items[0]["id"]
        detail = self.client.get(f"/item/{item_id}")
        self.assertEqual(detail.status_code, 200)
        self.assertIn(b"reaction-panel", detail.data)

    def test_item_detail_shows_klook_cta(self):
        items_resp = self.client.get("/api/items?lang=en")
        payload = items_resp.get_json()
        items = payload.get("items") or []
        self.assertTrue(items)
        item_id = items[0]["id"]
        detail = self.client.get(f"/item/{item_id}")
        self.assertEqual(detail.status_code, 200)
        body = detail.get_data(as_text=True)
        self.assertIn("https://klook.tpo.mx/ED7IfKaq", body)
        self.assertIn("booking-box", body)
        self.assertNotIn("Agoda", body)


if __name__ == "__main__":
    unittest.main()

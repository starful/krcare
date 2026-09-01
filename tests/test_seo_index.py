"""Tests for clinic indexability and sitemap filtering."""
import unittest

from app import INDEXABLE_CLINIC_IDS, app
from app.seo_index import is_indexable_clinic, body_word_count


class SeoIndexTest(unittest.TestCase):
    def test_gangnam_clinic_indexable_by_district(self):
        ok = is_indexable_clinic(
            address="123 Teheran-ro, Gangnam-gu, Seoul",
            lat=37.50,
            lng=127.03,
            content="Short listing.",
        )
        self.assertTrue(ok)

    def test_thin_non_featured_not_indexable(self):
        ok = is_indexable_clinic(
            address="Some clinic, Jeonju, Jeollabuk-do",
            lat=35.82,
            lng=127.15,
            content="Brief KTO listing only.",
        )
        self.assertFalse(ok)

    def test_rich_content_indexable_outside_featured(self):
        words = "word " * 160
        ok = is_indexable_clinic(
            address="Remote area",
            lat=36.0,
            lng=128.0,
            content=words,
        )
        self.assertTrue(ok)

    def test_body_word_count_skips_frontmatter(self):
        md = "---\ntitle: Test\n---\n\nOne two three four five."
        self.assertEqual(body_word_count(md), 5)

    def test_sitemap_excludes_thin_clinics(self):
        import re

        client = app.test_client()
        sitemap = client.get("/sitemap.xml").get_data(as_text=True)
        self.assertIn("/guide/", sitemap)
        locs = re.findall(r"<loc>([^<]+)</loc>", sitemap)
        item_locs = [u for u in locs if "/item/mdcl_" in u]
        self.assertEqual(len(item_locs), len(INDEXABLE_CLINIC_IDS))
        self.assertLess(len(item_locs), 320)

    def test_thin_clinic_has_noindex(self):
        client = app.test_client()
        # Find a non-indexable clinic by scanning EN ids
        from pathlib import Path
        import frontmatter

        content_dir = Path(__file__).resolve().parents[1] / "app" / "content"
        thin_id = None
        for path in content_dir.glob("mdcl_*_en.md"):
            post = frontmatter.loads(path.read_text(encoding="utf-8"))
            bid = path.stem.removesuffix("_en")
            if bid not in INDEXABLE_CLINIC_IDS:
                thin_id = path.stem
                break
        self.assertIsNotNone(thin_id, "expected at least one thin clinic")
        resp = client.get(f"/item/{thin_id}")
        self.assertEqual(resp.status_code, 200)
        self.assertIn('noindex', resp.get_data(as_text=True))

    def test_about_mentions_korea_not_japan(self):
        client = app.test_client()
        body = client.get("/about.html").get_data(as_text=True)
        self.assertIn("South Korea", body)
        self.assertNotIn("Japan has to offer", body)

    def test_privacy_uses_site_name(self):
        client = app.test_client()
        body = client.get("/privacy.html").get_data(as_text=True)
        self.assertIn("KR Care", body)
        self.assertNotIn("OK Template", body)
        self.assertNotIn("example.com", body)

    def test_contact_uses_krcare_branding(self):
        client = app.test_client()
        body = client.get("/contact.html").get_data(as_text=True)
        self.assertIn("KR Care", body)
        self.assertIn("site=krcare", body)
        self.assertNotIn("OK Template", body)
        self.assertNotIn("example.com", body)
        self.assertNotIn("site=okramen", body)

    def test_terms_and_disclaimer_in_sitemap(self):
        client = app.test_client()
        sitemap = client.get("/sitemap.xml").get_data(as_text=True)
        self.assertIn("/terms.html", sitemap)
        self.assertIn("/disclaimer.html", sitemap)


if __name__ == "__main__":
    unittest.main()

"""Check this package's metadata against WorkBuddy's publishing field list.

This flat-header check does not replace the platform's YAML parser or review.
"""

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]


class PublicationTests(unittest.TestCase):
    def test_eight_required_publishing_fields(self):
        content = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        match = re.match(r"\A---\n(.*?)\n---\n", content, re.DOTALL)
        self.assertIsNotNone(match)
        fields = dict(re.findall(r"^([a-z][a-z_-]*):[ \t]*(.*)$", match.group(1), re.MULTILINE))
        for key in ("name", "display_name", "display_name_en", "description",
                    "description_zh", "description_en", "version", "author"):
            with self.subTest(field=key):
                self.assertTrue(fields.get(key, "").strip(), f"Missing publishing field: {key}")
        self.assertEqual(fields["name"], ROOT.name)
        self.assertEqual(fields["version"], (ROOT / "VERSION").read_text().strip())

    def test_entrypoint_references_are_bundled(self):
        content = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        for link in re.findall(r"\]\(([^)]+)\)", content):
            if "://" not in link and not link.startswith("#"):
                with self.subTest(link=link):
                    self.assertTrue((ROOT / link.split("#", 1)[0]).is_file())

    def test_upstream_licenses_remain_present(self):
        for name in ("LICENSE", "LICENSE-ahao.txt", "LICENSE-ghost-writer.txt"):
            with self.subTest(name=name):
                text = (ROOT / name).read_text(encoding="utf-8")
                self.assertIn("MIT License", text)
                self.assertIn("Copyright (c)", text)


if __name__ == "__main__":
    unittest.main()

import tempfile
import unittest
from pathlib import Path

from agent_retro.privacy import delete_derived, redact_excerpt


class PrivacyTests(unittest.TestCase):
    def test_redacts_credentials_and_bounds_excerpt(self) -> None:
        text = "password=secret token: abc123 Authorization: Bearer xyz " + ("x" * 600)

        excerpt = redact_excerpt(text)

        self.assertNotIn("secret", excerpt)
        self.assertNotIn("abc123", excerpt)
        self.assertNotIn("xyz", excerpt)
        self.assertLessEqual(len(excerpt), 500)

    def test_delete_is_limited_to_state_root(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            artifact = root / "reports" / "daily.md"
            artifact.parent.mkdir()
            artifact.write_text("derived", encoding="utf-8")

            delete_derived(root, Path("reports/daily.md"))

            self.assertFalse(artifact.exists())
            with self.assertRaises(ValueError):
                delete_derived(root, Path("../transcript.jsonl"))


if __name__ == "__main__":
    unittest.main()

import sqlite3
import tempfile
import unittest
from pathlib import Path

from agent_retro.store import ProposalStore


class ProposalStoreInitializationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.path = Path(self.temporary.name) / "state" / "proposals.sqlite3"

    def test_initialization_is_idempotent_and_versioned(self) -> None:
        store = ProposalStore(self.path)

        store.initialize()
        store.initialize()

        with sqlite3.connect(self.path) as connection:
            self.assertEqual(connection.execute("PRAGMA user_version").fetchone()[0], 1)
            tables = connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name"
            ).fetchall()
        self.assertEqual(tables, [("events",), ("proposals",), ("revisions",)])

    def test_corrupt_database_is_not_replaced(self) -> None:
        self.path.parent.mkdir()
        original = b"not a sqlite database"
        self.path.write_bytes(original)

        with self.assertRaises(sqlite3.DatabaseError):
            ProposalStore(self.path).initialize()

        self.assertEqual(self.path.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()

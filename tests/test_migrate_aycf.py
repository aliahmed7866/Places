import sqlite3
import tempfile
import unittest
from pathlib import Path

from migrate_aycf import migrate


class AycfMigrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.source = root / "travel-journal.sqlite3"
        self.target = root / "places.sqlite3"
        db = sqlite3.connect(self.source)
        db.execute("""CREATE TABLE places (
            id INTEGER PRIMARY KEY, country TEXT NOT NULL, place TEXT NOT NULL,
            status TEXT NOT NULL, visited_on TEXT NOT NULL DEFAULT '', notes TEXT NOT NULL DEFAULT ''
        )""")
        db.executemany(
            "INSERT INTO places(country,place,status,visited_on,notes) VALUES(?,?,?,?,?)",
            [
                ("GE", "Mestia", "visited", "2026-10-04", "Mountains"),
                ("JP", "Tokyo", "wishlist", "", "One day"),
            ],
        )
        db.commit()
        db.close()

    def tearDown(self):
        self.tmp.cleanup()

    def test_migrates_dates_and_wishlist(self):
        total, inserted = migrate(self.source, self.target)
        self.assertEqual((total, inserted), (2, 2))
        db = sqlite3.connect(self.target)
        rows = db.execute(
            "SELECT country,status,start_date,end_date FROM places ORDER BY country"
        ).fetchall()
        db.close()
        self.assertEqual(rows[0], ("GE", "visited", "2026-10-04", "2026-10-04"))
        self.assertEqual(rows[1], ("JP", "wishlist", "", ""))

    def test_rerun_is_idempotent(self):
        self.assertEqual(migrate(self.source, self.target), (2, 2))
        self.assertEqual(migrate(self.source, self.target), (2, 0))

    def test_dry_run_does_not_create_target(self):
        self.assertEqual(migrate(self.source, self.target, dry_run=True), (2, 0))
        self.assertFalse(self.target.exists())


if __name__ == "__main__":
    unittest.main()

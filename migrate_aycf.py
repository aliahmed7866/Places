#!/usr/bin/env python3
"""Migrate the old AYCF Places journal into the standalone Places database.

Safe to re-run: rows are inserted with INSERT OR IGNORE using the standalone
Places uniqueness constraint. Existing AYCF `visited_on` values are mapped to
both `start_date` and `end_date`.
"""
from __future__ import annotations

import argparse
import os
import sqlite3
from pathlib import Path

DEFAULT_TARGET = Path(os.environ.get("PLACES_DB_PATH", Path(os.environ.get("PLACES_DATA_DIR", Path.home() / ".local" / "share" / "places")) / "places.sqlite3"))
SOURCE_CANDIDATES = [
    Path(os.environ["AYCF_JOURNAL_DB_PATH"]) if os.environ.get("AYCF_JOURNAL_DB_PATH") else None,
    Path(os.environ["AYCF_DB_PATH"]).expanduser().with_name("travel-journal.sqlite3") if os.environ.get("AYCF_DB_PATH") else None,
    Path(os.environ["AYCF_STATE_DIR"]).expanduser() / "travel-journal.sqlite3" if os.environ.get("AYCF_STATE_DIR") else None,
    Path.home() / ".local" / "share" / "aycf" / "travel-journal.sqlite3",
    Path.home() / ".local" / "share" / "aycf-trip-planner" / "travel-journal.sqlite3",
]


def detect_source(explicit: str | None) -> Path:
    if explicit:
        path = Path(explicit).expanduser()
        if not path.exists():
            raise SystemExit(f"AYCF journal not found: {path}")
        return path
    for candidate in SOURCE_CANDIDATES:
        if candidate and candidate.exists():
            return candidate
    checked = "\n  ".join(str(p) for p in SOURCE_CANDIDATES if p)
    raise SystemExit(
        "Could not find the AYCF travel journal automatically. Checked:\n  " + checked +
        "\nPass its path with --source."
    )


def ensure_target_schema(db: sqlite3.Connection) -> None:
    db.execute(
        """CREATE TABLE IF NOT EXISTS places (
            id INTEGER PRIMARY KEY,
            country TEXT NOT NULL,
            place TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL,
            start_date TEXT NOT NULL DEFAULT '',
            end_date TEXT NOT NULL DEFAULT '',
            notes TEXT NOT NULL DEFAULT '',
            UNIQUE(country, place, start_date, end_date, status)
        )"""
    )


def migrate(source: Path, target: Path, dry_run: bool = False) -> tuple[int, int]:
    source_db = sqlite3.connect(source.resolve().as_uri() + "?mode=ro", uri=True)
    source_db.row_factory = sqlite3.Row
    try:
        columns = {row[1] for row in source_db.execute("PRAGMA table_info(places)")}
        required = {"country", "place", "status", "visited_on", "notes"}
        if not required.issubset(columns):
            missing = ", ".join(sorted(required - columns))
            raise SystemExit(f"Source database is not the expected AYCF Places journal; missing columns: {missing}")
        rows = [dict(r) for r in source_db.execute(
            "SELECT country, place, status, visited_on, notes FROM places ORDER BY id"
        )]
    finally:
        source_db.close()

    from app import validate
    values = []
    for row in rows:
        try:
            values.append(validate({**row, "start_date": row["visited_on"], "end_date": row["visited_on"]}))
        except ValueError as exc:
            raise SystemExit(f"Invalid AYCF record ({row['country']}, {row['place']}): {exc}") from exc
    if dry_run:
        return len(rows), 0

    target.parent.mkdir(parents=True, exist_ok=True)
    target_db = sqlite3.connect(target)
    try:
        ensure_target_schema(target_db)
        inserted = 0
        for row in values:
            cursor = target_db.execute(
                """INSERT OR IGNORE INTO places(country, place, status, start_date, end_date, notes)
                   VALUES(:country,:place,:status,:start_date,:end_date,:notes)""", row)
            inserted += cursor.rowcount
        target_db.commit()
    finally:
        target_db.close()
    return len(rows), inserted


def main() -> int:
    parser = argparse.ArgumentParser(description="Migrate AYCF Places data to the standalone Places app")
    parser.add_argument("--source", help="Path to AYCF travel-journal.sqlite3")
    parser.add_argument("--target", default=str(DEFAULT_TARGET), help="Destination Places database")
    parser.add_argument("--dry-run", action="store_true", help="Validate and count rows without writing")
    args = parser.parse_args()

    source = detect_source(args.source)
    target = Path(args.target).expanduser()
    total, inserted = migrate(source, target, args.dry_run)
    print(f"Source: {source}")
    print(f"Target: {target}")
    if args.dry_run:
        print(f"Validated {total} AYCF place record(s); no changes written.")
    else:
        print(f"Processed {total} record(s); inserted {inserted}; skipped {total - inserted} existing duplicate(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

import os
import sqlite3
from contextlib import contextmanager
from datetime import date, timedelta
from pathlib import Path

import pycountry
from flask import Flask, abort, jsonify, render_template, request

APP_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.environ.get("PLACES_DATA_DIR", Path.home() / ".local" / "share" / "places"))
DB_PATH = Path(os.environ.get("PLACES_DB_PATH", DATA_DIR / "places.sqlite3"))

app = Flask(__name__)

COUNTRIES = sorted(
    [{"code": c.alpha_2, "name": c.name} for c in pycountry.countries],
    key=lambda c: c["name"],
)
# AYCF also supports Kosovo, which has no ISO 3166 entry in pycountry.
COUNTRIES.append({"code": "XK", "name": "Kosovo"})
COUNTRIES.sort(key=lambda c: c["name"])
COUNTRY_CODES = {c["code"] for c in COUNTRIES}


@contextmanager
def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB_PATH, timeout=15)
    db.row_factory = sqlite3.Row
    try:
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
        yield db
        db.commit()
    finally:
        db.close()


def validate(payload):
    if not isinstance(payload, dict):
        raise ValueError("Enter a place to save.")
    country = str(payload.get("country", "")).strip().upper()
    place = str(payload.get("place", "")).strip()
    status = str(payload.get("status", "")).strip()
    start_date = str(payload.get("start_date", "")).strip()
    end_date = str(payload.get("end_date", "")).strip()
    notes = str(payload.get("notes", "")).strip()

    if country not in COUNTRY_CODES:
        raise ValueError("Choose a valid country.")
    if len(place) > 120 or len(notes) > 4000:
        raise ValueError("One of the fields is too long.")
    if status not in {"visited", "wishlist"}:
        raise ValueError("Choose visited or wishlist.")

    if status == "wishlist":
        start_date = end_date = ""
    else:
        if bool(start_date) != bool(end_date):
            end_date = start_date or end_date
            start_date = start_date or end_date
        if start_date:
            try:
                start = date.fromisoformat(start_date)
                end = date.fromisoformat(end_date)
            except ValueError as exc:
                raise ValueError("Enter valid travel dates.") from exc
            if end < start:
                raise ValueError("End date cannot be before start date.")
            if not (1900 <= start.year <= end.year <= 2200):
                raise ValueError("Travel dates must be between 1900 and 2200.")
            start_date, end_date = start.isoformat(), end.isoformat()

    return {
        "country": country,
        "place": place,
        "status": status,
        "start_date": start_date,
        "end_date": end_date,
        "notes": notes,
    }


def iter_days(start_text, end_text):
    if not start_text:
        return
    current = date.fromisoformat(start_text)
    end = date.fromisoformat(end_text or start_text)
    while current <= end:
        yield current
        if current == end:
            break
        current += timedelta(days=1)


@app.get("/")
def home():
    return render_template("index.html", countries=COUNTRIES, current_year=date.today().year)


@app.get("/health")
def health():
    with connect() as db:
        db.execute("SELECT 1").fetchone()
    return jsonify(ok=True, database="ready")


@app.get("/api/places")
def list_places():
    with connect() as db:
        rows = [dict(r) for r in db.execute(
            "SELECT * FROM places ORDER BY start_date DESC, id DESC"
        )]
    return jsonify(places=rows)


@app.post("/api/places")
def create_place():
    try:
        values = validate(request.get_json(silent=True))
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
    try:
        with connect() as db:
            cursor = db.execute(
                """INSERT INTO places(country, place, status, start_date, end_date, notes)
                VALUES(:country,:place,:status,:start_date,:end_date,:notes)""",
                values,
            )
            new_id = cursor.lastrowid
    except sqlite3.IntegrityError:
        return jsonify(error="That trip or place already exists."), 409
    return jsonify(id=new_id), 201


@app.put("/api/places/<int:record_id>")
def update_place(record_id):
    try:
        values = validate(request.get_json(silent=True))
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
    values["id"] = record_id
    try:
        with connect() as db:
            cursor = db.execute(
                """UPDATE places SET country=:country,place=:place,status=:status,
                start_date=:start_date,end_date=:end_date,notes=:notes WHERE id=:id""",
                values,
            )
            if not cursor.rowcount:
                abort(404)
    except sqlite3.IntegrityError:
        return jsonify(error="That trip or place already exists."), 409
    return jsonify(id=record_id)


@app.delete("/api/places/<int:record_id>")
def delete_place(record_id):
    with connect() as db:
        if not db.execute("DELETE FROM places WHERE id=?", (record_id,)).rowcount:
            abort(404)
    return "", 204


@app.get("/api/calendar/<int:year>")
def calendar(year):
    if year < 1900 or year > 2200:
        abort(400)
    day_map = {}
    with connect() as db:
        rows = [dict(r) for r in db.execute(
            "SELECT * FROM places WHERE status='visited' AND start_date<>''"
        )]
    for row in rows:
        start = max(row["start_date"], f"{year}-01-01")
        end = min(row["end_date"] or row["start_date"], f"{year}-12-31")
        for day in iter_days(start, end):
            if day.year != year:
                continue
            key = day.isoformat()
            day_map.setdefault(key, []).append({
                "id": row["id"], "country": row["country"], "place": row["place"]
            })
    return jsonify(year=year, days=day_map)


@app.get("/api/export")
def export_data():
    with connect() as db:
        rows = [dict(r) for r in db.execute("SELECT * FROM places ORDER BY id")]
    response = jsonify(version=1, places=rows)
    response.headers["Content-Disposition"] = "attachment; filename=places-export.json"
    return response


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("PLACES_PORT", "8084")), debug=False)

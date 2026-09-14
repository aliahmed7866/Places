# Places

A local-first personal travel journal extracted from the AYCF trip planner.

## Features

- Year-in-travel calendar with country flags on every travelled day
- Multi-day trip ranges and multiple countries on the same day
- Visited and wishlist entries
- Searchable travel journal with notes
- Country, travel-day, trip and wishlist totals
- JSON export
- SQLite storage kept outside the repository by default
- Local-only Flask server on `127.0.0.1:8084`

## Run

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open `http://127.0.0.1:8084`.

Data defaults to `~/.local/share/places/places.sqlite3`. Override with `PLACES_DB_PATH` or `PLACES_DATA_DIR`.

## Tests

```bash
python -m unittest discover -s tests -v
```

## AYCF migration

The old AYCF Places feature stored a single `visited_on` date. When moving existing data over, map that date to both `start_date` and `end_date`. New entries support full date ranges so the travel calendar can mark every day of a trip.

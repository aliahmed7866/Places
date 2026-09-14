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

## Termux

For the local Android setup:

```bash
bash termux/install.sh
```

The installer creates a `places` command. Useful commands are:

```bash
places start
places status
places logs
places restart
places update
places stop
```

The service runs locally on `http://127.0.0.1:8084` and stores runtime state under `~/.local/state/places`.

## AYCF migration

The old AYCF Places feature stored a single `visited_on` date. The migration utility maps that date to both `start_date` and `end_date`; new entries support full date ranges so the travel calendar can mark every day of a trip.

On Termux, after installing Places:

```bash
places migrate --dry-run
places migrate
```

The migration automatically checks the usual AYCF journal locations and is safe to re-run: existing matching rows are skipped. If the old journal lives elsewhere, provide it explicitly:

```bash
places migrate --source /path/to/travel-journal.sqlite3
```

The old AYCF database is opened read-only and is never modified.

## Tests

```bash
python -m unittest discover -s tests -v
```

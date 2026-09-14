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

The installer uses the current checkout, creates `~/.local/bin/places`, saves runtime settings under `~/.config/places/env`, and registers Places in the Admin Hub without replacing other apps. It also creates a Termux:Boot startup script; Android boot startup requires Termux:Boot to be installed. The installer creates a `places` command. Useful commands are:

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

## Custom port or data directory

If another app already uses 8084, choose a free port before installing:

```bash
PLACES_PORT=8094 bash termux/install.sh
```

`PLACES_DATA_DIR` and `PLACES_DB_PATH` are also saved by the installer and reused by the service and migration. Registered port conflicts stop installation without replacing the registry. Updates follow this repository's `main` branch; the separate AYCF/Hub integration targets AYCF's `deploy/termux` branch.

Calendar dates are supported from 1900 through 2200. Overlapping entries count once per travel day. Duplicate edits return a clear conflict, preserving both records. Migration validates all source rows before writing and leaves the AYCF journal intact. A dry run validates source records, but does not compare them with existing target records.

For the full regression suite (including installer/service simulations), install pytest and run `python -m pytest -q`.

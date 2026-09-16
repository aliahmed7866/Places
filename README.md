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

## Map and travel planner

Places opens on the interactive world map. Visited countries are green, planned destinations blue and wishlist countries clay; visited takes visual priority when a country has several kinds of entries. Zoom controls let you explore smaller countries. The bundled Natural Earth map needs no external tile provider or API key. Small islands remain selectable through Add a place.

The separate Planner opens on one month with large date buttons. Tap a day to choose a country, optionally extend the end date, and save its flag across the range. Flagged days show existing entries for editing and still allow another country to be added. Month/year selectors, previous/next controls and a Year overview support longer trips. Planned trips retain dates without increasing visited totals; change their status to Visited after travelling. Existing entries and dates are retained, and the Journal remains available for search, editing and export.

## Detailed atlas and country memories

The map bundles Natural Earth 1:50m outlines for 237 countries and territories, including coastlines and smaller islands. Drag to pan, pinch or use the buttons to zoom, search any country, or choose a continent. Country labels appear as you zoom closer. Keyboard users can focus countries and press Enter; the map supports arrow keys and +/−. Ctrl+wheel zooms; ordinary wheel scrolling stays available outside the focused map. This is a country atlas, not a street-map or navigation service.

Selecting a country opens its visits, date ranges and notes, plus buttons to add a visit or planned trip. Regional progress counts mapped countries and territories; it is not a count of sovereign states.

Each country can have an Instagram Highlight/profile link and a saved cover photo. These are manually added memories: the app does not connect to Instagram accounts, scrape Highlights or synchronize Instagram images. Save an image you own to your device, select the country and choose **Add a saved cover photo**. The browser resizes the image before storing it in the existing external SQLite database. JPEG and PNG uploads are supported, up to 2 MB after resizing. Country photos and links are included in the version 2 JSON export. They are retained independently of itinerary entries.

The finer map is bundled and has no new Termux dependencies. To regenerate it during development, install Shapely and run `python tools/build_atlas.py /path/to/ne_50m_admin_0_countries.geojson`; provenance is recorded in `static/places-map-source.txt`.

## Earth globe

The atlas now uses a rotatable orthographic globe with ocean lighting and a shaded edge. Drag or use arrow keys to rotate, pinch or use +/− to zoom. Country search rotates the selected country to the front. Labels are HTML overlays with adjustable screen-sized text and measured spacing to avoid collisions; they do not stretch with the globe. Countries beyond the horizon are clipped. D3 7.9.0 and the map geometry are bundled locally, so this requires no tile service, API key or new Termux package.

## Clear country labels and expanded exploration

Country labels have Standard (15px), Large (18px), and Extra large (21px) settings. They stay upright at a constant screen size, wrap long names, and use opaque high-contrast backgrounds. Each label connects to a dot inside its country; labels can be tapped to open that country's memories. The selected country gets first priority, followed by saved destinations and larger countries, so small territories do not crowd out major country names. Overlapping labels are omitted, while **Countries in view** lists every visible country anchor for easy selection of crowded countries and islands. **Expand map** gives the globe more room.

Country names are shared across the map, search, planner and forms; the two Congos and the two Koreas have distinct labels. Search also accepts two-letter country codes and the bundled atlas names. All 237 bundled anchors are checked against their corresponding spherical country geometry with `node tests/test_globe_geometry.js`. This remains a country-level globe; no terrain elevation, street maps or live satellite imagery is included.

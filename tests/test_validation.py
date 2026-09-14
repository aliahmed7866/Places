import importlib
import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setenv('PLACES_DB_PATH', str(tmp_path / 'places.sqlite3'))
    import app
    return importlib.reload(app).app.test_client()


def record(**kw):
    return {'country': 'GE', 'place': 'Mestia', 'status': 'visited',
            'start_date': '2026-09-30', 'end_date': '2026-10-02', **kw}


def test_duplicate_update_is_conflict_and_preserves_records(client):
    first = client.post('/api/places', json=record()).json['id']
    second = client.post('/api/places', json=record(place='Tbilisi')).json['id']
    assert client.put(f'/api/places/{second}', json=record()).status_code == 409
    rows = client.get('/api/places').json['places']
    assert {r['place'] for r in rows} == {'Mestia', 'Tbilisi'}


def test_cross_year_overlap_leap_day_and_normalization(client):
    assert client.post('/api/places', json=record(start_date='2023-12-31', end_date='2024-03-01')).status_code == 201
    assert client.post('/api/places', json=record(country='GB', start_date='2024-02-29', end_date='')).status_code == 201
    days = client.get('/api/calendar/2024').json['days']
    assert len(days) == 61
    assert {x['country'] for x in days['2024-02-29']} == {'GE', 'GB'}
    assert len(client.get('/api/calendar/2023').json['days']) == 1
    assert client.post('/api/places', json=record(start_date='9999-12-31', end_date='')).status_code == 400
    assert client.get('/api/calendar/1800').status_code == 400


def test_custom_migration_target_and_invalid_dry_run(monkeypatch, tmp_path):
    monkeypatch.delenv('PLACES_DB_PATH', raising=False)
    monkeypatch.setenv('PLACES_DATA_DIR', str(tmp_path / 'custom'))
    import migrate_aycf
    migration = importlib.reload(migrate_aycf)
    assert migration.DEFAULT_TARGET == tmp_path / 'custom/places.sqlite3'
    source = tmp_path / 'old?#.sqlite3'
    with sqlite3.connect(source) as db:
        db.execute('CREATE TABLE places(id INTEGER PRIMARY KEY,country,place,status,visited_on,notes)')
        db.execute("INSERT INTO places VALUES(1,'GE','Mestia','visited','bad date','')")
    with pytest.raises(SystemExit, match='Invalid AYCF record'):
        migration.migrate(source, migration.DEFAULT_TARGET, dry_run=True)
    assert not migration.DEFAULT_TARGET.exists()


def test_registration_preserves_apps_and_custom_paths(tmp_path):
    from termux.register import install
    root = tmp_path / 'custom checkout'
    registry = tmp_path / '.config/aycf/apps.json'
    registry.parent.mkdir(parents=True)
    registry.write_text(json.dumps({'apps': [{'id': 'mediahub', 'name': 'Media Hub', 'port': 8084}]}))
    env = {'PLACES_PORT': '8094', 'PLACES_DATA_DIR': str(tmp_path / 'my data')}
    install(tmp_path, root, env)
    install(tmp_path, root, env)
    rows = json.loads(registry.read_text())['apps']
    assert len(rows) == 2 and rows[0]['port'] == 8084
    assert rows[1]['port'] == 8094
    assert (tmp_path / '.local/bin/places').exists()
    assert '8094' in (tmp_path / '.config/places/env').read_text()
    assert (tmp_path / '.termux/boot/15-places').exists()


def test_stale_pid_does_not_stop_unrelated_process(tmp_path):
    state = tmp_path / '.local/state/places'
    state.mkdir(parents=True)
    sleeper = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'])
    try:
        (state / 'places.pid').write_text(str(sleeper.pid))
        result = subprocess.run(['bash', str(ROOT / 'termux/run.sh'), 'stop'],
            env={**os.environ, 'HOME': str(tmp_path), 'PLACES_APP_DIR': str(ROOT)}, capture_output=True, timeout=5)
        assert result.returncode == 0
        assert sleeper.poll() is None
    finally:
        sleeper.terminate()
        sleeper.wait()


def test_registration_port_conflict_leaves_registry_unchanged(tmp_path):
    from termux.register import install
    registry = tmp_path / '.config/aycf/apps.json'
    registry.parent.mkdir(parents=True)
    original = json.dumps({'apps': [{'id': 'mediahub', 'port': 8084}]})
    registry.write_text(original)
    with pytest.raises(ValueError, match='already registered'):
        install(tmp_path, ROOT, {})
    assert registry.read_text() == original


@pytest.mark.skipif(not Path("/proc/self/cmdline").exists(), reason="Service identity checks require procfs; exercised in Linux CI")
def test_installer_and_runtime_with_custom_home_and_paths(tmp_path):
    import shutil
    root = tmp_path / 'Places checkout'
    shutil.copytree(ROOT / 'termux', root / 'termux')
    shutil.copy(ROOT / 'app.py', root / 'app.py')
    shutil.copy(ROOT / 'requirements.txt', root / 'requirements.txt')
    bin_dir = tmp_path / 'fake-bin'
    bin_dir.mkdir()
    pkg = bin_dir / 'pkg'
    pkg.write_text('#!/bin/sh\nexit 0\n')
    pkg.chmod(0o700)
    # Simulate package installation only; execute the actual installer, registry,
    # wrapper, process controls and Flask application.
    python = bin_dir / 'python'
    python.write_text('#!/bin/sh\nexit 0\n')
    python.chmod(0o700)
    venv = root / '.venv/bin'
    venv.mkdir(parents=True)
    import shlex
    (venv / 'python').write_text('#!/bin/sh\nexec ' + shlex.quote(sys.executable) + ' "$@"\n')
    (venv / 'python').chmod(0o700)
    (venv / 'pip').write_text('#!/bin/sh\nexit 0\n')
    (venv / 'pip').chmod(0o700)
    import socket
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    env = {**os.environ, 'HOME': str(tmp_path), 'PATH': str(bin_dir) + ':' + os.environ['PATH'],
           'PLACES_APP_DIR': str(root), 'PLACES_DATA_DIR': str(tmp_path / 'data'), 'PLACES_PORT': str(port)}
    env.pop('PLACES_DB_PATH', None)
    subprocess.run(['bash', str(root / 'termux/install.sh')], env=env, check=True, capture_output=True)
    runtime_env = {k:v for k,v in env.items() if not k.startswith('PLACES_')}
    runner = tmp_path / '.local/bin/places'
    def run(action):
        return subprocess.run(['bash', str(runner), action], env=runtime_env, capture_output=True, text=True, timeout=12)
    try:
        assert run('start').returncode == 0
        status = run('status')
        assert status.returncode == 0 and f':{port}' in status.stdout
        from urllib.request import urlopen
        with urlopen(f'http://127.0.0.1:{port}/health', timeout=3) as response:
            assert json.load(response)['ok']
        assert (tmp_path / 'data/places.sqlite3').exists()
        assert run('restart').returncode == 0
    finally:
        run('stop')
    assert run('status').returncode == 1

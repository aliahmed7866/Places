"""Persist runtime paths and register Places without replacing other apps."""
import json
import os
from pathlib import Path
import shlex


def install(home, root, env):
    config = home / '.config/places'
    config.mkdir(parents=True, exist_ok=True)
    values = {'PLACES_APP_DIR': str(root), 'PLACES_PORT': env.get('PLACES_PORT', '8084'),
              'PLACES_DATA_DIR': env.get('PLACES_DATA_DIR', str(home / '.local/share/places'))}
    if env.get('PLACES_DB_PATH'):
        values['PLACES_DB_PATH'] = env['PLACES_DB_PATH']
    port = int(values['PLACES_PORT'])
    if not 1 <= port <= 65535:
        raise ValueError('Invalid Places port')
    registry = Path(env.get('AYCF_ADMIN_REGISTRY', str(Path(env.get('AYCF_CONFIG_DIR', str(home / '.config/aycf'))) / 'apps.json')))
    payload = json.loads(registry.read_text()) if registry.exists() else {'apps': []}
    if not isinstance(payload, dict) or not isinstance(payload.get('apps'), list):
        raise ValueError('Invalid Admin Hub registry; original file was preserved')
    existing = next((x for x in payload['apps'] if x.get('id') == 'places'), {})
    # Use an explicitly selected port, otherwise preserve a previously registered one.
    if 'PLACES_PORT' not in env and existing.get('port'):
        port = int(existing['port'])
        values['PLACES_PORT'] = str(port)
    occupied = {int(x['port']) for x in payload['apps'] if x.get('id') != 'places' and x.get('port')}
    if port in occupied:
        raise ValueError(f'Port {port} is already registered to another app; set PLACES_PORT to a free port')
    row = {**existing, 'id': 'places', 'name': 'Places', 'icon': '🌍',
           'description': 'Travel journal and year-in-travel calendar', 'manager': 'command',
           'working_dir': str(root), 'port': port, 'health_url': f'http://127.0.0.1:{port}/health',
           'open_url': f'http://127.0.0.1:{port}'}
    runner = home / '.local/bin/places'
    for action in ('status', 'start', 'stop', 'restart'):
        row[f'{action}_command'] = [str(runner), action]
    payload['apps'] = [x for x in payload['apps'] if x.get('id') != 'places'] + [row]
    registry.parent.mkdir(parents=True, exist_ok=True)
    temp = registry.with_suffix('.tmp')
    temp.write_text(json.dumps(payload, indent=2) + '\n')
    temp.replace(registry)
    (config / 'env').write_text(''.join(f'export {k}={shlex.quote(v)}\n' for k, v in values.items()))
    (config / 'env').chmod(0o600)
    runner.parent.mkdir(parents=True, exist_ok=True)
    runner.write_text('#!/data/data/com.termux/files/usr/bin/bash\nexec bash ' + shlex.quote(str(root / 'termux/run.sh')) + ' "$@"\n')
    runner.chmod(0o700)
    boot = home / '.termux/boot/15-places'
    boot.parent.mkdir(parents=True, exist_ok=True)
    boot.write_text('#!/data/data/com.termux/files/usr/bin/bash\nexec bash ' + shlex.quote(str(runner)) + ' start\n')
    boot.chmod(0o700)


if __name__ == '__main__':
    install(Path.home(), Path(os.environ.get('PLACES_APP_DIR', Path(__file__).resolve().parents[1])), os.environ)

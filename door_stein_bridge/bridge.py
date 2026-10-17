"""Door Stein test bridge. No hardware actions. Python 3, HA Supervisor API."""
import hashlib
import hmac
import json
import logging
import os
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import requests
import yaml

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
LOG = logging.getLogger('door-stein')
OPTIONS = '/data/options.json'
DB_PATH = '/data/processed.sqlite3'
HA_BASE = 'http://supervisor/core/api'
ENTITIES = {
    'building': 'input_boolean.door_stein_hauseingang',
    'apartment': 'input_boolean.door_stein_wohnungstuer',
}


def load_config():
    options = json.loads(Path(OPTIONS).read_text(encoding='utf-8'))
    worker = options['worker_url'].rstrip('/')
    parsed = urlparse(worker)
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in ('', '/'):
        raise ValueError('worker_url muss eine HTTPS-Origin ohne Pfad sein')
    secret_file = options.get('secrets_file', 'secrets.yaml')
    if Path(secret_file).name != secret_file:
        raise ValueError('secrets_file darf nur ein Dateiname sein')
    data = yaml.safe_load((Path('/homeassistant') / secret_file).read_text(encoding='utf-8')) or {}
    token = data.get('door_stein_api_token')
    secret = data.get('door_stein_hmac_secret')
    if not isinstance(token, str) or not isinstance(secret, str) or len(token) < 32 or len(secret) < 32:
        raise ValueError('door_stein_api_token und door_stein_hmac_secret fehlen oder sind zu kurz')
    supervisor = os.environ.get('SUPERVISOR_TOKEN') or os.environ.get('HASSIO_TOKEN')
    if not supervisor:
        present = [name for name in ('SUPERVISOR_TOKEN', 'HASSIO_TOKEN') if os.environ.get(name)]
        raise ValueError('Supervisor-API-Token fehlt (SUPERVISOR_TOKEN/HASSIO_TOKEN); App-Berechtigungen und installierte Version prüfen. Token-Variablen vorhanden: ' + ','.join(present))
    return options, worker, token, secret.encode('utf-8'), supervisor


def parse_expiry(raw):
    if not isinstance(raw, str):
        raise ValueError('Ungültige Ablaufzeit')
    value = datetime.fromisoformat(raw.replace('Z', '+00:00'))
    if value.tzinfo is None:
        raise ValueError('Ablaufzeit ohne Zeitzone')
    return value.timestamp()


def validate(job, secret):
    job_id, door, expiry, signature = (job.get(k) for k in ('id', 'door_id', 'expires_at', 'signature'))
    if not all(isinstance(x, str) for x in (job_id, door, expiry, signature)):
        raise ValueError('Auftrag unvollständig')
    if len(job_id) > 100 or door not in ENTITIES or len(signature) != 64:
        raise ValueError('Auftrag ungültig')
    msg = f'door-stein-v1\n{job_id}\n{door}\n{expiry}'.encode('utf-8')
    expected = hmac.new(secret, msg, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        raise ValueError('HMAC-Prüfung fehlgeschlagen')
    if not (time.time() < parse_expiry(expiry) <= time.time() + 30):
        raise ValueError('Auftrag abgelaufen oder zeitlich ungültig')
    return job_id, door, signature


def mark_once(db, job_id):
    try:
        with db:
            db.execute('INSERT INTO processed(id, processed_at) VALUES(?, ?)', (job_id, int(time.time())))
        return True
    except sqlite3.IntegrityError:
        return False


def ha_call(session, supervisor_token, entity, service):
    response = session.post(
        f'{HA_BASE}/services/input_boolean/{service}',
        headers={'Authorization': f'Bearer {supervisor_token}'},
        json={'entity_id': entity}, timeout=4,
    )
    response.raise_for_status()


def ack(session, worker, token, job_id, signature, status):
    response = session.post(f'{worker}/api/ha/ack',
                            headers={'Authorization': f'Bearer {token}'},
                            json={'id': job_id, 'status': status, 'signature': signature}, timeout=5)
    response.raise_for_status()


def run():
    options, worker, token, secret, supervisor_token = load_config()
    interval = max(2, min(60, int(options.get('poll_seconds', 5))))
    pulse = max(1, min(5, int(options.get('pulse_seconds', 1))))
    db = sqlite3.connect(DB_PATH)
    db.execute('PRAGMA journal_mode=WAL')
    db.execute('CREATE TABLE IF NOT EXISTS processed (id TEXT PRIMARY KEY, processed_at INTEGER NOT NULL)')
    db.commit()
    http = requests.Session()
    LOG.info('Bridge gestartet: Testbetrieb, Polling alle %d Sekunden', interval)
    while True:
        try:
            response = http.get(f'{worker}/api/ha/poll', headers={'Authorization': f'Bearer {token}'}, timeout=5)
            response.raise_for_status()
            data = response.json()
            if data.get('emergency_stop') is True:
                LOG.info('Testbetrieb gesperrt (Not-Aus)')
            elif data.get('emergency_stop') is not False:
                LOG.error('Unerwartete Not-Aus-Antwort: keine Ausführung')
            else:
                for job in data.get('jobs', []):
                    job_id = job.get('id', '?') if isinstance(job, dict) else '?'
                    try:
                        job_id, door, signature = validate(job, secret)
                        if not mark_once(db, job_id):
                            LOG.warning('Auftrag bereits verarbeitet: %s', job_id)
                            continue
                        # Markierung erfolgt persistent VOR der Aktion. Kein erneutes Schalten nach Fehler.
                        entity = ENTITIES[door]
                        try:
                            ha_call(http, supervisor_token, entity, 'turn_on')
                            time.sleep(pulse)
                        finally:
                            # Auch bei Fehlern immer versuchen, den Test-Helper auszuschalten.
                            ha_call(http, supervisor_token, entity, 'turn_off')
                        ack(http, worker, token, job_id, signature, 'completed')
                        LOG.info('Testimpuls bestätigt: %s (%s)', job_id, door)
                    except Exception as exc:
                        LOG.error('Auftrag %s fehlgeschlagen: %s', job_id, exc)
                        # Best effort: niemals dieselbe Aktion erneut ausführen.
                        if isinstance(job, dict) and isinstance(job.get('signature'), str) and isinstance(job.get('id'), str):
                            try:
                                ack(http, worker, token, job['id'], job['signature'], 'cancelled')
                            except Exception:
                                pass
        except Exception as exc:
            LOG.error('Polling fehlgeschlagen: %s', exc)
        time.sleep(interval)


if __name__ == '__main__':
    run()

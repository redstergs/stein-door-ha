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
AUDIT_RETENTION_DAYS = 30
AUDIT_MAX_ROWS = 1000
ERROR_REPEAT_SECONDS = 300
AUDIT_CLEANUP_SECONDS = 86400
# HA input_boolean is the local permission gate; unknown state fails closed.

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
    current = time.time()
    if not (current < parse_expiry(expiry) <= current + 30):
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


FREIGABE_ENTITY = 'input_boolean.door_stein_freigabe'


def locally_enabled(session, supervisor_token):
    response = session.get(f'{HA_BASE}/states/{FREIGABE_ENTITY}',
        headers={'Authorization': f'Bearer {supervisor_token}'}, timeout=4)
    response.raise_for_status()
    state = response.json()
    return isinstance(state, dict) and state.get('entity_id') == FREIGABE_ENTITY and state.get('state') == 'on'


def ack(session, worker, token, job_id, signature, status):
    response = session.post(f'{worker}/api/ha/ack',
                            headers={'Authorization': f'Bearer {token}'},
                            json={'id': job_id, 'status': status, 'signature': signature}, timeout=5)
    response.raise_for_status()


def audit(db, job_id, door, event, detail=''):
    # Local audit log persists across restarts; no credentials or personal data.
    with db:
        db.execute('INSERT INTO bridge_audit(job_id,door_id,event,detail,created_at) VALUES(?,?,?,?,?)',
                   (str(job_id)[:100], str(door)[:32], event, str(detail)[:160],
                    datetime.now(timezone.utc).isoformat()))


def initialize_db(db):
    db.execute('PRAGMA journal_mode=WAL')
    db.execute('CREATE TABLE IF NOT EXISTS processed (id TEXT PRIMARY KEY, processed_at INTEGER NOT NULL)')
    db.execute('CREATE TABLE IF NOT EXISTS bridge_audit (seq INTEGER PRIMARY KEY AUTOINCREMENT, job_id TEXT, door_id TEXT, event TEXT NOT NULL, detail TEXT, created_at TEXT NOT NULL)')
    db.commit()


def prune_audit(db):
    """Prune only human-readable audit events, NEVER the replay-protection table."""
    cutoff = datetime.fromtimestamp(time.time() - AUDIT_RETENTION_DAYS * 86400, timezone.utc).isoformat()
    with db:
        db.execute('DELETE FROM bridge_audit WHERE created_at < ?', (cutoff,))
        db.execute("""DELETE FROM bridge_audit WHERE seq NOT IN
                      (SELECT seq FROM bridge_audit ORDER BY seq DESC LIMIT ?)""", (AUDIT_MAX_ROWS,))
    remaining = db.execute('SELECT COUNT(*) FROM bridge_audit').fetchone()[0]
    LOG.info('Audit-Pflege: maximal %d Einträge / %d Tage; aktuell %d Einträge; Duplikatschutz unverändert',
             AUDIT_MAX_ROWS, AUDIT_RETENTION_DAYS, remaining)


class ErrorReporter:
    """Log first failure, then periodic summaries; log a single recovery."""
    def __init__(self):
        self.states = {}

    def failure(self, channel, exc):
        now = time.monotonic()
        state = self.states.get(channel)
        kind = type(exc).__name__
        detail = str(exc)
        if state is None:
            LOG.error('%s fehlgeschlagen (%s): %s', channel, kind, detail)
            self.states[channel] = [now, 1]
        else:
            state[1] += 1
            if now - state[0] >= ERROR_REPEAT_SECONDS:
                LOG.error('%s weiterhin gestört: %d Fehler seit letzter Meldung; letzter Fehler (%s): %s',
                          channel, state[1], kind, detail)
                state[0], state[1] = now, 0

    def success(self, channel):
        if channel in self.states:
            LOG.info('%s wieder erreichbar', channel)
            del self.states[channel]


def run():
    options, worker, token, secret, supervisor_token = load_config()
    if options.get('security_selftest', True):
        from security_selftest import run_selftest
        run_selftest()
    interval = max(2, min(60, int(options.get('poll_seconds', 5))))
    pulse = max(1, min(5, int(options.get('pulse_seconds', 1))))
    db = sqlite3.connect(DB_PATH)
    initialize_db(db)
    prune_audit(db)
    next_cleanup = time.monotonic() + AUDIT_CLEANUP_SECONDS
    reporter = ErrorReporter()
    http = requests.Session()
    LOG.info('Door Stein Bridge 0.4.0: TESTBETRIEB, Polling alle %d Sekunden; keine echten Schlösser', interval)
    LOG.info('Lokale HA-Freigabe wird vor jedem Auftrag geprüft; lokales Audit aktiviert')
    while True:
        try:
            if time.monotonic() >= next_cleanup:
                prune_audit(db)
                next_cleanup = time.monotonic() + AUDIT_CLEANUP_SECONDS
            # Separate diagnostic channel. Never maps to Home Assistant service calls.
            try:
                diagnostic_response = http.get(f'{worker}/api/ha/diagnostics/poll',
                    headers={'Authorization': f'Bearer {token}'}, timeout=5)
                diagnostic_response.raise_for_status()
                reporter.success('Diagnose-Polling')
                diagnostic_data = diagnostic_response.json()
                if not isinstance(diagnostic_data, dict) or not isinstance(diagnostic_data.get('jobs'), list):
                    raise ValueError('Ungültiges Diagnoseformat')
                from diagnostic_tests import execute_diagnostic
                for diagnostic in diagnostic_data['jobs']:
                    if not isinstance(diagnostic, dict):
                        continue
                    try:
                        result = execute_diagnostic(diagnostic, secret, db)
                        audit(db, diagnostic.get('id', '?'), 'diagnostic',
                              'diagnostic_passed' if result['passed'] else 'diagnostic_failed', diagnostic.get('test_type', '?'))
                        LOG.info('DIAGNOSE %s: %s – %s', 'BESTANDEN' if result['passed'] else 'FEHLGESCHLAGEN', diagnostic.get('test_type'), result['message'])
                        response_result = http.post(f'{worker}/api/ha/diagnostics/result',
                            headers={'Authorization': f'Bearer {token}'},
                            json={'id': diagnostic['id'], 'signature': diagnostic['signature'], **result}, timeout=5)
                        response_result.raise_for_status()
                    except Exception as exc:
                        LOG.error('Diagnoseauftrag abgelehnt/fehlgeschlagen: %s', type(exc).__name__)
            except Exception as exc:
                reporter.failure('Diagnose-Polling', exc)
            response = http.get(f'{worker}/api/ha/poll', headers={'Authorization': f'Bearer {token}'}, timeout=5)
            response.raise_for_status()
            reporter.success('Auftrags-Polling')
            data = response.json()
            if not isinstance(data, dict) or not isinstance(data.get('jobs'), list):
                raise ValueError('Ungültiges Polling-Antwortformat')
            if data.get('emergency_stop') is True:
                LOG.info('Testbetrieb gesperrt (Cloudflare-Not-Aus)')
            elif data.get('emergency_stop') is not False:
                LOG.error('Unerwartete Not-Aus-Antwort: keine Ausführung')
            else:
                for job in data.get('jobs', []):
                    job_id = job.get('id', '?') if isinstance(job, dict) else '?'
                    try:
                        job_id, door, signature = validate(job, secret)
                        if not mark_once(db, job_id):
                            audit(db, job_id, door, 'duplicate_rejected')
                            LOG.warning('Auftrag bereits verarbeitet: %s', job_id)
                            continue
                        audit(db, job_id, door, 'claimed_locally')
                        # Markierung erfolgt persistent VOR der Aktion. Kein erneutes Schalten nach Fehler.
                        if not locally_enabled(http, supervisor_token):
                            audit(db, job_id, door, 'local_gate_denied')
                            LOG.warning('Lokale Freigabe AUS oder nicht verfügbar: Auftrag %s blockiert', job_id)
                            ack(http, worker, token, job_id, signature, 'cancelled')
                            continue
                        entity = ENTITIES[door]
                        # Zuerst sicherstellen, dass der Helper nicht bereits eingeschaltet ist.
                        ha_call(http, supervisor_token, entity, 'turn_off')
                        try:
                            if not locally_enabled(http, supervisor_token):
                                audit(db, job_id, door, 'local_gate_denied')
                                ack(http, worker, token, job_id, signature, 'cancelled')
                                continue
                            ha_call(http, supervisor_token, entity, 'turn_on')
                            time.sleep(pulse)
                        finally:
                            # Auch bei Fehlern immer versuchen, den Test-Helper auszuschalten.
                            ha_call(http, supervisor_token, entity, 'turn_off')
                        audit(db, job_id, door, 'pulse_finished')
                        ack(http, worker, token, job_id, signature, 'completed')
                        audit(db, job_id, door, 'ack_completed')
                        LOG.info('Testimpuls bestätigt: %s (%s)', job_id, door)
                    except Exception as exc:
                        LOG.error('Auftrag %s fehlgeschlagen: %s', job_id, exc)
                        audit(db, job_id, job.get('door_id', '?') if isinstance(job, dict) else '?', 'error', type(exc).__name__)
                        # Best effort: niemals dieselbe Aktion erneut ausführen.
                        if isinstance(job, dict) and isinstance(job.get('signature'), str) and isinstance(job.get('id'), str):
                            try:
                                # No cancellation ACK after a pulse: execution outcome may be ambiguous.
                                if not db.execute("SELECT 1 FROM bridge_audit WHERE job_id=? AND event='pulse_finished'", (job['id'],)).fetchone():
                                    ack(http, worker, token, job['id'], job['signature'], 'cancelled')
                            except Exception:
                                pass
        except Exception as exc:
            reporter.failure('Auftrags-Polling', exc)
        time.sleep(interval)


if __name__ == '__main__':
    run()

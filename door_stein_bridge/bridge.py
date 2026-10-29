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
}
LOCK_ENTITY = 'lock.door_stein_wohnungstur_testschloss'
LOCK_ACTIONS = {'lock': ('lock', 'locked'), 'unlock': ('unlock', 'unlocked'), 'open': ('open', 'unlocked')}


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
    """Legacy v1 is allowed only for the building impulse. Apartment requires signed v2 action."""
    if not isinstance(job, dict):
        raise ValueError('Auftrag ist kein Objekt')
    job_id, door, expiry, signature = (job.get(k) for k in ('id', 'door_id', 'expires_at', 'signature'))
    if not all(isinstance(x, str) for x in (job_id, door, expiry, signature)):
        raise ValueError('Auftrag unvollständig')
    if not (1 <= len(job_id) <= 100) or len(signature) != 64:
        raise ValueError('Auftrag ungültig')
    if door == 'building' and 'action' not in job and 'version' not in job:
        action = 'pulse'
        msg = f'door-stein-v1\n{job_id}\n{door}\n{expiry}'.encode('utf-8')
    elif door == 'apartment' and job.get('version') == 2 and job.get('action') in LOCK_ACTIONS:
        action = job['action']
        msg = f'door-stein-v2\n{job_id}\n{door}\n{action}\n{expiry}'.encode('utf-8')
    else:
        raise ValueError('Nicht unterstützte Tür, Aktion oder Protokollversion')
    expected = hmac.new(secret, msg, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        raise ValueError('HMAC-Prüfung fehlgeschlagen')
    current = time.time()
    if not (current < parse_expiry(expiry) <= current + 30):
        raise ValueError('Auftrag abgelaufen oder zeitlich ungültig')
    return job_id, door, signature, action


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


def lock_state(session, supervisor_token):
    response = session.get(f'{HA_BASE}/states/{LOCK_ENTITY}',
        headers={'Authorization': f'Bearer {supervisor_token}'}, timeout=4)
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict) or payload.get('entity_id') != LOCK_ENTITY:
        raise ValueError('Ungültige Schlosszustandsantwort')
    return payload.get('state')


def lock_action(session, supervisor_token, action):
    response = session.post(f'{HA_BASE}/services/lock/{action}',
        headers={'Authorization': f'Bearer {supervisor_token}'},
        json={'entity_id': LOCK_ENTITY}, timeout=4)
    response.raise_for_status()


def execute_lock(session, supervisor_token, job, action, db):
    """Fail closed. No retries of lock.open; unknown results are never successes."""
    if action not in LOCK_ACTIONS:
        raise ValueError('Unbekannte Schlossaktion')
    if not locally_enabled(session, supervisor_token):
        raise PermissionError('Lokale Freigabe ausgeschaltet')
    before = lock_state(session, supervisor_token)
    if before not in ('locked', 'unlocked'):
        raise UnsafeOutput('Schlosszustand nicht eindeutig')
    if action == 'open' and before != 'unlocked':
        raise PermissionError('Falle ziehen nur bei bestätigtem unlocked')
    if time.time() >= parse_expiry(job['expires_at']):
        raise ValueError('Auftrag vor Schlossaktion abgelaufen')
    # Immediately re-read both gates before the irreversible latch command.
    if not locally_enabled(session, supervisor_token):
        raise PermissionError('Lokale Freigabe entzogen')
    if action == 'open' and lock_state(session, supervisor_token) != 'unlocked':
        raise UnsafeOutput('Schloss unmittelbar vor Falleziehen nicht unlocked')
    audit(db, job['id'], 'apartment', 'lock_action_attempt_started', action)
    lock_action(session, supervisor_token, action)
    if action == 'open':
        # The HA lock interface has no reliable sensor for a successful latch pull.
        # Therefore do not claim a physically confirmed opening.
        audit(db, job['id'], 'apartment', 'latch_command_sent_unverified')
        return 'command_sent'
    expected = LOCK_ACTIONS[action][1]
    deadline = time.monotonic() + 12
    while time.monotonic() < deadline:
        if lock_state(session, supervisor_token) == expected:
            return 'confirmed'
        time.sleep(0.3)
    raise TimeoutError('Schlosszustand nicht bestätigt: ' + expected)


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



class UnsafeOutput(RuntimeError):
    """The HA output cannot be verified OFF; all further pulses must stop."""


def helper_is_off(session, supervisor_token, entity):
    response = session.get(f'{HA_BASE}/states/{entity}',
        headers={'Authorization': f'Bearer {supervisor_token}'}, timeout=4)
    response.raise_for_status()
    state = response.json()
    return isinstance(state, dict) and state.get('entity_id') == entity and state.get('state') == 'off'


def ensure_outputs_off(session, supervisor_token, db, reason='recovery', retries=3):
    """Only OFF commands; never generate an ON pulse during recovery."""
    failed = []
    for door, entity in ENTITIES.items():
        verified = False
        for attempt in range(retries):
            try:
                ha_call(session, supervisor_token, entity, 'turn_off')
                if helper_is_off(session, supervisor_token, entity):
                    verified = True
                    break
            except Exception as exc:
                LOG.warning('OFF-Recovery %s Versuch %d: %s', door, attempt + 1, type(exc).__name__)
            if attempt + 1 < retries:
                time.sleep(min(attempt + 1, 2))
        if not verified:
            failed.append(door)
    if failed:
        audit(db, 'system', ','.join(failed), 'output_state_unknown', reason)
        raise UnsafeOutput('Tür-Helper nicht sicher AUS: ' + ','.join(failed))


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
    LOG.info('Door Stein Bridge 1.1.0: Hauseingang-Impuls und signierte v2-Schlossaktionen; Polling %d s', interval)
    LOG.info('Lokale HA-Freigabe wird vor jedem Auftrag geprüft; lokales Audit aktiviert')
    outputs_safe = False
    while True:
        try:
            if time.monotonic() >= next_cleanup:
                prune_audit(db)
                next_cleanup = time.monotonic() + AUDIT_CLEANUP_SECONDS
            if not outputs_safe:
                try:
                    ensure_outputs_off(http, supervisor_token, db, 'startup_or_recovery')
                    outputs_safe = True
                    reporter.success('Sicherer Ausgangszustand')
                    audit(db, 'system', 'all', 'outputs_verified_off')
                except Exception as exc:
                    reporter.failure('Sicherer Ausgangszustand', exc)
            if not outputs_safe:
                LOG.warning('Keine Auftragsabholung: Ausgänge nicht sicher AUS')
                time.sleep(interval)
                continue
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
                LOG.info('Türsteuerung gesperrt (Cloudflare-Not-Aus)')
            elif data.get('emergency_stop') is not False:
                LOG.error('Unerwartete Not-Aus-Antwort: keine Ausführung')
            elif not outputs_safe:
                LOG.warning('Öffnungsaufträge blockiert: Ausgangszustand unklar')
            else:
                for job in data.get('jobs', []):
                    if not outputs_safe:
                        LOG.error('Jobliste abgebrochen: Ausgangszustand unklar')
                        break
                    try:
                        ensure_outputs_off(http, supervisor_token, db, 'before_next_job')
                    except Exception as exc:
                        outputs_safe = False
                        reporter.failure('Globaler Ausgangs-Preflight', exc)
                        break
                    job_id = job.get('id', '?') if isinstance(job, dict) else '?'
                    turn_on_started = False
                    door = '?'
                    try:
                        job_id, door, signature, action = validate(job, secret)
                        if not mark_once(db, job_id):
                            audit(db, job_id, door, 'duplicate_rejected')
                            LOG.warning('Auftrag bereits verarbeitet: %s', job_id)
                            continue
                        audit(db, job_id, door, 'claimed_locally')
                        if not locally_enabled(http, supervisor_token):
                            audit(db, job_id, door, 'local_gate_denied')
                            ack(http, worker, token, job_id, signature, 'cancelled')
                            continue
                        if door == 'apartment':
                            # Marked as claimed before any action; never retry a possibly executed command.
                            turn_on_started = True
                            result = execute_lock(http, supervisor_token, job, action, db)
                            # Legacy worker understands only completed/cancelled. 'open' is
                            # acknowledged as dispatched, NOT as verified physical opening.
                            audit(db, job_id, door, 'lock_' + result, action)
                            ack(http, worker, token, job_id, signature, 'completed')
                            audit(db, job_id, door, 'ack_completed', action)
                            continue
                        entity = ENTITIES[door]
                        # The preflight must verify OFF, not merely request it.
                        ha_call(http, supervisor_token, entity, 'turn_off')
                        if not helper_is_off(http, supervisor_token, entity):
                            raise UnsafeOutput('Preflight AUS nicht bestätigt')
                        if not locally_enabled(http, supervisor_token):
                            audit(db, job_id, door, 'local_gate_denied')
                            ack(http, worker, token, job_id, signature, 'cancelled')
                            continue
                        # Re-check signed expiry immediately before the ON service call.
                        if time.time() >= parse_expiry(job['expires_at']):
                            audit(db, job_id, door, 'expired_before_pulse')
                            ack(http, worker, token, job_id, signature, 'cancelled')
                            continue
                        turn_on_started = True
                        audit(db, job_id, door, 'turn_on_attempt_started')
                        try:
                            ha_call(http, supervisor_token, entity, 'turn_on')
                            time.sleep(pulse)
                        finally:
                            try:
                                ensure_outputs_off(http, supervisor_token, db, 'after_pulse')
                            except Exception:
                                outputs_safe = False
                                raise
                        audit(db, job_id, door, 'pulse_finished')
                        ack(http, worker, token, job_id, signature, 'completed')
                        audit(db, job_id, door, 'ack_completed')
                        LOG.info('Impuls bestätigt: %s (%s)', job_id, door)
                    except Exception as exc:
                        LOG.error('Auftrag %s fehlgeschlagen: %s', job_id, exc)
                        audit(db, job_id, door, 'outcome_unknown' if turn_on_started else 'error', type(exc).__name__)
                        # Any unexpected failure requires a verified OFF recovery before another pulse.
                        outputs_safe = False
                        # Never claim cancellation after a possible ON attempt.
                        if not turn_on_started and isinstance(job, dict) and isinstance(job.get('signature'), str) and isinstance(job.get('id'), str):
                            try:
                                ack(http, worker, token, job['id'], job['signature'], 'cancelled')
                            except Exception:
                                pass
                        break  # Fail closed: never process another job from this poll after an error.

        except Exception as exc:
            reporter.failure('Auftrags-Polling', exc)
        time.sleep(interval)


if __name__ == '__main__':
    run()

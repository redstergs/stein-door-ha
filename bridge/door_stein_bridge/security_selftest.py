"""Isolated security self-test. No network, no HA calls, no production DB writes."""
import hashlib
import hmac
import logging
import sqlite3
from datetime import datetime, timedelta, timezone

from bridge import validate, mark_once, ENTITIES

LOG = logging.getLogger('door-stein')


def run_selftest():
    # Test-specific secret; production credentials are never used for these fixtures.
    secret = b'door-stein-isolated-test-secret-not-production'
    def make_job(job_id, door, expiry):
        timestamp = expiry.isoformat().replace('+00:00', 'Z')
        msg = f'door-stein-v1\n{job_id}\n{door}\n{timestamp}'.encode('utf-8')
        return {'id': job_id, 'door_id': door, 'expires_at': timestamp,
                'signature': hmac.new(secret, msg, hashlib.sha256).hexdigest()}

    def check(name, action):
        try:
            action()
        except Exception:
            LOG.exception('SICHERHEITSTEST FEHLGESCHLAGEN: %s', name)
            raise RuntimeError('Sicherheitsselbsttest fehlgeschlagen: ' + name) from None
        LOG.info('SICHERHEITSTEST BESTANDEN: %s', name)

    def must_reject(job):
        try:
            validate(job, secret)
        except ValueError:
            return
        raise AssertionError('Ungültiger Auftrag wurde akzeptiert')

    now = datetime.now(timezone.utc)
    valid = make_job('selftest-valid', 'building', now + timedelta(seconds=12))
    def valid_signature():
        assert validate(valid, secret)[1] == 'building'
    check('Gültige Signatur und Ablaufzeit', valid_signature)

    def duplicate():
        # In-memory DB, never /data/processed.sqlite3.
        with sqlite3.connect(':memory:') as db:
            db.execute('CREATE TABLE processed (id TEXT PRIMARY KEY, processed_at INTEGER NOT NULL)')
            assert mark_once(db, 'selftest-duplicate') is True
            assert mark_once(db, 'selftest-duplicate') is False
    check('Doppelte Auftrags-ID abgelehnt', duplicate)

    check('Abgelaufener Auftrag abgelehnt', lambda: must_reject(
        make_job('selftest-expired', 'building', now - timedelta(seconds=5))))

    def tamper():
        altered = make_job('selftest-tamper', 'building', now + timedelta(seconds=12))
        altered['door_id'] = 'apartment'
        must_reject(altered)
    check('Manipulierte Tür-ID / HMAC abgelehnt', tamper)

    check('Unbekannte Tür-ID abgelehnt', lambda: must_reject(
        make_job('selftest-unknown', 'unknown-door', now + timedelta(seconds=12))))
    assert set(ENTITIES) == {'building', 'apartment'}, 'Unerwartete Türkonfiguration'
    LOG.info('SICHERHEITSTEST: 5/5 bestanden; KEINE Test-Helper geschaltet')

"""Signed, isolated diagnostics. NEVER call HA services or production opening_jobs."""
import hashlib
import hmac
import os
import sqlite3
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from bridge import validate, mark_once

ALLOWED = {'valid_signature','duplicate','expired','tampered','unknown_door',
           'audit_persistence','restart_duplicate','lost_ack','ha_api_error'}
TEST_SECRET = b'door-stein-diagnostic-test-key-isolated'

def fixture(job_id, door, delta):
    expiry = (datetime.now(timezone.utc)+timedelta(seconds=delta)).isoformat().replace('+00:00','Z')
    message = f'door-stein-v1\n{job_id}\n{door}\n{expiry}'.encode()
    return {'id':job_id,'door_id':door,'expires_at':expiry,
            'signature':hmac.new(TEST_SECRET,message,hashlib.sha256).hexdigest()}

def rejected(job):
    try: validate(job,TEST_SECRET)
    except ValueError: return True
    return False

def execute_diagnostic(job, secret, production_db):
    # Validate signed envelope and strict lifetime before ANY test.
    if not isinstance(job,dict): raise ValueError('Ungültiges Format')
    job_id,kind,expiry,sig=(job.get(k) for k in ('id','test_type','expires_at','signature'))
    if not all(isinstance(x,str) for x in (job_id,kind,expiry,sig)) or kind not in ALLOWED or len(job_id)>100 or len(sig)!=64:
        raise ValueError('Ungültiger Diagnoseauftrag')
    message=f'door-stein-diagnostic-v1\n{job_id}\n{kind}\n{expiry}'.encode()
    if not hmac.compare_digest(sig,hmac.new(secret,message,hashlib.sha256).hexdigest()):
        raise ValueError('Diagnosesignatur ungültig')
    timestamp=datetime.fromisoformat(expiry.replace('Z','+00:00'))
    if timestamp.tzinfo is None or not (time.time()<timestamp.timestamp()<=time.time()+65):
        raise ValueError('Diagnose abgelaufen')
    # Use production DB only for separate diagnostic replay ledger; never modify opening ledger.
    with production_db:
        production_db.execute('CREATE TABLE IF NOT EXISTS diagnostic_seen (id TEXT PRIMARY KEY)')
        try: production_db.execute('INSERT INTO diagnostic_seen(id) VALUES(?)',(job_id,))
        except sqlite3.IntegrityError: raise ValueError('Diagnose bereits verarbeitet')
    try:
        if kind=='valid_signature':
            assert validate(fixture('valid','building',12),TEST_SECRET)[1]=='building'
        elif kind=='duplicate':
            with sqlite3.connect(':memory:') as db:
                db.execute('CREATE TABLE processed (id TEXT PRIMARY KEY, processed_at INTEGER NOT NULL)')
                assert mark_once(db,'duplicate') and not mark_once(db,'duplicate')
        elif kind=='expired': assert rejected(fixture('expired','building',-5))
        elif kind=='tampered':
            j=fixture('tampered','building',12);j['door_id']='apartment';assert rejected(j)
        elif kind=='unknown_door': assert rejected(fixture('unknown','invalid',12))
        elif kind in ('audit_persistence','restart_duplicate'):
            with tempfile.TemporaryDirectory() as directory:
                path=str(Path(directory)/'test.sqlite3')
                with sqlite3.connect(path) as db:
                    db.execute('CREATE TABLE processed (id TEXT PRIMARY KEY, processed_at INTEGER NOT NULL)')
                    db.execute('CREATE TABLE audit (event TEXT)')
                    assert mark_once(db,'replay');db.execute('INSERT INTO audit VALUES(?)',('test_event',));db.commit()
                with sqlite3.connect(path) as db:
                    assert not mark_once(db,'replay')
                    assert db.execute('SELECT event FROM audit').fetchone()[0]=='test_event'
        elif kind=='lost_ack':
            # Mocked acknowledgment failure, check no re-execution after a claimed ID.
            with sqlite3.connect(':memory:') as db:
                db.execute('CREATE TABLE processed (id TEXT PRIMARY KEY, processed_at INTEGER NOT NULL)')
                count=0
                for _ in range(2):
                    if mark_once(db,'lost-ack'): count+=1 # simulated pulse, no HA call
                assert count==1
        elif kind=='ha_api_error':
            # Mocked API exception after claim, never retry same ID.
            with sqlite3.connect(':memory:') as db:
                db.execute('CREATE TABLE processed (id TEXT PRIMARY KEY, processed_at INTEGER NOT NULL)')
                assert mark_once(db,'ha-error')
                try: raise TimeoutError('simulated')
                except TimeoutError: pass
                assert not mark_once(db,'ha-error')
        return {'passed':True,'message':'Isolierter Test bestanden; keine HA-Schaltung'}
    except Exception as exc:
        return {'passed':False,'message':'Prüfung fehlgeschlagen: '+type(exc).__name__}

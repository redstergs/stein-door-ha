"""Focused offline regressions for 2026-10-30 security audit."""
import sqlite3
import tempfile
from unittest.mock import patch
import bridge

class Response:
    def raise_for_status(self): pass
    def json(self): return {'ok': True}
class Session:
    def __init__(self): self.posts=[]
    def post(self, url, headers, json, timeout):
        self.posts.append(dict(json))
        return Response()

def test_heartbeat():
    session=Session(); publisher=bridge.LockStatePublisher()
    with patch.object(bridge, 'lock_state', return_value='locked'), patch.object(bridge.time, 'monotonic', side_effect=[0,299,300,300]):
        publisher.publish(session,'https://example.test','token','supervisor')
        publisher.publish(session,'https://example.test','token','supervisor')
        publisher.publish(session,'https://example.test','token','supervisor')
    assert [p['seq'] for p in session.posts]==[0,1], session.posts

def test_boot_generation():
    with tempfile.TemporaryDirectory() as tmp:
        db=sqlite3.connect(tmp+'/bridge.sqlite')
        bridge.initialize_db(db)
        first=bridge.next_boot_id(db)
        second=bridge.next_boot_id(db)
        db.close()
        db=sqlite3.connect(tmp+'/bridge.sqlite')
        third=bridge.next_boot_id(db)
        assert first < second < third
        assert first.startswith('g')
        db.close()

def test_expiry_final_gate():
    calls=[]
    class Clock:
        n=100
        @classmethod
        def time(cls):return cls.n
    job={'id':'job','expires_at':'1970-01-01T00:01:41+00:00'}
    def gate(*args):
        Clock.n+=0.6
        return True
    with patch.object(bridge,'locally_enabled',side_effect=gate),patch.object(bridge,'lock_state',return_value='unlocked'),patch.object(bridge.time,'time',side_effect=Clock.time),patch.object(bridge,'audit'),patch.object(bridge,'lock_action',side_effect=lambda *args:calls.append(args)):
        try:bridge.execute_lock(None,'token',job,'open',None)
        except ValueError as exc: assert 'abgelaufen' in str(exc)
        else:raise AssertionError('Expired latch command accepted')
    assert not calls

if __name__=='__main__':
    test_heartbeat();test_boot_generation();test_expiry_final_gate();print('Audit regression tests: 3 passed')

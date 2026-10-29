"""Offline tests for Worker v1.1.0 lock-state reporting contract."""
from unittest.mock import patch
import bridge

class Response:
    def raise_for_status(self): pass
    def json(self): return {'ok': True}
class Session:
    def __init__(self): self.calls=[]; self.fail=False
    def post(self, url, headers, json, timeout):
        self.calls.append(dict(json))
        if self.fail: raise ConnectionError('offline')
        return Response()

def test():
    states=iter(['locked','locked','unlocked','unknown','unlocked','unlocked'])
    with patch.object(bridge,'lock_state',side_effect=lambda *args:next(states)):
        s=Session(); p=bridge.LockStatePublisher()
        p.publish(s,'https://example.test','token','supervisor',force=True)
        assert s.calls[-1]['seq']==0 and s.calls[-1]['state']=='locked'
        p.publish(s,'https://example.test','token','supervisor')
        assert len(s.calls)==1
        s.fail=True
        p.publish(s,'https://example.test','token','supervisor')
        assert s.calls[-1]['seq']==1 and p.seq==1
        s.fail=False
        p.publish(s,'https://example.test','token','supervisor')
        assert s.calls[-1]['seq']==1 and s.calls[-1]['state']=='unlocked'
        p.publish(s,'https://example.test','token','supervisor')
        assert s.calls[-1]['seq']==2 and s.calls[-1]['state']=='unknown'
        p.publish(s,'https://example.test','token','supervisor',force=True)
        assert s.calls[-1]['seq']==3
    print('Status-Synchronisierung: Offline-Tests bestanden')

if __name__=='__main__': test()

from pathlib import Path
from datetime import timedelta
import json, sqlite3
import pytest
from fastapi.testclient import TestClient
from backend.app.main import create_app
from backend.app.schemas.models import TripInput
from backend.app.services.eta import dt

@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(tmp_path/'ops.sqlite3')) as c:yield c

def issue(c,**overrides):
    t=c.get('/api/trips/1').json();orders=c.get('/api/operations').json()['orders']
    p=dict(trip_id=1,trip_revision=t['revision'],expected_version=max((o['version'] for o in orders if o['trip_id']==1),default=0),driver='LX-01',action='hold',instructions='Dừng ở vị trí an toàn, chờ điều vận.',confirmed=True)
    p.update(overrides)
    return c.post('/api/orders',json=p)

def event(c,id,action,**extra):
    return c.post(f'/api/orders/{id}/driver',json=dict(driver='LX-01',action=action,confirmed=True,**extra))

def preview(c,text,trip_id=1):return c.post('/api/notices/preview',json=dict(trip_id=trip_id,kind='booking',text=text))

def change(c,id=1,**values):
    t=c.get(f'/api/trips/{id}').json();p={k:v for k,v in t.items() if k in TripInput.model_fields};p.update(values)
    return c.put(f'/api/trips/{id}',json=p)

@pytest.fixture
def fleet():
    return [dict(plate=p,tours=t,km=k,at_yard=y,trailer_ok=True,capacity_ok=True,ready=True,hours_ok=True,cutoff_ok=True) for p,t,k,y in [('61C-172.28',56.5,154.54,False),('61C-277.11',55,147.96,False),('61C-304.40',56.5,149.51,True)]]

def test_pilot_matches_report(client,fleet):
    r=client.post('/api/pilot/analyze',json={'vehicles':fleet}).json()
    assert r['recommended']=='61C-304.40'
    assert [v['display_score'] for v in r['options']]==[0.656,0.977,1.0]
    fleet[0]['at_yard']=True;fleet[2]['at_yard']=False
    assert client.post('/api/pilot/analyze',json={'vehicles':fleet}).json()['recommended']=='61C-172.28'

@pytest.mark.parametrize('constraint',['trailer_ok','capacity_ok','ready','hours_ok','cutoff_ok'])
def test_pilot_hard_constraints(client,fleet,constraint):
    fleet[2][constraint]=False;r=client.post('/api/pilot/analyze',json={'vehicles':fleet}).json()
    assert r['recommended']=='61C-277.11' and len(r['rejected'])==1

def test_pilot_no_feasible_and_zero_data(client,fleet):
    for v in fleet:v['ready']=False
    r=client.post('/api/pilot/analyze',json={'vehicles':fleet}).json();assert r['recommended'] is None and len(r['rejected'])==3
    for v in fleet:v.update(ready=True,tours=0,km=0)
    assert client.post('/api/pilot/analyze',json={'vehicles':fleet}).status_code==200
    fleet[1]['plate']=fleet[0]['plate'];assert client.post('/api/pilot/analyze',json={'vehicles':fleet}).status_code==422

def test_notice_preview_requires_approval_and_preserves_progress(client):
    client.post('/api/clock',json={'action':'advance','minutes':20});before=client.get('/api/trips/1').json()
    cutoff=(dt(before['cutoff'])+timedelta(hours=2)).isoformat()
    n=preview(client,'Booking: NEW-BOOK\nCut-off: '+cutoff).json()
    assert len(n['changes'])==2 and client.get('/api/trips/1').json()['cutoff']==before['cutoff']
    assert client.post('/api/notices/'+n['id']+'/apply',json={}).status_code==422
    assert client.post('/api/notices/'+n['id']+'/apply',json={'confirmed':True}).status_code==200
    t=client.get('/api/trips/1').json();assert t['cutoff']==cutoff and t['remaining_minutes']==before['remaining_minutes']
    assert not client.get('/api/operations').json()['orders']
    assert client.post('/api/notices/'+n['id']+'/apply',json={'confirmed':True}).status_code==409

def test_notice_cancel_flags_and_later_read_uses_baseline(client):
    n=preview(client,'Booking: BK-NEW\nTrạng thái: Hủy').json()
    client.post('/api/notices/'+n['id']+'/apply',json={'confirmed':True})
    assert client.get('/api/trips/1').json()['status']=='dang_chay'
    assert client.get('/api/trips/1').json()['data_issue']=='missing'
    assert any(a['active'] and a['kind']=='booking' for a in client.get('/api/alerts').json())
    r=preview(client,'Booking: BK-NEW\nTrạng thái: Hủy').json();assert r['changes']==[]
    assert client.post('/api/notices/'+r['id']+'/apply',json={'confirmed':True}).status_code==422

@pytest.mark.parametrize('text',['Cut-off: 2026-10-17T10:30:00','Cut-off: invalid','Booking: A\nBooking: B','Không có dữ liệu nhận diện'])
def test_notice_malformed(client,text):assert preview(client,text).status_code==422

def test_notice_stale_revision_and_simultaneous_preview(client):
    a=preview(client,'Booking: BK-A').json();b=preview(client,'Booking: BK-B').json()
    assert client.post('/api/notices/'+a['id']+'/apply',json={'confirmed':True}).status_code==200
    assert client.post('/api/notices/'+b['id']+'/apply',json={'confirmed':True}).status_code==409
    n=preview(client,'Booking: BK-C').json();change(client,note='Changed')
    assert client.post('/api/notices/'+n['id']+'/apply',json={'confirmed':True}).status_code==409

def test_notice_completed_and_invalid_cutoff(client):
    assert preview(client,'Booking: BK-X',5).status_code==409
    n=preview(client,'Cut-off: 2000-01-01T00:00:00+07:00').json()
    assert client.post('/api/notices/'+n['id']+'/apply',json={'confirmed':True}).status_code==422

def test_order_consent_and_version_conflict(client):
    assert issue(client,confirmed=False).status_code==422
    a=issue(client).json();assert a['version']==1
    assert issue(client,expected_version=0).status_code==409
    b=issue(client).json();assert b['version']==2
    old=next(o for o in client.get('/api/operations').json()['orders'] if o['id']==a['id'])
    assert not old['active'] and old['superseded_at']
    assert event(client,a['id'],'receive').status_code==409

def test_driver_full_lifecycle(client):
    o=issue(client).json();id=o['id']
    assert event(client,id,'confirm').status_code==409
    assert client.post(f'/api/orders/{id}/driver',json=dict(driver='OTHER',action='receive',confirmed=True)).status_code==409
    assert event(client,id,'receive').json()['received_at']
    client.post('/api/clock',json={'action':'advance','minutes':2})
    r=event(client,id,'confirm');assert r.status_code==200 and r.json()['response_minutes']==2
    assert event(client,id,'execute').status_code==200
    assert client.get('/api/trips/1').json()['status']=='tam_dung'
    assert event(client,id,'confirm').status_code==409
    m=client.get('/api/operations').json()['metrics'];assert m['within_five_rate']==100 and m['waiting']==0

def test_timeout_alert_resolves_on_confirmation(client):
    o=issue(client).json();id=o['id']
    client.post('/api/clock',json={'action':'advance','minutes':4.9})
    assert not any(a['active'] and a['kind']=='order' for a in client.get('/api/alerts').json())
    client.post('/api/clock',json={'action':'advance','minutes':0.1})
    assert any(a['active'] and a['kind']=='order' for a in client.get('/api/alerts').json())
    event(client,id,'receive');event(client,id,'confirm')
    assert not any(a['active'] and a['kind']=='order' for a in client.get('/api/alerts').json())

def test_clock_reset_does_not_erase_order_deadline(client):
    o=issue(client).json();client.post('/api/clock',json={'action':'advance','minutes':6})
    client.post('/api/clock',json={'action':'reset'})
    order=client.get('/api/operations').json()['orders'][0]
    assert order['elapsed_minutes']==6 and order['overdue'] and order['stale']

def test_edit_after_confirmation_cannot_execute(client):
    o=issue(client).json();event(client,o['id'],'receive');event(client,o['id'],'confirm');change(client,note='Changed again')
    assert event(client,o['id'],'execute').status_code==409

def test_rejection_reason_and_fresh_alert(client):
    o=issue(client).json();client.post('/api/clock',json={'action':'advance','minutes':6})
    alerts=client.get('/api/alerts').json();a=next(a for a in alerts if a['active'] and a['kind']=='order')
    client.post('/api/alerts/'+a['id']+'/ack');event(client,o['id'],'receive')
    assert event(client,o['id'],'reject',reason='').status_code==422
    assert event(client,o['id'],'reject',reason='Không thể đến kịp').status_code==200
    alerts=client.get('/api/alerts').json();assert any(a['active'] and not a['acknowledged'] and a['kind']=='order' and 'từ chối' in a['title'] for a in alerts)

def test_unassigned_and_completed_cannot_issue(client):
    assert issue(client,trip_id=2).status_code==422
    assert issue(client,trip_id=5).status_code==409

def test_reset_clears_operations(client):
    issue(client);preview(client,'Booking: BK-NEW');r=client.post('/api/demo/reset').json()
    assert not r['operations']['orders'] and not r['operations']['notices']

def test_migration_and_persistence(tmp_path):
    p=tmp_path/'old.db'
    with TestClient(create_app(p)) as c:
        change(c,cost=3210000)
    with sqlite3.connect(p) as db:
        db.execute('DROP TABLE orders');db.execute('DROP TABLE notices')
        clock=json.loads(db.execute("SELECT value FROM meta WHERE key='clock'").fetchone()[0]);clock.pop('elapsed_minutes',None)
        db.execute("UPDATE meta SET value=? WHERE key='clock'",(json.dumps(clock),))
    with TestClient(create_app(p)) as c:
        assert c.get('/api/trips/1').json()['cost']==3210000
        assert c.get('/api/operations').json()['orders']==[]
        o=issue(c).json();preview(c,'Booking: BK-NEW')
    with TestClient(create_app(p)) as c:
        assert c.get('/api/operations').json()['orders'][0]['id']==o['id']
        assert len(c.get('/api/operations').json()['notices'])==1


def test_assets_and_frontend_hooks(client):
    import re
    root=Path(__file__).resolve().parents[2]
    html=(root/'frontend/index.html').read_text();js=(root/'frontend/operations.js').read_text()
    ids=re.findall(r'id="([^"]+)"',html);assert len(ids)==len(set(ids))
    assert set(re.findall(r"q\('([^']+)'\)",js))-set(ids)==set()
    assert client.get('/static/operations.js').status_code==200
    r=client.get('/');assert 'https://tile.openstreetmap.org' in r.headers['content-security-policy']


def test_order_csv_neutralizes_formulas(client):
    issue(client,instructions='=HYPERLINK(unsafe)',driver='@LX-01')
    r=client.get('/api/orders/export.csv')
    assert r.status_code==200 and r.content.startswith(b'\xef\xbb\xbf')
    assert "'=HYPERLINK" in r.text and "'@LX-01" in r.text


def test_deleting_trip_deactivates_pending_order(client):
    o=issue(client).json();client.delete('/api/trips/1')
    r=client.get('/api/operations').json()
    assert not r['orders'][0]['active'] and r['metrics']['waiting']==0
    assert event(client,o['id'],'receive').status_code==409

@pytest.mark.parametrize('kind,text,field,new_value',[
    ('pickup','Điểm lấy: Kho mới Bình Dương','origin','Kho mới Bình Dương'),
    ('delivery','Điểm giao: Depot mới Thủ Đức','destination','Depot mới Thủ Đức'),
    ('container','Container: UIXX1234567','container_id','UIXX1234567'),
])
def test_operational_notice_types(client,kind,text,field,new_value):
    before=client.get('/api/trips/1').json()
    r=client.post('/api/notices/preview',json={'trip_id':1,'kind':kind,'text':text})
    assert r.status_code==200
    n=r.json();assert n['changes'][0]['field']==field
    assert client.get('/api/trips/1').json()==before
    assert client.post('/api/notices/'+n['id']+'/apply',json={'confirmed':True}).status_code==200
    again=client.post('/api/notices/preview',json={'trip_id':1,'kind':kind,'text':text}).json()
    assert again['changes']==[]
    if field in ['origin','destination']:assert client.get('/api/trips/1').json()[field]==new_value


def test_vehicle_notice_checks_assignment_and_invalidates_order(client):
    order=issue(client).json();event(client,order['id'],'receive');event(client,order['id'],'confirm')
    # Unknown and incompatible vehicles must never bypass the assignment checks.
    for vehicle in ['UNKNOWN-VEHICLE','61C-123.45']:
        n=client.post('/api/notices/preview',json={'trip_id':1,'kind':'vehicle','text':'Phương tiện: '+vehicle}).json()
        assert client.post('/api/notices/'+n['id']+'/apply',json={'confirmed':True}).status_code in [409,422]
    vehicles=client.get('/api/snapshot').json()['vehicles']
    t=client.get('/api/trips/1').json()
    suitable=next(v for v in vehicles if v['available_now'] and v['type']==t['vehicle_type'] and v['capacity']>=t['load'])
    n=client.post('/api/notices/preview',json={'trip_id':1,'kind':'vehicle','text':'Phương tiện: '+suitable['id']}).json()
    assert client.post('/api/notices/'+n['id']+'/apply',json={'confirmed':True}).status_code==200
    assert client.get('/api/trips/1').json()['vehicle_id']==suitable['id']
    assert event(client,order['id'],'execute').status_code==409


def test_incident_creates_alert_without_automatic_vehicle_stop(client):
    before=client.get('/api/trips/1').json()
    def notice(text):
        n=client.post('/api/notices/preview',json={'trip_id':1,'kind':'incident','text':text}).json()
        assert client.post('/api/notices/'+n['id']+'/apply',json={'confirmed':True}).status_code==200
    notice('Sự cố: Xe hỏng lốp')
    assert client.get('/api/trips/1').json()['status']==before['status']
    assert any(a['kind']=='incident' and a['active'] for a in client.get('/api/alerts').json())
    notice('Sự cố: Đã xử lý')
    assert not any(a['kind']=='incident' and a['active'] for a in client.get('/api/alerts').json())

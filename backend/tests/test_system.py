from datetime import timedelta
from pathlib import Path
from copy import deepcopy
import pytest
from fastapi.testclient import TestClient
from backend.app.main import create_app
from backend.app.services.eta import dt, evaluate, progress
from backend.app.services.dispatch import analyze
from backend.app.schemas.models import TripInput
from backend.app.adapters.integrations import TMSAdapter, GPSAdapter, ONPAdapter, IntegrationNotConfigured
from backend.app.adapters.mock import MockDataAdapter

@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(tmp_path/'test.sqlite3')) as c: yield c

@pytest.fixture
def sample(client):
    t=client.get('/api/trips/1').json()
    return {k:v for k,v in t.items() if k in TripInput.model_fields}

@pytest.mark.parametrize('path',['/','/docs','/static/app.js','/static/style.css','/static/docs.js','/openapi.json','/health','/api/trips','/api/sources','/api/snapshot','/api/alerts','/api/reports','/api/decisions','/api/clock'])
def test_routes(client,path): assert client.get(path).status_code==200

def test_eta_and_risk_boundaries(sample):
    now=dt(sample['start_at']);t={**sample,'status':'cho_lenh','remaining_minutes':100,'eta_manual':None}
    for slack,risk in [(-1,'cao'),(0,'trung_binh'),(29.9,'trung_binh'),(30,'thap'),(100,'thap')]:
        t['cutoff']=(now+timedelta(minutes=100+slack)).isoformat()
        v=evaluate(t,now)
        assert v['buffer_minutes']==slack
        assert v['risk']==risk

def test_waiting_eta_slips_with_simulation(client):
    t=client.get('/api/trips/2').json();a=client.post('/api/clock',json={'action':'advance','minutes':30}).json()
    u=next(x for x in a['trips'] if x['id']==2)
    assert (dt(u['eta'])-dt(t['eta'])).total_seconds()==1800
    assert u['buffer_minutes']==t['buffer_minutes']-30

def test_running_eta_constant_and_completes(client):
    t=client.get('/api/trips/1').json()
    client.post('/api/clock',json={'action':'advance','minutes':60})
    u=client.get('/api/trips/1').json()
    assert u['remaining_minutes']==t['remaining_minutes']-60
    assert u['eta']==t['eta']
    client.post('/api/clock',json={'action':'advance','minutes':100})
    v=client.get('/api/trips/1').json()
    assert v['status']=='hoan_thanh'
    assert v['eta']==t['eta']
    assert v['buffer_minutes']==t['buffer_minutes']

def test_simulation_speed_pause_resume(client,monkeypatch):
    import backend.app.store as store
    anchor=store.utcnow();monkeypatch.setattr(store,'utcnow',lambda:anchor)
    base=dt(client.get('/api/clock').json()['now'])
    client.post('/api/clock',json={'action':'speed','speed':60})
    client.post('/api/clock',json={'action':'start'})
    anchor+=timedelta(seconds=2)
    assert (dt(client.get('/api/clock').json()['now'])-base).total_seconds()==120
    client.post('/api/clock',json={'action':'pause'})
    anchor+=timedelta(seconds=10)
    assert (dt(client.get('/api/clock').json()['now'])-base).total_seconds()==120
    client.post('/api/clock',json={'action':'resume'})
    anchor+=timedelta(seconds=1)
    assert (dt(client.get('/api/clock').json()['now'])-base).total_seconds()==180

def test_reset_keeps_edits(client,sample):
    sample.update(code='KEEP',vehicle_id=None,cost=3333333)
    client.put('/api/trips/2',json=sample)
    client.post('/api/clock',json={'action':'advance','minutes':30})
    d=client.post('/api/clock',json={'action':'reset'}).json()
    t=next(x for x in d['trips'] if x['id']==2)
    assert t['code']=='KEEP' and t['cost']==3333333
    assert d['clock']['now']==d['clock']['base']
    assert not d['clock']['running']

def test_crud_and_duplicate(client,sample):
    sample.update(code='NEW-01',vehicle_id=None)
    r=client.post('/api/trips',json=sample);assert r.status_code==201
    id=r.json()['id']
    assert client.post('/api/trips',json=sample).status_code==409
    sample['delay_minutes']=180
    u=client.put(f'/api/trips/{id}',json=sample).json()
    assert u['risk']=='cao'
    assert client.delete(f'/api/trips/{id}').status_code==200
    assert client.get(f'/api/trips/{id}').status_code==404
    assert client.put(f'/api/trips/{id}',json=sample).status_code==404

@pytest.mark.parametrize('key,value',[('load',100),('travel_minutes',-1),('cost',-1),('origin',''),('start_at','2026-10-16T08:00:00'),('code','<script>'),('data_issue','arbitrary'),('extra_field','bad')])
def test_validation(client,sample,key,value):
    sample.update(code='INVALID',vehicle_id=None);sample[key]=value
    assert client.post('/api/trips',json=sample).status_code==422

def test_vehicle_conflict(client,sample):
    sample['code']='CONFLICT'
    assert client.post('/api/trips',json=sample).status_code==409

def test_eta_manual_lower_bound(client,sample):
    sample.update(code='MANUAL',vehicle_id=None,eta_manual=(dt(sample['cutoff'])+timedelta(hours=1)).isoformat())
    t=client.post('/api/trips',json=sample).json()
    assert t['eta']==sample['eta_manual'] and t['risk']=='cao'

def test_alert_ack_and_history(client):
    alerts=client.get('/api/alerts').json()
    assert {'cutoff','missing','source_error'} <= {a['kind'] for a in alerts}
    id=alerts[0]['id']
    assert client.post(f'/api/alerts/{id}/ack').json()['acknowledged']
    assert next(a for a in client.get('/api/alerts').json() if a['id']==id)['acknowledged']
    assert client.post('/api/alerts/unknown/ack').status_code==404

def test_weights_change_recommendation(client):
    fast=client.post('/api/dispatch/analyze',json={'trip_id':2,'weights':{'time':100,'cost':0,'risk':0,'utilization':0}}).json()
    cheap=client.post('/api/dispatch/analyze',json={'trip_id':2,'weights':{'time':0,'cost':100,'risk':0,'utilization':0}}).json()
    assert len(fast['options'])>=2
    assert fast['recommended_id']=='XE-02'
    assert cheap['recommended_id']=='XE-03'
    assert all(0<=o['score']<=100 for o in fast['options'])
    assert sum(fast['weights'].values())==1

def test_no_overload_and_type_options(client,sample):
    sample.update(code='HEAVY',vehicle_id=None,load=31,capacity=32)
    t=client.post('/api/trips',json=sample).json()
    a=client.post('/api/dispatch/analyze',json={'trip_id':t['id']}).json()
    assert [o['id'] for o in a['options']]==['XE-03']
    assert a['rejected']

def test_confirm_requires_consent_and_is_idempotent(client):
    a=client.post('/api/dispatch/analyze',json={'trip_id':2}).json()
    body={'analysis_id':a['id'],'option_id':a['recommended_id']}
    assert client.post('/api/dispatch/confirm',json=body).status_code==422
    body['confirmed']=True
    assert client.post('/api/dispatch/confirm',json=body).status_code==200
    assert client.post('/api/dispatch/confirm',json=body).status_code==409
    t=client.get('/api/trips/2').json()
    assert t['vehicle_id']==body['option_id'] and t['status']=='dang_chay'
    assert len(client.get('/api/decisions').json())==1

def test_analysis_stale_after_edit(client,sample):
    a=client.post('/api/dispatch/analyze',json={'trip_id':1}).json()
    sample['delay_minutes']=30;client.put('/api/trips/1',json=sample)
    assert client.post('/api/dispatch/confirm',json={'analysis_id':a['id'],'option_id':a['recommended_id'],'confirmed':True}).status_code==409

def test_analysis_stale_after_clock_jump(client):
    a=client.post('/api/dispatch/analyze',json={'trip_id':2}).json()
    client.post('/api/clock',json={'action':'advance','minutes':10})
    assert client.post('/api/dispatch/confirm',json={'analysis_id':a['id'],'option_id':a['recommended_id'],'confirmed':True}).status_code==409

def test_deleted_trip_cannot_confirm(client):
    a=client.post('/api/dispatch/analyze',json={'trip_id':2}).json();client.delete('/api/trips/2')
    assert client.post('/api/dispatch/confirm',json={'analysis_id':a['id'],'option_id':a['recommended_id'],'confirmed':True}).status_code==404

def test_invalid_weights_and_completed(client):
    assert client.post('/api/dispatch/analyze',json={'trip_id':2,'weights':{'time':0,'cost':0,'risk':0,'utilization':0}}).status_code==422
    assert client.post('/api/dispatch/analyze',json={'trip_id':5}).status_code==422
    assert client.post('/api/clock',json={'action':'speed','speed':2}).status_code==422
    assert client.post('/api/clock',json={'action':'advance','minutes':-1}).status_code==422

def test_reports_and_csv_safety(client,sample):
    sample.update(code='CSV-01',vehicle_id=None,origin='=HYPERLINK("bad")')
    client.post('/api/trips',json=sample)
    r=client.get('/api/reports').json()
    assert r['total_trips']==6 and r['active_trips']==5
    assert r['risk_rate']==round(r['at_risk']/r['active_trips']*100,1)
    csv=client.get('/api/reports/export.csv')
    assert csv.content.startswith(b'\xef\xbb\xbf')
    assert "'=HYPERLINK" in csv.text
    assert 'attachment' in csv.headers['content-disposition']

def test_database_persistence(tmp_path):
    path=tmp_path/'persist.db'
    with TestClient(create_app(path)) as c:
        c.delete('/api/trips/1');c.post('/api/clock',json={'action':'advance','minutes':45})
        now=c.get('/api/clock').json()['now']
    with TestClient(create_app(path)) as c:
        assert len(c.get('/api/trips').json())==4
        assert c.get('/api/clock').json()['now']==now

def test_demo_reset(client):
    client.delete('/api/trips/1')
    r=client.post('/api/demo/reset').json()
    assert len(r['trips'])==5 and not r['clock']['running']

@pytest.mark.parametrize('cls',[TMSAdapter,GPSAdapter,ONPAdapter])
def test_integration_never_claims_connected(cls):
    a=cls();assert not a.status().connected
    assert a.timeout_seconds>0
    with pytest.raises(IntegrationNotConfigured):a.fetch_trips()

def test_mock_contract():
    for row in MockDataAdapter().fetch_trips(): assert TripInput.model_validate(row)

def test_frontend_hooks_and_local_assets(client):
    import re
    from html.parser import HTMLParser
    root=Path(__file__).resolve().parents[2]
    html=(root/'frontend/index.html').read_text();js=(root/'frontend/app.js').read_text()
    ids=set(re.findall(r'id="([^"]+)"',html))
    used=set(re.findall(r"\$\('([^']+)'\)",js))
    assert used-ids==set()
    assert 'https://' not in html
    assert 'eval(' not in js
    assert "content-security-policy" in client.get('/').headers

def test_confirm_respects_future_departure(client,sample):
    now=dt(client.get('/api/clock').json()['now'])
    sample.update(code='FUTURE',vehicle_id=None,status='cho_lenh',start_at=(now+timedelta(hours=1)).isoformat(),cutoff=(now+timedelta(hours=5)).isoformat())
    t=client.post('/api/trips',json=sample).json()
    a=client.post('/api/dispatch/analyze',json={'trip_id':t['id']}).json()
    o=a['options'][0]
    assert client.post('/api/dispatch/confirm',json={'analysis_id':a['id'],'option_id':o['id'],'confirmed':True}).status_code==200
    new=client.get('/api/trips/'+str(t['id'])).json()
    assert new['eta']==o['eta']

def test_real_time_is_not_simulated_time(client):
    before=client.get('/api/snapshot').json()
    after=client.post('/api/clock',json={'action':'advance','minutes':120}).json()
    assert (dt(after['clock']['now'])-dt(before['clock']['now'])).total_seconds()==7200
    assert (dt(after['real_time'])-dt(before['real_time'])).total_seconds()<10

def test_ack_does_not_remove_risk(client):
    before=client.get('/api/snapshot').json()
    alert=next(a for a in before['alerts'] if a['kind']=='cutoff')
    client.post('/api/alerts/'+alert['id']+'/ack')
    after=client.get('/api/snapshot').json()
    assert after['report']['at_risk']==before['report']['at_risk']

def test_clock_state_survives_restart(tmp_path):
    path=tmp_path/'clock.db'
    with TestClient(create_app(path)) as c:
        c.post('/api/clock',json={'action':'speed','speed':10})
        c.post('/api/clock',json={'action':'start'})
    with TestClient(create_app(path)) as c:
        clock=c.get('/api/clock').json()
        assert clock['running'] and clock['speed']==10

def test_empty_database_reports_are_defined(client):
    for t in client.get('/api/trips').json(): client.delete('/api/trips/'+str(t['id']))
    r=client.get('/api/reports').json()
    assert r['total_trips']==0 and r['risk_rate']==0 and r['on_time_rate'] is None

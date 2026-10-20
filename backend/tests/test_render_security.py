from fastapi.testclient import TestClient
import pytest
from backend.app.main import create_app

@pytest.fixture
def hosted(tmp_path,monkeypatch):
    monkeypatch.setenv('APP_ENV','production')
    monkeypatch.setenv('DEMO_USERNAME','lecturer')
    monkeypatch.setenv('DEMO_PASSWORD','temporary-test-only-password')
    with TestClient(create_app(tmp_path/'hosted.db')) as c:yield c

@pytest.mark.parametrize('path',['/','/api/snapshot','/static/app.js','/docs','/openapi.json','/api/enterprise/status'])
def test_hosted_routes_require_auth(hosted,path):
    r=hosted.get(path)
    assert r.status_code==401
    assert r.headers['WWW-Authenticate']=='Basic realm="Dispatch AI", charset="UTF-8"'
    assert r.headers['Cache-Control']=='no-store'
    assert hosted.get(path,auth=('lecturer','temporary-test-only-password')).status_code==200

def test_health_available_without_credentials(hosted):assert hosted.get('/health').status_code==200

def test_wrong_and_malformed_credentials(hosted):
    assert hosted.get('/',auth=('lecturer','wrong')).status_code==401
    assert hosted.get('/',headers={'Authorization':'Basic not-base64'}).status_code==401

def test_missing_configuration_fails_closed(hosted,monkeypatch):
    monkeypatch.delenv('DEMO_PASSWORD')
    r=hosted.get('/');assert r.status_code==503 and r.headers['Cache-Control']=='no-store'

def test_unicode_password_is_supported(hosted,monkeypatch):
    import base64
    monkeypatch.setenv('DEMO_PASSWORD','Mật khẩu kiểm thử riêng')
    header=base64.b64encode('lecturer:Mật khẩu kiểm thử riêng'.encode()).decode()
    assert hosted.get('/',headers={'Authorization':'Basic '+header}).status_code==200


def test_hosted_clock_uses_wall_time_and_blocks_simulation(hosted,monkeypatch):
    from datetime import datetime, timezone, timedelta
    import backend.app.store as store_module
    auth=('lecturer','temporary-test-only-password')
    first=hosted.get('/api/snapshot',auth=auth).json()
    now=datetime.now(timezone.utc)
    clock=first['clock']
    assert clock['mode']=='live' and clock['running'] and clock['speed']==1
    assert abs((datetime.fromisoformat(clock['now'])-now).total_seconds())<5
    assert all(hosted.post('/api/clock',auth=auth,json={'action':action}).status_code==409 for action in ['pause','reset','advance'])
    t=first['trips'][0]
    order=hosted.post('/api/orders',auth=auth,json={'trip_id':t['id'],'trip_revision':t['revision'],'expected_version':0,'driver':'CLOCK-TEST','action':'hold','instructions':'Chờ tại điểm an toàn','confirmed':True}).json()
    future=datetime.now(timezone.utc)+timedelta(minutes=6)
    monkeypatch.setattr(store_module,'utcnow',lambda:future)
    updated=hosted.get('/api/snapshot',auth=auth).json()
    o=next(o for o in updated['operations']['orders'] if o['id']==order['id'])
    assert o['overdue'] and o['elapsed_minutes']>=6
    assert datetime.fromisoformat(updated['clock']['now'])==future
    assert updated['trips'][0]['remaining_minutes']<t['remaining_minutes']-5


def test_hosted_ui_has_no_simulation_or_test_controls(hosted):
    r=hosted.get('/',auth=('lecturer','temporary-test-only-password'))
    assert '<title>Dispatch AI' in r.text
    for text in ['U&I','Kịch bản thử nghiệm','data-clock=','Tài liệu & kiểm thử','id="orderAdvance"','id="pilotReset"','id="resetDemo"']:
        assert text not in r.text
    assert 'id="mapSearch"' in r.text and 'id="mapFilter"' in r.text


def test_local_app_defaults_to_live_clock(tmp_path,monkeypatch):
    from datetime import datetime, timezone
    monkeypatch.delenv('CLOCK_MODE',raising=False)
    monkeypatch.setenv('APP_ENV','local')
    with TestClient(create_app(tmp_path/'local-live.db')) as c:
        clock=c.get('/api/snapshot').json()['clock']
        assert clock['mode']=='live' and clock['running'] and clock['speed']==1
        assert abs((datetime.fromisoformat(clock['now'])-datetime.now(timezone.utc)).total_seconds())<5
        assert c.post('/api/clock',json={'action':'advance','minutes':30}).status_code==409

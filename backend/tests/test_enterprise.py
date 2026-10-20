import csv,io,json
from datetime import timedelta
import httpx,pytest
from fastapi.testclient import TestClient
from backend.app.main import create_app
from backend.app.services.enterprise import sample_rows
from backend.app.services.eta import dt
import backend.app.adapters.enterprise as adapter

@pytest.fixture
def client(tmp_path,monkeypatch):
    for s in ['TMS','GPS','ONP']:monkeypatch.setenv(s+'_READ_ENABLED','false')
    with TestClient(create_app(tmp_path/'enterprise.db')) as c:yield c

def preview(c,source,rows,format='json'):
    if format=='json':text=json.dumps(rows)
    else:
        out=io.StringIO();w=csv.DictWriter(out,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows);text='\ufeff'+out.getvalue()
    return c.post('/api/enterprise/'+source+'/preview-file',json={'format':format,'text':text})

def commit(c,source,batch,confirmed=True):return c.post('/api/enterprise/'+source+'/commit',json={'confirmed':confirmed,'batch_id':batch['id']})

def fake_api(monkeypatch,status=200,payload=None,content=None,timeout=False):
    monkeypatch.setenv('GPS_READ_ENABLED','true');monkeypatch.setenv('GPS_API_URL','https://gps.example.test/data')
    monkeypatch.setenv('GPS_ALLOWED_HOSTS','gps.example.test');monkeypatch.setenv('GPS_API_TOKEN','SECRET-TEST-DO-NOT-EXPOSE')
    requests=[]
    def handler(req):
        requests.append(req)
        if timeout:raise httpx.ReadTimeout('SECRET-TEST-DO-NOT-EXPOSE',request=req)
        return httpx.Response(status,json=payload) if content is None else httpx.Response(status,content=content)
    original=httpx.Client
    monkeypatch.setattr(adapter.httpx,'Client',lambda **kwargs:original(transport=httpx.MockTransport(handler),**kwargs))
    return requests

@pytest.mark.parametrize('source',['TMS','GPS','ONP'])
@pytest.mark.parametrize('format',['json','csv'])
def test_preview_and_commit_roundtrip(client,source,format):
    values=sample_rows(source);r=preview(client,source,values,format);assert r.status_code==200,r.text
    batch=r.json();assert not batch['errors']
    assert not client.get('/api/enterprise/'+source+'/data').json()['records']
    assert commit(client,source,batch,False).status_code==422
    assert commit(client,source,batch).status_code==200
    assert commit(client,source,batch).status_code==409
    stored=client.get('/api/enterprise/'+source+'/data').json()['records'];assert len(stored)==1
    assert stored[0]['source_updated_at']==values[0]['source_updated_at']
    assert stored[0]['ingestion_method']=='file'
    assert len(client.get('/api/trips').json())==5

def test_missing_bad_rows_block_entire_batch(client):
    values=sample_rows('GPS');values.append({**values[0],'vehicle_id':'BAD','latitude':100})
    b=preview(client,'GPS',values).json();assert b['valid_count']==1 and len(b['errors'])==1
    assert commit(client,'GPS',b).status_code==422
    assert not client.get('/api/enterprise/GPS/data').json()['records']

@pytest.mark.parametrize('value',['2026-10-17T10:00:00','wrong'])
def test_timezone_required(client,value):
    rows=sample_rows('GPS');rows[0]['source_updated_at']=value
    assert preview(client,'GPS',rows).json()['errors']

def test_mapping_and_nested_json(client):
    conf={'mapping':{'vehicle_id':'truck.plate','latitude':'lat','longitude':'lon','source_updated_at':'time','speed_kmh':'speed'},'rows_path':'data.positions'}
    assert client.put('/api/enterprise/GPS/config',json=conf).status_code==200
    source=sample_rows('GPS')[0]
    rows={'data':{'positions':[{'truck':{'plate':'VEH-22'},'lat':10.8,'lon':106.7,'time':source['source_updated_at'],'speed':20}]}}
    b=preview(client,'GPS',rows).json();assert not b['errors'] and b['records'][0]['vehicle_id']=='VEH-22'
    client.put('/api/enterprise/GPS/config',json=conf)
    assert commit(client,'GPS',b).status_code==409

def test_stale_batch_after_data_changed(client):
    a=preview(client,'GPS',sample_rows('GPS')).json();b=preview(client,'GPS',sample_rows('GPS')).json()
    assert commit(client,'GPS',a).status_code==200
    assert commit(client,'GPS',b).status_code==409

def test_source_times_prevent_rollback(client):
    rows=sample_rows('GPS');now=dt(rows[0]['source_updated_at'])
    b=preview(client,'GPS',rows).json();commit(client,'GPS',b)
    rows[0].update(latitude=11,source_updated_at=(now-timedelta(hours=1)).isoformat())
    b=preview(client,'GPS',rows).json();r=commit(client,'GPS',b).json();assert r['ignored_older_or_equal']==1
    assert client.get('/api/enterprise/GPS/data').json()['records'][0]['latitude']!=11
    rows[0]['source_updated_at']=(now+timedelta(minutes=1)).isoformat();commit(client,'GPS',preview(client,'GPS',rows).json())
    assert client.get('/api/enterprise/GPS/data').json()['records'][0]['latitude']==11

def test_batch_source_and_duplicate_guard(client):
    rows=sample_rows('GPS');b=preview(client,'GPS',rows+rows).json();assert b['errors']
    assert commit(client,'TMS',b).status_code==404

def test_tms_does_not_invent_missing_cost(client):
    rows=sample_rows('TMS');del rows[0]['cost']
    b=preview(client,'TMS',rows).json();assert b['errors'] and 'cost' in b['errors'][0]['message']

def test_disabled_api_does_not_call_network(client,monkeypatch):
    def no_network(**kw):raise AssertionError('Network must not run')
    monkeypatch.setattr(adapter.httpx,'Client',no_network)
    assert client.post('/api/enterprise/GPS/preview-api',json={'confirmed':True}).status_code==502

def test_api_requires_consent_and_private_secrets(client,monkeypatch):
    requests=fake_api(monkeypatch,payload=sample_rows('GPS'))
    assert client.post('/api/enterprise/GPS/preview-api',json={}).status_code==422 and not requests
    r=client.post('/api/enterprise/GPS/preview-api',json={'confirmed':True});assert r.status_code==200
    assert requests[0].method=='GET' and requests[0].headers['Authorization']=='Bearer SECRET-TEST-DO-NOT-EXPOSE'
    status=client.get('/api/enterprise/status');assert 'SECRET-TEST' not in status.text and 'https://' not in status.text
    assert 'SECRET-TEST' not in r.text
    assert client.get('/api/enterprise/GPS/data').json()['records']==[]
    commit(client,'GPS',r.json())
    assert client.get('/api/enterprise/GPS/data').json()['records'][0]['ingestion_method']=='api'

@pytest.mark.parametrize('code',[301,401,403,429,500])
def test_api_errors_no_secret_echo(client,monkeypatch,code):
    fake_api(monkeypatch,status=code,payload={'error':'SECRET-TEST-DO-NOT-EXPOSE'})
    r=client.post('/api/enterprise/GPS/preview-api',json={'confirmed':True});assert r.status_code==502
    assert 'SECRET-TEST' not in r.text
    state=next(x for x in client.get('/api/enterprise/status').json() if x['source']=='GPS')
    assert not state['last_test']['success']

@pytest.mark.parametrize('kind',['timeout','invalid_json','too_large'])
def test_api_timeout_and_payload_limits(client,monkeypatch,kind):
    fake_api(monkeypatch,payload=sample_rows('GPS'),timeout=kind=='timeout',content=b'invalid' if kind=='invalid_json' else b'x'*2000001 if kind=='too_large' else None)
    r=client.post('/api/enterprise/GPS/preview-api',json={'confirmed':True});assert r.status_code==502 and 'SECRET-TEST' not in r.text

@pytest.mark.parametrize('endpoint,allowed',[('http://gps.example.test/data','gps.example.test'),('https://gps.example.test/data','wrong.test'),('https://user:password@gps.example.test/data','gps.example.test')])
def test_approved_host_and_https_gate(client,monkeypatch,endpoint,allowed):
    requests=fake_api(monkeypatch,payload=sample_rows('GPS'));monkeypatch.setenv('GPS_API_URL',endpoint);monkeypatch.setenv('GPS_ALLOWED_HOSTS',allowed)
    assert client.post('/api/enterprise/GPS/preview-api',json={'confirmed':True}).status_code==502 and not requests

@pytest.mark.parametrize('source',['GPS','TMS','ONP'])
def test_templates(client,source):
    template=client.get('/api/enterprise/'+source+'/template.csv');assert template.status_code==200
    r=client.post('/api/enterprise/'+source+'/preview-file',json={'format':'csv','text':template.text})
    assert r.status_code==200 and not r.json()['errors'],r.text

def test_invalid_format_paths_and_rows(client):
    for rows in [{},[],[1],sample_rows('GPS')*1001]:
        assert preview(client,'GPS',rows).status_code==422
    assert client.post('/api/enterprise/GPS/preview-file',json={'format':'csv','text':'lat,lat\n1,2'}).status_code==422
    assert client.put('/api/enterprise/GPS/config',json={'mapping':{'secret':'token'}}).status_code==422

def test_reset_removes_enterprise_data(client):
    commit(client,'GPS',preview(client,'GPS',sample_rows('GPS')).json())
    client.post('/api/demo/reset')
    assert not client.get('/api/enterprise/GPS/data').json()['records']


@pytest.mark.parametrize('mode',['api_key','none'])
def test_other_auth_modes(client,monkeypatch,mode):
    requests=fake_api(monkeypatch,payload=sample_rows('GPS'));monkeypatch.setenv('GPS_AUTH_MODE',mode)
    r=client.post('/api/enterprise/GPS/preview-api',json={'confirmed':True});assert r.status_code==200
    if mode=='api_key':assert requests[0].headers['X-API-Key']=='SECRET-TEST-DO-NOT-EXPOSE'
    else:assert 'Authorization' not in requests[0].headers and 'X-API-Key' not in requests[0].headers

def test_health_describes_configuration_not_live_connection(client):
    r=client.get('/health').json();assert not any(r['external_read_enabled'].values()) and not r['outbound_orders_enabled']


def test_navigation_assets_bust_stale_cache(client):
    from html.parser import HTMLParser
    class Scripts(HTMLParser):
        def __init__(self):super().__init__();self.paths=[]
        def handle_starttag(self,tag,attrs):
            a=dict(attrs)
            if tag=='script' and '/static/vendor/' not in a.get('src',''):self.paths.append(a.get('src',''))
    r=client.get('/');parser=Scripts();parser.feed(r.text)
    assert r.headers['cache-control']=='no-store'
    assert parser.paths and all('?v=1.4.1' in p for p in parser.paths)
    for path in parser.paths:
        a=client.get(path);assert a.status_code==200 and a.headers['cache-control']=='no-store'
    assert client.get('/api/enterprise/status').headers['cache-control']=='no-store'
    assert "enterprise:['Kết nối doanh nghiệp'" in client.get('/static/app.js?v=1.4.1').text

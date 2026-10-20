import csv,io
import pytest
from fastapi.testclient import TestClient
from backend.app.main import create_app

@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(tmp_path/'fleet.db')) as c:yield c

def fleet(n):
    return [dict(plate=f'XE-{i:03}',tours=20+i,km=60+i,at_yard=i==n-1,trailer_ok=True,capacity_ok=True,ready=True,hours_ok=True,cutoff_ok=True) for i in range(n)]

def csv_text(vehicles,delimiter=','):
    s=io.StringIO();w=csv.DictWriter(s,fieldnames=list(vehicles[0]),delimiter=delimiter);w.writeheader();w.writerows(vehicles);return '\ufeff'+s.getvalue()

@pytest.mark.parametrize('n',[1,2,3,10,100])
def test_all_input_vehicles_considered_top_three(client,n):
    vehicles=fleet(n);r=client.post('/api/pilot/analyze',json={'vehicles':vehicles})
    assert r.status_code==200;r=r.json()
    assert r['input_count']==r['feasible_count']==n
    assert len(r['options'])==min(n,3) and len(r['ranking'])==n
    assert {v['plate'] for v in r['ranking']}=={v['plate'] for v in vehicles}
    expected=min(vehicles,key=lambda v:((v['tours']/max(x['tours'] for x in vehicles)+v['km']/max(x['km'] for x in vehicles)+(0 if v['at_yard'] else 1))/3,v['plate']))
    assert r['recommended']==expected['plate']
    assert r['options']==r['ranking'][:3]

def test_all_rejected_and_mixed_fleet(client):
    vehicles=fleet(10)
    for v in vehicles:v['ready']=False
    r=client.post('/api/pilot/analyze',json={'vehicles':vehicles}).json()
    assert r['recommended'] is None and not r['options'] and len(r['rejected'])==10
    vehicles[5]['ready']=True
    r=client.post('/api/pilot/analyze',json={'vehicles':vehicles}).json()
    assert r['recommended']==vehicles[5]['plate'] and r['feasible_count']==1

@pytest.mark.parametrize('delimiter',[',',';'])
def test_import_csv_considers_all_rows(client,delimiter):
    values=fleet(10);r=client.post('/api/pilot/fleet/import',json={'text':csv_text(values,delimiter)})
    assert r.status_code==200 and r.json()['vehicles']==values
    # Preview/import does not replace saved data before the user saves.
    assert len(client.get('/api/pilot/fleet').json()['vehicles'])==3
    assert client.put('/api/pilot/fleet',json=r.json()).status_code==200
    assert len(client.get('/api/pilot/fleet').json()['vehicles'])==10

def test_csv_decimal_comma(client):
    text=csv_text(fleet(1),';').replace(';20;60;',';20,5;60,5;')
    r=client.post('/api/pilot/fleet/import',json={'text':text});assert r.status_code==200
    assert r.json()['vehicles'][0]['tours']==20.5

@pytest.mark.parametrize('kind',['duplicate','bad_boolean','missing_column','bad_number','empty','duplicate_header','nan'])
def test_csv_rejects_invalid_data(client,kind):
    values=fleet(2)
    if kind=='duplicate':values[1]['plate']=values[0]['plate'].lower()
    if kind=='bad_boolean':values[0]['ready']='perhaps'
    if kind=='bad_number':values[0]['tours']='bad'
    if kind=='nan':values[0]['km']='NaN'
    text=csv_text(values)
    if kind=='missing_column':text=text.replace('trailer_ok,','')
    if kind=='duplicate_header':text=text.replace('plate,tours','plate,plate')
    if kind=='empty':text=text.splitlines()[0]+'\n'
    r=client.post('/api/pilot/fleet/import',json={'text':text});assert r.status_code==422,r.text
    assert len(client.get('/api/pilot/fleet').json()['vehicles'])==3

def test_save_persistence_validation_and_reset(tmp_path):
    path=tmp_path/'saved.db'
    with TestClient(create_app(path)) as c:
        assert c.put('/api/pilot/fleet',json={'vehicles':fleet(10)}).status_code==200
        assert c.put('/api/pilot/fleet',json={'vehicles':[]}).status_code==422
    with TestClient(create_app(path)) as c:
        assert c.get('/api/pilot/fleet').json()['vehicles']==fleet(10)
        c.post('/api/demo/reset')
        assert len(c.get('/api/pilot/fleet').json()['vehicles'])==3

def test_template_roundtrip(client):
    r=client.get('/api/pilot/fleet/template.csv');assert r.status_code==200
    assert client.post('/api/pilot/fleet/import',json={'text':r.text}).status_code==200

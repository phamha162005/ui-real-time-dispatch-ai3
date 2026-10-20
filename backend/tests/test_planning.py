import base64,io,json
from email.message import EmailMessage
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient
from backend.app.main import create_app

@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(tmp_path/'planning.db')) as c:yield c

def option(name='Tiếp tục',cost=100):
    return dict(name=name,action='continue',extra_minutes=10,extra_km=2,wait_minutes=0,buffer_minutes=35,trailer_ok=True,capacity_ok=True,hours_ok=True,booking_ok=True,safety_ok=True,costs=dict(fuel=cost,toll=0,waiting=0,handling=0,return_outsource=0,other=0),evidence='Đơn giá được duyệt')
def comparison(c,options=None,limit=50):
    return c.post('/api/planning/comparisons',json=dict(trip_id=1,reason='Tàu thay đổi lịch hạ',options=options or [option(),option('Chờ',200)],approval_limit=limit))
def approve(c,id,**kw):
    return c.post('/api/planning/comparisons/'+id+'/approve',json=dict(option_index=0,reviewer='Trưởng bộ phận',note='Đã kiểm tra và duyệt',confirmed=True,**kw))

def test_eml_html_attachments_and_match(client):
    m=EmailMessage();m['Subject']='Booking changed';m['From']='operations@example.com';m.set_content('Booking no: BK-UI-1001\nDelivery: Depot Thủ Đức\nStatus: Cancelled')
    r=client.post('/api/planning/document',json={'name':'notice.eml','content_base64':base64.b64encode(m.as_bytes()).decode()})
    assert r.status_code==200 and r.json()['subject']=='Booking changed'
    v=client.post('/api/planning/extract',json={'text':r.json()['text']}).json()
    assert v['values']['cancelled'] is True and v['matches'][0]['id']==1
    assert v['values']['destination']=='Depot Thủ Đức'
    # Reading is non-mutating: a separate review/confirmation remains necessary.
    assert client.get('/api/trips/1').json()['destination']!='Depot Thủ Đức'
    m=EmailMessage();m.set_content('<p>Booking: BK-UI-1001</p><script>evil()</script>',subtype='html')
    r=client.post('/api/planning/document',json={'name':'html.eml','content_base64':base64.b64encode(m.as_bytes()).decode()})
    assert '<script>' not in r.json()['text'] and 'evil()' not in r.json()['text']

def test_document_limits_and_no_silent_pdf_success(client):
    assert client.post('/api/planning/document',json={'name':'x.eml','content_base64':'!'}).status_code==422
    assert client.post('/api/planning/document',json={'name':'x.exe','content_base64':'YQ=='}).status_code==422
    assert client.post('/api/planning/document',json={'name':'x.pdf','content_base64':'YQ=='}).status_code==422
    from pypdf import PdfWriter
    b=io.BytesIO();p=PdfWriter();p.add_blank_page(width=100,height=100);p.write(b)
    r=client.post('/api/planning/document',json={'name':'scan.pdf','content_base64':base64.b64encode(b.getvalue()).decode()})
    assert r.status_code==422 and 'OCR' in r.text

def test_connections_no_secret_and_require_permission(client,monkeypatch):
    monkeypatch.delenv('MAIL_READ_ENABLED',raising=False);monkeypatch.delenv('OPENAI_API_KEY',raising=False)
    r=client.get('/api/planning/connections').json();assert not r['mail_ready'] and not r['ai_ready']
    assert client.post('/api/planning/mail/read',json={'confirmed':False}).status_code==422
    assert client.post('/api/planning/mail/read',json={'confirmed':True}).status_code==409
    assert client.post('/api/planning/extract',json={'text':'Booking: ABC','use_ai':True}).status_code==422
    assert client.post('/api/planning/extract',json={'text':'Booking: ABC','use_ai':True,'confirmed':True}).status_code==409

def test_unknown_cost_and_constraints_never_recommended(client):
    a,b=option(),option('Chờ',0);b['costs']['waiting']=None
    v=comparison(client,[a,b]).json()
    assert v['recommended'] is None and v['options'][1]['total'] is None
    b['safety_ok']=False
    v=comparison(client,[a,b]).json();assert v['recommended']==0 and not v['options'][1]['feasible']
    assert approve(client,v['id'],manager_approved=False).status_code==422
    assert approve(client,v['id'],manager_approved=True).status_code==200
    assert approve(client,v['id'],manager_approved=True).status_code==409

@pytest.mark.parametrize('field',['trailer_ok','capacity_ok','hours_ok','booking_ok','safety_ok','buffer_minutes'])
def test_constraint_filters(client,field):
    a=option();a[field]=-1 if field=='buffer_minutes' else False
    v=comparison(client,[a,option('Đổi xe',200)]).json()
    assert not v['options'][0]['feasible'] and v['recommended']==1
    assert approve(client,v['id'],manager_approved=True).status_code==422

def test_missing_cost_schema_rejected_and_nan(client):
    a=option();del a['costs']['fuel'];assert comparison(client,[a,option('Chờ')]).status_code==422
    a=option();a['costs']['fuel']=-1;assert comparison(client,[a,option('Chờ')]).status_code==422

def test_revision_and_linked_order(client):
    v=comparison(client).json();assert approve(client,v['id'],manager_approved=True).status_code==200
    t=client.get('/api/trips/1').json()
    body=dict(trip_id=1,trip_revision=t['revision'],expected_version=0,driver='LX-01',action='hold',instructions='Dừng an toàn theo phương án đã duyệt',comparison_id=v['id'],confirmed=True)
    r=client.post('/api/orders',json=body);assert r.status_code==201 and r.json()['approved_option']['total']==100
    body['comparison_id']='bad';body['expected_version']=1;assert client.post('/api/orders',json=body).status_code==409
    from backend.app.schemas.models import TripInput
    p={k:t[k] for k in TripInput.model_fields if k in t};p['note']='Chuyến đã đổi';assert client.put('/api/trips/1',json=p).status_code==200
    body['comparison_id']=v['id'];body['trip_revision']=client.get('/api/trips/1').json()['revision'];assert client.post('/api/orders',json=body).status_code==409

def test_mock_ai_is_validated_and_never_executes(client,monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY','test-secret');monkeypatch.setenv('DOCUMENT_AI_MODEL','approved-model')
    import httpx
    payload={'choices':[{'message':{'content':json.dumps({'booking':'BK-UI-1001','cancelled':True})}}]}
    with patch('backend.app.services.documents.httpx.Client') as factory:
        factory.return_value.__enter__.return_value.post.return_value=httpx.Response(200,json=payload,request=httpx.Request('POST','https://api.openai.com'))
        v=client.post('/api/planning/extract',json={'text':'Untrusted source document','use_ai':True,'confirmed':True})
    assert v.status_code==200 and v.json()['values']['cancelled'] is True
    assert 'test-secret' not in v.text


def test_outcome_and_report(client):
    v=comparison(client).json();approve(client,v['id'],manager_approved=True)
    p=dict(actual_extra_cost=130,actual_wait_minutes=20,actual_extra_km=3,evidence='Chứng từ đã đối chiếu',confirmed=True)
    assert client.post('/api/planning/comparisons/'+v['id']+'/outcome',json=p).status_code==200
    assert client.post('/api/planning/comparisons/'+v['id']+'/outcome',json=p).status_code==409
    m=client.get('/api/planning/metrics').json();assert m['outcome_count']==1 and m['average_cost_error']==30
    assert client.get('/api/planning/export.csv').status_code==200


def test_imap_readonly_peek_and_tls(monkeypatch):
    from backend.app.services.documents import inbox
    monkeypatch.setenv('MAIL_READ_ENABLED','true');monkeypatch.setenv('MAIL_IMAP_HOST','mail.example.com');monkeypatch.setenv('MAIL_ALLOWED_HOSTS','mail.example.com');monkeypatch.setenv('MAIL_USERNAME','user');monkeypatch.setenv('MAIL_PASSWORD','private')
    raw=b'Subject: Schedule\r\n\r\nBooking: BK-UI-1001'
    with patch('backend.app.services.documents.imaplib.IMAP4_SSL') as f:
        m=f.return_value.__enter__.return_value;m.select.return_value=('OK',[b'1'])
        m.uid.side_effect=[('OK',[b'123']),('OK',[b'1 (RFC822.SIZE 49)']),('OK',[(b'body',raw)])]
        v=inbox()
        assert v[0]['uid']=='123'
        assert m.select.call_args.kwargs['readonly'] is True
        assert m.uid.call_args.args==('fetch',b'123','(BODY.PEEK[])')
        assert f.call_args.kwargs['ssl_context'].check_hostname
        assert 'private' not in str(v)

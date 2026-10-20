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
    assert r.headers['WWW-Authenticate']=='Basic realm="U&I Dispatch Demo", charset="UTF-8"'
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

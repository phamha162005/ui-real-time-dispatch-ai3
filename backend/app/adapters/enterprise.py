"""Read-only JSON connector. No endpoint or secret can be supplied by the browser."""
import json,os,time
from urllib.parse import urlsplit
import httpx

class SourceError(RuntimeError):pass

class ReadOnlyJSONAdapter:
    def __init__(self,source):
        self.source=source
        self.endpoint=os.getenv(source+'_API_URL','').strip()
        self.enabled=os.getenv(source+'_READ_ENABLED','false').lower()=='true'
        self.hosts=[x.strip().lower() for x in os.getenv(source+'_ALLOWED_HOSTS','').split(',') if x.strip()]
        self.auth=os.getenv(source+'_AUTH_MODE','bearer').lower()
        self.secret=os.getenv(source+'_API_TOKEN','')
        try:self.timeout=max(1,min(10,float(os.getenv('EXTERNAL_API_TIMEOUT_SECONDS','8'))))
        except ValueError:self.timeout=8
    def checks(self):
        try:
            url=urlsplit(self.endpoint)
            endpoint_ok=url.scheme=='https' and bool(url.hostname) and not url.username and not url.password and not url.fragment and (url.port is None or 1<=url.port<=65535) and not any(c in self.endpoint for c in ['\r','\n','\t'])
            allowed=bool(endpoint_ok and url.hostname.lower() in self.hosts)
        except ValueError:endpoint_ok=False;allowed=False
        auth_ok=self.auth=='none' or (self.auth in ['bearer','api_key'] and bool(self.secret) and '\r' not in self.secret and '\n' not in self.secret)
        return {'read_enabled':self.enabled,'endpoint_configured':endpoint_ok,'host_allowed':allowed,'authentication_configured':auth_ok,'auth_mode':self.auth if self.auth in ['bearer','api_key','none'] else 'unsupported','timeout_seconds':self.timeout,'ready':self.enabled and endpoint_ok and allowed and auth_ok}
    def read(self):
        if not self.checks()['ready']:raise SourceError('Chưa đủ cấu hình được cấp quyền: cần bật đọc, URL HTTPS, hostname cho phép và thông tin xác thực ở backend.')
        headers={'Accept':'application/json','User-Agent':'UI-Dispatch-ReadConnector/1.4'}
        if self.auth=='bearer':headers['Authorization']='Bearer '+self.secret
        elif self.auth=='api_key':headers['X-API-Key']=self.secret
        started=time.monotonic();body=bytearray()
        try:
            with httpx.Client(timeout=self.timeout,follow_redirects=False,trust_env=False) as c:
                with c.stream('GET',self.endpoint,headers=headers) as r:
                    if r.status_code in [401,403]:raise SourceError('Nguồn từ chối xác thực hoặc chưa cấp quyền đọc (401/403).')
                    if r.status_code==429:raise SourceError('Nguồn đang giới hạn tần suất (429). Thử lại sau.')
                    if r.status_code>=300:raise SourceError('Nguồn trả lỗi HTTP hoặc chuyển hướng; kiểm tra endpoint đã được phê duyệt.')
                    for chunk in r.iter_bytes():
                        body.extend(chunk)
                        if len(body)>2000000:raise SourceError('Phản hồi vượt 2 MB; cần endpoint phân trang hoặc thu hẹp khoảng thời gian.')
                        if time.monotonic()-started>10:raise SourceError('Đọc nguồn vượt thời hạn; kiểm tra kết nối hoặc chia nhỏ dữ liệu.')
            return json.loads(body)
        except httpx.TimeoutException:raise SourceError('Nguồn không phản hồi trong thời hạn cấu hình.') from None
        except (httpx.HTTPError,httpx.InvalidURL):raise SourceError('Không đọc được nguồn. Kiểm tra DNS, mạng, chứng chỉ TLS hoặc quyền truy cập.') from None
        except (ValueError,UnicodeError):raise SourceError('Phản hồi chưa phải JSON hợp lệ.') from None

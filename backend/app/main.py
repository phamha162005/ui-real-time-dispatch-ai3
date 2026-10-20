import base64, hmac, logging, os, sqlite3
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from .api.routes import router
from .api.operations import router as operations_router
from .api.enterprise import router as enterprise_router
from .store import Store
from .adapters.enterprise import ReadOnlyJSONAdapter

ROOT=Path(__file__).resolve().parents[2]
load_dotenv(ROOT/'.env')

def create_app(database_path=None):
    app=FastAPI(docs_url=None,redoc_url=None,title='Dispatch AI',version='1.6.0',description='Bản demo dùng dữ liệu giả lập. Bộ máy quy tắc hỗ trợ quyết định; chưa có mô hình AI huấn luyện. Không gửi lệnh điều xe thật. Khi triển khai công khai, bật APP_ENV=production và cấu hình DEMO_USERNAME/DEMO_PASSWORD.')
    path=database_path or os.getenv('DATABASE_PATH','data/dispatch.sqlite3')
    if not Path(path).is_absolute(): path=ROOT/path
    app.state.store=Store(path)
    app.include_router(router)
    app.include_router(operations_router)
    app.include_router(enterprise_router)
    @app.exception_handler(sqlite3.OperationalError)
    async def database_error(request:Request,exc):
        logging.exception('Database operation failed')
        return JSONResponse(status_code=503,content={'detail':'Cơ sở dữ liệu đang bận hoặc không khả dụng. Hãy thử lại.'})
    @app.middleware('http')
    async def headers(request,call_next):
        # Hosted demo: protect every page and API except the minimal health probe.
        if os.getenv('APP_ENV', 'local').lower() == 'production' and request.url.path != '/health':
            username=os.getenv('DEMO_USERNAME', '')
            password=os.getenv('DEMO_PASSWORD', '')
            if not username or not password:
                return JSONResponse(status_code=503, content={'detail':'Demo credentials are not configured.'},headers={'Cache-Control':'no-store'})
            auth=request.headers.get('authorization', '')
            valid=False
            if auth.startswith('Basic '):
                try:
                    decoded=base64.b64decode(auth[6:], validate=True).decode('utf-8')
                    supplied_user, supplied_password=decoded.split(':', 1)
                    valid=hmac.compare_digest(supplied_user.encode('utf-8'), username.encode('utf-8')) and hmac.compare_digest(supplied_password.encode('utf-8'), password.encode('utf-8'))
                except (ValueError, UnicodeDecodeError):
                    valid=False
            if not valid:
                return JSONResponse(status_code=401, content={'detail':'Authentication required.'}, headers={'WWW-Authenticate':'Basic realm="Dispatch AI", charset="UTF-8"', 'Cache-Control':'no-store'})
        response=await call_next(request)
        if request.url.path=='/' or request.url.path.startswith(('/api/','/static/')):
            response.headers['Cache-Control']='no-store'
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['Referrer-Policy']='strict-origin-when-cross-origin'
        response.headers['Content-Security-Policy']="default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https://tile.openstreetmap.org https://*.tile.openstreetmap.org; connect-src 'self'; frame-ancestors 'none'" if not request.url.path.startswith(('/docs','/redoc')) else "frame-ancestors 'none'"
        return response
    app.mount('/static',StaticFiles(directory=ROOT/'frontend'),name='static')
    @app.get('/',include_in_schema=False)
    def home(): return FileResponse(ROOT/'frontend/index.html')
    @app.get('/docs',include_in_schema=False)
    def docs(): return FileResponse(ROOT/'frontend/docs.html')
    @app.get('/health',tags=['Trạng thái'])
    def health():
        if os.getenv('APP_ENV','local').lower()=='production':return {'status':'ok'}
        return {'status':'ok','mode':'demo','external_read_enabled':{source:ReadOnlyJSONAdapter(source).enabled for source in ['TMS','GPS','ONP']},'outbound_orders_enabled':False}
    return app

app=create_app()

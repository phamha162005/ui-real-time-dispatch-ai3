import json,uuid,csv,io
from datetime import datetime,timezone
from fastapi import APIRouter,Request,HTTPException
from fastapi.responses import Response
from ..schemas.enterprise import Source,SourceConfig,FilePreview,BatchApproval
from ..schemas.operations import Approval
from ..services.enterprise import fields,parse_file,extract_rows,normalize,sample_rows
from ..services.eta import dt,evaluate
from ..adapters.enterprise import ReadOnlyJSONAdapter,SourceError
from ..store import utcnow

router=APIRouter(prefix='/api/enterprise',tags=['Kết nối doanh nghiệp'])

def configuration(s,db,source):return s.get(db,'enterprise-config:'+source) or {'mapping':{k:k for k in fields(source)},'rows_path':'','revision':0}
def dataset(s,db,source):return s.get(db,'enterprise-data:'+source) or {'records':[],'revision':0,'updated_at':None}
def approved(p):
    if not p.confirmed:raise HTTPException(422,'Cần xác nhận trước khi đọc nguồn hoặc cập nhật dữ liệu')

@router.get('/status')
def status(request:Request):
    s=request.app.state.store
    with s.tx() as db:
        return [{'source':src,'checks':ReadOnlyJSONAdapter(src).checks(),'fields':fields(src),'config':configuration(s,db,src),'dataset_count':len(dataset(s,db,src)['records']),'dataset_updated_at':dataset(s,db,src)['updated_at'],'last_test':s.get(db,'enterprise-test:'+src)} for src in ['TMS','GPS','ONP']]

@router.put('/{source}/config')
def save_config(source:Source,p:SourceConfig,request:Request):
    if set(p.mapping)-set(fields(source)):raise HTTPException(422,'Ánh xạ chứa trường nội bộ không hợp lệ')
    s=request.app.state.store
    with s.tx() as db:
        config={**p.model_dump(),'revision':configuration(s,db,source)['revision']+1}
        s.put(db,'enterprise-config:'+source,config);return config

def preview_result(s,db,source,rows,config,method):
    valid,errors=normalize(source,rows,config['mapping'])
    batch={'id':uuid.uuid4().hex,'source':source,'method':method,'created_at':utcnow().isoformat(),'count':len(rows),'valid_count':len(valid),'errors':errors,'records':valid,'config_revision':config['revision'],'data_revision':dataset(s,db,source)['revision'],'applied':False}
    s.put(db,'enterprise-batch:'+batch['id'],batch)
    # Keep at most 20 staged batches; all data stays in the local SQLite file.
    keys=[r['key'] for r in db.execute("SELECT key FROM meta WHERE key LIKE 'enterprise-batch:%' ORDER BY rowid DESC")]
    for key in keys[20:]:db.execute('DELETE FROM meta WHERE key=?',(key,))
    return batch

@router.post('/{source}/preview-file')
def preview_file(source:Source,p:FilePreview,request:Request):
    s=request.app.state.store
    with s.tx() as db:
        config=configuration(s,db,source);rows=parse_file(p.format,p.text,config['rows_path'])
        return preview_result(s,db,source,rows,config,'file')

@router.post('/{source}/preview-api')
def preview_api(source:Source,p:Approval,request:Request):
    approved(p);s=request.app.state.store
    with s.tx() as db:config=configuration(s,db,source)
    try:
        payload=ReadOnlyJSONAdapter(source).read();rows=extract_rows(payload,config['rows_path'])
    except (SourceError,HTTPException) as e:
        message=str(e) if isinstance(e,SourceError) else str(e.detail)
        with s.tx() as db:s.put(db,'enterprise-test:'+source,{'attempted_at':utcnow().isoformat(),'success':False,'message':message})
        raise HTTPException(502,message) from None
    with s.tx() as db:
        if configuration(s,db,source)['revision']!=config['revision']:raise HTTPException(409,'Ánh xạ đã đổi trong lúc đọc API. Kiểm tra và đọc lại')
        batch=preview_result(s,db,source,rows,config,'api')
        s.put(db,'enterprise-test:'+source,{'attempted_at':utcnow().isoformat(),'success':not batch['errors'],'message':f"Đã đọc {len(rows)} dòng; {len(batch['errors'])} lỗi chuẩn hóa. Chưa cập nhật dữ liệu."})
        return batch

@router.post('/{source}/commit')
def commit(source:Source,p:BatchApproval,request:Request):
    approved(p);s=request.app.state.store
    with s.tx() as db:
        batch=s.get(db,'enterprise-batch:'+p.batch_id)
        if not batch or batch['source']!=source:raise HTTPException(404,'Không tìm thấy đợt dữ liệu của nguồn này')
        if batch['applied']:raise HTTPException(409,'Đợt dữ liệu đã cập nhật; không ghi lại')
        old=dataset(s,db,source)
        if old['revision']!=batch['data_revision'] or configuration(s,db,source)['revision']!=batch['config_revision']:raise HTTPException(409,'Dữ liệu hoặc ánh xạ đã thay đổi. Xem trước lại trước khi cập nhật')
        if batch['errors'] or not batch['records']:raise HTTPException(422,'Cần xử lý hết lỗi dữ liệu trước khi cập nhật toàn bộ đợt')
        def key(r):return r['vehicle_id'] if source=='GPS' else r['code'] if source=='TMS' else r['external_id']
        merged={key(r):r for r in old['records']};ignored=0
        for r in batch['records']:
            existing=merged.get(key(r))
            if existing and dt(r['source_updated_at'])<=dt(existing['source_updated_at']):ignored+=1;continue
            merged[key(r)]={**r,'ingested_at':utcnow().isoformat(),'ingestion_method':batch['method']}
        if len(merged)>10000:raise HTTPException(422,'Kho dữ liệu nguồn vượt 10.000 khóa; cần thu hẹp phạm vi hoặc lưu trữ lịch sử riêng')
        saved={'revision':old['revision']+1,'updated_at':utcnow().isoformat(),'records':list(merged.values())}
        s.put(db,'enterprise-data:'+source,saved);batch['applied']=True;s.put(db,'enterprise-batch:'+batch['id'],batch)
        return {'source':source,'count':len(saved['records']),'ignored_older_or_equal':ignored,'updated_at':saved['updated_at'],'message':'Đã cập nhật khu vực dữ liệu doanh nghiệp; chưa sửa hoặc gửi lệnh điều xe.'}

@router.get('/{source}/data')
def data(source:Source,request:Request):
    s=request.app.state.store
    with s.tx() as db:result=dataset(s,db,source)
    result['total_count']=len(result['records'])
    result['records']=result['records'][:1000]
    if source=='GPS':
        now=utcnow()
        for r in result['records']:r['age_minutes']=round((now-dt(r['source_updated_at'])).total_seconds()/60,1)
    if source=='TMS':
        for r in result['records']:
            t={**r,'remaining_minutes':r['travel_minutes']+r['handling_minutes']+r['delay_minutes']}
            # A source snapshot has no live progress beyond its own timestamp.
            r['source_eta_preview']=None if r['status']=='hoan_thanh' else evaluate(t,dt(r['source_updated_at']))['eta']
    return result

@router.get('/{source}/template.csv')
def template(source:Source):
    rows=sample_rows(source);out=io.StringIO();writer=csv.DictWriter(out,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    return Response(('\ufeff'+out.getvalue()).encode('utf-8'),media_type='text/csv; charset=utf-8',headers={'Content-Disposition':f'attachment; filename="{source.lower()}_template.csv"'})

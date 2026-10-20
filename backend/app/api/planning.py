import base64,binascii,json,uuid
from datetime import datetime
from typing import Literal
from fastapi import APIRouter,Request,HTTPException
from pydantic import Field,field_validator
from ..schemas.operations import Input,Approval
from ..services.documents import read_document,extract,config,inbox
from ..services.operations import baseline
from ..store import utcnow
from .routes import trip_by_id

router=APIRouter(prefix='/api/planning',tags=['Đọc chứng từ & xử lý thay đổi'])
class DocumentInput(Input):
    name:str=Field(max_length=200)
    content_base64:str=Field(max_length=2700000)
class ExtractInput(Input):
    text:str=Field(min_length=5,max_length=12000)
    use_ai:bool=False
    confirmed:bool=False
class CostOption(Input):
    name:str=Field(min_length=2,max_length=80)
    action:Literal['continue','wait','return','reschedule','replace','outsource','reorder','combine','alternative']
    extra_minutes:float=Field(ge=0,le=100000)
    extra_km:float=Field(ge=0,le=100000)
    wait_minutes:float=Field(ge=0,le=100000)
    buffer_minutes:float=Field(ge=-100000,le=100000)
    trailer_ok:bool=False
    capacity_ok:bool=False
    hours_ok:bool=False
    booking_ok:bool=False
    safety_ok:bool=False
    costs:dict[str,float|None]
    evidence:str=Field(default='',max_length=1000)
    @field_validator('costs')
    @classmethod
    def check_costs(cls,v):
        keys={'fuel','toll','waiting','handling','return_outsource','other'}
        if set(v)!=keys:raise ValueError('Cần đủ sáu cấu phần chi phí; để null khi thiếu dữ liệu.')
        import math
        if any(x is not None and (not math.isfinite(x) or x<0 or x>1e12) for x in v.values()):raise ValueError('Chi phí cần số không âm hữu hạn.')
        return v
class Comparison(Input):
    trip_id:int
    reason:str=Field(min_length=5,max_length=1000)
    options:list[CostOption]=Field(min_length=2,max_length=9)
    approval_limit:float=Field(ge=0,le=1e12)
class Decision(Approval):
    option_index:int=Field(ge=0,le=8)
    reviewer:str=Field(min_length=2,max_length=80)
    manager_approved:bool=False
    note:str=Field(min_length=5,max_length=1000)

@router.get('/connections')
def connections():return config()
@router.post('/document')
def document(p:DocumentInput):
    try:raw=base64.b64decode(p.content_base64,validate=True)
    except (ValueError,binascii.Error):raise HTTPException(422,'Tệp mã hóa không hợp lệ.') from None
    return read_document(p.name,raw)
@router.post('/extract')
def extraction(p:ExtractInput,request:Request):
    if p.use_ai and not p.confirmed:raise HTTPException(422,'Cần đồng ý gửi nội dung sang dịch vụ AI đã cấu hình.')
    result=extract(p.text,p.use_ai)
    s=request.app.state.store
    with s.tx() as db:
        matches=[]
        for t in s.rows(db):
            old=baseline(s,db,t)
            if t['status']=='hoan_thanh':continue
            v=result['values'];reasons=[]
            if v.get('booking') and v['booking']==old['booking']:reasons.append('Trùng booking')
            if t['code'].casefold() in p.text.casefold():reasons.append('Có mã chuyến')
            if v.get('container_id') and v['container_id']==old.get('container_id'):reasons.append('Trùng container')
            if reasons:matches.append({'id':t['id'],'code':t['code'],'reasons':reasons,'vehicle_id':t['vehicle_id'],'cutoff':t['cutoff']})
    return {**result,'matches':matches,'warning':'Chỉ đề xuất chuyến khớp mã; không tự chọn hoặc cập nhật chuyến.'}
@router.post('/mail/read')
def read_mail(p:Approval):
    if not p.confirmed:raise HTTPException(422,'Cần xác nhận đọc hộp thư đã được cấp quyền.')
    return {'messages':inbox()}

def save(s,db,v):s.put(db,'case:'+v['id'],v)
@router.post('/comparisons')
def compare(p:Comparison,request:Request):
    s=request.app.state.store
    with s.tx() as db:
        t=trip_by_id(s,db,p.trip_id)
        if t['status']=='hoan_thanh':raise HTTPException(409,'Chuyến đã hoàn thành.')
        options=[]
        for i,o in enumerate(p.options):
            v=o.model_dump();missing=[k for k,x in o.costs.items() if x is None]
            why=[k for k in ['trailer_ok','capacity_ok','hours_ok','booking_ok','safety_ok'] if not getattr(o,k)]
            if o.buffer_minutes<0:why.append('cutoff')
            options.append({**v,'index':i,'missing':missing,'feasible':not why,'violations':why,'total':None if missing else round(sum(o.costs.values()),2)})
        eligible=[o for o in options if o['feasible'] and o['total'] is not None]
        eligible.sort(key=lambda o:(o['total'],o['extra_minutes'],o['extra_km']))
        # Do not call any option cheapest while another feasible alternative has unknown cost.
        complete=not any(o['feasible'] and o['missing'] for o in options)
        v={'id':uuid.uuid4().hex,'trip_id':t['id'],'trip_code':t['code'],'source_revision':t['revision'],'reason':p.reason,'options':options,'approval_limit':p.approval_limit,'status':'draft','created_at':utcnow().isoformat(),'recommended':eligible[0]['index'] if eligible and complete else None,'cost_comparison_complete':complete,'ranking':[o['index'] for o in eligible]}
        save(s,db,v);return v
@router.get('/comparisons')
def history(request:Request):
    s=request.app.state.store
    with s.tx() as db:
        rows=[json.loads(x['value']) for x in db.execute("SELECT value FROM meta WHERE key LIKE 'case:%'")]
        return sorted(rows,key=lambda x:x['created_at'],reverse=True)[:50]
@router.post('/comparisons/{id}/approve')
def approve(id:str,p:Decision,request:Request):
    if not p.confirmed:raise HTTPException(422,'Cần xác nhận quyết định.')
    s=request.app.state.store
    with s.tx() as db:
        v=s.get(db,'case:'+id)
        if not v:raise HTTPException(404,'Không có bảng so sánh.')
        t=trip_by_id(s,db,v['trip_id'])
        if v['status']!='draft' or t['revision']!=v['source_revision'] or t['status']=='hoan_thanh':raise HTTPException(409,'Bảng đã duyệt hoặc chuyến đã đổi; lập bảng mới.')
        if p.option_index>=len(v['options']):raise HTTPException(422,'Phương án không tồn tại.')
        o=v['options'][p.option_index]
        if not o['feasible'] or o['missing']:raise HTTPException(422,'Phương án chưa đủ ràng buộc hoặc dữ liệu chi phí.')
        if o['total']>v['approval_limit'] and not p.manager_approved:raise HTTPException(422,'Vượt hạn mức: cần ghi nhận phê duyệt của Trưởng bộ phận.')
        v.update(status='approved',selected_index=p.option_index,reviewer=p.reviewer,manager_approved=p.manager_approved,note=p.note,approved_at=utcnow().isoformat())
        save(s,db,v);return v

class Outcome(Approval):
    actual_extra_cost:float=Field(ge=0,le=1e12)
    actual_wait_minutes:float=Field(ge=0,le=100000)
    actual_extra_km:float=Field(ge=0,le=100000)
    evidence:str=Field(min_length=5,max_length=1000)
@router.post('/comparisons/{id}/outcome')
def outcome(id:str,p:Outcome,request:Request):
    if not p.confirmed:raise HTTPException(422,'Cần xác nhận số liệu thực tế.')
    s=request.app.state.store
    with s.tx() as db:
        v=s.get(db,'case:'+id)
        if not v or v['status']!='approved':raise HTTPException(409,'Cần phương án đã duyệt.')
        if v.get('outcome'):raise HTTPException(409,'Đã ghi nhận kết quả; giữ nguyên để đối chiếu nhật ký.')
        v['outcome']={**p.model_dump(exclude={'confirmed'}),'recorded_at':utcnow().isoformat()};save(s,db,v);return v
@router.get('/metrics')
def metrics(request:Request):
    rows=history(request);approved=[v for v in rows if v['status']=='approved'];actual=[v for v in approved if v.get('outcome')]
    deltas=[v['outcome']['actual_extra_cost']-v['options'][v['selected_index']]['total'] for v in actual]
    elapsed=[( datetime.fromisoformat(v['approved_at'])-datetime.fromisoformat(v['created_at'])).total_seconds()/60 for v in approved]
    return {'case_count':len(rows),'approved_count':len(approved),'complete_count':sum(v['cost_comparison_complete'] for v in rows),'outcome_count':len(actual),'average_decision_minutes':round(sum(elapsed)/len(elapsed),2) if elapsed else None,'average_cost_error':round(sum(deltas)/len(deltas),2) if deltas else None,'scope':'Tối đa 50 bảng gần nhất. Thời gian từ lập bảng đến phê duyệt; chưa bao gồm thời gian trước khi tiếp nhận. Chưa có kỳ cơ sở để kết luận tỷ lệ tiết kiệm.'}
@router.get('/export.csv')
def export(request:Request):
    import csv,io
    from fastapi.responses import Response
    out=io.StringIO();w=csv.writer(out);w.writerow(['Mã chuyến','Tình huống','Phương án','Chi phí tăng thêm dự kiến','Phút tăng thêm','Km tăng thêm','Phút chờ','Đủ điều kiện','Thiếu chi phí','Người duyệt','Chi phí thực tế của phương án đã chọn'])
    def safe(x):
        s='' if x is None else str(x)
        return "'"+s if s.lstrip().startswith(('=','+','-','@')) else s
    for v in history(request):
        for o in v['options']:w.writerow([safe(x) for x in [v['trip_code'],v['reason'],o['name'],o['total'],o['extra_minutes'],o['extra_km'],o['wait_minutes'],o['feasible'],','.join(o['missing']),v.get('reviewer'),v.get('outcome',{}).get('actual_extra_cost') if o['index']==v.get('selected_index') else None]])
    return Response(('\ufeff'+out.getvalue()).encode(),media_type='text/csv; charset=utf-8',headers={'Content-Disposition':'attachment; filename="so_sanh_chi_phi.csv"'})

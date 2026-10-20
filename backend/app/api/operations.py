import json, uuid
from fastapi import APIRouter, HTTPException, Request
from ..schemas.operations import NoticeInput, Approval, OrderInput, DriverEvent, PilotInput, FleetCSV
from ..services.operations import parse_notice, baseline, changes, pilot_analysis, order_rows, save_order, view_order, workflow_state
from ..schemas.models import TripInput
from ..store import utcnow
from .routes import trip_by_id, save_input

router=APIRouter(prefix='/api',tags=['Thay đổi & xác nhận'])

def require_confirmed(p):
    if not p.confirmed:raise HTTPException(422,'Cần xác nhận trước khi thực hiện')

def record(db,table,id):
    row=db.execute(f'SELECT payload FROM {table} WHERE id=?',(id,)).fetchone()
    if not row:raise HTTPException(404,'Không tìm thấy bản ghi')
    return dict(json.loads(row['payload']),id=id)

@router.post('/notices/preview')
def preview(p:NoticeInput,request:Request):
    s=request.app.state.store
    with s.tx() as db:
        c=s.tick(db);t=trip_by_id(s,db,p.trip_id)
        if t['status']=='hoan_thanh':raise HTTPException(409,'Chuyến đã hoàn thành; chỉ xem lịch sử, không điều chỉnh')
        values,warnings=parse_notice(p.text)
        if 'origin' in values or 'destination' in values:warnings.append('Đổi điểm lấy/giao: cần kiểm tra lại quãng đường và thời gian di chuyển trong Quản lý chuyến xe.')
        if 'vehicle_id' in values:warnings.append('Xe thay thế phải thuộc đội xe, đúng loại, đủ tải và chưa được phân công cho chuyến khác.')
        if values.get('incident'):warnings.append('Ghi nhận sự cố chưa tự dừng xe. Điều vận cần phát hành lệnh xử lý và chờ lái xe xác nhận.')
        old=baseline(s,db,t);diff=changes(old,values)
        v={'id':uuid.uuid4().hex,'trip_id':t['id'],'trip_code':t['code'],'kind':p.kind,'text':p.text,'values':values,'changes':diff,'warnings':warnings,'source_revision':t['revision'],'before':old,'status':'pending','created_at':c['now'],'real_at':utcnow().isoformat(),'source_text':p.source_text,'source_name':p.source_name,'read_method':p.read_method,'method':'Đối chiếu trường đã trích xuất bằng quy tắc; cần nhân viên xác minh'}
        db.execute('INSERT INTO notices VALUES(?,?)',(v['id'],json.dumps(v,ensure_ascii=False)))
        return v

@router.post('/notices/{id}/apply')
def apply_notice(id:str,p:Approval,request:Request):
    require_confirmed(p);s=request.app.state.store
    with s.tx() as db:
        c=s.tick(db);n=record(db,'notices',id);t=trip_by_id(s,db,n['trip_id'])
        if n['status']!='pending':raise HTTPException(409,'Thông báo đã được xử lý')
        if t['status']=='hoan_thanh' or t['revision']!=n['source_revision'] or baseline(s,db,t)!=n['before']:
            raise HTTPException(409,'Dữ liệu đã đổi; đọc và đối chiếu thông báo lại')
        if not n['changes']:raise HTTPException(422,'Không có thay đổi để cập nhật')
        data=TripInput.model_validate({k:t[k] for k in TripInput.model_fields if k in t}).model_dump(mode='json')
        for k in ['cutoff','origin','destination','vehicle_id']:
            if k in n['values']:data[k]=n['values'][k]
        if n['values'].get('cancelled'):data['data_issue']='missing'
        # An elapsed job keeps the current remaining work when its metadata changes.
        current_remaining=t['remaining_minutes']
        try:validated=TripInput.model_validate(data).model_dump(mode='json')
        except ValueError as e:raise HTTPException(422,'Thông báo không phù hợp thời gian/tải trọng chuyến. Kiểm tra dữ liệu trước khi cập nhật.') from e
        save_input(s,db,validated,t['id'])
        latest=trip_by_id(s,db,t['id']);latest['remaining_minutes']=current_remaining
        s.save_trip(db,latest,t['id'])
        s.put(db,'notice-baseline:'+str(t['id']),{**n['before'],**n['values']})
        n.update(status='applied',applied_at=c['now'],applied_real_at=utcnow().isoformat())
        db.execute('UPDATE notices SET payload=? WHERE id=?',(json.dumps(n,ensure_ascii=False),id))
        return {**n,'next_step':'Đã cập nhật dữ liệu. Phát hành lệnh mới và chờ lái xe xác nhận trong mục Lệnh & xác nhận; chưa gửi lệnh ra ngoài.'}

@router.post('/pilot/analyze',tags=['Tái phân bổ phương tiện'])
def pilot(p:PilotInput):return pilot_analysis([v.model_dump() for v in p.vehicles])

@router.get('/operations')
def operations(request:Request):
    s=request.app.state.store
    with s.tx() as db:return workflow_state(s,db,s.tick(db))

@router.post('/orders',status_code=201)
def issue(p:OrderInput,request:Request):
    require_confirmed(p);s=request.app.state.store
    with s.tx() as db:
        c=s.tick(db);t=trip_by_id(s,db,p.trip_id)
        if t['status']=='hoan_thanh':raise HTTPException(409,'Không phát hành lệnh cho chuyến đã hoàn thành')
        if not t.get('vehicle_id'):raise HTTPException(422,'Chọn và phân công xe cho chuyến trước khi phát hành lệnh')
        case=None
        if p.comparison_id:
            case=s.get(db,'case:'+p.comparison_id)
            if not case or case['status']!='approved' or case['trip_id']!=t['id'] or case['source_revision']!=t['revision']:
                raise HTTPException(409,'Phương án phê duyệt không còn khớp chuyến; phân tích và duyệt lại.')
        previous=[o for o in order_rows(db) if o['trip_id']==t['id']]
        version=max((o['version'] for o in previous),default=0)
        if p.trip_revision!=t['revision'] or p.expected_version!=version:raise HTTPException(409,'Chuyến hoặc phiên bản lệnh đã thay đổi; tải lại trước khi phát hành')
        for o in previous:
            if o['active']:
                o.update(active=False,superseded_at=c['now']);save_order(db,o)
        event={'event':'sent','sim_at':c['now'],'real_at':utcnow().isoformat()}
        o={'trip_id':t['id'],'trip_code':t['code'],'vehicle_id':t['vehicle_id'],'driver':p.driver,'version':version+1,'source_revision':t['revision'],'action':p.action,'instructions':p.instructions,'trip_snapshot':{k:t[k] for k in ['origin','destination','cutoff','vehicle_id']},'active':True,'status':'sent','sent_at':c['now'],'received_at':None,'confirmed_at':None,'sent_elapsed':c.get('elapsed_minutes',0),'confirmed_elapsed':None,'events':[event],'comparison_id':p.comparison_id,'approved_option':case['options'][case['selected_index']] if case else None}
        id=db.execute('INSERT INTO orders(payload) VALUES(?)',(json.dumps(o,ensure_ascii=False),)).lastrowid
        return {**o,'id':id}

@router.post('/orders/{id}/driver')
def driver_event(id:int,p:DriverEvent,request:Request):
    require_confirmed(p);s=request.app.state.store
    with s.tx() as db:
        c=s.tick(db);o=record(db,'orders',id)
        if not o['active']:raise HTTPException(409,'Lệnh đã hết hiệu lực; không thể thao tác phiên bản cũ')
        if o['driver']!=p.driver:raise HTTPException(409,'Lệnh thuộc lái xe khác')
        t=trip_by_id(s,db,o['trip_id'])
        if view_order(o,c,s.rows(db))['stale']:raise HTTPException(409,'Dữ liệu chuyến đã đổi; yêu cầu điều vận phát hành lệnh mới')
        if t['status']=='hoan_thanh':raise HTTPException(409,'Chuyến đã hoàn thành')
        allowed={'receive':['sent'],'confirm':['received'],'reject':['received'],'execute':['confirmed']}
        if o['status'] not in allowed[p.action]:raise HTTPException(409,'Thao tác không phù hợp trạng thái hiện tại')
        event={'event':p.action,'sim_at':c['now'],'real_at':utcnow().isoformat()}
        if p.action=='receive':o.update(status='received',received_at=c['now'],received_elapsed=c.get('elapsed_minutes',0))
        elif p.action=='confirm':
            o.update(status='confirmed',confirmed_at=c['now'],confirmed_elapsed=c.get('elapsed_minutes',0))
        elif p.action=='reject':
            if len(p.reason)<3:raise HTTPException(422,'Nhập lý do không thể thực hiện (ít nhất 3 ký tự)')
            o.update(status='rejected',reason=p.reason);event['reason']=p.reason
        else:
            t.update(status='tam_dung' if o['action']=='hold' else 'dang_chay',revision=t['revision']+1,updated_at=utcnow().isoformat())
            s.save_trip(db,t,t['id']);o.update(status='executing',source_revision=t['revision'],executed_at=c['now'])
        o['events'].append(event);save_order(db,o)
        return view_order(o,c,s.rows(db))

@router.get('/orders/export.csv')
def export_orders(request:Request):
    import csv, io
    from fastapi.responses import Response
    s=request.app.state.store
    with s.tx() as db:
        c=s.tick(db);orders=workflow_state(s,db,c)['orders']
    out=io.StringIO();w=csv.writer(out)
    w.writerow(['Mã chuyến','Phiên bản','Xe','Lái xe','Hiệu lực','Trạng thái','Gửi (+07:00)','Nhận (+07:00)','Xác nhận (+07:00)','Phản hồi (phút)','Nội dung'])
    def safe(v):
        st='' if v is None else str(v)
        return "'"+st if st.lstrip().startswith(('=','+','-','@','\t','\r')) else st
    for o in orders:w.writerow([safe(v) for v in [o['trip_code'],o['version'],o['vehicle_id'],o['driver'],o['active'],o['status'],o['sent_at'],o['received_at'],o['confirmed_at'],o['response_minutes'],o['instructions']]])
    return Response(('\ufeff'+out.getvalue()).encode('utf-8'),media_type='text/csv; charset=utf-8',headers={'Content-Disposition':'attachment; filename="nhat_ky_lenh.csv"'})


DEFAULT_PILOT_FLEET=[
    dict(plate=p,tours=t,km=k,at_yard=y,trailer_ok=True,capacity_ok=True,ready=True,hours_ok=True,cutoff_ok=True)
    for p,t,k,y in [('61C-172.28',56.5,154.54,False),('61C-277.11',55,147.96,False),('61C-304.40',56.5,149.51,True)]
]

@router.get('/pilot/fleet',tags=['Tái phân bổ phương tiện'])
def get_pilot_fleet(request:Request):
    s=request.app.state.store
    with s.tx() as db:
        saved=s.get(db,'comparison-fleet')
        return saved if saved is not None else {'vehicles':DEFAULT_PILOT_FLEET}

@router.put('/pilot/fleet',tags=['Tái phân bổ phương tiện'])
def save_pilot_fleet(p:PilotInput,request:Request):
    s=request.app.state.store
    with s.tx() as db:
        s.put(db,'comparison-fleet',p.model_dump())
        return p.model_dump()

@router.post('/pilot/fleet/import',tags=['Tái phân bổ phương tiện'])
def import_pilot_fleet(p:FleetCSV):
    import csv,io
    from pydantic import ValidationError
    text=p.text.lstrip('\ufeff')
    columns=['plate','tours','km','at_yard','trailer_ok','capacity_ok','ready','hours_ok','cutoff_ok']
    header=text.splitlines()[0]
    delimiter=';' if header.count(';')>header.count(',') else ','
    reader=csv.DictReader(io.StringIO(text),delimiter=delimiter)
    fields=[(v or '').strip() for v in (reader.fieldnames or [])]
    if len(fields)!=len(set(fields)) or set(fields)!=set(columns):
        raise HTTPException(422,'CSV cần đủ, không trùng các cột: '+', '.join(columns))
    reader.fieldnames=fields
    vehicles=[]
    for row in reader:
        if not any(str(v or '').strip() for v in row.values()):continue
        if None in row or any(row.get(k) is None for k in columns):raise HTTPException(422,f'Dòng {reader.line_num}: sai số cột')
        v={k:str(row[k]).strip() for k in columns}
        for k in ['tours','km']:
            try:v[k]=float(v[k].replace(',','.'))
            except ValueError:raise HTTPException(422,f'Dòng {reader.line_num}: {k} phải là số')
        for k in columns[3:]:
            word=v[k].casefold()
            if word in ['1','true','yes','có','co']:v[k]=True
            elif word in ['0','false','no','không','khong']:v[k]=False
            else:raise HTTPException(422,f'Dòng {reader.line_num}: {k} cần 1/0 hoặc true/false')
        vehicles.append(v)
        if len(vehicles)>10000:raise HTTPException(422,'Tối đa 10.000 xe mỗi danh sách')
    try:return PilotInput(vehicles=vehicles).model_dump()
    except ValidationError as e:
        errors='; '.join(' / '.join(map(str,x['loc']))+': '+x['msg'] for x in e.errors())
        raise HTTPException(422,'CSV chưa hợp lệ: '+errors)

@router.get('/pilot/fleet/template.csv',tags=['Tái phân bổ phương tiện'])
def fleet_template():
    import csv,io
    from fastapi.responses import Response
    out=io.StringIO();writer=csv.DictWriter(out,fieldnames=list(DEFAULT_PILOT_FLEET[0]))
    writer.writeheader();writer.writerows(DEFAULT_PILOT_FLEET)
    return Response(('\ufeff'+out.getvalue()).encode('utf-8'),media_type='text/csv; charset=utf-8',headers={'Content-Disposition':'attachment; filename="danh_sach_xe_mau.csv"'})

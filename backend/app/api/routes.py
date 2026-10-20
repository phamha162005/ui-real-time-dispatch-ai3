import csv, io, json, sqlite3, uuid
from dataclasses import asdict
from datetime import timedelta
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response
from ..schemas.models import TripInput, ClockCommand, AnalysisInput, ConfirmInput
from ..services.eta import dt, evaluate
from ..services.dispatch import analyze
from ..services.reporting import report
from ..services.operations import order_alerts, workflow_state, order_rows, save_order
from ..store import utcnow
from ..adapters.mock import MockDataAdapter, VEHICLES
from ..adapters.integrations import TMSAdapter, GPSAdapter, ONPAdapter

router=APIRouter(prefix='/api')

def trip_by_id(store, db, id):
    t=next((t for t in store.rows(db) if t['id']==id),None)
    if not t: raise HTTPException(404,'Không tìm thấy chuyến xe')
    return t

def vehicle_check(store,db,data,exclude=None):
    if not data.get('vehicle_id'): return
    v=next((v for v in VEHICLES if v['id']==data['vehicle_id']),None)
    if not v: raise HTTPException(422,'Mã xe không tồn tại trong đội xe demo')
    if v['type']!=data['vehicle_type'] or v['capacity']<data['load']:
        raise HTTPException(422,'Xe được chọn không phù hợp loại xe hoặc tải hàng')
    if data['status']!='hoan_thanh' and any(t['id']!=exclude and t['vehicle_id']==v['id'] and t['status']!='hoan_thanh' for t in store.rows(db)):
        raise HTTPException(409,'Xe đã được phân công cho chuyến khác')

def sync_alerts(s,db,trips,c):
    wanted=order_alerts(s,db,c)
    for t in trips:
        if t['risk']!='thap' and t['status']!='hoan_thanh':
            key=f"trip:{t['id']}:{t['risk']}:{t['revision']}"
            wanted[key]={'kind':'cutoff','trip_id':t['id'],'level':t['risk'],'title':t['code']+' • '+t['risk_reason']}
        if t.get('data_issue','none')!='none':
            kind=t['data_issue'];key=f"data:{t['id']}:{kind}:{t['revision']}"
            wanted[key]={'kind':kind,'trip_id':t['id'],'level':'trung_binh','title':t['code']+(' • Thiếu xác nhận booking/container' if kind=='missing' else ' • Lỗi nguồn dữ liệu mô phỏng; cần xác minh thủ công')}
    for t in trips:
        n=s.get(db,'notice-baseline:'+str(t['id'])) or {}
        if n.get('cancelled') and t['status']!='hoan_thanh':
            key=f"booking-cancelled:{t['id']}:{t['revision']}"
            wanted[key]={'kind':'booking','trip_id':t['id'],'level':'cao','title':t['code']+' • Booking đã hủy; kiểm tra và phát hành lệnh xử lý cho lái xe'}
    old={row['id']:json.loads(row['payload']) for row in db.execute('SELECT * FROM alerts')}
    for key,v in wanted.items():
        old[key]={**v,'id':key,'created_at':old.get(key,{}).get('created_at',c['now']),'acknowledged':old.get(key,{}).get('acknowledged',False),'active':True}
    for key,a in old.items():
        if key not in wanted: a['active']=False
        db.execute('INSERT OR REPLACE INTO alerts VALUES(?,?)',(key,json.dumps(a)))
    return sorted(old.values(),key=lambda a:(a['active'],not a['acknowledged'],a['created_at']),reverse=True)

def snapshot(s,db):
    c=s.tick(db);trips=[evaluate(t,dt(c['now'])) for t in s.rows(db)]
    busy={t['vehicle_id'] for t in trips if t['status']!='hoan_thanh'}
    vehicles=[{**v,'available_now':v['available'] and v['id'] not in busy} for v in VEHICLES]
    alerts=sync_alerts(s,db,trips,c)
    return {'clock':c,'real_time':utcnow().isoformat(),'data_updated_at':utcnow().isoformat(),'trips':trips,'vehicles':vehicles,'alerts':alerts,'report':report(trips),'operations':workflow_state(s,db,c),'demo':True}

@router.get('/snapshot',tags=['Dashboard'])
def get_snapshot(request:Request):
    s=request.app.state.store
    with s.tx() as db: return snapshot(s,db)

@router.get('/trips',tags=['Chuyến xe'])
def list_trips(request:Request): return get_snapshot(request)['trips']

@router.get('/trips/{id}',tags=['Chuyến xe'])
def get_trip(id:int,request:Request):
    s=request.app.state.store
    with s.tx() as db:
        c=s.tick(db);return evaluate(trip_by_id(s,db,id),dt(c['now']))

def save_input(s,db,data,id=None):
    vehicle_check(s,db,data,id)
    old=trip_by_id(s,db,id) if id else None
    data['remaining_minutes']=data['travel_minutes']+data['handling_minutes']+data['delay_minutes']
    data['revision']=(old['revision']+1) if old else 1
    data['updated_at']=utcnow().isoformat()
    if data['status']=='hoan_thanh':
        data['remaining_minutes']=0
        data['completed_at']=old.get('completed_at',s.get(db,'clock')['now']) if old else s.get(db,'clock')['now']
    # Input durations represent work remaining at save time, avoiding hidden progress.
    try: id=s.save_trip(db,data,id)
    except sqlite3.IntegrityError: raise HTTPException(409,'Mã chuyến đã tồn tại')
    return id

@router.post('/trips',status_code=201,tags=['Chuyến xe'])
def create_trip(payload:TripInput,request:Request):
    s=request.app.state.store
    with s.tx() as db:
        c=s.tick(db);id=save_input(s,db,payload.model_dump(mode='json'))
        return evaluate(trip_by_id(s,db,id),dt(c['now']))

@router.put('/trips/{id}',tags=['Chuyến xe'])
def update_trip(id:int,payload:TripInput,request:Request):
    s=request.app.state.store
    with s.tx() as db:
        c=s.tick(db);save_input(s,db,payload.model_dump(mode='json'),id)
        return evaluate(trip_by_id(s,db,id),dt(c['now']))

@router.delete('/trips/{id}',tags=['Chuyến xe'])
def delete_trip(id:int,request:Request):
    s=request.app.state.store
    with s.tx() as db:
        trip_by_id(s,db,id)
        for o in order_rows(db):
            if o['trip_id']==id and o['active']:
                o.update(active=False,superseded_at=s.get(db,'clock')['now']);save_order(db,o)
        db.execute('DELETE FROM trips WHERE id=?',(id,))
        return {'deleted':id}

@router.get('/clock',tags=['Mô phỏng'])
def get_clock(request:Request): return get_snapshot(request)['clock']

@router.post('/clock',tags=['Mô phỏng'])
def control_clock(payload:ClockCommand,request:Request):
    s=request.app.state.store
    with s.tx() as db:
        c=s.tick(db)
        if payload.action in ['start','resume']: c['running']=True
        elif payload.action=='pause': c['running']=False
        elif payload.action=='speed':
            if payload.speed is None: raise HTTPException(422,'Cần chọn tốc độ 1, 10 hoặc 60')
            c['speed']=payload.speed
        elif payload.action=='reset':
            # Reset clock, and restart progress of unfinished trips only.
            c['now']=c['base'];c['running']=False;c['speed']=1
            for t in s.rows(db):
                if t['status']!='hoan_thanh':
                    t['remaining_minutes']=t['travel_minutes']+t['handling_minutes']+t['delay_minutes'];t['revision']+=1
                    s.save_trip(db,t,t['id'])
            db.execute('DELETE FROM analyses')
        s.put(db,'clock',c)
        if payload.action=='advance': s.tick(db,advance=payload.minutes)
        return snapshot(s,db)

@router.post('/demo/reset',tags=['Mô phỏng'])
def reset_demo(request:Request):
    s=request.app.state.store
    with s.tx() as db:
        s.seed(db);return snapshot(s,db)

@router.get('/sources',tags=['Nguồn dữ liệu'])
def sources(): return [asdict(x().status()) for x in [MockDataAdapter,TMSAdapter,GPSAdapter,ONPAdapter]]

@router.get('/alerts',tags=['Cảnh báo'])
def alerts(request:Request): return get_snapshot(request)['alerts']

@router.post('/alerts/{id}/ack',tags=['Cảnh báo'])
def acknowledge(id:str,request:Request):
    s=request.app.state.store
    with s.tx() as db:
        snapshot(s,db)
        row=db.execute('SELECT payload FROM alerts WHERE id=?',(id,)).fetchone()
        if not row: raise HTTPException(404,'Không tìm thấy cảnh báo')
        a=json.loads(row['payload']);a['acknowledged']=True;a['acknowledged_at']=utcnow().isoformat()
        db.execute('UPDATE alerts SET payload=? WHERE id=?',(json.dumps(a),id))
        return a

@router.post('/dispatch/analyze',tags=['Hỗ trợ quyết định'])
def analysis(payload:AnalysisInput,request:Request):
    s=request.app.state.store
    with s.tx() as db:
        c=s.tick(db);trip=trip_by_id(s,db,payload.trip_id)
        try: result=analyze(trip,s.rows(db),dt(c['now']),payload.weights.model_dump())
        except ValueError as e: raise HTTPException(422,str(e))
        result.update(id=uuid.uuid4().hex,trip_id=trip['id'],trip_code=trip['code'],trip_revision=trip['revision'],sim_at=c['now'],real_at=utcnow().isoformat(),fleet_state=[(t['id'],t['revision'],t['status'],t.get('vehicle_id')) for t in s.rows(db)],applied=False)
        db.execute('INSERT INTO analyses VALUES(?,?)',(result['id'],json.dumps(result)))
        return result

@router.post('/dispatch/confirm',tags=['Hỗ trợ quyết định'])
def confirm(payload:ConfirmInput,request:Request):
    if not payload.confirmed: raise HTTPException(422,'Nhân viên phải xác nhận trước khi áp dụng')
    s=request.app.state.store
    with s.tx() as db:
        c=s.tick(db);row=db.execute('SELECT payload FROM analyses WHERE id=?',(payload.analysis_id,)).fetchone()
        if not row: raise HTTPException(404,'Không tìm thấy phân tích')
        a=json.loads(row['payload'])
        if a['applied']: raise HTTPException(409,'Phương án đã được áp dụng; không gửi lại')
        t=trip_by_id(s,db,a['trip_id'])
        fleet=[[x['id'],x['revision'],x['status'],x.get('vehicle_id')] for x in s.rows(db)]
        if a['fleet_state']!=fleet or (dt(c['now'])-dt(a['sim_at'])).total_seconds()>300 or (utcnow()-dt(a['real_at'])).total_seconds()>300:
            raise HTTPException(409,'Dữ liệu/thời gian đã thay đổi. Hãy phân tích lại trước khi duyệt')
        o=next((x for x in a['options'] if x['id']==payload.option_id),None)
        if not o: raise HTTPException(422,'Phương án không thuộc phân tích này')
        # Recalculate against the current clock before committing the chosen vehicle.
        latest=analyze(t,s.rows(db),dt(c['now']),a['weights'])
        o=next((x for x in latest['options'] if x['id']==payload.option_id),None)
        if not o: raise HTTPException(409,'Xe không còn khả dụng; hãy phân tích lại')
        start_at=max(dt(c['now']),dt(t['start_at'])).isoformat()
        t.update(vehicle_id=o['id'],capacity=o['capacity'],status='dang_chay',start_at=start_at,remaining_minutes=o['minutes'],revision=t['revision']+1,updated_at=utcnow().isoformat())
        # Preserve cost estimate semantics; the waiting penalty is not booked cost.
        t['estimated_saving']=max(x['cost'] for x in a['options'])-o['cost']
        s.save_trip(db,t,t['id']);a['applied']=True
        db.execute('UPDATE analyses SET payload=? WHERE id=?',(json.dumps(a),a['id']))
        event={'trip_id':t['id'],'trip_code':t['code'],'vehicle_id':o['id'],'analysis_id':a['id'],'sim_at':c['now'],'real_at':utcnow().isoformat(),'estimated_cost':o['cost'],'confirmed_by':'Nhân viên demo','message':'Chỉ cập nhật SQLite demo; không gửi lệnh thật'}
        db.execute('INSERT INTO decisions(payload) VALUES(?)',(json.dumps(event),))
        return event

@router.get('/decisions',tags=['Hỗ trợ quyết định'])
def decisions(request:Request):
    s=request.app.state.store
    with s.tx() as db: return [json.loads(x['payload']) for x in db.execute('SELECT payload FROM decisions ORDER BY id DESC')]

@router.get('/reports',tags=['Báo cáo'])
def reports(request:Request): return get_snapshot(request)['report']

@router.get('/reports/export.csv',tags=['Báo cáo'])
def export(request:Request):
    snap=get_snapshot(request);out=io.StringIO();w=csv.writer(out)
    w.writerow(['Mã chuyến','Điểm lấy','Điểm giao','Trạng thái','ETA (+07:00)','Cut-off','Dự phòng (phút)','Rủi ro','Chi phí (VND)','Thời gian mô phỏng'])
    # Neutralize spreadsheet formula injection, including user text.
    def safe(v):
        st=str(v)
        return "'"+st if st.lstrip().startswith(('=','+','-','@','\t','\r')) else st
    for t in snap['trips']:
        w.writerow([safe(v) for v in [t['code'],t['origin'],t['destination'],t['status'],t['eta'],t['cutoff'],t['buffer_minutes'],t['risk'],t['cost'],snap['clock']['now']]])
    return Response(('\ufeff'+out.getvalue()).encode('utf-8'),media_type='text/csv; charset=utf-8',headers={'Content-Disposition':'attachment; filename="bao_cao_dieu_xe.csv"'})

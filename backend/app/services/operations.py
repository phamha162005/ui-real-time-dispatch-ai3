"""Explicit rules for notices, an illustrative ranking, and versioned orders.
No AI model, external TMS, driver messaging, or GPS calls are performed here.
"""
import json, re, unicodedata
from datetime import datetime
from fastapi import HTTPException
from .eta import dt

BASELINE_KEYS={'booking':'Booking','vessel':'Tên tàu','voyage':'Chuyến tàu','ship_eta':'ETA tàu','ship_etd':'ETD tàu','cutoff':'Cut-off','origin':'Điểm lấy','destination':'Điểm giao','cancelled':'Hủy booking','container_id':'Container','vehicle_id':'Phương tiện','incident':'Sự cố xe'}

def fold(s):
    return ''.join(c for c in unicodedata.normalize('NFD',s.lower().replace('đ','d')) if unicodedata.category(c)!='Mn').strip()

def parse_notice(text):
    aliases={'booking':'booking','ma booking':'booking','ten tau':'vessel','tau':'vessel','chuyen tau':'voyage','eta tau':'ship_eta','etd tau':'ship_etd','cut-off':'cutoff','cutoff':'cutoff','diem lay':'origin','diem giao':'destination','trang thai':'cancelled','container':'container_id','ma container':'container_id','phuong tien':'vehicle_id','bien so':'vehicle_id','ma xe':'vehicle_id','su co':'incident','su co xe':'incident'}
    values={};warnings=[]
    for line in text.splitlines():
        if ':' not in line:continue
        name,value=line.split(':',1);field=aliases.get(fold(name));value=value.strip()
        if not field or not value:continue
        if field in values:raise HTTPException(422,f'Trường {BASELINE_KEYS[field]} xuất hiện nhiều lần; cần xác minh lại')
        if field in ['cutoff','ship_eta','ship_etd']:
            try:
                parsed=datetime.fromisoformat(value.replace('Z','+00:00'))
                if parsed.utcoffset() is None:raise ValueError()
                value=parsed.isoformat()
            except ValueError:raise HTTPException(422,f'{BASELINE_KEYS[field]} cần ngày giờ ISO có múi giờ, ví dụ 2026-10-17T11:30:00+07:00')
        elif field=='cancelled':
            if fold(value) in ['huy','da huy','cancelled','canceled']:value=True
            elif fold(value) in ['hoat dong','con hieu luc','active']:value=False
            else:
                warnings.append('Trạng thái chưa nhận diện; chỉ hỗ trợ Hủy hoặc Hoạt động.');continue
        elif field=='incident' and fold(value) in ['da xu ly','da khac phuc','resolved']:value=''
        elif len(value)>120:raise HTTPException(422,f'{BASELINE_KEYS[field]} quá dài (tối đa 120 ký tự)')
        values[field]=value
    if not values:raise HTTPException(422,'Chưa đọc được trường nào. Dùng nhãn Booking, Cut-off, Điểm lấy, Điểm giao, Container, Phương tiện hoặc Sự cố.')
    return values,warnings

def baseline(s,db,t):
    return {**{'booking':'BK-'+t['code'],'vessel':'','voyage':'','ship_eta':'','ship_etd':'','cancelled':False,'container_id':'','incident':''},**(s.get(db,'notice-baseline:'+str(t['id'])) or {}),**{k:t[k] for k in ['cutoff','origin','destination','vehicle_id']}}

def changes(before,after):
    result=[]
    for field,value in after.items():
        old=before.get(field,'')
        equal=(dt(old)==dt(value)) if field in ['cutoff','ship_eta','ship_etd'] and old else old==value
        if not equal:result.append({'field':field,'label':BASELINE_KEYS[field],'before':old,'after':value})
    return result

def pilot_analysis(vehicles):
    tours=max(v['tours'] for v in vehicles);km=max(v['km'] for v in vehicles)
    options=[];rejected=[]
    labels={'trailer_ok':'Loại moóc không phù hợp','capacity_ok':'Không đủ tải trọng','ready':'Xe chưa sẵn sàng','hours_ok':'Không đủ thời gian làm việc','cutoff_ok':'Không đáp ứng cut-off'}
    for v in vehicles:
        why=[label for k,label in labels.items() if not v[k]]
        if why:rejected.append({'plate':v['plate'],'reasons':why});continue
        tn=v['tours']/tours if tours else 0;kn=v['km']/km if km else 0;p=0 if v['at_yard'] else 1
        score=(tn+kn+p)/3
        options.append({**v,'score':round(score,6),'display_score':round(score,3),'tour_component':round(tn,6),'km_component':round(kn,6),'position_component':p,'_sort':score})
    options.sort(key=lambda x:(x['_sort'],x['plate']))
    for x in options:del x['_sort']
    return {'options':options[:3],'ranking':options,'input_count':len(vehicles),'feasible_count':len(options),'returned_count':min(3,len(options)),'rejected':rejected,'recommended':options[0]['plate'] if options else None,'max_tours':tours,'max_km':km,'formula':'Sᵢ = (Tᵢ/Tmax + Kᵢ/Kmax + Pᵢ)/3; P = 0 ở Bãi Xe U&I, 1 ở nơi khác. Điểm thấp được ưu tiên.','note':'Xếp hạng theo dữ liệu đầu vào, đề xuất tối đa 03 phương án. Km lũy kế không phải km phát sinh/chạy rỗng. Các ràng buộc phải được kiểm tra trước khi xếp hạng. Không phải tối ưu tuyến hoặc mô hình AI được huấn luyện. Nếu Tmax/Kmax = 0, thành phần tương ứng bằng 0 cho mọi xe.'}

def order_rows(db):
    return [dict(json.loads(x['payload']),id=x['id']) for x in db.execute('SELECT * FROM orders ORDER BY id DESC')]

def save_order(db,o):
    db.execute('UPDATE orders SET payload=? WHERE id=?',(json.dumps({k:v for k,v in o.items() if k!='id'},ensure_ascii=False),o['id']))

def view_order(o,c,trips):
    t=next((t for t in trips if t['id']==o['trip_id']),None)
    elapsed=max(0,c.get('elapsed_minutes',0)-o['sent_elapsed'])
    stale=t is None or (t['revision']!=o['source_revision'] and o['status'] in ['sent','received','confirmed'])
    waiting=o['status'] in ['sent','received'] and o['active']
    return {**o,'elapsed_minutes':round(elapsed,2),'stale':stale,'overdue':waiting and elapsed>=5,'response_minutes':None if o.get('confirmed_elapsed') is None else round(o['confirmed_elapsed']-o['sent_elapsed'],2)}

def workflow_state(s,db,c):
    orders=[view_order(o,c,s.rows(db)) for o in order_rows(db)]
    sent=len(orders);confirmed=[o for o in orders if o.get('confirmed_elapsed') is not None]
    within=sum(o['response_minutes']<=5 for o in confirmed)
    return {'orders':orders,'notices':[json.loads(x['payload']) for x in db.execute('SELECT payload FROM notices ORDER BY rowid DESC LIMIT 30')], 'metrics':{'issued':sent,'confirmed':len(confirmed),'within_five_minutes':within,'within_five_rate':round(within/sent*100,1) if sent else None,'waiting':sum(o['active'] and o['status'] in ['sent','received'] for o in orders),'overdue':sum(o['overdue'] for o in orders)}}

def order_alerts(s,db,c):
    wanted={}
    for o in order_rows(db):
        if not o['active']:continue
        v=view_order(o,c,s.rows(db));why=[]
        if v['overdue']:why.append('Quá 05 phút chưa xác nhận')
        if v['stale']:why.append('Dữ liệu chuyến đã đổi; cần phát hành phiên bản mới')
        if o['status']=='rejected':why.append('Lái xe từ chối: '+o.get('reason',''))
        if why:
            key='order:'+str(o['id'])+':'+('stale' if v['stale'] else 'rejected' if o['status']=='rejected' else 'timeout')
            wanted[key]={'kind':'order','trip_id':o['trip_id'],'level':'cao','title':f"{o['trip_code']} · Lệnh v{o['version']} · "+'; '.join(why)}
    return wanted

from datetime import timedelta
from ..adapters.mock import VEHICLES
from .eta import dt

def analyze(trip, trips, now, weights):
    if trip['status']=='hoan_thanh': raise ValueError('Chuyến đã hoàn thành, không thể điều phối lại')
    busy={t['vehicle_id'] for t in trips if t['status']!='hoan_thanh' and t['vehicle_id'] and t['id']!=trip['id']}
    options=[];rejected=[]
    for v in VEHICLES:
        current=v['id']==trip.get('vehicle_id')
        why=[]
        if v['type']!=trip['vehicle_type']: why.append('Không phù hợp loại xe')
        if v['capacity']<trip['load']: why.append('Không đủ tải trọng')
        if v['id'] in busy or (not v['available'] and not current): why.append('Xe đang được phân công')
        if why:
            rejected.append({'vehicle_id':v['id'],'reasons':why});continue
        # Existing moving vehicle keeps its actual remaining work. A waiting
        # order uses the whole editable estimate with replacement assumptions.
        minutes=trip['remaining_minutes'] if current else v['ready_minutes']+v['approach_minutes']+trip['travel_minutes']*v['travel_factor']+trip['handling_minutes']+trip['delay_minutes']
        eta=max(now,dt(trip['start_at']))+timedelta(minutes=minutes)
        if trip.get('eta_manual'): eta=max(eta,dt(trip['eta_manual']))
        slack=(dt(trip['cutoff'])-eta).total_seconds()/60
        late=max(0,-slack)
        cost=trip['cost']+(0 if current else v['fixed_cost'])+late/60*trip['wait_cost_per_hour']
        options.append(dict(id=v['id'],vehicle=v['name'],capacity=v['capacity'],minutes=round(minutes,2),eta=eta.isoformat(),buffer_minutes=round(slack,2),cost=round(cost),risk='cao' if slack<0 else ('trung_binh' if slack<30 else 'thap'),utilization=round(trip['load']/v['capacity']*100,2),current=current))
    if not options: raise ValueError('Không có xe đáp ứng loại xe, tải trọng và trạng thái khả dụng')
    total=sum(weights.values());wn={k:v/total for k,v in weights.items()}
    def norm(value,values):
        lo,hi=min(values),max(values)
        return 1 if hi==lo else (hi-value)/(hi-lo)
    for o in options:
        components={'time':norm(o['minutes'],[v['minutes'] for v in options]),'cost':norm(o['cost'],[v['cost'] for v in options]),'risk':0 if o['buffer_minutes']<0 else min(1,o['buffer_minutes']/30),'utilization':o['utilization']/100}
        o['components']={k:round(v*100,2) for k,v in components.items()}
        o['score']=round(sum(wn[k]*v for k,v in components.items())*100,2)
        o['explanation']=f"Dự kiến {o['minutes']:.0f} phút, dự phòng {o['buffer_minutes']:.0f} phút; chi phí ước tính {o['cost']:,.0f} đ; sử dụng tải {o['utilization']:.0f}%."
    options.sort(key=lambda o:(-o['score'],o['cost'],o['id']))
    return {'options':options,'rejected':rejected,'weights':wn,'recommended_id':options[0]['id'],'formula':'Điểm = 100 × Σ(trọng số chuẩn hóa × điểm thành phần). Thời gian/chi phí: min–max đảo chiều; rủi ro: max(0,min(1,dự phòng/30)); sử dụng: tải hàng/tải trọng. Chi phí = chi phí chuyến + huy động xe + phút trễ/60 × phí chờ.','warning':'Bộ máy mô phỏng theo quy tắc và công thức; chưa có mô hình AI được huấn luyện. Điểm cao không bảo đảm đúng hạn. Nhân viên điều vận cần xác minh trước khi duyệt.'}

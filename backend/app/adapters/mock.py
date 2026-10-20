from datetime import timedelta
from .base import DataAdapter, SourceStatus

VEHICLES = [
 {"id":"XE-01","name":"Đầu kéo 01","type":"container","capacity":30,"available":True,"ready_minutes":0,"approach_minutes":0,"travel_factor":1,"fixed_cost":0},
 {"id":"XE-02","name":"Đầu kéo 02","type":"container","capacity":28,"available":True,"ready_minutes":10,"approach_minutes":15,"travel_factor":0.82,"fixed_cost":550000},
 {"id":"XE-03","name":"Đầu kéo 03","type":"container","capacity":32,"available":True,"ready_minutes":5,"approach_minutes":5,"travel_factor":1.08,"fixed_cost":120000},
 {"id":"XE-04","name":"Xe tải 04","type":"tai","capacity":10,"available":True,"ready_minutes":5,"approach_minutes":10,"travel_factor":1,"fixed_cost":200000}
]

class MockDataAdapter(DataAdapter):
    def status(self): return SourceStatus("Mock",True,"demo","Dữ liệu giả lập lưu tại SQLite; không kết nối doanh nghiệp")
    def fetch_trips(self, base=None):
        if base is None:
            from datetime import datetime, timezone
            base=datetime.now(timezone(timedelta(hours=7))).replace(hour=8,minute=0,second=0,microsecond=0)
        rows=[
          ("UI-1001","XE-01","dang_chay",110,30,185,0,"KCN Sóng Thần","Cảng Cát Lái","Đang di chuyển; theo dõi cut-off"),
          ("UI-1002",None,"cho_lenh",95,35,105,20,"Kho Bình Dương","Cảng Cát Lái","Tàu chậm: cân nhắc giữ xe và đổi giờ hạ"),
          ("UI-1003",None,"tam_dung",70,20,120,15,"Depot Linh Trung","KCN VSIP","Booking thay đổi: chờ nhân viên xác minh"),
          ("UI-1004",None,"cho_lenh",85,30,240,45,"Depot Bình Dương","Kho Đồng Nai","Depot thiếu container: cần xác minh nguồn cung"),
          ("UI-1005",None,"hoan_thanh",60,20,90,0,"Kho Đồng Nai","Cảng Cát Lái","Chuyến mẫu đã hoàn thành đúng hạn")
        ]
        return [dict(code=c,vehicle_id=v,vehicle_type="container",capacity=30,load=22,origin=o,destination=d,start_at=base.isoformat(),cutoff=(base+timedelta(minutes=cut)).isoformat(),travel_minutes=t,handling_minutes=h,delay_minutes=delay,distance_km=55+i*12,cost=1800000+i*280000,wait_cost_per_hour=150000,status=s,data_issue=("missing" if i==2 else "source_error" if i==3 else "none"),eta_manual=None,note=n) for i,(c,v,s,t,h,cut,delay,o,d,n) in enumerate(rows)]

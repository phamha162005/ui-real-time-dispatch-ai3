import csv,io,json
from datetime import datetime,timedelta,timezone
from fastapi import HTTPException
from pydantic import ValidationError
from ..schemas.enterprise import GPSRow,ONPRow,TMSRow

MODELS={'GPS':GPSRow,'TMS':TMSRow,'ONP':ONPRow}
REQUIRED_TMS={'code','vehicle_type','capacity','load','origin','destination','start_at','cutoff','travel_minutes','handling_minutes','delay_minutes','distance_km','cost','wait_cost_per_hour','status','data_issue','source_updated_at'}

def fields(source):return list(MODELS[source].model_fields)

def path_value(value,path):
    if not path:return value
    if isinstance(value,dict) and path in value:return value[path]
    for k in path.split('.'):
        if not isinstance(value,dict) or k not in value:raise KeyError(path)
        value=value[k]
    return value

def parse_file(format,text,rows_path):
    try:
        if format=='json':return extract_rows(json.loads(text.lstrip('\ufeff')),rows_path)
        text=text.lstrip('\ufeff');head=text.splitlines()[0]
        reader=csv.DictReader(io.StringIO(text),delimiter=';' if head.count(';')>head.count(',') else ',',strict=True)
        names=[(x or '').strip() for x in reader.fieldnames or []]
        if not names or len(names)!=len(set(names)):raise ValueError('Cột CSV bị trống hoặc trùng')
        reader.fieldnames=names;rows=[]
        for row in reader:
            if None in row:raise ValueError('Số cột CSV không khớp')
            if any(str(x or '').strip() for x in row.values()):rows.append(row)
            if len(rows)>1000:raise ValueError('Tối đa 1.000 dòng mỗi lần nhập nguồn')
        return extract_rows(rows,'')
    except (ValueError,csv.Error,IndexError,KeyError):raise HTTPException(422,'Không đọc được tệp. Kiểm tra cấu trúc CSV/JSON, vị trí danh sách và giới hạn 1.000 dòng.') from None

def extract_rows(value,path):
    try:rows=path_value(value,path)
    except KeyError:raise HTTPException(422,'Không tìm thấy danh sách tại đường dẫn JSON đã cấu hình')
    if not isinstance(rows,list) or not rows or len(rows)>1000 or any(not isinstance(r,dict) for r in rows):raise HTTPException(422,'Nguồn phải là danh sách từ 1 đến 1.000 bản ghi dạng đối tượng')
    return rows

def normalize(source,rows,mapping):
    model=MODELS[source];valid=[];errors=[]
    for i,row in enumerate(rows):
        data={};missing=[]
        for field in fields(source):
            key=mapping.get(field,field)
            try:data[field]=path_value(row,key)
            except KeyError:
                if (source=='TMS' and field in REQUIRED_TMS) or model.model_fields[field].is_required():missing.append(field)
        for key,value in list(data.items()):
            if isinstance(value,str):
                value=value.strip()
                if value=='' and key in ['vehicle_id','eta_manual']:value=None
                data[key]=value
        if missing:errors.append({'row':i+1,'message':'Thiếu trường: '+', '.join(missing)});continue
        try:
            v=model.model_validate(data).model_dump(mode='json');valid.append(v)
        except ValidationError as e:
            errors.append({'row':i+1,'message':'; '.join('.'.join(map(str,x['loc']))+': '+x['msg'] for x in e.errors())})
    identities=set()
    for i,r in enumerate(valid):
        # GPS accepts many timestamps for one vehicle, but not duplicate samples.
        ident=(r['vehicle_id'],r['source_updated_at']) if source=='GPS' else r['code'] if source=='TMS' else (r['external_id'],r['source_updated_at'])
        if ident in identities:errors.append({'row':None,'message':'Nguồn có bản ghi trùng khóa; cần đối soát trước khi cập nhật'});break
        identities.add(ident)
    return valid,errors

def sample_rows(source):
    now=datetime.now(timezone(timedelta(hours=7))).replace(microsecond=0)
    if source=='GPS':return [{'vehicle_id':'SAMPLE-GPS-01','latitude':10.901,'longitude':106.745,'speed_kmh':0,'source_updated_at':now.isoformat()}]
    if source=='ONP':return [{'external_id':'SAMPLE-ONP-01','trip_code':'SAMPLE-01','container_id':'SAMPLE-CONTAINER','status':'CAN_XAC_MINH','source_updated_at':now.isoformat()}]
    return [{'code':'SAMPLE-TMS-01','vehicle_id':None,'vehicle_type':'container','capacity':30,'load':20,'origin':'Điểm lấy mẫu','destination':'Điểm giao mẫu','start_at':now.isoformat(),'cutoff':(now+timedelta(hours=5)).isoformat(),'travel_minutes':90,'handling_minutes':30,'delay_minutes':0,'distance_km':50,'cost':0,'wait_cost_per_hour':0,'status':'cho_lenh','data_issue':'none','eta_manual':None,'note':'Dữ liệu mẫu để kiểm tra định dạng, không phải lệnh doanh nghiệp','source_updated_at':now.isoformat()}]

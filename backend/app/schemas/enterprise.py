from datetime import datetime
from typing import Literal
from pydantic import Field, field_validator
from .operations import Input, Approval
from .models import TripInput

Source=Literal['TMS','GPS','ONP']

class AwareTime(Input):
    source_updated_at:datetime
    @field_validator('source_updated_at')
    @classmethod
    def aware(cls,v):
        if v.utcoffset() is None:raise ValueError('Thời gian nguồn cần múi giờ +07:00 hoặc Z')
        return v

class GPSRow(AwareTime):
    vehicle_id:str=Field(min_length=2,max_length=80)
    latitude:float=Field(ge=-90,le=90)
    longitude:float=Field(ge=-180,le=180)
    speed_kmh:float=Field(ge=0,le=250)

class ONPRow(AwareTime):
    external_id:str=Field(min_length=1,max_length=120)
    trip_code:str=Field(min_length=2,max_length=40)
    container_id:str=Field(default='',max_length=40)
    status:str=Field(min_length=1,max_length=120)

class TMSRow(TripInput):
    source_updated_at:datetime
    @field_validator('source_updated_at')
    @classmethod
    def aware_source(cls,v):
        if v.utcoffset() is None:raise ValueError('Thời gian nguồn cần múi giờ')
        return v

class SourceConfig(Input):
    mapping:dict[str,str]=Field(default_factory=dict,max_length=40)
    rows_path:str=Field(default='',max_length=150)
    @field_validator('mapping')
    @classmethod
    def mapping_size(cls,v):
        if any(not k or not s.strip() or len(k)>80 or len(s)>150 for k,s in v.items()):raise ValueError('Tên trường ánh xạ không hợp lệ')
        return {k:s.strip() for k,s in v.items()}

class FilePreview(Input):
    format:Literal['csv','json']
    text:str=Field(min_length=1,max_length=2000000)

class BatchApproval(Approval):
    batch_id:str=Field(min_length=10,max_length=60)

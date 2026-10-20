from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator

class Input(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True,allow_inf_nan=False)

class NoticeInput(Input):
    source_text:str=Field(default='',max_length=12000)
    source_name:str=Field(default='',max_length=500)
    read_method:str=Field(default='manual',max_length=120)
    trip_id:int
    kind:Literal['booking','schedule','pickup','delivery','container','vehicle','incident']
    text:str=Field(min_length=5,max_length=12000)

class Approval(Input):
    confirmed:bool=False

class OrderInput(Approval):
    comparison_id:str|None=Field(default=None,max_length=40)
    trip_id:int
    trip_revision:int
    expected_version:int=Field(ge=0)
    driver:str=Field(min_length=2,max_length=80)
    action:Literal['continue','hold','adjust']
    instructions:str=Field(min_length=5,max_length=1000)

class DriverEvent(Approval):
    driver:str=Field(min_length=2,max_length=80)
    action:Literal['receive','confirm','reject','execute']
    reason:str=Field(default='',max_length=500)

class PilotVehicle(Input):
    plate:str=Field(min_length=2,max_length=30)
    tours:float=Field(ge=0,le=10000)
    km:float=Field(ge=0,le=100000)
    at_yard:bool=False
    trailer_ok:bool=True
    capacity_ok:bool=True
    ready:bool=True
    hours_ok:bool=True
    cutoff_ok:bool=True

class PilotInput(Input):
    vehicles:list[PilotVehicle]=Field(min_length=1,max_length=10000)
    @field_validator('vehicles')
    @classmethod
    def unique(cls,values):
        if len({v.plate.casefold() for v in values})!=len(values):raise ValueError('Biển số xe phải khác nhau')
        return values

class FleetCSV(Input):
    text:str=Field(min_length=1,max_length=5000000)

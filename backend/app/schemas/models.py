from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator

class TripInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, allow_inf_nan=False)
    code: str = Field(min_length=2, max_length=40, pattern=r"^[A-Za-z0-9_-]+$")
    vehicle_id: str | None = None
    vehicle_type: Literal["container", "tai"] = "container"
    capacity: float = Field(default=30, gt=0, le=100)
    load: float = Field(default=20, gt=0, le=100)
    origin: str = Field(min_length=2, max_length=120)
    destination: str = Field(min_length=2, max_length=120)
    start_at: datetime
    cutoff: datetime
    travel_minutes: float = Field(gt=0, le=10080)
    handling_minutes: float = Field(default=30, ge=0, le=1440)
    delay_minutes: float = Field(default=0, ge=0, le=2880)
    distance_km: float = Field(default=50, gt=0, le=5000)
    cost: float = Field(default=2000000, ge=0, le=1000000000)
    wait_cost_per_hour: float = Field(default=150000, ge=0, le=10000000)
    status: Literal["cho_lenh", "dang_chay", "tam_dung", "hoan_thanh"] = "cho_lenh"
    data_issue: Literal["none", "missing", "source_error"] = "none"
    eta_manual: datetime | None = None
    note: str = Field(default="", max_length=500)

    @field_validator("start_at", "cutoff", "eta_manual")
    @classmethod
    def aware(cls, v):
        if v is not None and v.utcoffset() is None:
            raise ValueError("Thời gian phải có múi giờ, ví dụ +07:00")
        return v

    @model_validator(mode="after")
    def coherent(self):
        if self.load > self.capacity:
            raise ValueError("Tải hàng vượt tải trọng xe")
        if self.cutoff <= self.start_at:
            raise ValueError("Cut-off phải sau thời gian khởi hành")
        return self

class ClockCommand(BaseModel):
    action: Literal["start", "pause", "resume", "reset", "advance", "speed"]
    speed: Literal[1,10,60] | None = None
    minutes: float = Field(default=30, ge=0, le=1440, allow_inf_nan=False)

class Weights(BaseModel):
    time: float = Field(default=45, ge=0, le=100, allow_inf_nan=False)
    cost: float = Field(default=30, ge=0, le=100, allow_inf_nan=False)
    risk: float = Field(default=20, ge=0, le=100, allow_inf_nan=False)
    utilization: float = Field(default=5, ge=0, le=100, allow_inf_nan=False)
    @model_validator(mode="after")
    def positive(self):
        if sum(self.model_dump().values()) == 0: raise ValueError("Tổng trọng số phải lớn hơn 0")
        return self

class AnalysisInput(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    trip_id: int
    weights: Weights = Field(default_factory=Weights)

class ConfirmInput(BaseModel):
    analysis_id: str
    option_id: str
    confirmed: bool = False

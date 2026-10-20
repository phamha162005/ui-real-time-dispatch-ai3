from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

@dataclass
class SourceStatus:
    name: str
    connected: bool
    mode: str
    message: str

class DataAdapter(ABC):
    """fetch_trips returns validated TripInput-compatible records, ISO 8601 with offset.
    Never send raw vendor payloads directly to ETA/dispatch services.
    """
    @abstractmethod
    def status(self) -> SourceStatus: ...
    @abstractmethod
    def fetch_trips(self) -> list[dict[str, Any]]: ...

from .base import DataAdapter, SourceStatus
from .enterprise import ReadOnlyJSONAdapter

class IntegrationNotConfigured(RuntimeError):pass

class IntegrationAdapter(DataAdapter):
    name='External'
    def __init__(self):
        self.reader=ReadOnlyJSONAdapter(self.name)
        self.timeout_seconds=self.reader.timeout
    def status(self):
        ready=self.reader.checks()['ready']
        return SourceStatus(self.name,False,'configured' if ready else 'not_connected',
            'Cấu hình đọc API đã đủ; kiểm tra và xem trước tại Kết nối doanh nghiệp.' if ready else 'Chưa bật đọc API; cấu hình tại backend và ánh xạ tại Kết nối doanh nghiệp. Có thể nhập CSV/JSON trước.')
    def fetch_trips(self):
        raise IntegrationNotConfigured(f'{self.name}: dùng connector chỉ đọc, ánh xạ và xem trước trước khi cập nhật; GPS/ONP không mặc định là danh sách chuyến')

class TMSAdapter(IntegrationAdapter):name='TMS'
class GPSAdapter(IntegrationAdapter):name='GPS'
class ONPAdapter(IntegrationAdapter):name='ONP'

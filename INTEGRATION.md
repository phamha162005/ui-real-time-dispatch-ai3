# Kết nối dữ liệu doanh nghiệp v1.4

Phiên bản này có connector **chỉ đọc JSON qua HTTPS** và luồng nhập **CSV/JSON → ánh xạ → kiểm tra → xem trước → xác nhận** cho TMS, GPS, ONP. API mặc định tắt. Chưa kết nối doanh nghiệp nào khi bàn giao.

## Phạm vi đã có

| Nguồn | Dữ liệu chuẩn hóa | Sau khi xác nhận |
| --- | --- | --- |
| TMS | Mã chuyến, xe nguồn, loại xe, tải trọng/tải hàng, điểm lấy/giao, thời gian, cut-off, công việc còn lại, chi phí, trạng thái, thời điểm nguồn | Lưu ảnh chụp lệnh riêng; hiển thị ETA ước tính tại mốc nguồn cho chuyến chưa hoàn thành |
| GPS | Mã xe, vĩ độ, kinh độ, tốc độ, thời điểm nguồn | Giữ bản ghi mới nhất theo xe; mở vị trí trên bản đồ và hiển thị tuổi dữ liệu theo đồng hồ thật |
| ONP | Mã bản ghi, mã chuyến liên quan, container, trạng thái nguồn, thời điểm nguồn | Lưu trạng thái nguyên nghĩa, không suy diễn ONP là hệ thống nào hoặc tự đổi lệnh |

Kho doanh nghiệp tách khỏi chuyến/đội xe mẫu và danh sách xét tái phân bổ. Nhập nguồn không tự phân công xe hoặc phát hành lệnh. Chưa triển khai đồng bộ ngược, gọi API ghi, gửi SMS/Zalo/push, tối ưu bằng GPS trực tiếp hay tự động cập nhật ETA toàn đội xe. Để đưa nguồn đã xác minh vào vận hành thật cần chốt ánh xạ ID chuyến/xe/lái xe, đơn vị, trạng thái, quy tắc xung đột và kiểm thử theo tài liệu doanh nghiệp.

## Cách thử bằng tệp

1. Mở **Kết nối doanh nghiệp**, chọn TMS/GPS/ONP.
2. Tải CSV mẫu đúng nguồn. Các dòng mẫu chỉ để thử định dạng, không phải dữ liệu thật.
3. Với Excel, xuất **CSV UTF-8**. PDF/ảnh không được đọc trực tiếp ở luồng này; cần trích xuất và xác minh riêng.
4. Trong **Ánh xạ dữ liệu nguồn**, nhập tên cột thực tế tương ứng từng trường nội bộ rồi bấm Lưu ánh xạ. Nếu tên giống mẫu thì giữ nguyên.
5. Chọn tệp, bấm **Đọc tệp & xem trước**. Kiểm tra các giá trị đã chuẩn hóa và lỗi theo dòng.
6. Xác nhận cập nhật khu vực doanh nghiệp nếu đúng. Đợt có bất kỳ lỗi nào đều bị chặn toàn bộ; không tự bỏ dòng lỗi.
7. Xem dữ liệu đã lưu. Với GPS, bấm **Xem vị trí**. Tuổi dữ liệu lấy theo đồng hồ thật và thời điểm nguồn, không theo đồng hồ mô phỏng.

Giới hạn mỗi lần đọc: 2 MB và 1–1.000 dòng. Giao diện hiển thị tối đa 1.000 khóa đầu; tổng kho mỗi nguồn tối đa 10.000 khóa trong bản local. Không cung cấp chức năng lưu trữ toàn bộ lịch sử GPS.

## Cấu hình API sau khi được cấp quyền

Cần có tài liệu API, endpoint thử nghiệm/chính thức được duyệt, cơ chế xác thực, quyền đọc, cấu trúc phản hồi, đơn vị, múi giờ và giới hạn tần suất. Không đưa khóa vào JavaScript, CSV hoặc ảnh chụp màn hình. IT cấu hình trên máy backend:

1. Dừng server. Sao chép `.env.example` thành `.env` nếu chưa có.
2. Điền các biến tương ứng, ví dụ GPS:

```dotenv
GPS_READ_ENABLED=true
GPS_API_URL=https://gps.vendor.example/api/positions
GPS_ALLOWED_HOSTS=gps.vendor.example
GPS_AUTH_MODE=bearer
GPS_API_TOKEN=<điền khóa được doanh nghiệp cấp tại máy backend>
EXTERNAL_API_TIMEOUT_SECONDS=8
```

URL ở trên chỉ minh họa, không phải API có thể truy cập. `API_URL` phải là endpoint HTTPS hoàn chỉnh cho một yêu cầu GET, không chứa user/password trong URL. Hostname phải trùng một tên trong danh sách cho phép phân cách bằng dấu phẩy. Giao diện không chấp nhận URL tùy ý hoặc khóa truy cập.

Các chế độ xác thực có sẵn:

- `bearer`: header `Authorization: Bearer …`.
- `api_key`: header `X-API-Key: …`.
- `none`: chỉ dùng khi doanh nghiệp xác nhận endpoint không cần xác thực và quyền truy cập được kiểm soát theo cách khác.

TMS và ONP dùng các biến cùng tên với tiền tố tương ứng. Adapter hiện chưa hỗ trợ OAuth tự gia hạn, chữ ký HMAC, cookie phiên, mTLS hoặc header API key khác. Nếu nhà cung cấp yêu cầu các cơ chế này, IT mở rộng `backend/app/adapters/enterprise.py` theo tài liệu đã được cấp, không giả định chỉ thêm token là đủ.

3. Khởi động lại `START_WINDOWS.bat` để nhận cấu hình.
4. Trên web, chọn nguồn và kiểm tra bốn ô cấu hình. Đủ cấu hình **không** đồng nghĩa đã kiểm tra kết nối thành công.
5. Nếu API trả một list, để trống **Vị trí danh sách trong JSON**. Nếu trả `{"data":{"items":[...]}}`, nhập `data.items` rồi lưu.
6. Ánh xạ tên trường hoặc đường dẫn lồng nhau; ví dụ trường nội bộ `vehicle_id` lấy từ `vehicle.plate`. Trường có dấu chấm trong tên được thử đối chiếu nguyên tên trước, rồi mới duyệt đường dẫn.
7. Bấm **Đọc API đã được cấp quyền**, xác nhận quyền đọc và xem trước dữ liệu. Sau khi kiểm tra, xác nhận cập nhật kho doanh nghiệp riêng.

## Quy tắc chuẩn hóa

- Giờ phải là ISO 8601 có múi giờ, ví dụ `2026-10-17T10:30:00+07:00` hoặc giờ UTC với `Z`.
- Tải trọng/tải hàng dùng tấn; thời lượng dùng phút; khoảng cách dùng km; tiền dùng VND; tốc độ GPS dùng km/h. Số thập phân của luồng nhập nguồn dùng dấu chấm. Chưa tự chuyển kg → tấn hoặc giây → phút.
- Trạng thái TMS dùng `cho_lenh`, `dang_chay`, `tam_dung`, `hoan_thanh`; loại xe `container` hoặc `tai`; chất lượng dữ liệu `none`, `missing`, `source_error`. Nếu mã doanh nghiệp khác, cần bổ sung bộ chuyển đổi theo tài liệu hoặc chuẩn hóa tệp trước khi nhập.
- TMS bắt buộc có các trường vận hành và chi phí đã xác minh, không tự điền chi phí mặc định khi nguồn thiếu. `vehicle_id`, `eta_manual`, `note` là các trường tùy chọn. `source_updated_at` luôn bắt buộc.
- GPS cần `vehicle_id`, `latitude`, `longitude`, `speed_kmh`, `source_updated_at`. Kiểm tra tọa độ hợp lệ và tốc độ 0–250 km/h. Bản ghi trùng mã xe + dấu thời gian trong cùng đợt bị báo lỗi. Vị trí có giờ nguồn nằm trong tương lai được hiển thị để kiểm tra lại đồng hồ nguồn.
- ONP cần `external_id`, `trip_code`, `status`, `source_updated_at`; `container_id` tùy chọn. Không suy diễn ý nghĩa trạng thái khi chưa có từ điển nghiệp vụ.
- Khi cập nhật: khóa TMS = mã chuyến; GPS = mã xe; ONP = mã bản ghi. Bản ghi có giờ nguồn cũ hơn hoặc bằng dữ liệu đã lưu bị bỏ qua, có trả số lượng để đối chiếu. Cùng một đợt không thể xác nhận hai lần.
- Nếu ánh xạ hoặc kho dữ liệu đổi sau lúc xem trước, phải đọc lại trước khi xác nhận. Các đợt chờ xem trước được giữ tối đa 20 đợt gần nhất trong SQLite.

## Vận hành connector chỉ đọc

Chỉ thực hiện GET khi người dùng chủ động đọc. Mặc định không tự gọi API lúc mở trang, không lập lịch và không retry. Timeout được giới hạn 1–10 giây; có giới hạn 2 MB phản hồi giải nén. Không đi theo chuyển hướng HTTP; TLS được xác minh mặc định. Trả lỗi tách biệt cho timeout, 401/403, 429, lỗi HTTP, cấu trúc JSON và lỗi chuẩn hóa. Nội dung lỗi từ nguồn, URL có query và token không được chuyển vào thông báo cho người dùng.

`trust_env=False` trong HTTP client: không tự dùng proxy từ biến môi trường. Nếu doanh nghiệp cần VPN, proxy, CA nội bộ hoặc mTLS, IT phải cấu hình và kiểm thử riêng. Không tắt xác minh TLS để vượt lỗi chứng chỉ. Endpoint nội bộ có thể được cấu hình ở backend khi được cấp quyền; không nhận hostname từ trình duyệt.

Connector đọc đúng một phản hồi. Nếu API phân trang hoặc có khoảng thời gian, cần cấu hình endpoint chỉ trả phạm vi phù hợp và bổ sung logic phân trang/cursor theo tài liệu trước khi gọi là đồng bộ đầy đủ. Lần đọc thất bại không xóa kho đã lưu. Lưu riêng dấu thời gian kiểm tra, nguồn ghi nhận và nhập vào ứng dụng; không gắn nhãn đang theo dõi trực tiếp chỉ vì đọc tệp thành công.

## Các API nội bộ

- `GET /api/enterprise/status`: mức sẵn sàng cấu hình, ánh xạ và lần thử gần nhất; không trả URL hoặc khóa.
- `PUT /api/enterprise/{TMS|GPS|ONP}/config`: lưu ánh xạ và đường dẫn danh sách JSON.
- `POST /api/enterprise/{source}/preview-file`: đọc nội dung CSV/JSON để xem trước.
- `POST /api/enterprise/{source}/preview-api`: yêu cầu đọc endpoint đã cấu hình, có xác nhận.
- `POST /api/enterprise/{source}/commit`: xác nhận cập nhật batch đã kiểm tra.
- `GET /api/enterprise/{source}/data`: ảnh chụp dữ liệu nguồn đã được xác nhận.
- `GET /api/enterprise/{source}/template.csv`: tệp mẫu của nguồn.

Mã triển khai: `adapters/enterprise.py` phụ trách đọc mạng; `services/enterprise.py` phụ trách đọc tệp/ánh xạ; `schemas/enterprise.py` kiểm tra dữ liệu; `api/enterprise.py` quản lý batch, phiên bản và ghi SQLite. Các lớp TMSAdapter/GPSAdapter/ONPAdapter cũ tiếp tục báo chưa kết nối cho hợp đồng `fetch_trips`; GPS và ONP không bị giả định là danh sách chuyến. Luồng thật đi qua adapter JSON chỉ đọc và bước chuẩn hóa riêng.

Bản bàn giao vẫn là ứng dụng local không có xác thực người dùng. Trước khi dùng khóa/dữ liệu doanh nghiệp trong môi trường nhiều người hoặc công khai, cần bổ sung đăng nhập, phân quyền thao tác nguồn, quản lý bí mật và nhật ký vận hành phù hợp. Chưa có bất kỳ endpoint gửi lệnh ra doanh nghiệp nào.

# U&I Real-Time Dispatch AI
## Điều phối vận tải thông minh theo thời gian thực

Bản v1.4 bổ sung đối chiếu lịch tàu/booking, tái phân bổ theo danh sách xe đầu vào (bộ 03 xe của mục 3.3.3 là dữ liệu mẫu) và luồng phiên bản lệnh – lái xe nhận/xác nhận theo mục 3.3.4. Các trang điều vận, ETA/cut-off, bản đồ và phân tích theo trọng số vẫn hoạt động như trước.

Website phục vụ trình diễn đề tài AI hỗ trợ ra quyết định điều xe tại U&I Logistics. Backend Python + FastAPI, giao diện HTML/CSS/JavaScript, SQLite. Đội xe vận hành mặc định và các thông báo mẫu là dữ liệu giả lập. Trang “Tái phân bổ xe” nhận danh sách người dùng nhập; bộ mẫu báo cáo dùng các số liệu được trình bày trong hai file báo cáo người dùng cung cấp; đây là bài toán minh họa có giả định, không phải GPS trực tiếp hoặc đánh giá hiệu quả thực tế.

**Đây là bộ máy hỗ trợ quyết định theo quy tắc và công thức; chưa có mô hình AI được huấn luyện. Nguồn doanh nghiệp mặc định chưa bật. Connector chỉ đọc được cấu hình sau khi được cấp quyền; không gửi lệnh điều xe ra doanh nghiệp.**

## 1. Chạy trên Windows, dành cho người mới

### Chuẩn bị

- Máy Windows 10/11, Python 3.11 trở lên (khuyến nghị Python 3.12).
- Cài Python từ https://www.python.org/downloads/windows/ và đánh dấu **Add python.exe to PATH** trong trình cài đặt.
- Dùng Chrome hoặc Edge. Không cần Node.js, tài khoản API, API key hay phần mềm cơ sở dữ liệu.
- Cần Internet lúc cài thư viện Python lần đầu. Sau khi cài thành công, giao diện, biểu đồ, trang `/docs` và dữ liệu mẫu chạy cục bộ. Bản đồ đường phố cần Internet để tải nền OpenStreetMap; mở chỉ đường Google Maps cũng cần Internet. Thư viện Leaflet được đóng gói sẵn, không tải từ CDN.

### Cách nhanh bằng file BAT

1. Nhấp phải file ZIP → **Extract All / Giải nén tất cả**. Không chạy trực tiếp trong cửa sổ ZIP.
2. Mở thư mục `ui-dispatch-ai` sau khi giải nén. Thư mục này phải có `requirements.txt`, `README.md`, `backend` và `frontend`.
3. Nhấp đúp `SETUP_WINDOWS.bat`. Chờ tạo `.venv` và cài thư viện. Nếu lỗi, đọc dòng thông báo trong cửa sổ, chưa đóng cửa sổ đó.
4. Khi cài xong, nhấp đúp `START_WINDOWS.bat`. Giữ cửa sổ này mở khi trình diễn.
5. Mở trình duyệt tại **http://127.0.0.1:8000**.
6. Trang tài liệu và thử API: **http://127.0.0.1:8000/docs**.
7. Dừng server bằng **Ctrl+C** trong cửa sổ đang chạy.

`START_WINDOWS.bat` không cài lại thư viện và không tự bật trình duyệt. Nếu chạy trên cổng khác, xem cách thủ công dưới đây.

### Cách thủ công bằng Command Prompt (CMD)

Mở thư mục `ui-dispatch-ai` trong File Explorer, nhấp thanh địa chỉ, gõ `cmd`, nhấn Enter. CMD sẽ mở đúng thư mục dự án. Gõ từng dòng:

```bat
py -3 --version
py -3 -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

Nếu không có lệnh `py` nhưng có `python`, dùng `python --version` và `python -m venv .venv` thay cho hai dòng đầu. Python phải >=3.11.

Khi thấy dòng `Uvicorn running on http://127.0.0.1:8000`, mở website. **Frontend được FastAPI phục vụ cùng backend**, không chạy server frontend riêng, không mở `frontend/index.html` bằng cách nhấp đúp. Giao diện gọi API cùng địa chỉ nên không cần cấu hình CORS.

Không muốn kích hoạt môi trường ảo? Chạy trực tiếp:

```bat
.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

### Cấu hình tùy chọn

Mặc định không cần file `.env`. Để thay đổi, sao chép `.env.example` thành `.env`:

```bat
copy .env.example .env
```

Ví dụ `DATABASE_PATH=data/dispatch.sqlite3`. Đường dẫn tương đối được tính từ thư mục dự án, không phụ thuộc vị trí của CMD. Thư mục `data` và SQLite được tạo tự động lần đầu. Không đưa `.env`, token hoặc dữ liệu thật lên Git. Các biến TMS/GPS/ONP trong `.env.example` hiện chỉ là chỗ giữ cấu hình, thêm URL/token **không** tự kích hoạt kết nối.

## 2. Kịch bản trình diễn 5–7 phút

1. **Tổng quan**: giới thiệu đồng hồ thật Việt Nam và đồng hồ điều hành (mô phỏng). Thông tin về dữ liệu mẫu và giới hạn kết nối nằm trong trang Nguồn dữ liệu. Đồng hồ mô phỏng mặc định 08:00 ngày tạo dữ liệu, đang tạm dừng. Bản đồ đường phố OpenStreetMap cho phép kéo, zoom, mở rộng và chọn chuyến. Điểm mặc định chỉ tham chiếu khu vực KCN Sóng Thần / Cát Lái, chưa xác minh cổng kho/cảng; các địa chỉ chung như “Kho Bình Dương” cần nhập tọa độ. Không hiển thị vị trí xe GPS khi chưa kết nối nguồn GPS.
2. **Bắt đầu** rồi chọn **60x**: một giây thật bằng một phút mô phỏng. Tạm dừng, tiếp tục, hoặc bấm **+30 phút** để tua nhanh. Thời gian thật vẫn chạy độc lập.
3. Theo dõi **UI-1002**, chuyến chờ lệnh: khi chưa khởi hành, ETA lùi theo thời gian, dự phòng giảm. **UI-1001** đang chạy: công việc còn lại giảm, ETA ổn định nếu không phát sinh chậm trễ. Khi hoàn thành, thời điểm hoàn thành được giữ nguyên.
4. Vào **Quản lý chuyến xe**, thêm một chuyến hoặc sửa UI-1002. Thử tăng chậm thêm 30 phút, giảm cut-off hoặc đổi tải hàng. Lưu để thấy ETA, rủi ro và báo cáo đổi ngay. Khi sửa, các thời lượng nhập là khối lượng công việc **còn lại** tại thời điểm lưu.
5. Vào **Hỗ trợ quyết định**, chọn UI-1002; phân tích với ưu tiên đúng hạn rồi ưu tiên chi phí. Dữ liệu mẫu cho phép so sánh ít nhất hai xe phù hợp. Mở mục công thức để giải thích điểm. Nếu tải quá lớn hoặc xe bận, số phương án hợp lệ có thể giảm; hệ thống không tạo phương án không đáp ứng ràng buộc chỉ để đủ hai xe.
6. Bấm chọn phương án, xem hộp xác nhận và xác nhận. Xe, tiến độ chuyến và nhật ký thay đổi trong SQLite demo. Kết quả cũ bị chặn nếu bản ghi/đội xe thay đổi hoặc quá 5 phút mô phỏng / 5 phút thực tế; hãy phân tích lại.
7. Vào **Cảnh báo**, đánh dấu đã xử lý. Rủi ro chuyến không tự biến mất; cảnh báo được lưu lịch sử. Có tình huống thiếu xác nhận booking/container và lỗi nguồn giả lập. Sửa mục chất lượng dữ liệu về “Đầy đủ” để kết thúc các cảnh báo đó.
8. Vào **Báo cáo**, xuất CSV và mở bằng Excel. Vào **Nguồn dữ liệu** để thấy Mock hoạt động, TMS/GPS/ONP chưa kết nối.
9. Muốn trình diễn lại từ đầu: **Nguồn dữ liệu → Khôi phục toàn bộ dữ liệu mẫu**. Có hộp xác nhận trước khi xóa dữ liệu bạn đã nhập.

Các tình huống giả lập gồm tàu chậm, booking thay đổi, depot thiếu container. Người dùng thay đổi dữ liệu bằng biểu mẫu; chưa có NLP tự đọc thông báo lịch tàu/booking, mô hình dự báo học máy, hoặc tối ưu đội xe nhiều chuyến đồng thời.

## 3. Cách tính ETA, cut-off và tiến độ

- `công việc còn lại = di chuyển + bốc dỡ + chậm thêm` khi tạo/lưu chuyến.
- `ETA = max(thời gian mô phỏng hiện tại, khởi hành dự kiến) + công việc còn lại`.
- Nếu có ETA nhập tay, lấy `max(ETA tính toán, ETA nhập tay)`. ETA nhập tay là **mốc không đến trước**, không ghi đè kết quả bằng một giờ sớm bất hợp lý.
- Với chuyến đang chạy: trừ thời gian mô phỏng đã trôi qua kể từ lúc được phép khởi hành khỏi công việc còn lại. Vì vậy chỉ tua nhanh thời gian không tự làm ETA của xe đang chạy bị lùi, nếu không có sự cố mới.
- Chuyến chờ lệnh/tạm dừng chưa tiêu thụ công việc còn lại; thời gian chờ kéo ETA về sau. Chậm thêm là thời lượng phát sinh giả lập do người dùng nhập, không phải dự đoán từ GPS.
- Chuyến đang chạy có công việc bằng 0 được đánh dấu hoàn thành khi tới ETA, bao gồm điều kiện ETA nhập tay. Chuyến hoàn thành giữ thời điểm hoàn thành để đánh giá đúng/trễ hạn.
- `dự phòng = cut-off − ETA`, đơn vị phút. `thời gian tới hạn = cut-off − thời gian mô phỏng`.
- Cao: ETA sau cut-off, hoặc đã qua cut-off mà chuyến chưa hoàn thành.
- Trung bình: dự phòng từ 0 đến dưới 30 phút.
- Thấp: dự phòng từ 30 phút trở lên.
- Chuyến đã hoàn thành: đánh giá đúng/trễ theo giờ hoàn thành; không tính vào nhóm chuyến đang có nguy cơ trễ.

Đồng hồ thật là giờ thiết bị theo `Asia/Ho_Chi_Minh`; backend dùng timestamp có múi giờ. Đồng hồ mô phỏng được lưu riêng trong SQLite; tốc độ 1x/10x/60x; API đồng bộ tiến độ trong giao dịch SQLite. Giao diện hiển thị trơn đồng hồ và lấy snapshot tính toán mới mỗi 2 giây. Khi server không phản hồi, hiện thông báo dữ liệu có thể cũ và ngừng nội suy đồng hồ mô phỏng.

**Đặt lại đồng hồ** đưa mốc về 08:00, dừng đồng hồ và khởi tạo lại công việc còn lại của chuyến chưa hoàn thành; giữ nguyên dữ liệu nhập và các chuyến đã hoàn thành. Đây không phải khôi phục toàn bộ kịch bản. Muốn khôi phục toàn bộ, dùng chức năng riêng ở trang Nguồn dữ liệu.

Đồng hồ/tiến độ được lưu qua lần khởi động. Nếu đóng server khi đồng hồ đang chạy, lần mở sau hệ thống tính cả thời gian thật đã trôi qua theo tốc độ lưu. **Tạm dừng trước khi đóng server** nếu muốn giữ nguyên cảnh trình diễn.

## 4. Bộ máy so sánh phương án

Phạm vi: lựa chọn một xe cho một chuyến, không phải thuật toán tối ưu toàn bộ đội xe.

1. Loại xe bận ở chuyến chưa hoàn thành khác, xe sai loại hoặc không đủ tải trọng. Xe hiện tại của chuyến vẫn có thể được so sánh.
2. Xe thay thế: thời gian = sẵn sàng + tiếp cận + di chuyển × hệ số xe + bốc dỡ + chậm thêm. Hệ số/thời gian/chi phí huy động xe là tham số giả lập trong `adapters/mock.py`.
3. Xe hiện tại: dùng công việc còn lại thực tế trong mô phỏng.
4. Chi phí phương án = chi phí đầu vào chuyến + chi phí huy động xe thay thế + số phút trễ dự kiến / 60 × phí chờ theo giờ. Đây là chi phí ước tính, chưa gồm dem/det, nâng hạ hay thuê ngoài chi tiết. Không được coi như số liệu tài chính thực tế.
5. Bốn điểm thành phần (0–1):
   - Thời gian: `(lớn nhất − giá trị) / (lớn nhất − nhỏ nhất)` trong tập xe hợp lệ.
   - Chi phí: chuẩn hóa đảo chiều tương tự thời gian.
   - Cut-off: `max(0, min(1, dự phòng / 30))`.
   - Sử dụng xe: `tải hàng / tải trọng xe`.
   - Nếu mọi giá trị thời gian/chi phí bằng nhau, điểm thành phần đó bằng 1 cho mọi xe.
6. Trọng số chuẩn hóa bằng cách chia cho tổng; tổng 0 bị từ chối. Điểm = 100 × tổng (trọng số chuẩn hóa × điểm thành phần).
7. Sắp điểm cao xuống thấp; hòa điểm ưu tiên chi phí thấp rồi mã xe. Phương án được điểm cao vẫn có thể trễ khi mọi xe đều không kịp, hoặc khi người dùng ưu tiên chi phí; giao diện hiển thị cảnh báo và yêu cầu xác nhận.
8. Lúc xác nhận, kiểm tra tính hợp lệ của phân tích và tính lại xe đã chọn theo thời gian mới. Chỉ cập nhật dữ liệu demo, không có thao tác truyền lệnh ra ngoài.

Báo cáo cộng chi phí đầu vào, không tự cộng chi phí ước tính phương án vào chi phí đã phát sinh. Tỷ lệ đúng hạn chỉ dựa trên chuyến đã hoàn thành; nguy cơ trễ chỉ dựa trên chuyến chưa hoàn thành. Chưa có dữ liệu đối chứng kỳ trước – kỳ sau để chứng minh giảm ≥20% chi phí.

## 5. API và trang `/docs`

Trang http://127.0.0.1:8000/docs là **API Explorer cục bộ** sinh danh sách endpoint và schema từ OpenAPI của FastAPI. Chọn endpoint, sửa đường dẫn/JSON, bấm **Gửi yêu cầu**, xem mã HTTP và kết quả. Không phụ thuộc Swagger CDN. OpenAPI tiêu chuẩn tại `/openapi.json`, dùng được với các công cụ kiểm thử khác.

| Phương thức | Đường dẫn | Chức năng |
|---|---|---|
| GET | `/health` | Trạng thái server |
| GET | `/api/snapshot` | Đồng hồ, chuyến, xe, cảnh báo và báo cáo cùng mốc tính |
| GET / POST | `/api/trips` | Danh sách / tạo chuyến |
| GET / PUT / DELETE | `/api/trips/{id}` | Chi tiết / cập nhật toàn bộ / xóa chuyến |
| GET / POST | `/api/clock` | Đọc / điều khiển thời gian mô phỏng |
| POST | `/api/dispatch/analyze` | Phân tích chuyến và trọng số |
| POST | `/api/dispatch/confirm` | Xác nhận phương án demo |
| GET | `/api/decisions` | Nhật ký xác nhận |
| GET | `/api/alerts` | Cảnh báo và lịch sử |
| POST | `/api/alerts/{id}/ack` | Đánh dấu đã xử lý |
| GET | `/api/sources` | Trạng thái nguồn dữ liệu |
| GET | `/api/reports` | Chỉ số và dữ liệu biểu đồ |
| GET | `/api/reports/export.csv` | Tải CSV UTF-8 BOM cho Excel |
| POST | `/api/demo/reset` | Khôi phục toàn bộ dữ liệu mẫu |

Ví dụ CMD:

```bat
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/api/trips
curl -X POST http://127.0.0.1:8000/api/clock -H "Content-Type: application/json" -d "{\"action\":\"advance\",\"minutes\":30}"
```

Để phân tích trong `/docs`: GET `/api/trips`, lấy ID của chuyến chưa hoàn thành; POST `/api/dispatch/analyze` với:

```json
{"trip_id":2,"weights":{"time":45,"cost":30,"risk":20,"utilization":5}}
```

ID 2 chỉ là ví dụ lần tạo dữ liệu đầu; ID có thể đổi sau khi khôi phục mẫu. Lấy ID thực từ danh sách.

Để xác nhận, lấy `id` của phân tích và `id` của phương án trả về:

```json
{"analysis_id":"ID_PHAN_TICH","option_id":"XE-02","confirmed":true}
```

Lệnh đồng hồ: `start`, `pause`, `resume`, `reset`, `advance` (thêm `minutes`), `speed` (thêm `speed`: 1/10/60).

Mã phản hồi: 201 tạo mới; 404 không tồn tại; 409 trùng mã / xung đột xe / phân tích hết hiệu lực / đã duyệt; 422 dữ liệu không hợp lệ; 503 SQLite bận. Thời gian API phải là ISO 8601 có múi giờ, ví dụ `2026-10-16T08:00:00+07:00`. API PUT nhận bản ghi đầy đủ theo TripInput, không phải bản vá.

## 6. Cấu trúc dự án

```text
ui-dispatch-ai/
  backend/
    app/
      api/routes.py             REST endpoint
      schemas/models.py         TripInput, trọng số, lệnh đồng hồ
      services/eta.py           ETA, tiến độ, rủi ro
      services/dispatch.py      Lọc và chấm điểm phương án
      services/reporting.py     Chỉ số báo cáo
      adapters/base.py          Hợp đồng nguồn dữ liệu
      adapters/mock.py          Dữ liệu mẫu, thông số đội xe
      adapters/integrations.py  TMSAdapter, GPSAdapter, ONPAdapter
      store.py                  Giao dịch SQLite, đồng hồ, dữ liệu
      main.py                   FastAPI, static frontend, cấu hình
    tests/test_system.py        Kiểm thử tự động
  frontend/
    index.html / style.css / app.js
    docs.html / docs.js          API Explorer không cần CDN
  data/                         Tạo SQLite khi chạy lần đầu
  .env.example / .gitignore
  requirements.txt
  SETUP_WINDOWS.bat / START_WINDOWS.bat / TEST_WINDOWS.bat
  README.md / INTEGRATION.md / TEST_REPORT.md
```

Không cần file báo cáo Word, ảnh, tài nguyên CDN, hoặc bất kỳ file riêng nào ngoài dự án để chạy sau khi đã cài thư viện.

## 7. Kiểm thử

Trong CMD tại thư mục dự án:

```bat
.venv\Scripts\python.exe -m pytest backend\tests -q
```

Hoặc nhấp đúp `TEST_WINDOWS.bat`. Mỗi bài kiểm thử dùng SQLite tạm, không ghi vào dữ liệu trình diễn. Các ca bao gồm ETA, ngưỡng cut-off, tiến độ hoàn thành, đồng hồ độc lập, tốc độ/tạm dừng/tiếp tục, CRUD, validate, xung đột xe, trọng số làm thay đổi phương án, kiểm tra trước xác nhận, lịch sử cảnh báo, báo cáo, CSV chống công thức, persistence, adapter và móc nối DOM tĩnh. Xem `TEST_REPORT.md` cho kết quả thật và giới hạn kiểm tra.

## 8. Lỗi thường gặp

| Hiện tượng | Cách xử lý |
|---|---|
| `py` / `python` không nhận diện | Cài Python và chọn Add to PATH; mở CMD mới. Thử `py -3` hoặc `python`. |
| Không tìm thấy `requirements.txt` / module `backend` | Bạn đang sai thư mục. Dùng File Explorer mở thư mục có `README.md`, gõ `cmd` trên thanh địa chỉ. |
| `No module named fastapi/uvicorn` | Chạy SETUP; hoặc `.venv\Scripts\python.exe -m pip install -r requirements.txt`. Dùng đúng Python trong `.venv`. |
| Cài thư viện lỗi mạng/proxy | Kiểm tra Internet/quyền truy cập PyPI, rồi chạy lại SETUP. Website không cần API key. |
| PowerShell chặn `Activate.ps1` | Dùng CMD, hoặc gọi thẳng `.venv\Scripts\python.exe`; không cần đổi chính sách PowerShell. |
| `[WinError 10048]` / cổng 8000 đang dùng | Đóng phiên server cũ bằng Ctrl+C, hoặc đổi `--port 8001`; mở `http://127.0.0.1:8001`. |
| Website mất kết nối | Server cần đang chạy. Mở bằng `http://127.0.0.1:8000`, không mở file HTML. Kiểm tra đúng cổng. |
| CSV có dấu tiếng Việt sai | File có UTF-8 BOM; dùng Excel Data → From Text/CSV → UTF-8 nếu bản Excel cũ không tự nhận. |
| Không đủ hai phương án | Kiểm tra tải trọng, loại xe và xe đang bận; dữ liệu mặc định UI-1002 có hai xe thay thế hợp lệ. |
| Không duyệt được phương án | Dữ liệu đổi hoặc quá 5 phút; tạm dừng mô phỏng và phân tích lại. |
| SQLite chỉ đọc/không ghi được | Giải nén vào thư mục bạn có quyền ghi, ví dụ Desktop; không chạy bên trong ZIP hay Program Files. |
| Dữ liệu cũ vẫn còn | SQLite lưu qua lần chạy. Dùng Nguồn dữ liệu → Khôi phục toàn bộ dữ liệu mẫu (có xác nhận). |
| Máy sai giờ | Chỉnh giờ Windows. Đồng hồ thật theo giờ hệ điều hành, hiển thị múi giờ Việt Nam. |

## 9. Giới hạn triển khai

Dự án được thiết kế cho một phiên demo local, một tiến trình Uvicorn, bind `127.0.0.1`. Chưa có đăng nhập, phân quyền hoặc mô hình học máy. Có luồng nhập tệp và connector JSON HTTPS chỉ đọc, mặc định tắt; không tự kết nối doanh nghiệp. Các API thay đổi dữ liệu được công khai trong phiên local có chủ ý để học/thử nghiệm. Không đổi host sang `0.0.0.0` hay công khai lên Internet trước khi bổ sung xác thực, phân quyền, kiểm soát truy cập, HTTPS, audit và quy trình vận hành phù hợp. Không nhập dữ liệu thật khi chưa có quyền.

Xem `INTEGRATION.md` để cấu hình, ánh xạ và kiểm tra connector chỉ đọc khi có tài liệu và quyền truy cập hợp lệ.

## Bản đồ đường phố (bản cập nhật)

- Chọn chuyến trên bản đồ để xem điểm lấy A và điểm giao B. Dùng nút +/− hoặc thao tác chạm để zoom; kéo bản đồ để di chuyển.
- “Xem toàn tuyến” căn khung chứa hai điểm, không tính đường lái xe. “Mở rộng” mở vùng bản đồ lớn; Escape thu gọn.
- Mở “Định vị điểm lấy / giao hàng”, nhập vĩ độ, kinh độ theo dạng `10.758, 106.790` rồi lưu. Vị trí lưu trên trình duyệt hiện tại theo chuyến và tên hai đầu tuyến; đổi tên địa điểm cần định vị lại. Không đồng bộ tọa độ qua SQLite hoặc máy khác.
- “Chỉ đường Google Maps” mở đường lái xe trong tab mới. Nếu chưa có tọa độ, Google tìm theo tên địa điểm; cần chọn lại địa chỉ chính xác khi tên chưa rõ.
- Nền bản đồ thật không có nghĩa là vị trí xe đang được theo dõi thật. Chưa kết nối GPS; không vẽ xe chạy giả, không tự suy ra vị trí xe từ đồng hồ mô phỏng. ETA trong bảng vẫn theo công thức vận hành, chưa lấy từ Google Maps và chưa tính giao thông trực tiếp.
- Bản đồ dùng Leaflet 1.9.4 (BSD-2-Clause, giấy phép trong `frontend/vendor/leaflet/LICENSE`). Giữ nguyên dòng © OpenStreetMap contributors. Tiles chỉ tải theo vùng đang xem, không tải trước/offline. Chính sách: https://operations.osmfoundation.org/policies/tiles/ . Khi triển khai quy mô lớn, cần nhà cung cấp tiles phù hợp.
- Khi mất Internet, các chức năng điều vận cục bộ vẫn dùng được; nền bản đồ chưa có trong cache có thể không tải được.

## 11. Trình diễn các giải pháp trong báo cáo (v1.4)

### Thông báo lịch tàu và booking — mục 3.3.1–3.3.2

1. Mở **Thông báo thay đổi**, chọn đúng chuyến bị ảnh hưởng.
2. Bấm **Mẫu tàu chậm** hoặc **Mẫu hủy booking**; có thể sửa nội dung.
3. Bấm **Đọc & đối chiếu thay đổi**. Hệ thống dùng quy tắc để đọc các dòng có nhãn và hiển thị giá trị cũ – mới. Các giờ trong bảng so sánh được hiển thị theo giờ Việt Nam.
4. Kiểm tra chuyến và dữ liệu, bấm **Xác minh & cập nhật dữ liệu chuyến**, rồi xác nhận trong hộp thoại. Dữ liệu ETA/rủi ro sẽ được tính lại. Nếu chuyến đã được sửa từ lúc đối chiếu, cần đọc lại thông báo.
5. Sau đó mở **Lệnh & xác nhận** để phát hành hướng xử lý. Việc cập nhật thông báo không tự gửi lệnh hoặc tự dừng xe. Booking bị hủy làm phát cảnh báo và đánh dấu cần xác minh; trạng thái di chuyển chỉ thay đổi khi thao tác thực hiện lệnh được ghi nhận.

Các nhãn được đọc: `Booking`, `Tên tàu`, `Chuyến tàu`, `ETA tàu`, `ETD tàu`, `Cut-off`, `Điểm lấy`, `Điểm giao`, `Trạng thái`. Trạng thái nhận `Hủy` hoặc `Hoạt động`. Ngày giờ nhập theo ISO có múi giờ, ví dụ `2026-10-17T13:30:00+07:00`. Thiếu trường nghĩa là giữ nguyên dữ liệu hiện tại; trường lặp bị từ chối để nhân viên kiểm tra.

Bản hiện tại chưa đọc email/PDF trực tiếp, chưa dùng OCR hoặc mô hình ngôn ngữ và chưa dự báo chậm tàu từ lịch sử. Người dùng chọn chuyến bị ảnh hưởng, không tự đối chiếu mã booking với TMS thật. Lịch tàu/booking đã xác minh lưu trong SQLite để làm cơ sở đối chiếu lần sau.

### Tái phân bổ theo danh sách xe — mục 3.3.3

Mở **Tái phân bổ xe**, nhập danh sách cần xét rồi bấm **Phân tích toàn bộ danh sách**. Không cố định 03 xe: có thể xét 1, 2, 10 hoặc nhiều xe tùy dữ liệu đầu vào (tối đa 10.000 xe mỗi danh sách trong phiên bản này). Hệ thống kiểm tra toàn bộ đầu vào và chỉ hiển thị tối đa **03 phương án tốt nhất**; mở phần thứ hạng để xem mọi xe hợp lệ, xe bị loại được ghi rõ lý do.

Bộ **03 xe mẫu báo cáo** vẫn có thể nạp riêng:

| Xe | Tour tháng | Km lũy kế | Ở Bãi Xe U&I | Điểm S (xấp xỉ) |
| --- | ---: | ---: | --- | ---: |
| 61C-172.28 | 56,5 | 154,54 | Không | 1,000 |
| 61C-277.11 | 55 | 147,96 | Không | 0,977 |
| 61C-304.40 | 56,5 | 149,51 | Có | 0,656 |

Công thức: `S = (T/Tmax + K/Kmax + P)/3`; `P=0` nếu ở bãi, `P=1` nếu ngoài bãi. Điểm thấp được ưu tiên. `Tmax` và `Kmax` lấy từ toàn bộ danh sách xe nhập; nếu một mẫu số bằng 0 thì thành phần tương ứng bằng 0 cho mọi xe. Xe không đáp ứng moóc, tải trọng, trạng thái sẵn sàng, thời gian làm việc hoặc cut-off bị loại trước khi xếp hạng. Các cờ điều kiện là giá trị người dùng xác minh, chưa lấy từ thiết bị.

Bạn có thể thêm, sửa, xóa xe, thay tour, km, vị trí hoặc điều kiện để thấy kết quả đổi. Xe mới thêm có các điều kiện chưa được đánh dấu; cần xác minh trước khi xếp hạng. Nút **Nạp 03 xe mẫu báo cáo** thay danh sách hiện tại bằng bộ mẫu sau khi xác nhận. Chọn **Lưu danh sách** để lưu vào SQLite; phân tích thành công cũng lưu danh sách. Khi sửa đầu vào, kết quả cũ được xóa để tránh dùng nhầm. Danh sách đã lưu được giữ khi khởi động lại web.

Nhập CSV: chọn **Tải CSV mẫu**, giữ các tên cột `plate,tours,km,at_yard,trailer_ok,capacity_ok,ready,hours_ok,cutoff_ok`; thêm bao nhiêu dòng xe tùy dữ liệu. CSV UTF-8 (có hoặc không BOM), dùng dấu phẩy hoặc chấm phẩy. Các cột điều kiện nhận `true/false`, `1/0`, `yes/no` hoặc `có/không`. Khi số thập phân dùng dấu phẩy, sử dụng dấu chấm phẩy phân cột hoặc đặt giá trị số trong dấu nháy kép theo chuẩn CSV. File cần đủ các cột điều kiện để tránh mặc định xe đáp ứng ràng buộc khi chưa xác minh. Nhập CSV được kiểm tra trước; file sai không ghi đè danh sách đã lưu. Xác nhận thay danh sách rồi bấm Lưu hoặc Phân tích. Tối đa 5 MB mỗi CSV. Biển số không được trùng (không phân biệt hoa/thường). Trang này tách khỏi danh sách đội xe vận hành mẫu; không tự áp dụng phân công sang các chuyến `UI-*`. Km lũy kế không phải km chạy rỗng hoặc km phát sinh. Công thức minh họa chưa phải bộ tối ưu tuyến OR-Tools.

### Lệnh, phiên bản và phản hồi lái xe — mục 3.3.4

1. Mở **Lệnh & xác nhận**, chọn chuyến đã được phân công xe. Với chuyến chưa có xe, dùng **Hỗ trợ quyết định** hoặc chỉnh chuyến để phân công trước.
2. Nhập mã lái xe (ví dụ `LX-01`), hướng xử lý và nội dung lệnh. Bấm **Kiểm tra & phát hành phiên bản mới**, đọc lại rồi xác nhận.
3. Ở màn hình lái xe cùng trang, nhập đúng mã người nhận. Bấm **Ghi nhận đã nhận** → **Đã hiểu & xác nhận** → **Bắt đầu thực hiện**. Các bước đều cần xác nhận. Lệnh dừng an toàn chỉ đổi trạng thái chuyến thành tạm dừng khi ghi nhận bắt đầu thực hiện.
4. Khi không thể thực hiện, sau bước nhận lệnh chọn **Không thể thực hiện**, nhập lý do và xác nhận. Điều vận sẽ nhận cảnh báo.
5. Để trình diễn quá hạn, phát hành một lệnh và chưa xác nhận, bấm **+5 phút kiểm tra phản hồi**. Cảnh báo xuất hiện trong trang này và **Trung tâm cảnh báo**. Đồng hồ tăng cũng tác động ETA và tiến độ chuyến.
6. Phát hành phiên bản mới: phiên bản cũ lập tức hết hiệu lực và không thể nhận/xác nhận/thực hiện lại. Nếu dữ liệu chuyến hoặc phiên bản đổi trong lúc đang soạn, bấm **Nạp lại dữ liệu chuyến / phiên bản**, kiểm tra nội dung rồi phát hành lại.
7. Xem **Nhật ký** để đối chiếu dấu thời gian điều hành và thời gian thực. Trang **Báo cáo** có chỉ số phản hồi và xuất nhật ký CSV cho Excel.

Mốc 05 phút tính theo thời gian điều hành tích lũy. Tạm dừng đồng hồ thì thời gian chờ không tăng; tốc độ 10x/60x và nút tăng thời gian tác động tới thời hạn. **Đặt lại đồng hồ** không xóa thời gian chờ tích lũy hoặc lịch sử; lệnh đang chờ có thể cần phát hành lại vì tiến độ chuyến đã đổi. **Khôi phục toàn bộ dữ liệu mẫu** xóa cả thông báo, lệnh, quyết định và lịch sử phiên thử.

Tỷ lệ xác nhận trong 05 phút = số phiên bản có xác nhận không quá 05 phút / tất cả phiên bản đã phát hành (kể cả phiên bản bị thay thế). Không có lệnh thì hiển thị “—”. Đây là chỉ số thao tác thử, không tự chứng minh mục tiêu 95% hoặc mức tiết kiệm ≥20% trong báo cáo.

Màn hình lái xe hiện là thao tác chuyển vai trong cùng phiên local; mã lái xe không phải thông tin đăng nhập hoặc xác thực. Chưa gửi SMS/Zalo/push tới điện thoại, chưa cập nhật TMS thật, chưa kiểm tra GPS xem xe có đi theo lệnh mới.

### Dữ liệu và nâng cấp từ bản trước

SQLite tự bổ sung bảng `orders` và `notices` khi khởi động, giữ lại dữ liệu chuyến hiện có. Nên sao lưu file `data/dispatch.sqlite3` trước khi thay mã nguồn. Để giữ dữ liệu, dừng server, giải nén bản mới vào thư mục khác rồi chép bản sao database vào thư mục `data` của bản mới. Không chạy hai bản cùng một database. Chạy `SETUP_WINDOWS.bat` nếu chưa có môi trường và mở lại `START_WINDOWS.bat`. Nếu trình duyệt còn giao diện cũ, bấm Ctrl+F5.

API mới: `POST /api/notices/preview`, `POST /api/notices/{id}/apply`, `POST /api/pilot/analyze`, `GET /api/operations`, `GET/PUT /api/pilot/fleet`, `POST /api/pilot/fleet/import`, `GET /api/pilot/fleet/template.csv`, `POST /api/orders`, `POST /api/orders/{id}/driver`, `GET /api/orders/export.csv`. Xem schema và ví dụ trường dữ liệu tại `/docs`.

Kiểm tra bổ sung tùy chọn nếu có Node.js: `node backend/tests/test_map_logic.cjs`. Node.js không bắt buộc để chạy website.

## 12. Kết nối doanh nghiệp — v1.4

Mở **Kết nối doanh nghiệp**, chọn TMS/GPS/ONP. Có thể tải CSV mẫu, ánh xạ tên cột hoặc đường dẫn JSON, đọc tệp và kiểm tra lỗi. Chỉ sau khi xác nhận, dữ liệu mới vào khu vực doanh nghiệp riêng. GPS có thể mở vị trí theo bản ghi nguồn trên bản đồ, kèm dấu thời gian và độ mới; TMS/ONP có bảng dữ liệu nguồn để đối soát. Excel cần xuất CSV UTF-8; luồng này chưa đọc Excel/PDF trực tiếp.

Khi được cấp quyền API, IT cấu hình các biến trong `.env.example`, khởi động lại server, lưu ánh xạ theo tài liệu API và bấm đọc để kiểm tra. Hỗ trợ HTTPS GET trả JSON, Bearer token hoặc header X-API-Key. Khóa ở backend, không nhập ở trình duyệt. Chưa có OAuth tự gia hạn, chữ ký riêng hoặc đồng bộ tự động/phân trang. Không có URL/token doanh nghiệp thật trong gói bàn giao.

Đợt dữ liệu có lỗi bị chặn toàn bộ; dữ liệu đến cũ hơn hoặc cùng dấu thời gian không ghi đè bản mới. Nhập nguồn không ghi đè chuyến mẫu, không tự phân công hoặc gửi lệnh ra ngoài. Đưa dữ liệu đã xác minh vào quy trình điều vận cần chốt thêm ID, đơn vị, mã trạng thái và quy tắc nghiệp vụ theo doanh nghiệp.

Xem **INTEGRATION.md** trong cùng thư mục để thực hiện từng bước. Chức năng nguồn được kiểm thử bằng dữ liệu mẫu và API giả lập; chưa kiểm tra với API thật của U&I hoặc nhà cung cấp GPS/TMS.

## Sửa điều hướng do tài nguyên cũ — v1.4.1

Nếu bấm Kết nối doanh nghiệp lại thấy Tổng quan, trình duyệt có thể đang giữ app.js của phiên bản trước. Bản v1.4.1 gắn mã phiên bản cho các file JavaScript/CSS và đặt Cache-Control: no-store cho HTML, tài nguyên ứng dụng và API.

Dừng cửa sổ START_WINDOWS.bat cũ bằng Ctrl+C, giải nén trọn bộ bản mới và chạy START_WINDOWS.bat trong đúng thư mục mới. Mở http://127.0.0.1:8000 rồi bấm Ctrl+F5. Có thể vào thẳng http://127.0.0.1:8000/#enterprise. Không chỉ sao chép riêng file index.html sang mã nguồn cũ. Xem hướng dẫn giữ database trong mục nâng cấp nếu cần giữ dữ liệu đã nhập.

# Biên bản kiểm tra v1.4.1

Ngày kiểm tra: 17/10/2026. Môi trường: Linux, Python 3.12, FastAPI TestClient, Node.js và Chromium headless. Đây là kết quả của bản mã nguồn bàn giao, không phải kết quả triển khai tại doanh nghiệp.

## Kết quả đã thực hiện

- `python -m pytest backend/tests -q`: **132 passed**. Có một cảnh báo deprecation từ Starlette TestClient về thư viện HTTP; không có bài kiểm thử thất bại.
- Kiểm tra cú pháp `frontend/app.js`, `frontend/map.js` và `frontend/operations.js` bằng `node --check`: đạt.
- `node backend/tests/test_map_logic.cjs`: đạt, dùng DOM/Leaflet giả lập để kiểm tra tọa độ, điểm tham chiếu, URL Google Maps, lưu/xóa vị trí, địa chỉ chưa rõ và danh sách rỗng.
- Kiểm thử giao diện trên Chromium headless: tính/xếp hạng 03 xe theo báo cáo; bỏ ràng buộc để đổi xe đề xuất; phát hành lệnh; tăng 05 phút để tạo cảnh báo; lái xe nhận, xác nhận và bắt đầu thực hiện; đối chiếu và cập nhật lịch tàu; phát hành v2 làm v1 hết hiệu lực; lái xe từ chối kèm lý do; kiểm tra cảnh báo, báo cáo và CSV. Không ghi nhận lỗi JavaScript hoặc phản hồi HTTP lỗi trong luồng này.
- Kiểm tra 6 trang Tổng quan, Bài toán 03 xe, Lệnh & xác nhận, Thông báo thay đổi, Báo cáo và Nguồn dữ liệu ở viewport rộng 390 px: không tràn ngang toàn trang. Các bảng rộng cuộn bên trong khung.
- Đã tạo và xem ảnh kiểm tra nội bộ của màn hình bài toán 03 xe, lệnh, thông báo và giao diện hẹp.

## Phạm vi các kiểm thử backend

- CRUD, kiểm tra tải trọng/loại xe và xung đột phân công; ETA, cut-off, tiến độ, trạng thái hoàn thành, tốc độ/tạm dừng/đặt lại đồng hồ.
- Phân tích trọng số, xác nhận, chống áp dụng lại hoặc áp dụng phân tích cũ; báo cáo và CSV chống công thức trong dữ liệu người dùng.
- Bài toán 03 xe cho đúng điểm xấp xỉ **0,656 – 0,977 – 1,000**, thay đổi đầu vào làm đổi kết quả; lọc đủ 5 nhóm ràng buộc; xử lý không có xe hợp lệ, mẫu số bằng 0 và biển số trùng.
- Thông báo: xem trước không cập nhật chuyến; yêu cầu xác nhận; giữ công việc còn lại khi đổi metadata; hủy booking tạo cảnh báo; không tự dừng xe; phát hiện ngày giờ sai, nhãn lặp, dữ liệu đã thay đổi và áp dụng lặp.
- Lệnh: yêu cầu xác nhận, kiểm tra xe đã được phân công, kiểm tra phiên bản, lệnh cũ hết hiệu lực, đúng mã người nhận, thứ tự nhận/xác nhận/thực hiện, chặn thao tác sau khi dữ liệu chuyến đổi, bắt buộc lý do từ chối.
- Cảnh báo tại ngưỡng 05 phút, giải quyết cảnh báo sau xác nhận; từ chối sau khi đã đánh dấu cảnh báo quá hạn tạo cảnh báo mới; đặt lại đồng hồ không xóa thời gian chờ; xóa chuyến vô hiệu hóa lệnh đang chờ.
- SQLite: giữ dữ liệu chuyến khi bổ sung bảng mới vào cấu trúc cũ; duy trì lệnh/thông báo qua lần khởi động lại; khôi phục dữ liệu mẫu xóa lịch sử phiên thử.
- Kiểm tra DOM hooks, tài nguyên cục bộ, CSP cho máy chủ tiles và Referrer-Policy.

## Giới hạn đã xác định

- Chưa chạy trực tiếp trên Windows. File BAT và hướng dẫn dùng Python được giữ trong gói; chưa xác minh quy trình cài mới qua Internet trên máy Windows.
- Trong kiểm thử Chromium, request OpenStreetMap được thay bằng ảnh kiểm thử để không tự động tải/prefetch public tiles. Vì vậy kiểm thử xác minh khung bản đồ/markers và các thao tác ứng dụng, chưa xác minh hình nền đường phố thực tế hoặc kết nối Internet trên máy người dùng. Không kiểm thử giao thông trực tiếp hoặc Google Maps cung cấp tuyến chính xác cho một địa chỉ chưa rõ.
- Chưa tích hợp email/PDF/OCR/LLM, chưa kết nối API thật của TMS/GPS/ONP hoặc tin nhắn tới điện thoại. Connector JSON chỉ đọc và nhập tệp đã được bổ sung ở v1.4, mặc định tắt nguồn API. Nhận diện thông báo hiện dùng dòng văn bản có nhãn; người dùng xác minh chuyến bị ảnh hưởng. Không có mô hình AI được huấn luyện.
- Mã lái xe là công cụ chuyển vai thử nghiệm trong cùng phiên local, không phải cơ chế xác thực. Không coi bản local là hệ thống đã sẵn sàng vận hành công khai.
- Chưa có số liệu vận hành trước – sau tại U&I. Các chỉ số xác nhận phát sinh từ thao tác thử; chưa chứng minh đạt ≥95% hoặc giảm ≥20% chi phí. Dữ liệu bài toán 03 xe chỉ minh họa công thức trong báo cáo, không thay thế chi phí/km và quãng đường phát sinh thực tế.

Biên bản này thay thế các ghi chú kiểm tra v1.0/v1.1 trước đó; đặc biệt bản v1.2 và v1.3 đã có kiểm thử giao diện bằng Chromium như mô tả ở trên.

## Bổ sung v1.3 — số xe đầu vào linh hoạt

- Không còn cố định 03 xe trong API hoặc bảng nhập tái phân bổ. Kiểm tra với 1, 2, 3, 10 và 100 xe: xét đầy đủ danh sách, đề xuất tối đa 03 phương án và trả thứ hạng mọi xe hợp lệ.
- Kiểm tra loại xe theo ràng buộc, không còn xe hợp lệ, trùng biển số không phân biệt hoa/thường, lưu SQLite, đọc lại sau khởi động và khôi phục dữ liệu mẫu.
- Kiểm tra CSV: 10 dòng xe; UTF-8 BOM; phân cột bằng phẩy/chấm phẩy; số thập phân có dấu phẩy; thiếu/trùng cột; cờ điều kiện sai; số sai/NaN; danh sách rỗng; mẫu tải xuống nhập lại được. Dữ liệu nhập lỗi không ghi đè danh sách đã lưu.
- Chromium: thêm/sửa/xóa, phân tích 1/3/4/10 xe; tối đa 03 thẻ phương án; bảng thứ hạng đầy đủ; nhập CSV 10 xe; lưu và tải lại sau reload; xóa kết quả cũ khi đầu vào đổi; nạp 03 xe mẫu sau xác nhận; giao diện 390 px không tràn ngang toàn trang. Đã xem ảnh nội bộ màn hình desktop.
- Danh sách xét tái phân bổ được lưu riêng, chưa đồng bộ với danh sách xe vận hành mẫu trong phần Quản lý chuyến/Hỗ trợ quyết định. Công thức vẫn là mô hình minh họa trong báo cáo; không phải tối ưu tuyến thực tế hoặc AI được huấn luyện.

## Bổ sung v1.4 — kết nối doanh nghiệp

- Luồng CSV/JSON TMS/GPS/ONP: ánh xạ trường, đường dẫn JSON lồng nhau, kiểm tra dữ liệu, xem trước không ghi kho dữ liệu chính, yêu cầu xác nhận, chống áp dụng lại và chặn batch lỗi toàn bộ. GPS giữ mẫu mới nhất theo mã xe, không cho bản ghi nguồn cũ ghi đè bản mới.
- TMS không tự điền chi phí khi thiếu dữ liệu. Kiểm tra ngày giờ có múi giờ, GPS sai tọa độ và số dòng/cấu trúc sai; template CSV cả ba nguồn nhập lại được.
- Connector được kiểm thử bằng httpx.MockTransport: API mặc định tắt nên không gọi mạng; yêu cầu xác nhận; HTTPS, hostname cho phép và xác thực; Bearer/X-API-Key/none; lỗi 301, 401/403, 429, 500, timeout, JSON sai và phản hồi quá 2 MB. Thông báo không tiết lộ token hoặc lỗi thô từ nguồn. Không gọi API doanh nghiệp thật trong kiểm thử.
- Chromium: trang nguồn API bị khóa khi chưa cấu hình; nhập GPS CSV → xem trước → xác nhận → mở marker bản đồ; đổi tên trường nguồn; GPS sai tọa độ bị chặn; JSON theo ánh xạ; TMS/ONP nhập CSV; giao diện 390 px không tràn ngang. Tiles được thay bằng ảnh kiểm thử, chưa kiểm chứng nền đường phố qua Internet. Đã xem ảnh desktop của giao diện kết nối.
- Bản v1.4 được chuẩn bị cho kết nối JSON HTTPS GET có cấu hình phù hợp, không phải connector đã hoàn tất cho mọi nhà cung cấp. Chưa có phân trang tự động, lập lịch đồng bộ, OAuth tự gia hạn, chuyển đổi đơn vị/mã trạng thái riêng hoặc ghi ngược lệnh. Cần tài liệu, endpoint, quyền, thông tin xác thực và kiểm thử theo hệ thống thật trước khi vận hành.

## Sửa điều hướng v1.4.1

- Tái hiện bằng Chromium: HTML mới + phản hồi app.js v1.3 tại URL cũ khiến bấm Kết nối doanh nghiệp hiển thị Tổng quan. Đây là một nguyên nhân tái hiện được; chưa trực tiếp kiểm tra bộ nhớ đệm trên máy người dùng.
- Sau sửa: JavaScript/CSS có mã phiên bản, HTML/tài nguyên ứng dụng/API trả Cache-Control: no-store. Khi vẫn giả lập phản hồi cũ ở URL không phiên bản, giao diện tải mã mới và mở đúng trang Kết nối doanh nghiệp.
- Chromium kiểm tra cả bấm menu và vào thẳng /#enterprise; trường ánh xạ hiển thị đúng, nút API chưa cấu hình vẫn bị khóa, không có lỗi JavaScript.

## Chuẩn bị GitHub / Render ngày 20/10/2026

- Dùng bản RENDER_READY, đặt các file ở thư mục gốc repository. Không đưa .env, SQLite đang chạy, môi trường Python hoặc cache lên GitHub.
- Sửa header WWW-Authenticate, hỗ trợ so sánh mật khẩu UTF-8, cấu hình thiếu fail-closed và no-store. Health production chỉ trả trạng thái tối thiểu.
- Chạy lại 142 bài kiểm thử trên Linux/Python 3.12: đạt. Các kiểm thử hosting gồm trang/API/docs/static phải đăng nhập, thông tin sai bị từ chối, cấu hình thiếu bị chặn, health hoạt động và mật khẩu tiếng Việt được hỗ trợ.
- Kiểm tra cú pháp JavaScript và kiểm tra logic bản đồ bằng Node: đạt. Chưa triển khai Render hoặc kiểm thử trực tiếp Python 3.11/Windows trong lần này.


## Tinh chỉnh v1.5 — ngày 20/10/2026

- Linux/Python 3.12: 147 kiểm thử pytest đạt. Bổ sung kiểm tra thông báo đổi điểm lấy/giao, container, phương tiện và sự cố; giữ bước xác nhận, kiểm tra xe, chặn lệnh cũ và cảnh báo sự cố đến khi xử lý. Không tự dừng xe.
- Chromium: ghép cột theo tên nguồn; preview dạng bảng; CSV/JSON cả TMS/GPS/ONP; API chưa cấu hình vẫn khóa; xem trước lỗi bị chặn. Các trường bổ sung và JSON kỹ thuật được thu gọn.
- Tổng quan: không có GPS thì không vẽ xe; 2 bản ghi GPS thử nghiệm cho 1 xe dừng/cũ và 1 xe di chuyển/mới hiển thị đúng vị trí và mốc nguồn. Nền OpenStreetMap được thay bằng ảnh kiểm thử, không gọi API doanh nghiệp thật.
- Giờ Việt Nam hiển thị đúng ngay cả khi trình duyệt đặt múi giờ Los Angeles; giờ mô phỏng vẫn riêng để tính ETA và hạn phản hồi. Cả 5 loại thông báo mới được đối chiếu và xác nhận trên trình duyệt. 10 trang ở chiều rộng 390 px không tràn ngang toàn trang. Đã xem ảnh desktop/mobile nội bộ.
- Chưa kiểm chứng bản triển khai Render sau cập nhật; kiểm thử trình duyệt dùng dữ liệu tạm cục bộ.

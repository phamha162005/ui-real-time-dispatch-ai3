# Dispatch AI

Ứng dụng quản lý chuyến xe và hỗ trợ quyết định điều phối vận tải. Backend FastAPI, frontend HTML/CSS/JavaScript, cơ sở dữ liệu SQLite.

## Bản v1.6.0

- Giao diện Dispatch AI, không gắn tên doanh nghiệp.
- Giờ thực theo Việt Nam; ETA, tiến độ chuyến và hạn phản hồi tự cập nhật. Không có đồng hồ kịch bản, nút tua thời gian hay lối vào kiểm thử API trên giao diện điều vận.
- Bản đồ đội xe với tìm kiếm, lọc di chuyển/dừng/dữ liệu cũ, danh sách xe liên kết với marker, gom xe gần nhau và lưu góc nhìn. Vị trí lấy từ kho GPS đã xác nhận; không tự tạo tọa độ xe.
- Tab Điểm lấy/giao hiển thị địa điểm giao nhận của chuyến. Dùng Google Maps để xem tuyến đường thực tế; không vẽ đoạn thẳng rồi gọi là tuyến đường.
- Nhập CSV/JSON doanh nghiệp qua Field Mapping → xem trước bảng → xác nhận lưu. Kết nối API chỉ đọc sau khi cấu hình và được cấp quyền.
- Đối chiếu thông báo lịch tàu, booking, đổi điểm lấy/giao, container, phương tiện và sự cố. Dữ liệu được nhân viên xác nhận trước khi cập nhật.
- Xếp hạng phương tiện theo danh sách đầu vào và ràng buộc; quản lý phiên bản lệnh, gửi – nhận – xác nhận, cảnh báo và báo cáo CSV.

## Chạy trên Windows

1. Cài Python 3.11 hoặc 3.12. Đánh dấu **Add python.exe to PATH** khi cài.
2. Giải nén dự án; mở thư mục có `requirements.txt`, `backend/` và `frontend/`.
3. Chạy `SETUP_WINDOWS.bat`, chờ cài xong.
4. Chạy `START_WINDOWS.bat`, giữ cửa sổ đang chạy.
5. Mở http://127.0.0.1:8000 bằng Chrome hoặc Edge.

Hoặc chạy thủ công:

```bat
py -3.11 -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

Dừng máy chủ bằng Ctrl+C. Bản đồ đường phố cần Internet; Leaflet được đóng gói trong dự án.

## Triển khai Render

Repository có sẵn `render.yaml`. Xem `DEPLOY_RENDER_VI.md`. Đặt `DEMO_USERNAME` và `DEMO_PASSWORD` trong Render Environment; không đưa mật khẩu hoặc token vào GitHub.

Bản triển khai dùng giờ thực và bắt buộc đăng nhập cho trang, API và tài liệu; `/health` là kiểm tra trạng thái tối thiểu. API tua/dừng đồng hồ bị chặn khi dùng giờ thực. SQLite ở `/tmp` trên gói miễn phí không bảo đảm lưu lâu dài; cần cơ sở dữ liệu bền vững khi vận hành thực tế.

## Nguồn dữ liệu và cách dùng

- **Tổng quan:** mở Đội xe GPS để tìm/lọc xe; bấm xe để xem tọa độ, tốc độ và thời gian nguồn. Màu vàng biểu thị mẫu cũ hơn 5 phút hoặc thời điểm nằm trong tương lai. Nhãn dừng/di chuyển chỉ phản ánh lần ghi nhận.
- **Điểm lấy/giao:** chọn chuyến; A là điểm lấy, B là điểm giao. Tọa độ khu vực có sẵn chỉ để tham chiếu; có thể chỉnh tọa độ cổng kho/cảng và lưu riêng trong trình duyệt.
- **Chuyến xe:** thêm/sửa/xóa chuyến và nhập đúng tải trọng, thời gian, công việc còn lại, chi phí.
- **Thông báo:** nhập văn bản theo nhãn, chẳng hạn `Điểm giao: Depot Thủ Đức` hoặc `Sự cố: Xe hỏng lốp`. Xem đối chiếu rồi xác nhận. Đổi điểm cần kiểm tra lại quãng đường và thời gian; đổi xe phải đúng loại, đủ tải và chưa vướng chuyến khác.
- **Lệnh điều xe:** phát hành phiên bản mới, nhập mã người nhận; nhận/xác nhận/thực hiện trong ứng dụng. Lệnh cũ hoặc dữ liệu chuyến đã thay đổi bị chặn. Chưa gửi thông báo tới thiết bị lái xe.
- **Kết nối dữ liệu:** chọn nguồn, tải tệp mẫu, ghép tên cột, xem trước và xác nhận. GPS xuất hiện trên Tổng quan sau khi lưu. Xem `INTEGRATION.md` để cấu hình JSON HTTPS GET được cấp quyền.

Kho GPS được giao diện đọc lại mỗi 15 giây; đây không phải lịch tự gọi API nhà cung cấp. Không có GPS thì không hiển thị vị trí xe giả. Nguồn doanh nghiệp được lưu riêng, chưa tự ghi đè đội xe/chuyến khởi tạo.

## Phương pháp và giới hạn

Dữ liệu khởi tạo là dữ liệu minh họa. Bộ máy ETA, cảnh báo và xếp hạng dùng quy tắc/công thức, chưa có mô hình AI được huấn luyện. Phân tích không thay cho phê duyệt của nhân viên điều vận. Chưa có bằng chứng kỳ trước – kỳ sau để kết luận mức tiết kiệm thực tế.

Tái phân bổ xét 1–10.000 xe đầu vào và hiển thị tối đa 3 phương án tốt nhất. Điểm minh họa `S = (T/Tmax + K/Kmax + P)/3`, điểm thấp được ưu tiên; `P = 0` khi ở bãi, `1` khi ngoài bãi. Km lũy kế không phải km chạy rỗng phát sinh. Danh sách này được lưu riêng với đội xe vận hành.

## Dành cho phát triển

Tài liệu kỹ thuật vẫn ở `/docs` và `/openapi.json`, không nằm trong menu điều vận. Khi triển khai, các đường dẫn này cũng yêu cầu đăng nhập. Không ghi khóa truy cập vào giao diện.

```bash
python -m pytest -q
node backend/tests/test_map_logic.cjs
```

Kiểm thử API điều khiển thời gian dùng `CLOCK_MODE=simulation` trong môi trường local để bảo đảm kết quả lặp lại. Đây là công cụ phát triển, không xuất hiện trong giao diện. `APP_ENV=production` luôn dùng giờ thực, kể cả khi có cấu hình simulation cũ.

Các dữ liệu, giao dịch SQLite, chống lệnh cũ, xác nhận thay đổi, xác thực hosting và kết nối chỉ đọc được kiểm tra trong `backend/tests/`. Kết quả kiểm tra gần nhất: `TEST_REPORT.md`.

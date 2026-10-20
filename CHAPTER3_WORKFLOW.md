# Năm giải pháp Chương 3 trên Dispatch AI v1.7

## 3.3.1 — Lịch tàu thay đổi
Thông báo → Email & chứng từ → chọn EML/PDF/TXT hoặc dán nội dung → trích thông tin → kiểm tra tên tàu, chuyến, ETA/ETD, cut-off → chọn chuyến khớp mã → chuyển trường → Đọc & đối chiếu → Xác minh & cập nhật. Sau đó vào So sánh chi phí để xem tiếp tục/chờ/kéo về/dời thời điểm; chọn và ghi nhận phê duyệt. Lịch sử nguồn giữ nội dung gốc. AI chỉ trích xuất nếu được cấu hình và xác nhận; đối chiếu mã và phát cảnh báo dùng quy tắc. Chưa dự báo độ chậm từ dữ liệu lịch sử.

## 3.3.2 — Booking thay đổi
Cùng luồng tiếp nhận; kiểm tra booking hủy/đổi điểm/đổi giờ, mã chuyến và container. Danh sách khớp chỉ đề xuất, người dùng chọn. Sau xác minh, kiểm tra Đội xe GPS, nhập phương án tiếp tục/dừng/đổi lệnh hoặc lệnh thay thế. Lệnh thay thế phải xác minh booking, loại moóc, tải, thời gian và an toàn; không tự điều chỉnh toàn đội xe.

## 3.3.3 — Tái phân bổ
Phân bổ xe nhận 1–10.000 xe → kiểm tra ràng buộc → loại xe không đạt → xếp hạng S theo công thức minh họa trong báo cáo. Hỗ trợ quyết định dùng đội xe vận hành và thang điểm 100 riêng. Khi đủ dữ liệu theo sự cố, dùng So sánh chi phí để nhập km/thời gian/chi phí tăng thêm của các phương án khả thi. Ghép lệnh, đổi thứ tự và lệnh thay thế là phương án người dùng nhập, chưa có thuật toán tối ưu nhiều xe/nhiều lệnh tự động hoặc ghi về TMS.

## 3.3.4 — Phiên bản lệnh và xác nhận
Từ bảng chi phí đã duyệt → Chuẩn bị lệnh → kiểm tra đúng chuyến/xe/lái xe/nội dung → phát hành phiên bản mới → khóa bản cũ → nhận → xác nhận hoặc từ chối kèm lý do → thực hiện. Quá 5 phút chờ xác nhận phát cảnh báo. Kiểm tra GPS tại lần ghi nhận gần nhất; chưa tự kết luận xe đang theo tuyến cũ. Lệnh có liên kết bảng phê duyệt được backend chặn khi revision chuyến đổi. Chưa gửi tin đến điện thoại hoặc ghi dữ liệu về TMS.

## 3.3.5 — Chi phí tăng thêm
Nhập 2–9 phương án; sáu cấu phần: nhiên liệu, cầu đường, chờ, nâng hạ phát sinh, kéo về/thuê ngoài, khác. Chỉ nhập khoản thay đổi theo quyết định, loại chi phí chìm; chi hộ thu lại theo dõi riêng trong ghi chú. Chờ theo dõi phút; tiền chờ chỉ nhập khi có định mức. Trống là thiếu dữ liệu; số 0 chỉ khi xác minh không phát sinh. Kiểm tra điều kiện bắt buộc và dự phòng cut-off, không gọi phương án rẻ nhất nếu còn phương án hợp lệ thiếu tiền. Ghi nhận người phê duyệt, căn cứ và duyệt cấp trưởng bộ phận khi vượt hạn mức. Sau xử lý, ghi chi phí/phút chờ/km thực tế và chứng từ. Báo cáo tính chênh lệch thực tế − dự kiến và thời gian lập bảng → duyệt trên tối đa 50 bảng gần nhất; không tự kết luận giảm 20% hoặc ROI.

## Quy trình chung 3.3.6
Tiếp nhận → xác minh → kiểm tra chuyến và GPS → lập phương án, kiểm tra điều kiện → so sánh chi phí → ghi nhận phê duyệt → phiên bản lệnh → nhận/xác nhận → thực hiện → theo dõi, đối chiếu thực tế. Dữ liệu TMS/GPS/ONP nhập qua Field Mapping và xác nhận; nguồn API chỉ đọc khi đã cấp quyền. Hồ sơ, lịch sử và phê duyệt nằm trong SQLite; Render miễn phí /tmp chưa lưu bền vững. Cần cơ sở dữ liệu bền vững, phân quyền người dùng và kênh TMS/lái xe trước khi triển khai doanh nghiệp chính thức.

## Định dạng chứng từ
Quy tắc đọc các dòng nhãn như Booking, Tên tàu/Vessel, Chuyến tàu/Voyage, ETA/ETD, Cut-off, Điểm lấy/Pickup, Điểm giao/Delivery, Container, Phương tiện, Sự cố, Trạng thái/Status. Ngày giờ ISO cần múi giờ, ví dụ `2026-10-21T14:00:00+07:00`. Không đoán ngày mơ hồ. Tệp tối đa 2 MB, PDF tối đa 30 trang; PDF scan cần OCR trước. AI có thể đọc câu tự nhiên nhưng kết quả luôn cần người kiểm tra. Chưa kiểm chứng kết nối tài khoản IMAP/OpenAI doanh nghiệp thật; bộ kiểm thử dùng adapter giả lập.

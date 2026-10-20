# Đưa U&I Real-Time Dispatch AI lên Render (bản demo GVHD)

## Bản triển khai này có gì?
- Bảo vệ website, tệp frontend và API bằng tài khoản/mật khẩu HTTP Basic khi `APP_ENV=production`.
- `/health` chỉ trả về trạng thái tối thiểu để Render kiểm tra dịch vụ.
- Không bật kết nối TMS/GPS/ONP; chỉ sử dụng dữ liệu giả lập.
- Không có lệnh điều xe thật ra doanh nghiệp.
- Dữ liệu SQLite đặt ở `/tmp`, phù hợp bản demo miễn phí nhưng có thể bị xóa khi khởi động lại/triển khai lại. Dữ liệu không được đảm bảo lưu lâu dài.

## Cách triển khai dành cho người mới

1. Giải nén ZIP và mở thư mục `ui-dispatch-ai`.
2. Tạo tài khoản tại https://github.com/ rồi tạo repository mới, ví dụ `ui-real-time-dispatch-ai`.
3. Tải **các tệp bên trong** thư mục `ui-dispatch-ai` lên repository (không tải cả thư mục lồng thêm một cấp). Đảm bảo `render.yaml`, `requirements.txt`, `backend/` và `frontend/` nằm ngay ở thư mục gốc của repository.
4. Không tải `.env`, file SQLite thật, token hay dữ liệu vận tải của công ty lên GitHub. `.gitignore` đã loại trừ `.env` và các file SQLite trong `data/`.
5. Mở https://dashboard.render.com/ và đăng nhập bằng GitHub.
6. Chọn **New + → Blueprint**, chọn repository vừa tạo. Render đọc cấu hình `render.yaml` và tạo dịch vụ.
7. Khi Render hỏi hai biến bí mật `DEMO_USERNAME` và `DEMO_PASSWORD`, nhập tên đăng nhập và mật khẩu riêng. Dùng mật khẩu dài, khó đoán, không dùng mật khẩu tài khoản cá nhân. Nếu Blueprint tạo dịch vụ trước khi hỏi biến, vào **Dashboard → dịch vụ → Environment → Add Environment Variable** và thêm cả hai biến, rồi lưu/triển khai lại.
8. Chờ Build/Deploy kết thúc với trạng thái **Live**. Mở URL `https://...onrender.com` được hiển thị trên trang dịch vụ.
9. Trình duyệt sẽ hiện hộp yêu cầu tên đăng nhập/mật khẩu. Nhập thông tin vừa đặt. Sau đó thử các mục Tổng quan, Điều phối, Cảnh báo, Báo cáo và Nguồn dữ liệu.
10. Mở `https://TEN-MIEN.onrender.com/health` để kiểm tra. Kết quả mong đợi: `{"status":"ok"}`. Không gửi đường dẫn này thay cho trang web cho GVHD; gửi URL gốc và cung cấp tài khoản demo riêng.

## Giới hạn cần biết
- Gói miễn phí có thể đưa dịch vụ vào trạng thái ngủ sau thời gian không hoạt động; lần mở đầu có thể chậm.
- Dữ liệu mẫu và các thay đổi trong buổi chấm có thể mất sau khi khởi động lại hoặc triển khai lại. Dùng chức năng khôi phục dữ liệu mẫu để chuẩn bị buổi demo.
- Tài khoản HTTP Basic là cách bảo vệ đơn giản cho bản trình diễn nhỏ, không phải hệ thống tài khoản nhiều người dùng. Không dùng với dữ liệu nhạy cảm hay dữ liệu thật của U&I.
- Không bật `TMS_READ_ENABLED`, `GPS_READ_ENABLED` hoặc `ONP_READ_ENABLED`, không nhập token doanh nghiệp vào bản demo.
- Khi kết thúc buổi chấm, có thể tạm dừng hoặc xóa dịch vụ trong Render.

## Nếu Build lỗi
- Mở dịch vụ trên Render → **Logs** → **Build Logs** hoặc **Deploy Logs**.
- Kiểm tra repository có `requirements.txt` ở thư mục gốc.
- Kiểm tra lệnh chạy là `uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT`.
- Kiểm tra đã nhập cả `DEMO_USERNAME` và `DEMO_PASSWORD`.
- Không chia sẻ mật khẩu hoặc token trong ảnh chụp log công khai.

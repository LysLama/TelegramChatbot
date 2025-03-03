# Chatbot Telegram Đa Năng

Đây là một chatbot Telegram tích hợp nhiều tính năng đa dạng nhằm mang lại trải nghiệm tương tác linh hoạt giữa người dùng và bot qua cả âm thanh lẫn văn bản. Chatbot hỗ trợ đa ngôn ngữ (tiếng Anh, tiếng Việt, Malaysia), tích hợp xác thực người dùng và quản lý phiên hội thoại mượt mà.

## Tính Năng Chính

- **Phản Hồi Văn Bản & Âm Thanh**  
  - *Test v5:* Cung cấp phản hồi dưới dạng audio và text, tự động xóa file dữ liệu sau khi sử dụng để giảm dung lượng lưu trữ.

- **Giao Diện Tương Tác**  
  - *Test v6:* Thêm inline keyboard cho phép người dùng chọn giữa chế độ audio và text, đồng thời hỗ trợ tiếng Việt.
  - *Test v12:* Tự động chuyển đổi giữa audio và text sau khi đã trả kết quả. Ẩn nút inline keyboard sau khi người dùng bấm và hiển thị lại khi có kết quả mới, loại bỏ lệnh /start và /stop không cần thiết.

- **Cải Tiến Giao Diện & Định Dạng Phản Hồi**  
  - *Test v7:* Sửa lỗi định dạng phản hồi.
  - *Test v8:* Thêm hiệu ứng loading khi phản hồi đang được xử lý và cho phép đoạn chat liên tục mượt mà mà không cần khởi động lại bằng /start.

- **Quản Lý Phiên Hội Thoại & Token**  
  - *Test v9:* Loại bỏ URL khỏi audio, giới hạn số token, và thêm tính năng /stop để kết thúc hội thoại khi cần.
  - *Test v13:* Thêm nút refresh token và gia hạn thời gian xử lý phản hồi để tránh lỗi time out.
  - *Test v16:* Cải tiến audio bằng cách xóa thông tin "token còn lại" và xử lý lỗi time out.

- **Quản Lý Tập Tin & Tốc Độ Audio**  
  - *Test v10:* Tự động xóa file sau 5 phút và đặt tốc độ audio mặc định là 1.5x.

- **Xác Thực & Lưu Trữ Người Dùng**  
  - *Test v14:* Lưu trữ dữ liệu người dùng thông qua hệ thống đăng nhập và đăng ký, đảm bảo bảo mật và cá nhân hóa trải nghiệm.

- **Hỗ Trợ Đa Ngôn Ngữ**  
  - *Test v15:* Cho phép người dùng chuyển đổi giữa các ngôn ngữ khác nhau, bao gồm tiếng Anh, tiếng Việt và Malaysia.

## Cài Đặt

1. **Clone Repository:**

   ```bash
   git clone https://github.com/AI-telegram-TTS/telegram-ai/tree/API-Telegram
   cd API-Telegram
   ```

2. **Cài Đặt Dependencies:**

   Cài đặt các thư viện cần thiết (ví dụ: `python-telegram-bot`, `gTTS`, ...):

   ```bash
   pip install -r requirements.txt
   ```

## Hướng Dẫn Sử Dụng

- **Khởi Động Bot:**  
  Chạy file chính của dự án (ví dụ: `testv16.py`). Chatbot sẽ tự động kích hoạt chế độ hội thoại khi nhận được tương tác từ người dùng.

- **Chọn Chế Độ Phản Hồi:**  
  Khi người dùng bắt đầu tương tác, inline keyboard sẽ hiện ra cho phép lựa chọn giữa phản hồi dạng âm thanh hoặc văn bản.

- **Tương Tác Liên Tục:**  
  Chatbot hỗ trợ hội thoại liên tục, chuyển đổi giữa phản hồi âm thanh và văn bản một cách mượt mà mà không cần dùng lệnh /start hay /stop.

- **Xác Thực Người Dùng:**  
  Người dùng có thể đăng nhập hoặc đăng ký để lưu trữ dữ liệu cá nhân, giúp cải thiện trải nghiệm tương tác qua các phiên làm việc sau.

## Cấu Trúc Dự Án

- **testv5.py:** Tích hợp phản hồi audio và text cơ bản, tự động xóa file dữ liệu sau khi sử dụng.
- **testv6.py:** Thêm inline keyboard cho lựa chọn audio/text và hỗ trợ tiếng Việt.
- **testv7.py:** Sửa lỗi định dạng trong phản hồi.
- **testv8.py:** Thêm hiệu ứng loading và cho phép hội thoại liên tục.
- **testv9.py:** Loại bỏ URL trong audio, giới hạn token và thêm lệnh /stop.
- **testv10.py:** Xóa file sau 5 phút và thiết lập tốc độ audio mặc định là 1.5x.
- **testv12.py:** Cải tiến chuyển đổi giữa audio và text, quản lý inline keyboard và loại bỏ các lệnh không cần thiết.
- **testv13.py:** Thêm nút refresh token và gia hạn thời gian xử lý để tránh time out.
- **testv14.py:** Thực hiện xác thực đăng nhập/đăng ký, lưu trữ dữ liệu người dùng.
- **testv15.py:** Hỗ trợ chuyển đổi đa ngôn ngữ.
- **testv16.py:** Loại bỏ hiển thị "token còn lại" trong audio và xử lý lỗi time out hiệu quả.

## Phát Triển & Góp Ý

Nếu bạn có bất kỳ ý kiến đóng góp hoặc vấn đề gì cần báo cáo, vui lòng tạo issue trên GitHub repository hoặc liên hệ qua email: [thanhlam211204@gmail.com](mailto:thanhlam211204@gmail.com)
[phanminhkhanh2004@gmail.com](mailto:phanminhkhanh2004@gmail.com)

## License

Thông tin về bản quyền và giấy phép sử dụng dự án.

---
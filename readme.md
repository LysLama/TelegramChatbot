Dưới đây là phiên bản cải tiến của file README.md, với cấu trúc rõ ràng, nội dung mạch lạc và hướng dẫn sử dụng cụ thể hơn:

---

# Chatbot Telegram Đa Năng

Chatbot Telegram Đa Năng là một giải pháp tương tác thông minh tích hợp đa dạng tính năng, cho phép người dùng trải nghiệm hội thoại linh hoạt qua cả văn bản và âm thanh. Với hỗ trợ đa ngôn ngữ (Tiếng Anh, Tiếng Việt, Malaysia) cùng chức năng xác thực và quản lý phiên làm việc, chatbot này hứa hẹn mang lại trải nghiệm mượt mà và an toàn cho người dùng.

---

## Mục Lục

- [Giới Thiệu](#giới-thiệu)
- [Tính Năng Nổi Bật](#tính-năng-nổi-bật)
- [Cài Đặt](#cài-đặt)
- [Hướng Dẫn Sử Dụng](#hướng-dẫn-sử-dụng)
- [Cấu Trúc Dự Án](#cấu-trúc-dự-án)
- [Phát Triển & Góp Ý](#phát-triển--góp-ý)
- [License](#license)

---

## Giới Thiệu

Dự án này được thiết kế nhằm mang đến một trải nghiệm hội thoại tự nhiên và trực quan trên nền tảng Telegram. Chatbot không chỉ trả lời dưới dạng văn bản mà còn hỗ trợ phản hồi bằng âm thanh với các hiệu ứng loading và chuyển đổi chế độ mượt mà, giúp tối ưu hóa quá trình tương tác giữa người dùng và bot.

---

## Tính Năng Nổi Bật

- **Phản Hồi Văn Bản & Âm Thanh**
  - *Test v5:* Trả lời đồng thời dưới dạng text và audio, với cơ chế tự động xóa file dữ liệu sau khi sử dụng nhằm tiết kiệm bộ nhớ.

- **Giao Diện Tương Tác Thông Minh**
  - *Test v6:* Tích hợp inline keyboard cho phép người dùng lựa chọn giữa chế độ phản hồi âm thanh hoặc văn bản, đồng thời hỗ trợ tiếng Việt.
  - *Test v12:* Tự động chuyển đổi giữa audio và text sau khi trả kết quả,testv17.py
   ```

   Chatbot sẽ tự động kích hoạt và chờ tương tác từ người dùng.

2. **Chọn Chế Độ Phản Hồi:**  
   - Khi bắt đầu tương tác, inline keyboard sẽ hiển thị để bạn lựa chọn giữa phản hồi dạng âm thanh hoặc văn bản.
   - Sau khi lựa chọn, bot sẽ xử lý yêu cầu và chuyển đổi giữa các chế độ một cách mượt mà.

3. **Tiếp Tục Hội Thoại:**  
   - Chatbot hỗ trợ hội thoại liên tục, không cần khởi động lại bằng lệnh /start hay /stop.
   - Sử dụng lệnh /stop khi cần kết thúc phiên hội thoại.

4. **Xác Thực & Lưu Trữ:**  
   - Người dùng có thể đăng nhập hoặc đăng ký để lưu trữ dữ liệu cá nhân, giúp cải thiện trải nghiệm qua các phiên làm việc sau.

---

## Cấu Trúc Dự Án

Dự án được chia thành các file mã nguồn với từng phiên bản cải tiến riêng biệt:

- **testv5.py:** Phản hồi cơ bản bằng audio và text, kèm cơ chế tự động xóa file sau khi sử dụng.
- **testv6.py:** Thêm inline keyboard cho lựa chọn giữa audio và text, hỗ trợ tiếng Việt.
- **testv7.py:** Sửa lỗi định dạng trong phản hồi.
- **testv8.py:** Thêm hiệu ứng loading và hỗ trợ hội thoại liên tục.
- **testv9.py:** Loại bỏ URL trong audio, giới hạn token và tích hợp lệnh /stop.
- **testv10.py:** Tự động xóa file sau 5 phút và thiết lập tốc độ audio mặc định là 1.5x.
- **testv12.py:** Cải tiến chuyển đổi giữa audio và text, quản lý inline keyboard hiệu quả.
- **testv13.py:** Thêm nút refresh token và kéo dài thời gian xử lý để tránh lỗi time out.
- **testv14.py:** Tích hợp chức năng đăng nhập/đăng ký và lưu trữ dữ liệu người dùng.
- **testv15.py:** Hỗ trợ chuyển đổi đa ngôn ngữ.
- **testv16.py:** Cải tiến hiển thị audio và xử lý lỗi time out.
- **testv17.py:** Cập nhật tính năng voice chat.

---

## Phát Triển & Góp Ý

Chúng tôi luôn trân trọng những ý kiến đóng góp để cải thiện dự án. Nếu bạn có bất kỳ thắc mắc, góp ý hay báo cáo lỗi, hãy:

- Tạo **Issue** trên GitHub repository.
- Liên hệ qua email:
  - [thanhlam211204@gmail.com](mailto:thanhlam211204@gmail.com)
  - [phanminhkhanh2004@gmail.com](mailto:phanminhkhanh2004@gmail.com)

---

## License

Thông tin về bản quyền và giấy phép sử dụng dự án được cung cấp trong file LICENSE (nếu có). Vui lòng tham khảo file này để biết thêm chi tiết về quyền sử dụng và phân phối.

---

Với cấu trúc được sắp xếp khoa học cùng hướng dẫn cài đặt và sử dụng chi tiết, README này hi vọng sẽ giúp người dùng nhanh chóng làm quen và khai thác tối đa các tính năng của Chatbot Telegram Đa Năng.

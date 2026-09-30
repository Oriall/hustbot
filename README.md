# HUSTBot - Trợ lý AI Bách Khoa (HUST)

> ### Xây dựng trợ lý AI cho sinh viên Đại học Bách khoa Hà Nội 

---
> [!IMPORTANT]
>
> Dự án này ban đầu được tạo ra không nhằm mục đích kiếm tiền, chỉ phục vụ nghiên cứu và học tập
> 
> **Cập nhật lớn (2026/09):**
> - Kết nối Gemini API để bot chat thật, thay cho khung sườn dữ liệu mẫu
> - Thêm system prompt riêng cho HUSTBot, kèm ngữ cảnh cá nhân (CPA, điểm rèn luyện, deadline, thời khóa biểu)
> - Cập nhật UI/UX: chuyển trang mượt, scrollbar mới, hiệu ứng tin nhắn
> - Xem README để biết chi tiết và các thư viện cần cài


# Cài đặt
## Yêu cầu
* **Python 3.9 trở lên**
* **Đổi tên file `.env.example` thành `.env`**
* **Tạo thư mục: static/css và static/js (nếu chưa có)**
* Chạy `pip3 install -r requirements.txt` để cài các thư viện cần thiết
---


> [!CAUTION]
> Luôn kiểm tra lại quy chế, điểm số và thủ tục với nguồn chính thức của trường
> Dự án này ban đầu được tạo ra không nhằm mục đích kiếm tiền, chỉ phục vụ nghiên cứu và học tập
>

## S: Chạy bot trên máy tính

0. Tạo file `.env` và điền `GEMINI_API_KEY`

1. Mở terminal hoặc command prompt

2. Di chuyển đến thư mục chứa dự án HUSTBot

3. Chạy `python3 app.py` hoặc `python app.py`, sau đó mở trình duyệt tại `http://127.0.0.1:5000`
---

### Chúc bạn trò chuyện vui vẻ!
---


## Tùy chọn: Cấu hình Gemini API

Để dùng các tính năng của Gemini API, làm theo các bước sau:

1. Lấy API key tại https://aistudio.google.com/app/apikey?hl=vi
2. Dán tên biến `GEMINI_API_KEY` vào `.env`
3. (Tùy chọn) Đổi model bằng biến `GEMINI_MODEL` (mặc định: `gemini-2.5-flash`)

## Tùy chọn: Cấu hình kho kiến thức (KB)

Để bot trả lời đúng quy chế của trường, làm theo các bước sau:

1. Chuẩn bị nội dung chính thức từ Sổ tay sinh viên hoặc https://ctsv.hust.edu.vn
2. Mở **app.py**, tìm biến `KB`
3. Thêm mục mới gồm `keys` (từ khóa), `src` (nguồn) và `ans` (nội dung)

> [!NOTE]
> Gemini API có một số giới hạn sử dụng.
> 
> Xem thêm chi tiết tại https://ai.google.dev/gemini-api/docs/quickstart
## Tùy chọn: Thiết lập system prompt

   0. Mở file `gemini_bot.py` và chỉnh nội dung biến `SYSTEM_PROMPT`


------
>  [**SERVER DISCORD**](https://discord.gg/78TnsrJd)
------

> **Cảnh báo**
>
> Bot có thể đưa ra thông tin quy chế chưa chính xác hoặc đã lỗi thời. Hãy đối chiếu với Phòng Đào tạo và Phòng Công tác sinh viên trước khi làm theo.


   > **Cảnh báo**
   > Bot hiện chỉ đang trong giai đoạn thử nghiệm, nên có thể gặp một số lỗi, đang được cập nhật và sẽ tiếp tục được cập nhật trong tương lai.
 ---
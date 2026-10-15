# HUSTBot - Trợ lý AI Bách Khoa (HUST)

> ### Trợ lý AI và bảng điều khiển học tập cho sinh viên Đại học Bách khoa Hà Nội

HUSTBot gom deadline, thời khóa biểu, điểm rèn luyện, học bổng và tiến độ chương trình đào tạo vào một nơi, kèm một trợ lý AI (Gemini) biết **đúng dữ liệu của chính bạn** để trả lời và thao tác thay bạn.

---
> [!IMPORTANT]
>
> Dự án này ban đầu được tạo ra không nhằm mục đích kiếm tiền, chỉ phục vụ nghiên cứu và học tập.
>
> **Cập nhật lớn (2026/10):**
> - **Đăng nhập theo MSSV**, dữ liệu lưu riêng cho từng sinh viên (SQLAlchemy, mặc định SQLite)
> - **Extension HUSTBot Connect**: gửi thời khóa biểu (qldt), chương trình đào tạo và bảng điểm (ctt-sis), học bổng (student) vào HUSTBot, không cần đưa mật khẩu hay cookie của trường cho server
> - **CPA tính từ bảng điểm thật** (`program_course`) và tự lưu vào `Student.cpa`, thay cho số nhập tay
> - **Trợ lý AI dạng agent**: Gemini gọi công cụ để xem deadline, lịch học, điểm rèn luyện, học bổng, tiến độ chương trình, đăng ký hoạt động, đánh dấu hoàn thành bài tập
> - **Trang Tổng quan mới** (orbital HUD): 6 node quanh lõi CPA/ĐRL, bảng chi tiết mở/đóng/phóng to, terminal nhỏ ghi lại thao tác, thanh đồng bộ nhanh
> - Giao diện extension được làm lại theo phong cách của HUSTBot

---

# Tính năng

| Trang | Đường dẫn | Nội dung |
|---|---|---|
| Tổng quan | `/` | Lõi CPA và điểm rèn luyện, deadline gấp, ca học hôm nay, học bổng đang mở, áp lực học tập trong tuần, trợ lý AI |
| Bài tập và bài thi | `/bai-tap` | Danh sách theo hạn nộp, đánh dấu hoàn thành |
| Trợ lý AI Bách Khoa | `/tro-ly-ai` | Chat với agent (ngoài ra có khung chat nổi ở mọi trang) |
| Điểm rèn luyện và hoạt động | `/diem-ren-luyen` | Điểm theo tiêu chí, điểm dự kiến, đăng ký hoạt động |
| Thời khóa biểu | `/thoi-khoa-bieu` | Lịch tuần T2 đến CN |
| Đăng nhập | `/dang-nhap` | Đăng nhập bằng MSSV và mật khẩu |

**Trợ lý AI có thể làm gì?** Mỗi lần bạn hỏi, Gemini được cấp một bộ công cụ gắn cố định với tài khoản đang đăng nhập:

- Xem và đánh dấu hoàn thành bài tập (`list_tasks`, `set_task_done`)
- Xem thời khóa biểu (`get_class_schedule`)
- Xem điểm rèn luyện, liệt kê và đăng ký hoạt động (`get_conduct_summary`, `list_events`, `register_event`)
- Xem học bổng và chi tiết từng học bổng (`list_awards`, `get_award_detail`)
- Xem tiến độ chương trình đào tạo, môn còn lại, tính CPA giả định (`get_program_summary`, `list_program_courses`)
- Tra cứu kho kiến thức quy chế (`search_knowledge_base`) và chuyển trang (`navigate_to`)

Công cụ không có tham số `student_id`: mã sinh viên lấy từ session đăng nhập, nên AI (kể cả khi bị prompt injection) không thể đọc hay ghi dữ liệu của người khác.

---

# Cài đặt

## Yêu cầu

* **Python 3.9 trở lên**
* **Trình duyệt Chrome hoặc Edge** (để cài extension HUSTBot Connect)
* **Đổi tên file `.env.example` thành `.env`**
* **Tạo thư mục `static/css` và `static/js` (nếu chưa có)**
* Chạy `pip3 install -r requirements.txt` để cài các thư viện cần thiết

---

> [!CAUTION]
> Luôn kiểm tra lại quy chế, điểm số và thủ tục với nguồn chính thức của trường.
> Dự án này ban đầu được tạo ra không nhằm mục đích kiếm tiền, chỉ phục vụ nghiên cứu và học tập.

## Cấu hình `.env`

| Biến | Bắt buộc | Ý nghĩa |
|---|---|---|
| `GEMINI_API_KEY` | Có | API key Gemini, lấy tại https://aistudio.google.com/app/apikey?hl=vi |
| `GEMINI_MODEL` | Không | Model Gemini (mặc định `gemini-2.5-flash`) |
| `SECRET_KEY` | Nên đặt | Khóa ký session. **Phải đổi khi triển khai thật** (giá trị mặc định chỉ dùng để phát triển) |
| `DATABASE_URL` | Không | Mặc định `sqlite:///hustbot.db` |
| `TOKEN_ENC_KEY` | Có | Khóa mã hóa dùng cho phần kết nối extension và học bổng. Giá trị mẫu xem trong `.env.example` |

> [!NOTE]
> `.env` được nạp trước khi import `connect` và `awards` vì hai module này đọc `TOKEN_ENC_KEY` ngay lúc import. Nếu thiếu biến này, server sẽ không khởi động được.

## Chạy bot trên máy tính

1. Tạo file `.env` và điền các biến ở bảng trên (ít nhất `GEMINI_API_KEY` và `TOKEN_ENC_KEY`)
2. Mở terminal, di chuyển đến thư mục chứa dự án HUSTBot
3. Chạy `python3 app.py` (hoặc `python app.py`)
4. Mở trình duyệt tại `http://127.0.0.1:5000` và đăng nhập

Lần chạy đầu tiên, `db.create_all()` tạo bảng và `seed_if_empty()` thêm dữ liệu mẫu (tài khoản demo, tiêu chí điểm rèn luyện, sự kiện, kho kiến thức). Tài khoản demo xem trong `seed.py`.

> [!NOTE]
> `db.create_all()` chỉ tạo bảng mới, **không thêm cột vào bảng đã có**. Nếu sau này bạn thêm cột vào model, hãy dùng migration hoặc `ALTER TABLE`, hoặc xóa file `instance/hustbot.db` để tạo lại khi đang thử nghiệm.

---

# Extension HUSTBot Connect

Extension chạy ngay trong trình duyệt của bạn: chỉ đọc nội dung trang trường đang mở rồi gửi lên HUSTBot khi bạn bấm nút. **Không lấy cookie hay token của trường**, và server HUSTBot không bao giờ giữ thông tin đăng nhập của trường.

## Cài extension

1. Mở `chrome://extensions` (hoặc `edge://extensions`)
2. Bật **Chế độ dành cho nhà phát triển** (Developer mode)
3. Bấm **Tải tiện ích đã giải nén** (Load unpacked) và chọn thư mục extension của dự án
4. Nếu HUSTBot chạy ở địa chỉ khác `http://localhost:5000`, thêm địa chỉ đó vào `host_permissions` trong `manifest.json` rồi tải lại extension

## Ghép nối với tài khoản

1. Đăng nhập web HUSTBot, ở trang Tổng quan bấm **Kết nối** (thanh phía dưới) để tạo **mã ghép nối**. Mã có hiệu lực **10 phút**
2. Mở popup của extension, điền địa chỉ HUSTBot và dán mã ghép nối
3. Mã chỉ được giữ đến khi bạn đóng trình duyệt

## Ba loại dữ liệu có thể gửi

| Nút trong popup | Mở trang nào trước | Dữ liệu được cập nhật |
|---|---|---|
| Gửi thời khóa biểu tuần này | `qldt.hust.edu.vn` → Thời khóa biểu → tab **Lịch** | Thời khóa biểu T2 đến CN |
| Gửi chương trình đào tạo | `ctt-sis.hust.edu.vn` (bung các nhóm học phần) | Chương trình đào tạo, điểm từng môn, **CPA** |
| Gửi học bổng | `student.hust.edu.vn` (hoặc qldt, đã đăng nhập) | Danh sách học bổng đang mở |

Mục **Nâng cao** trong popup có ô `userIds` cho học bổng. Bình thường extension tự tìm được, chỉ nhập tay khi có thông báo yêu cầu.

## CPA được tính như thế nào?

Sau khi bạn gửi chương trình đào tạo, HUSTBot tính CPA từ bảng điểm theo từng học phần:

- Công thức: `Σ(tín chỉ × điểm hệ 4) / Σ tín chỉ` của các môn đã có điểm
- Không tính các môn thể chất và quốc phòng (mã bắt đầu bằng `PE`, `MIL`); chỉnh trong `CPA_EXCLUDE_PREFIXES` ở `program_clean.py` nếu mã môn của bạn khác
- Mỗi môn chỉ tính một lần (giữ điểm cao nhất)
- Kết quả được lưu vào `Student.cpa` cùng lúc với bảng điểm. Chưa có môn nào có điểm thì giữ nguyên CPA cũ

> [!NOTE]
> Đây là CPA **ước tính**. Hãy đối chiếu với bảng điểm chính thức trên ctt-sis.

---

# Cấu trúc dự án

```
app.py              Flask app: trang, đăng nhập, API, công cụ của agent
models.py           Student, Task, ScheduleItem, ConductScore, Event, KBEntry...
seed.py             Dữ liệu mẫu cho lần chạy đầu tiên
gemini_bot.py       Gọi Gemini, chứa SYSTEM_PROMPT
connect.py          Ghép nối extension, đồng bộ thời khóa biểu / LMS
awards.py           Học bổng (đồng bộ từ extension)
program.py          Chương trình đào tạo và CPA (ProgramCourse)
program_clean.py    Kiểm tra và làm sạch dữ liệu extension gửi lên, tính CPA
templates/          Giao diện (base, overview, assignments, ...)
static/css/         overview.css và các file CSS khác
static/js/          connect.js, agent.js, ...
```

Mọi dữ liệu cá nhân đều có cột `student_id` và **mọi truy vấn đều lọc theo cột này**. Dữ liệu dùng chung (tiêu chí điểm rèn luyện, sự kiện, kho kiến thức) thì mọi sinh viên thấy như nhau.

---

## Tùy chọn: Cấu hình Gemini API

1. Lấy API key tại https://aistudio.google.com/app/apikey?hl=vi
2. Thêm dòng `GEMINI_API_KEY=...` vào `.env`
3. (Tùy chọn) Đổi model bằng biến `GEMINI_MODEL` (mặc định: `gemini-2.5-flash`)

> [!NOTE]
> Gemini API có một số giới hạn sử dụng.
> Xem thêm chi tiết tại https://ai.google.dev/gemini-api/docs/quickstart

## Tùy chọn: Cấu hình kho kiến thức (KB)

Kho kiến thức nằm trong bảng `KBEntry` của cơ sở dữ liệu (không còn là biến `KB` trong `app.py`). Để bot trả lời đúng quy chế của trường:

1. Chuẩn bị nội dung chính thức từ Sổ tay sinh viên hoặc https://ctsv.hust.edu.vn
2. Thêm bản ghi mới vào `KBEntry` (ví dụ thêm vào dữ liệu mẫu trong `seed.py`) gồm:
   - `keys`: danh sách từ khóa viết thường, bot khớp khi câu hỏi chứa một trong các từ này
   - `src`: nguồn (ví dụ tên văn bản, điều khoản)
   - `ans`: nội dung trả lời
3. Nếu `seed_if_empty()` chỉ chạy khi bảng trống, hãy thêm trực tiếp vào database hoặc xóa file database để tạo lại

## Tùy chọn: Thiết lập system prompt

Mở file `gemini_bot.py` và chỉnh nội dung biến `SYSTEM_PROMPT`.

## Tùy chọn: Điểm rèn luyện và sự kiện

Tiêu chí và sự kiện là dữ liệu dùng chung (`Criterion`, `Event`). Mỗi sinh viên có điểm riêng theo từng tiêu chí (`ConductScore`) và danh sách sự kiện đã đăng ký (`EventRegistration`). Mốc xếp loại **Xuất sắc** đặt ở `EXCELLENT = 90` trong `app.py`.

---

# Bảo mật và quyền riêng tư

- Mật khẩu được băm (`werkzeug.security`), session được ký và đặt `HttpOnly`, `SameSite=Lax`
- Khi triển khai thật: **đổi `SECRET_KEY`**, tắt `debug=True` và chạy sau HTTPS
- Extension xác thực bằng mã ghép nối ngắn hạn (10 phút), không dùng cookie của HUSTBot
- Dữ liệu từ extension luôn bị coi là không đáng tin: server kiểm tra cấu trúc, ép kiểu và cắt độ dài trước khi lưu
- Bạn có thể xóa dữ liệu điểm đã đồng bộ qua `DELETE /api/program`

---
> **Cộng đồng:** [**SERVER DISCORD**](https://discord.gg/78TnsrJd)
---

> [!WARNING]
> Bot có thể đưa ra thông tin quy chế chưa chính xác hoặc đã lỗi thời. Hãy đối chiếu với Phòng Đào tạo và Phòng Công tác sinh viên trước khi làm theo.

> [!WARNING]
> Bot hiện chỉ đang trong giai đoạn thử nghiệm, nên có thể gặp một số lỗi. Dự án đang được cập nhật và sẽ tiếp tục được cập nhật trong tương lai.

### Chúc bạn trò chuyện vui vẻ!
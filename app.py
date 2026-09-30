from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)
NOW = datetime.now()
from dotenv import load_dotenv
load_dotenv()
import gemini_bot
SOURCES = {"teams": "MS Teams", "fami": "FAMI Số hóa", "lms": "LMS HUST", "moocai": "MoocAI"}

# Dữ liệu mẫu: thay bằng dữ liệu thật khi có backend/crawler.
def _t(i, code, course, title, src, mins, kind, weight, extra, note, teacher, cls, dept, specs, digest, formulas, cta):
    return dict(id=i, code=code, course=course, title=title, source=src, mins=mins, kind=kind, weight=weight,
                extra=extra, note=note, teacher=teacher, cls=cls, dept=dept, specs=specs, digest=digest,
                formulas=formulas, cta=cta)

# Dữ liệu mẫu: thay bằng dữ liệu thật khi có backend/crawler.
_TASKS = [
    _t(1, "PH1110", "Vật lý đại cương 1", "Kiểm tra giữa kỳ - Trắc nghiệm 30 phút", "teams", 135, "Thi giữa kỳ", 30,
       "Lớp 142857", "Bắt buộc bật camera MS Teams", "PGS. TS. Lê Văn Thành", "142857 (K67 KHMT)", "Viện Vật lý Kỹ thuật",
       [("Thời lượng", "30 phút", "Tự động nộp khi hết giờ"), ("Cấu trúc đề", "20 câu", "Hệ số 3.0 (30% tổng kết)"),
        ("Giám sát thi", "Phòng 402-A1", "Bật webcam MS Teams"), ("Kết nối hệ thống", "Sẵn sàng", "Đã đồng bộ link và đề")],
       [("Trọng tâm kiến thức", ["15 câu lý thuyết từ trường (Chương 4, 5).", "5 câu tính nhanh thông lượng từ và suất điện động cảm ứng."]),
        ("Quy chế thi trực tuyến", ["Có mặt trên MS Teams trước giờ thi 10 phút để điểm danh camera.", "Đặt tên hiển thị: MSSV - Họ và Tên.", "Chỉ dùng máy tính bỏ túi trong danh mục cho phép."])],
       [("Suất điện động cảm ứng", "e = - dΦ/dt"), ("Từ trường ống dây vô hạn", "B = μ₀·μ·n·I"), ("Năng lượng từ trường", "W = ½·L·I²")],
       "Vào phòng thi và mở bài MS Teams"),
    _t(2, "MI3120", "Giải tích 2", "Bài tập tuần 6: Tích phân đường và mặt", "teams", 720, "Bài tập tuần", 10,
       "TS. Nguyễn Thế Khôi", "File PDF dưới 20MB", "TS. Nguyễn Thế Khôi", "MI3120.03", "Viện Toán ứng dụng",
       [("Hình thức", "Nộp PDF", "Dưới 20MB"), ("Trọng số", "10%", "Điểm quá trình"), ("Nhóm", "Cá nhân", ""), ("Kết nối hệ thống", "Sẵn sàng", "Đã đồng bộ")],
       [("Yêu cầu nộp", ["Scan rõ nét, ghi họ tên và MSSV ở đầu trang.", "Đặt tên file theo mẫu MSSV_HoTen."])], [], "Mở bài nộp trên MS Teams"),
    _t(3, "MI1141", "Đại số tuyến tính", "Quiz Chương 3: Không gian Vector", "fami", 2880, "Quiz trắc nghiệm", 15,
       "K67", "Làm 2 lần, lấy điểm cao nhất", "TS. Phạm Văn Bình", "MI1141.05", "Viện Toán ứng dụng",
       [("Thời lượng", "20 phút", "Tự động nộp"), ("Trọng số", "15%", ""), ("Số lần làm", "2 lần", "Lấy điểm cao nhất"), ("Kết nối hệ thống", "Sẵn sàng", "Đã đồng bộ")],
       [("Nội dung", ["Không gian con, cơ sở và số chiều.", "Ánh xạ tuyến tính cơ bản."])], [], "Mở bài trên FAMI Số hóa"),
    _t(4, "IT3080", "Mạng máy tính", "Lab 3: Lập trình Socket TCP/IP và đa luồng", "lms", 4320, "Báo cáo thực hành", 20,
       "TS. Vũ Thành Trung", "Nộp mã nguồn + video demo", "TS. Vũ Thành Trung", "IT3080.02", "SoICT",
       [("Hình thức", "Mã nguồn + video", ""), ("Trọng số", "20%", ""), ("Nhóm", "Cá nhân", ""), ("Kết nối hệ thống", "Sẵn sàng", "Đã đồng bộ")],
       [("Yêu cầu nộp", ["Server và client chạy được đa luồng.", "Video demo tối đa 3 phút."])], [], "Mở bài nộp trên LMS HUST"),
    _t(5, "ET3220", "Hệ thống nhúng", "Bài tập lớn: Hệ thống IoT giám sát môi trường", "teams", 21600, "Đồ án / BTL", 0,
       "Nhóm 4 người", "", "ThS. Đỗ Minh Quân", "ET3220.01", "SoICT",
       [("Hình thức", "Báo cáo + demo", ""), ("Trọng số", "Xem đề cương", ""), ("Nhóm", "4 người", ""), ("Kết nối hệ thống", "Sẵn sàng", "Đã đồng bộ")],
       [("Yêu cầu", ["Thiết kế phần cứng và firmware.", "Báo cáo PDF kèm demo trực tiếp."])], [], "Mở bài nộp trên MS Teams"),
]
DONE_COUNT = 18

def _label(m):
    if m < 0: return "Quá hạn", "late"
    if m < 60: return "Còn %d phút" % m, "soon"
    if m < 1440: return "Còn %dh %02dm" % (m // 60, m % 60), "soon"
    return "Còn %d ngày" % (m // 1440), "later"

def get_tasks():
    out = []
    for t in _TASKS:
        label, level = _label(t["mins"])
        due = NOW + timedelta(minutes=t["mins"])
        txt = ("Hôm nay " + due.strftime("%H:%M")) if due.date() == NOW.date() else due.strftime("%d/%m/%Y • %H:%M")
        group = "urgent" if t["mins"] < 1440 else "week" if t["mins"] < 4 * 1440 else "later"
        out.append(dict(t, source_name=SOURCES[t["source"]], label=label, level=level, due=txt,
                        due_iso=due.isoformat(), group=group))
    return out

SCHEDULE = [
    (2, "06:45", "09:15", "Kỹ thuật lập trình", "IT3040", "D9-401"),
    (2, "12:30", "15:05", "Giải tích 2", "MI1121", "TC-205"),
    (3, "06:45", "09:15", "Vật lý đại cương 1", "PH1110", "D3-301"),
    (4, "12:30", "15:05", "Giải tích 2", "MI1121", "TC-205"),
    (4, "15:15", "17:00", "Thực hành Mạng máy tính", "IT3080", "B1-Lab 302"),
    (5, "09:20", "11:55", "Kỹ thuật điện", "EE2020", "D5-201"),
    (6, "06:45", "09:15", "Tin học đại cương", "IT1110", "B1-Lab 101"),
]

# Tiêu chí điểm rèn luyện (mẫu) - điểm hiện tại / tối đa
CRITERIA = [
    dict(id=1, name="Ý thức học tập", now=18, max=20),
    dict(id=2, name="Chấp hành nội quy, quy chế", now=25, max=25),
    dict(id=3, name="Hoạt động chính trị - xã hội", now=12, max=20),
    dict(id=4, name="Quan hệ cộng đồng", now=20, max=25),
    dict(id=5, name="Phụ trách lớp, đoàn thể", now=8, max=10),
]
EVENTS = [
    dict(id=1, name="Giọt hồng Bách Khoa - hiến máu", crit=3, pts=5, date="12/10/2026", place="Hội trường C2"),
    dict(id=2, name="Mùa hè xanh - tập huấn tình nguyện", crit=3, pts=3, date="18/10/2026", place="Nhà C1"),
    dict(id=3, name="Hội thảo định hướng nghề nghiệp", crit=4, pts=2, date="20/10/2026", place="D9-101"),
    dict(id=4, name="Sinh hoạt lớp đầu kỳ", crit=2, pts=2, date="05/10/2026", place="Theo lớp"),
    dict(id=5, name="Cuộc thi Olympic Toán", crit=1, pts=2, date="25/10/2026", place="Nhà D3"),
]

# Kho kiến thức mẫu cho chatbot. Thay bằng nội dung Sổ tay sinh viên / ctsv.hust.edu.vn.
KB = [
    dict(keys=["học bổng", "kkht"], src="Sổ tay sinh viên",
         ans="Học bổng KKHT xét theo điểm học tập và điểm rèn luyện của kỳ. Nội dung mẫu: hãy thay bằng điều khoản chính thức."),
    dict(keys=["hiến máu", "rèn luyện", "điểm rèn luyện"], src="ctsv.hust.edu.vn",
         ans="Hoạt động hiến máu tình nguyện thường được cộng vào nhóm tiêu chí hoạt động chính trị - xã hội. Xem tab Điểm rèn luyện để biết sự kiện phù hợp."),
    dict(keys=["toeic", "tiếng anh", "miễn"], src="Sổ tay sinh viên",
         ans="Điều kiện miễn học phần Tiếng Anh dựa trên chứng chỉ quy đổi. Nội dung mẫu: cần nạp quy chế chính thức."),
]

@app.context_processor
def inject_user():
    return dict(user=dict(name="Nguyễn Văn A", mssv="20210001", cls="K66 KHMT", cpa="3.65", drl=sum(c["now"] for c in CRITERIA)))

@app.route("/")
def overview():
    tasks = get_tasks()
    today = [s for s in SCHEDULE if s[0] == NOW.isoweekday() + 1]
    return render_template("overview.html", tasks=tasks[:3], all_count=len(tasks), today=today, now=NOW)

@app.route("/bai-tap")
def assignments():
    return render_template("assignments.html", tasks=get_tasks(), sources=SOURCES, done=DONE_COUNT)

@app.route("/tro-ly-ai")
def assistant():
    return render_template("assistant.html")

@app.route("/diem-ren-luyen")
def activities():
    return render_template("activities.html", criteria=CRITERIA, events=EVENTS)

@app.route("/thoi-khoa-bieu")
def schedule():
    monday = NOW - timedelta(days=NOW.weekday())
    week = {d: (monday + timedelta(days=d - 2)).strftime("%d/%m") for d in range(2, 8)}
    return render_template("schedule.html", days=range(2, 8), items=SCHEDULE,
                           today=NOW.isoweekday() + 1, week=week,
                           week_range="%s - %s" % (week[2], week[7]), now=NOW)
def _user():
    return dict(name="Nguyễn Văn A", mssv="20210001", cls="K66 KHMT", cpa="3.65",
                drl=sum(c["now"] for c in CRITERIA))

@app.context_processor
def inject_user():
    return dict(user=_user())

@app.post("/api/chat")
def chat():
    data = request.get_json(silent=True) or {}
    msg = (data.get("q") or "").strip()[:2000]
    if not msg:
        return jsonify(ans="Bạn hãy nhập câu hỏi nhé.", src=""), 400

    low = msg.lower()
    kb_hits = [k for k in KB if any(w in low for w in k["keys"])]
    today = [s for s in SCHEDULE if s[0] == datetime.now().isoweekday() + 1]

    try:
        ans = gemini_bot.ask(msg, data.get("history"), _user(),
                             tasks=get_tasks()[:5], today_schedule=today, kb_hits=kb_hits)
    except Exception:
        app.logger.exception("Gemini error")
        return jsonify(ans="Trợ lý đang bận hoặc gặp sự cố kết nối. Bạn thử lại sau ít phút nhé.", src=""), 502

    return jsonify(ans=ans, src=", ".join(k["src"] for k in kb_hits))
if __name__ == "__main__":
    app.run(debug=True)

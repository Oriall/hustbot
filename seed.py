"""Nạp dữ liệu mẫu lần đầu (2 sinh viên để kiểm tra dữ liệu không bị trộn lẫn).
Đăng nhập thử: 20210001 / 123456  và  20210002 / 123456"""
from datetime import datetime, timedelta

from models import (ConductScore, Criterion, Event, KBEntry, ScheduleItem, Student, Task, db)

TASKS = [
    ("PH1110", "Vật lý đại cương 1", "Kiểm tra giữa kỳ - Trắc nghiệm 30 phút", "teams", 135,
     "Thi giữa kỳ", 30, "Lớp 142857", "Bắt buộc bật camera MS Teams", "PGS. TS. Lê Văn Thành",
     "142857 (K67 KHMT)", "Viện Vật lý Kỹ thuật",
     [("Thời lượng", "30 phút", "Tự động nộp khi hết giờ"), ("Cấu trúc đề", "20 câu", "Hệ số 3.0 (30% tổng kết)"),
      ("Giám sát thi", "Phòng 402-A1", "Bật webcam MS Teams"), ("Kết nối hệ thống", "Sẵn sàng", "Đã đồng bộ link và đề")],
     [("Trọng tâm kiến thức", ["15 câu lý thuyết từ trường (Chương 4, 5).", "5 câu tính nhanh thông lượng từ và suất điện động cảm ứng."]),
      ("Quy chế thi trực tuyến", ["Có mặt trên MS Teams trước giờ thi 10 phút để điểm danh camera.", "Đặt tên hiển thị: MSSV - Họ và Tên.", "Chỉ dùng máy tính bỏ túi trong danh mục cho phép."])],
     [("Suất điện động cảm ứng", "e = - dΦ/dt"), ("Từ trường ống dây vô hạn", "B = μ₀·μ·n·I"), ("Năng lượng từ trường", "W = ½·L·I²")],
     "Vào phòng thi và mở bài MS Teams"),
    ("MI3120", "Giải tích 2", "Bài tập tuần 6: Tích phân đường và mặt", "teams", 720, "Bài tập tuần", 10,
     "TS. Nguyễn Thế Khôi", "File PDF dưới 20MB", "TS. Nguyễn Thế Khôi", "MI3120.03", "Viện Toán ứng dụng",
     [("Hình thức", "Nộp PDF", "Dưới 20MB"), ("Trọng số", "10%", "Điểm quá trình"), ("Nhóm", "Cá nhân", ""), ("Kết nối hệ thống", "Sẵn sàng", "Đã đồng bộ")],
     [("Yêu cầu nộp", ["Scan rõ nét, ghi họ tên và MSSV ở đầu trang.", "Đặt tên file theo mẫu MSSV_HoTen."])], [],
     "Mở bài nộp trên MS Teams"),
    ("MI1141", "Đại số tuyến tính", "Quiz Chương 3: Không gian Vector", "fami", 2880, "Quiz trắc nghiệm", 15,
     "K67", "Làm 2 lần, lấy điểm cao nhất", "TS. Phạm Văn Bình", "MI1141.05", "Viện Toán ứng dụng",
     [("Thời lượng", "20 phút", "Tự động nộp"), ("Trọng số", "15%", ""), ("Số lần làm", "2 lần", "Lấy điểm cao nhất"), ("Kết nối hệ thống", "Sẵn sàng", "Đã đồng bộ")],
     [("Nội dung", ["Không gian con, cơ sở và số chiều.", "Ánh xạ tuyến tính cơ bản."])], [],
     "Mở bài trên FAMI Số hóa"),
    ("IT3080", "Mạng máy tính", "Lab 3: Lập trình Socket TCP/IP và đa luồng", "lms", 4320, "Báo cáo thực hành", 20,
     "TS. Vũ Thành Trung", "Nộp mã nguồn + video demo", "TS. Vũ Thành Trung", "IT3080.02", "SoICT",
     [("Hình thức", "Mã nguồn + video", ""), ("Trọng số", "20%", ""), ("Nhóm", "Cá nhân", ""), ("Kết nối hệ thống", "Sẵn sàng", "Đã đồng bộ")],
     [("Yêu cầu nộp", ["Server và client chạy được đa luồng.", "Video demo tối đa 3 phút."])], [],
     "Mở bài nộp trên LMS HUST"),
    ("ET3220", "Hệ thống nhúng", "Bài tập lớn: Hệ thống IoT giám sát môi trường", "teams", 21600, "Đồ án / BTL", 0,
     "Nhóm 4 người", "", "ThS. Đỗ Minh Quân", "ET3220.01", "SoICT",
     [("Hình thức", "Báo cáo + demo", ""), ("Trọng số", "Xem đề cương", ""), ("Nhóm", "4 người", ""), ("Kết nối hệ thống", "Sẵn sàng", "Đã đồng bộ")],
     [("Yêu cầu", ["Thiết kế phần cứng và firmware.", "Báo cáo PDF kèm demo trực tiếp."])], [],
     "Mở bài nộp trên MS Teams"),
]

SCHEDULE = [
    (2, "06:45", "09:15", "Kỹ thuật lập trình", "IT3040", "D9-401"),
    (2, "12:30", "15:05", "Giải tích 2", "MI1121", "TC-205"),
    (3, "06:45", "09:15", "Vật lý đại cương 1", "PH1110", "D3-301"),
    (4, "12:30", "15:05", "Giải tích 2", "MI1121", "TC-205"),
    (4, "15:15", "17:00", "Thực hành Mạng máy tính", "IT3080", "B1-Lab 302"),
    (5, "09:20", "11:55", "Kỹ thuật điện", "EE2020", "D5-201"),
    (6, "06:45", "09:15", "Tin học đại cương", "IT1110", "B1-Lab 101"),
]


def _add_tasks(student, rows):
    now = datetime.now()
    for (code, course, title, src, mins, kind, weight, extra, note, teacher, cls, dept,
         specs, digest, formulas, cta) in rows:
        db.session.add(Task(student_id=student.id, code=code, course=course, title=title, source=src,
                            due_at=now + timedelta(minutes=mins), kind=kind, weight=weight, extra=extra,
                            note=note, teacher=teacher, cls=cls, dept=dept, specs=specs, digest=digest,
                            formulas=formulas, cta=cta))


def _add_student(name, mssv, cls, cpa, done_base, tasks, schedule, scores):
    s = Student(name=name, mssv=mssv, cls=cls, cpa=cpa, done_base=done_base)
    s.set_password("123456")
    db.session.add(s)
    db.session.flush()  # lấy s.id
    _add_tasks(s, tasks)
    for row in schedule:
        db.session.add(ScheduleItem(student_id=s.id, day=row[0], start=row[1], end=row[2],
                                    subject=row[3], code=row[4], room=row[5]))
    for crit_id, now in scores.items():
        db.session.add(ConductScore(student_id=s.id, criterion_id=crit_id, now=now))


def seed_if_empty():
    if Student.query.first():
        return

    # ---- dữ liệu dùng chung
    db.session.add_all([
        Criterion(id=1, name="Ý thức học tập", max=20),
        Criterion(id=2, name="Chấp hành nội quy, quy chế", max=25),
        Criterion(id=3, name="Hoạt động chính trị - xã hội", max=20),
        Criterion(id=4, name="Quan hệ cộng đồng", max=25),
        Criterion(id=5, name="Phụ trách lớp, đoàn thể", max=10),
    ])
    db.session.flush()

    def d(s):
        return datetime.strptime(s, "%d/%m/%Y").date()

    db.session.add_all([
        Event(name="Giọt hồng Bách Khoa - hiến máu", crit=3, pts=5, date=d("12/10/2026"), place="Hội trường C2"),
        Event(name="Mùa hè xanh - tập huấn tình nguyện", crit=3, pts=3, date=d("18/10/2026"), place="Nhà C1"),
        Event(name="Hội thảo định hướng nghề nghiệp", crit=4, pts=2, date=d("20/10/2026"), place="D9-101"),
        Event(name="Sinh hoạt lớp đầu kỳ", crit=2, pts=2, date=d("05/10/2026"), place="Theo lớp"),
        Event(name="Cuộc thi Olympic Toán", crit=1, pts=2, date=d("25/10/2026"), place="Nhà D3"),
    ])
    db.session.add_all([
        KBEntry(keys=["học bổng", "kkht"], src="Sổ tay sinh viên",
                ans="Học bổng KKHT xét theo điểm học tập và điểm rèn luyện của kỳ. Nội dung mẫu: hãy thay bằng điều khoản chính thức."),
        KBEntry(keys=["hiến máu", "rèn luyện", "điểm rèn luyện"], src="ctsv.hust.edu.vn",
                ans="Hoạt động hiến máu tình nguyện thường được cộng vào nhóm tiêu chí hoạt động chính trị - xã hội. Xem tab Điểm rèn luyện để biết sự kiện phù hợp."),
        KBEntry(keys=["toeic", "tiếng anh", "miễn"], src="Sổ tay sinh viên",
                ans="Điều kiện miễn học phần Tiếng Anh dựa trên chứng chỉ quy đổi. Nội dung mẫu: cần nạp quy chế chính thức."),
    ])

    # ---- dữ liệu cá nhân của từng sinh viên
    _add_student("Nguyễn Văn A", "20210001", "K66 KHMT", 3.65, 18,
                 TASKS, SCHEDULE, {1: 18, 2: 25, 3: 12, 4: 20, 5: 8})
    _add_student("Trần Thị B", "20210002", "K66 CNTT", 3.20, 12,
                 TASKS[:3], SCHEDULE[:4], {1: 10, 2: 22, 3: 5, 4: 15, 5: 0})
    db.session.commit()
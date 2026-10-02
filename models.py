from datetime import datetime

from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

db = SQLAlchemy()

SOURCES = {"teams": "MS Teams", "fami": "FAMI Số hóa", "lms": "LMS HUST", "moocai": "MoocAI"}


def _label(m):
    if m < 0:
        return "Quá hạn", "late"
    if m < 60:
        return "Còn %d phút" % m, "soon"
    if m < 1440:
        return "Còn %dh %02dm" % (m // 60, m % 60), "soon"
    return "Còn %d ngày" % (m // 1440), "later"


def _owner():
    """Cột khóa ngoại trỏ về sinh viên sở hữu bản ghi. Mọi truy vấn dữ liệu cá nhân PHẢI lọc theo cột này."""
    return db.Column(db.Integer, db.ForeignKey("student.id"), nullable=False, index=True)


# ======================================================================
#  DỮ LIỆU CÁ NHÂN (mỗi dòng thuộc về đúng 1 sinh viên)
# ======================================================================
class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    mssv = db.Column(db.String(20), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    cls = db.Column(db.String(40))
    cpa = db.Column(db.Float, default=0.0)
    done_base = db.Column(db.Integer, default=0)  # số bài đã hoàn thành từ các kỳ/giai đoạn trước

    def set_password(self, pw):
        self.password_hash = generate_password_hash(pw)

    def check_password(self, pw):
        return check_password_hash(self.password_hash, pw)


class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = _owner()
    code = db.Column(db.String(20), nullable=False)
    course = db.Column(db.String(120), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    source = db.Column(db.String(20), nullable=False)  # teams | fami | lms | moocai
    due_at = db.Column(db.DateTime, nullable=False, index=True)
    kind = db.Column(db.String(60))
    weight = db.Column(db.Integer, default=0)
    extra = db.Column(db.String(255), default="")
    note = db.Column(db.String(255), default="")
    teacher = db.Column(db.String(120))
    cls = db.Column(db.String(60))
    dept = db.Column(db.String(120))
    specs = db.Column(db.JSON, default=list)
    digest = db.Column(db.JSON, default=list)
    formulas = db.Column(db.JSON, default=list)
    cta = db.Column(db.String(120))
    done = db.Column(db.Boolean, default=False, nullable=False)
    done_at = db.Column(db.DateTime)

    def to_dict(self, now=None):
        now = now or datetime.now()
        mins = int((self.due_at - now).total_seconds() // 60)
        label, level = _label(mins)
        if self.due_at.date() == now.date():
            due = "Hôm nay " + self.due_at.strftime("%H:%M")
        else:
            due = self.due_at.strftime("%d/%m/%Y • %H:%M")
        group = "urgent" if mins < 1440 else "week" if mins < 4 * 1440 else "later"
        return dict(
            id=self.id, code=self.code, course=self.course, title=self.title, source=self.source,
            mins=mins, kind=self.kind, weight=self.weight, extra=self.extra, note=self.note,
            teacher=self.teacher, cls=self.cls, dept=self.dept, specs=self.specs or [],
            digest=self.digest or [], formulas=self.formulas or [], cta=self.cta,
            source_name=SOURCES.get(self.source, self.source), label=label, level=level,
            due=due, due_iso=self.due_at.isoformat(), group=group, done=self.done,
        )


class ScheduleItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = _owner()
    day = db.Column(db.Integer, nullable=False, index=True)  # 2 = Thứ 2 ... 7 = Thứ 7, 8 = CN
    start = db.Column(db.String(5), nullable=False)
    end = db.Column(db.String(5), nullable=False)
    subject = db.Column(db.String(120), nullable=False)
    code = db.Column(db.String(20))
    room = db.Column(db.String(40))

    def as_tuple(self):
        return (self.day, self.start, self.end, self.subject, self.code, self.room)


class ConductScore(db.Model):
    """Điểm rèn luyện của từng sinh viên theo từng tiêu chí."""
    __table_args__ = (db.UniqueConstraint("student_id", "criterion_id"),)
    id = db.Column(db.Integer, primary_key=True)
    student_id = _owner()
    criterion_id = db.Column(db.Integer, db.ForeignKey("criterion.id"), nullable=False)
    now = db.Column(db.Integer, default=0, nullable=False)


class EventRegistration(db.Model):
    """Sinh viên nào đã đăng ký sự kiện nào."""
    __table_args__ = (db.UniqueConstraint("student_id", "event_id"),)
    id = db.Column(db.Integer, primary_key=True)
    student_id = _owner()
    event_id = db.Column(db.Integer, db.ForeignKey("event.id"), nullable=False)


# ======================================================================
#  DỮ LIỆU DÙNG CHUNG (mọi sinh viên thấy như nhau, không chứa thông tin riêng tư)
# ======================================================================
class Criterion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    max = db.Column(db.Integer, nullable=False)


class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    crit = db.Column(db.Integer, db.ForeignKey("criterion.id"), nullable=False)
    pts = db.Column(db.Integer, default=0)
    date = db.Column(db.Date, nullable=False)
    place = db.Column(db.String(120))

    def to_dict(self):
        return dict(id=self.id, name=self.name, crit=self.crit, pts=self.pts,
                    date=self.date.strftime("%d/%m/%Y"), place=self.place)


class KBEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    keys = db.Column(db.JSON, nullable=False)
    src = db.Column(db.String(120))
    ans = db.Column(db.Text, nullable=False)

    def to_dict(self):
        return dict(keys=self.keys, src=self.src, ans=self.ans)
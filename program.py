"""Chương trình đào tạo và bảng điểm theo học phần, lấy từ ctt-sis.hust.edu.vn qua extension.

Server không giữ thông tin đăng nhập của trường: extension tải trang ngay trong tab của sinh viên,
chỉ gửi các ô của bảng học phần; server kiểm tra (program_clean) rồi lưu theo từng sinh viên.
"""
from datetime import datetime

from flask import Blueprint, jsonify, request

from connect import PairToken, _hash          # dùng lại mã ghép nối 10 phút của extension
from models import _owner, db
from program_clean import is_passed, parse_program, summarize

bp = Blueprint("program", __name__)
MAX_BYTES = 1_500_000


# ------------------------------------------------------------------ model
class ProgramCourse(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = _owner()
    code = db.Column(db.String(20), nullable=False)
    name = db.Column(db.String(160), nullable=False)
    term = db.Column(db.Integer)                 # kỳ học gợi ý trong chương trình
    required = db.Column(db.Boolean, default=False)
    tc_prog = db.Column(db.Float, default=0)     # TC theo chương trình (cột "TC ĐT")
    tc_done = db.Column(db.Float)                # TC đã học (cột "TC học")
    code_taken = db.Column(db.String(20))
    note = db.Column(db.String(255))
    letter = db.Column(db.String(4))
    score = db.Column(db.Float)
    dept = db.Column(db.String(60))
    group_code = db.Column(db.String(20))
    group_name = db.Column(db.String(160))
    synced_at = db.Column(db.DateTime)


_FIELDS = ("code", "name", "term", "required", "tc_prog", "tc_done", "code_taken", "note",
           "letter", "score", "dept", "group_code", "group_name")


def _rows(sid):
    return [{f: getattr(c, f) for f in _FIELDS} for c in ProgramCourse.query.filter_by(student_id=sid).all()]


# ------------------------------------------------------------------ truy vấn (luôn theo sid)
def summary(sid):
    """Tổng hợp tiến độ; None nếu sinh viên chưa đồng bộ chương trình đào tạo."""
    rows = _rows(sid)
    if not rows:
        return None
    s = summarize(rows)
    s["synced_at"] = last_sync(sid)
    return s


def course_list(sid, status="remaining", only_required=True, limit=40):
    """status: remaining (chưa đạt) | done (đã đạt) | all. Sắp theo kỳ học gợi ý rồi mã học phần."""
    status = status if status in ("remaining", "done", "all") else "remaining"
    out = []
    for c in sorted(_rows(sid), key=lambda c: (c["term"] is None, c["term"] or 0, c["code"])):
        passed = is_passed(c)
        if (status == "remaining" and passed) or (status == "done" and not passed):
            continue
        if only_required and not c["required"]:
            continue
        out.append(dict(code=c["code"], name=c["name"], term=c["term"], required=c["required"], credits=c["tc_prog"],
                        group=c["group_name"], letter=c["letter"] or "", score=c["score"]))
    limit = max(1, min(int(limit or 40), 80))
    return out[:limit], max(0, len(out) - limit)


def last_sync(sid):
    return db.session.query(db.func.max(ProgramCourse.synced_at)).filter(ProgramCourse.student_id == sid).scalar()


# ------------------------------------------------------------------ API cho extension
# Nhớ thêm "program.ext_program" vào PUBLIC_ENDPOINTS (extension tự xác thực bằng mã ghép nối)
@bp.post("/api/ext/program")
def ext_program():
    if (request.content_length or 0) > MAX_BYTES:
        return jsonify(ok=False, error="Dữ liệu quá lớn"), 413
    token = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
    pt = PairToken.query.filter_by(token_hash=_hash(token)).first() if token else None
    if not pt or pt.expires_at < datetime.now():
        return jsonify(ok=False, error="Mã ghép nối sai hoặc đã hết hạn"), 401

    courses, err = parse_program(request.get_json(silent=True))
    if err:
        return jsonify(ok=False, error=err), 200

    sid, now = pt.student_id, datetime.now()
    ProgramCourse.query.filter_by(student_id=sid).delete()        # bản mới thay bản cũ
    for c in courses:
        db.session.add(ProgramCourse(student_id=sid, synced_at=now, **c))
    db.session.commit()
    s = summarize(courses)
    return jsonify(ok=True, synced=len(courses), earned=s["earned"], cpa_est=s["cpa_est"])


# ------------------------------------------------------------------ xóa dữ liệu (cần đăng nhập; gọi từ nút "Xóa dữ liệu điểm" nếu bạn thêm vào giao diện)
@bp.delete("/api/program")
def delete_program():
    from flask import g
    ProgramCourse.query.filter_by(student_id=g.student.id).delete()
    db.session.commit()
    return jsonify(ok=True)
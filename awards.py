"""Học bổng/chương trình đang mở đăng ký, lấy từ student.hust.edu.vn qua extension.

Server không giữ thông tin đăng nhập của trường: extension gọi API ngay trong tab của sinh viên
rồi gửi JSON lên đây; server tự lọc (awards_clean) và lưu theo từng sinh viên.
"""
from datetime import datetime

from flask import Blueprint, jsonify, request

from awards_clean import clean_award, find_awards
from connect import PairToken, _hash          # dùng lại mã ghép nối 10 phút của extension
from models import _owner, db

bp = Blueprint("awards", __name__)
MAX_BYTES, MAX_ITEMS = 3_000_000, 200


# ------------------------------------------------------------------ model
class Award(db.Model):
    __table_args__ = (db.UniqueConstraint("student_id", "ext_id"),)
    id = db.Column(db.Integer, primary_key=True)
    student_id = _owner()
    ext_id = db.Column(db.String(32), nullable=False)       # id gốc của trường (16 chữ số) -> lưu dạng chuỗi
    name = db.Column(db.String(255), nullable=False)
    kind = db.Column(db.String(120))
    partners = db.Column(db.String(255))
    value_text = db.Column(db.String(120))
    num_text = db.Column(db.String(40))
    register_from = db.Column(db.DateTime)
    register_to = db.Column(db.DateTime)
    semester = db.Column(db.String(10))
    student_years = db.Column(db.JSON, default=list)
    doc_urls = db.Column(db.JSON, default=list)
    description = db.Column(db.Text, default="")             # chữ thuần, không phải HTML
    available = db.Column(db.Boolean, default=False)
    synced_at = db.Column(db.DateTime)


# ------------------------------------------------------------------ truy vấn (luôn theo sid)
def _fmt(dt):
    return dt.strftime("%d/%m/%Y %H:%M") if dt else ""


def _is_open(a, now):
    return (a.available and (a.register_from is None or a.register_from <= now)
            and (a.register_to is None or a.register_to >= now))


def award_dicts(sid, only_open=True):
    """Danh sách tóm tắt, đang mở thì sắp theo hạn đăng ký gần nhất."""
    now = datetime.now()
    rows = Award.query.filter_by(student_id=sid).all()
    rows.sort(key=lambda a: (a.register_to or datetime.max))
    out = []
    for a in rows:
        op = _is_open(a, now)
        if only_open and not op:
            continue
        out.append(dict(
            id=a.ext_id, name=a.name, kind=a.kind or "", partners=a.partners or "", value=a.value_text or "",
            slots=a.num_text or "", register_from=_fmt(a.register_from), register_to=_fmt(a.register_to),
            days_left=(a.register_to.date() - now.date()).days if a.register_to else None,
            student_years=a.student_years or [], semester=a.semester or "", open=op))
    return out


def award_detail(sid, ext_id):
    """Chi tiết một học bổng của đúng sinh viên sid (điều kiện, mức, hồ sơ nằm trong description)."""
    a = Award.query.filter_by(student_id=sid, ext_id=str(ext_id)).first()
    if not a:
        return None
    d = next((x for x in award_dicts(sid, only_open=False) if x["id"] == a.ext_id), {})
    return dict(d, description=a.description or "", links=a.doc_urls or [])


def last_sync(sid):
    return db.session.query(db.func.max(Award.synced_at)).filter(Award.student_id == sid).scalar()


# ------------------------------------------------------------------ API cho extension
# Nhớ thêm "awards.ext_awards" vào PUBLIC_ENDPOINTS (extension tự xác thực bằng mã ghép nối)
@bp.post("/api/ext/awards")
def ext_awards():
    if (request.content_length or 0) > MAX_BYTES:
        return jsonify(ok=False, error="Dữ liệu quá lớn"), 413
    token = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
    pt = PairToken.query.filter_by(token_hash=_hash(token)).first() if token else None
    if not pt or pt.expires_at < datetime.now():
        return jsonify(ok=False, error="Mã ghép nối sai hoặc đã hết hạn"), 401

    data = request.get_json(silent=True) or {}
    items, seen = [], set()
    for raw in find_awards(data.get("response"))[:MAX_ITEMS]:
        a = clean_award(raw)
        if a and a["ext_id"] not in seen:
            seen.add(a["ext_id"])
            items.append(a)
    if not items:
        return jsonify(ok=False, error="Không thấy học bổng nào trong dữ liệu nhận được."), 200

    sid, now = pt.student_id, datetime.now()
    Award.query.filter_by(student_id=sid).delete()          # danh sách hiện tại thay thế bản cũ
    for a in items:
        db.session.add(Award(student_id=sid, synced_at=now, **a))
    db.session.commit()
    return jsonify(ok=True, synced=len(items), open=sum(1 for a in items if a["available"]))
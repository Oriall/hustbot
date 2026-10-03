"""Kết nối Cổng QLĐT (qldt.hust.edu.vn) qua extension đọc chữ trên trang đã hiển thị.

Server KHÔNG nhận token/cookie của qldt và không gọi API của trường: extension chỉ gửi phần chữ
của khung "Thông tin chi tiết" (lịch học của chính sinh viên), server tự đọc, kiểm tra rồi ghi vào ScheduleItem.

Env: TOKEN_ENC_KEY (khóa Fernet; dùng để mã hóa bản ghi kết nối)
"""
import hashlib
import json
import os
import secrets
from datetime import datetime, timedelta

from cryptography.fernet import Fernet
from flask import Blueprint, g, jsonify, request

from models import ScheduleItem, _owner, db
from qldt_text import parse_many

bp = Blueprint("connect", __name__)
_fernet = Fernet(os.environ["TOKEN_ENC_KEY"].encode())

PROVIDER = "qldt"
MAX_TEXTS, MAX_CHARS = 10, 60000


# ------------------------------------------------------------------ models
class Connection(db.Model):
    """Chỉ để theo dõi trạng thái/lần đồng bộ cuối (không còn chứa token của qldt)."""
    __table_args__ = (db.UniqueConstraint("student_id", "provider"),)
    id = db.Column(db.Integer, primary_key=True)
    student_id = _owner()
    provider = db.Column(db.String(20), nullable=False)
    secret_enc = db.Column(db.LargeBinary, nullable=False)
    status = db.Column(db.String(20), default="ok")
    last_sync = db.Column(db.DateTime)
    last_error = db.Column(db.String(255), default="")


class PairToken(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = _owner()
    token_hash = db.Column(db.String(64), unique=True, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)


def _hash(t):
    return hashlib.sha256(t.encode()).hexdigest()


# ------------------------------------------------------------------ API (cần đăng nhập)
@bp.get("/api/connections")
def list_connections():
    rows = Connection.query.filter_by(student_id=g.student.id).all()
    return jsonify([dict(provider=c.provider, status=c.status, last_sync=c.last_sync and c.last_sync.isoformat(),
                         error=c.last_error) for c in rows])


@bp.delete("/api/connections/<provider>")
def disconnect(provider):
    sid = g.student.id
    Connection.query.filter_by(student_id=sid, provider=provider).delete()
    ScheduleItem.query.filter_by(student_id=sid, source=provider).delete()   # xóa lịch đã đồng bộ
    db.session.commit()
    return jsonify(ok=True)


@bp.post("/api/connections/pair")
def make_pair_token():
    token = secrets.token_urlsafe(24)
    PairToken.query.filter_by(student_id=g.student.id).delete()
    db.session.add(PairToken(student_id=g.student.id, token_hash=_hash(token),
                             expires_at=datetime.now() + timedelta(minutes=10)))
    db.session.commit()
    return jsonify(token=token, expires_in=600)      # chỉ hiện 1 lần, hết hạn sau 10 phút


# ------------------------------------------------------------------ API cho extension
# Nhớ thêm "connect.ext_timetable" vào PUBLIC_ENDPOINTS (extension tự xác thực bằng mã ghép nối)
@bp.post("/api/ext/timetable")
def ext_timetable():
    token = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
    pt = PairToken.query.filter_by(token_hash=_hash(token)).first() if token else None
    if not pt or pt.expires_at < datetime.now():
        return jsonify(ok=False, error="Mã ghép nối sai hoặc đã hết hạn"), 401

    data = request.get_json(silent=True) or {}
    texts = data.get("texts")
    if (not isinstance(texts, list) or len(texts) > MAX_TEXTS
            or not all(isinstance(t, str) for t in texts) or sum(map(len, texts)) > MAX_CHARS):
        return jsonify(ok=False, error="Dữ liệu không hợp lệ"), 400

    items = parsed = parse_many(texts)                # server tự đọc và kiểm tra, không tin dữ liệu có cấu trúc từ client
    if not items:
        return jsonify(ok=False, error="Không thấy tiết học nào. Hãy mở tab Lịch và chọn một ngày có lớp."), 200

    sid = pt.student_id
    if data.get("mode") == "week":
        ScheduleItem.query.filter_by(student_id=sid).delete()              # đọc đủ cả tuần: thay toàn bộ
    else:
        ScheduleItem.query.filter(ScheduleItem.student_id == sid,          # chỉ đọc 1 ngày: giữ lịch qldt cũ,
                                  ScheduleItem.source != PROVIDER).delete()  # chỉ bỏ dữ liệu mẫu
        old = {(x.day, x.start, x.end, x.code) for x in ScheduleItem.query.filter_by(student_id=sid)}
        items = [i for i in items if (i["day"], i["start"], i["end"], i["code"]) not in old]
    for it in items:
        db.session.add(ScheduleItem(student_id=sid, source=PROVIDER, **it))

    conn = Connection.query.filter_by(student_id=sid, provider=PROVIDER).first()
    if not conn:
        conn = Connection(student_id=sid, provider=PROVIDER,
                          secret_enc=_fernet.encrypt(json.dumps({}).encode()))
        db.session.add(conn)
    conn.status, conn.last_error, conn.last_sync = "ok", "", datetime.now()
    db.session.commit()
    by_day = {}
    for it in parsed:
        by_day[it["day"]] = by_day.get(it["day"], 0) + 1
    return jsonify(ok=True, synced=len(items), total=len(parsed), by_day=by_day)
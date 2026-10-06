"""Kiểm tra dữ liệu thật trong database mà app đang dùng.
Chạy trong thư mục dự án (cạnh app.py):   python check_db.py
"""
import glob
import os
import time

from app import app
from awards import Award
from connect import Connection
from models import ScheduleItem, Student, db

with app.app_context():
    path = db.engine.url.database
    print("Database app đang dùng:\n  ", path)

    root = os.path.dirname(os.path.abspath(__file__))
    files = sorted(set(glob.glob(os.path.join(root, "*.db")) + glob.glob(os.path.join(root, "instance", "*.db"))))
    print("\nCác file .db trong dự án (nếu có 2 file, rất có thể bạn đang mở nhầm file):")
    for f in files:
        mark = "   <== app đang ghi vào file này" if os.path.abspath(f) == os.path.abspath(path or "") else ""
        print("   %s  (%d KB, sửa lần cuối %s)%s" % (
            f, os.path.getsize(f) // 1024, time.strftime("%d/%m %H:%M", time.localtime(os.path.getmtime(f))), mark))

    print("\nSố bản ghi theo từng sinh viên:")
    for s in Student.query.order_by(Student.id):
        aw = Award.query.filter_by(student_id=s.id)
        sch = ScheduleItem.query.filter_by(student_id=s.id)
        conns = ", ".join("%s=%s" % (c.provider, c.status) for c in Connection.query.filter_by(student_id=s.id)) or "chưa có"
        print("   %s %-22s | học bổng=%d (đang mở: %d) | lịch=%d (từ qldt: %d) | kết nối: %s" % (
            s.mssv, s.name, aw.count(), aw.filter_by(available=True).count(),
            sch.count(), sch.filter_by(source="qldt").count(), conns))

    print("\nBảng học bổng tên là 'award' (số ít). 5 học bổng mới nhất:")
    for a in Award.query.order_by(Award.synced_at.desc()).limit(5):
        print("   [sinh viên id=%s] %s | hạn: %s | mở đăng ký: %s" % (a.student_id, a.name[:55], a.register_to, a.available))
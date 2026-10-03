"""Đọc văn bản trong khung "Thông tin chi tiết" của trang Lịch (qldt.hust.edu.vn) thành các tiết học.

Mỗi tiết có dạng:
    767684 - Chạy - PE2601
    Thời gian:  Sáng Thứ 5, [08:00 - 09:00]
    Địa điểm:   SVD2
"""
import re

HEADER = re.compile(r"^[ \t]*(\d{4,})[ \t]*-[ \t]*(.+?)[ \t]*-[ \t]*([A-Za-z]{2,6}\d{3,5}[A-Za-z]?)[ \t]*$", re.M)
TIME = re.compile(r"\[\s*(\d{1,2}):(\d{2})\s*-\s*(\d{1,2}):(\d{2})\s*\]")
WEEKDAY = re.compile(r"Th[ứư]\s*([2-7])|(Ch[ủu]\s*nh[ậa]t)", re.I)
ROOM = re.compile(r"Địa điểm:[ \t]*([^\n]*)")


def parse_details(text):
    """Trả về list dict(day, start, end, subject, code, room). day: 2..7 = Thứ 2..Thứ 7, 8 = Chủ nhật."""
    text = text or ""
    heads = list(HEADER.finditer(text))
    items = []
    for i, h in enumerate(heads):
        block = text[h.end(): heads[i + 1].start() if i + 1 < len(heads) else len(text)]
        t, d = TIME.search(block), WEEKDAY.search(block)
        if not (t and d):
            continue
        day = int(d.group(1)) if d.group(1) else 8
        room = (ROOM.search(block) or [None, ""])[1].strip()
        items.append(dict(
            day=day,
            start="%02d:%s" % (int(t.group(1)), t.group(2)),
            end="%02d:%s" % (int(t.group(3)), t.group(4)),
            subject=h.group(2).strip()[:120],
            code=h.group(3).strip()[:20],
            room=room[:40]))
    return items


def parse_many(texts):
    """Gộp nhiều khung (mỗi ngày một khung), bỏ trùng, sắp theo thứ và giờ."""
    seen, out = set(), []
    for t in texts:
        for it in parse_details(t):
            key = (it["day"], it["start"], it["end"], it["code"])
            if key not in seen:
                seen.add(key)
                out.append(it)
    out.sort(key=lambda x: (x["day"], x["start"]))
    return out
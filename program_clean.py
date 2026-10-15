"""Làm sạch dữ liệu chương trình đào tạo (ctt-sis.hust.edu.vn/Students/StudentProgram.aspx) do extension gửi lên.
Dữ liệu từ client luôn bị coi là không đáng tin: kiểm tra cấu trúc, ép kiểu, cắt độ dài.

Extension gửi:  {"headers": ["Mã HP", ...], "rows": [["g", "Mã loại HP: 210 (...)"], ["d", {"Mã HP": "SSH1111", ...}], ...]}
"""
import math
import re

COLS = {"code": "Mã HP", "name": "Tên HP", "term": "Kỳ học", "required": "Bắt buộc", "tc_prog": "TC ĐT",
        "tc_done": "TC học", "code_taken": "Mã HP học", "note": "Ghi chú loại HP", "letter": "Điểm chữ",
        "score": "Điểm số", "dept": "Viện/Khoa"}
PASS = {"A+", "A", "B+", "B", "C+", "C", "D+", "D"}
GRADE_POINT = {"A+": 4.0, "A": 4.0, "B+": 3.5, "B": 3.0, "C+": 2.5, "C": 2.0, "D+": 1.5, "D": 1.0, "F": 0.0}
CPA_EXCLUDE_PREFIXES = ("PE", "MIL")     # GDTC, GDQP-AN: không tính vào CPA. Kiểm tra lại mã môn thật của bạn
MAX_ROWS = 600


def _s(v, n):
    return re.sub(r"\s+", " ", str(v if v is not None else "")).strip()[:n]


def _num(v):
    s = _s(v, 20).replace(",", ".")
    try:
        x = float(s) if s else None
    except ValueError:
        return None
    return x if x is None or (math.isfinite(x) and abs(x) <= 1000) else None     # chặn inf/nan/giá trị vô lý


def _n(x):
    """Số nguyên nếu tròn, ngược lại làm tròn 2 chữ số."""
    return int(x) if abs(x - round(x)) < 1e-9 else round(x, 2)


def parse_program(data):
    """Trả về (danh sách học phần, thông báo lỗi). Học phần có cả nhóm (mã loại HP, tên loại HP) lấy từ dòng nhóm phía trên."""
    if not isinstance(data, dict):
        return None, "Dữ liệu không hợp lệ"
    headers, rows = data.get("headers"), data.get("rows")
    if (not isinstance(headers, list) or not isinstance(rows, list) or len(rows) > MAX_ROWS
            or COLS["code"] not in headers or COLS["name"] not in headers):
        return None, "Không nhận ra cấu trúc bảng chương trình đào tạo (trang có thể đã đổi giao diện)."

    out, g_code, g_name = [], "", ""
    for r in rows:
        if not (isinstance(r, list) and len(r) == 2):
            continue
        kind, body = r
        if kind == "g" and isinstance(body, str):
            text = _s(body, 300)
            if text.startswith("Mã loại HP:"):
                m = re.match(r"Mã loại HP:\s*([^\s(]+)", text)
                g_code, g_name = (m.group(1) if m else ""), ""
            elif text.startswith("Loại HP:"):
                m = re.match(r"Loại HP:\s*(.*?)\s*(?:\(Count=|$)", text)
                g_name = m.group(1) if m else ""
        elif kind == "d" and isinstance(body, dict):
            code, name = _s(body.get(COLS["code"]), 20), _s(body.get(COLS["name"]), 160)
            if not code or not name:
                continue
            term = _num(body.get(COLS["term"]))
            out.append(dict(
                code=code, name=name, term=int(term) if term is not None else None,
                required=body.get(COLS["required"]) == "1",
                tc_prog=_num(body.get(COLS["tc_prog"])) or 0.0,
                tc_done=_num(body.get(COLS["tc_done"])),
                code_taken=_s(body.get(COLS["code_taken"]), 20),
                note=_s(body.get(COLS["note"]), 255),
                letter=_s(body.get(COLS["letter"]), 4),
                score=_num(body.get(COLS["score"])),
                dept=_s(body.get(COLS["dept"]), 60),
                group_code=_s(g_code, 20), group_name=_s(g_name, 160)))
    if not out:
        return None, "Không thấy học phần nào trong bảng."
    return out, ""


def is_passed(c):
    return (c.get("letter") or "") in PASS
def _grade_point(c):
    """Điểm hệ 4 của học phần; None nếu chưa có điểm."""
    s = c.get("score")
    if s is not None and 0 <= s <= 4:
        return s
    return GRADE_POINT.get((c.get("letter") or "").upper())     # score ngoài thang 4 -> quy đổi từ điểm chữ


def cpa_inputs(courses):
    """[(tín chỉ, điểm hệ 4)] của các học phần được tính vào CPA.
    Bỏ môn chưa có điểm, môn loại trừ (PE/MIL), mỗi môn chỉ tính một lần (giữ điểm cao nhất)."""
    best = {}
    for c in courses:
        credits, gp = c.get("tc_done") or 0, _grade_point(c)
        codes = [(c.get("code") or "").upper(), (c.get("code_taken") or "").upper()]
        if gp is None or credits <= 0 or any(x.startswith(CPA_EXCLUDE_PREFIXES) for x in codes if x):
            continue
        key = codes[1] or codes[0]
        if key not in best or gp > best[key][1]:
            best[key] = (credits, gp)
    return list(best.values())

def summarize(courses):
    passed = [c for c in courses if is_passed(c)]
    counted = cpa_inputs(courses)
    points = sum(cr * gp for cr, gp in counted)
    credits = sum(cr for cr, _ in counted)
    req = [c for c in courses if c["required"] and c["tc_prog"] > 0]
    req_left = [c for c in req if not is_passed(c)]
    return dict(
        cpa_est=round(points / credits, 2) if credits else None,
        graded_credits=_n(credits), grade_points=round(points, 2),          # để agent tính "nếu môn X được A thì CPA bao nhiêu"
        earned=_n(sum(c.get("tc_done") or 0 for c in passed)),               # tín chỉ đã đạt (cả bắt buộc lẫn tự chọn)
        passed_courses=len(passed),
        required_total=_n(sum(c["tc_prog"] for c in req)),                   # tổng TC các môn đánh dấu "Bắt buộc"
        required_done=_n(sum(c["tc_prog"] for c in req if is_passed(c))),
        required_left_courses=len(req_left),
        required_left_credits=_n(sum(c["tc_prog"] for c in req_left)))
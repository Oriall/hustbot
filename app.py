import os
from datetime import datetime, timedelta

from dotenv import load_dotenv
from flask import Flask, g, jsonify, redirect, render_template, request, session, url_for

load_dotenv()

import gemini_bot  # noqa: E402
from models import (SOURCES, ConductScore, Criterion, Event, EventRegistration, KBEntry,  # noqa: E402
                    ScheduleItem, Student, Task, db)
from seed import seed_if_empty  # noqa: E402
import connect
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///hustbot.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-only-doi-khoa-nay-khi-deploy")
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
db.init_app(app)
app.register_blueprint(connect.bp)
with app.app_context():
    db.create_all()
    seed_if_empty()

PAGES = {
    "overview": "Tổng quan",
    "assignments": "Bài tập & Bài thi",
    "assistant": "Trợ lý AI Bách Khoa",
    "activities": "Điểm rèn luyện & Hoạt động",
    "schedule": "Thời khóa biểu",
}
PUBLIC_ENDPOINTS = {"login", "static", "connect.ext_timetable"}


# ---------------------------------------------------------------- xác thực
@app.before_request
def load_student():
    """Xác định sinh viên đang đăng nhập từ session (đã ký). Đây là NGUỒN DUY NHẤT của student_id."""
    uid = session.get("uid")
    g.student = db.session.get(Student, uid) if uid else None
    if g.student is None and request.endpoint not in PUBLIC_ENDPOINTS:
        if request.path.startswith("/api/"):
            return jsonify(ans="Bạn cần đăng nhập để dùng trợ lý.", error="unauthorized", actions=[]), 401
        return redirect(url_for("login", next=request.path))


@app.route("/dang-nhap", methods=["GET", "POST"])
def login():
    error = ""
    if request.method == "POST":
        s = Student.query.filter_by(mssv=request.form.get("mssv", "").strip()).first()
        if s and s.check_password(request.form.get("password", "")):
            session.clear()          # chống session fixation
            session["uid"] = s.id
            nxt = request.args.get("next", "")
            return redirect(nxt if nxt.startswith("/") and not nxt.startswith("//") else url_for("overview"))
        error = "Sai MSSV hoặc mật khẩu."
    return render_template("login.html", error=error)


@app.post("/dang-xuat")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ---------------------------------------------------------------- truy vấn dữ liệu (luôn theo sid)
def get_criteria(sid):
    scores = {c.criterion_id: c.now for c in ConductScore.query.filter_by(student_id=sid)}
    return [dict(id=c.id, name=c.name, now=scores.get(c.id, 0), max=c.max)
            for c in Criterion.query.order_by(Criterion.id)]


def get_events(sid):
    reg = {r.event_id for r in EventRegistration.query.filter_by(student_id=sid)}
    return [dict(e.to_dict(), registered=e.id in reg) for e in Event.query.order_by(Event.date)]


def get_user(sid):
    s = db.session.get(Student, sid)
    drl = sum(c["now"] for c in get_criteria(sid))
    return dict(name=s.name, mssv=s.mssv, cls=s.cls, cpa="%.2f" % s.cpa, drl=drl)


def done_count(sid):
    s = db.session.get(Student, sid)
    return s.done_base + Task.query.filter_by(student_id=sid, done=True).count()


def get_tasks(sid, include_done=False):
    now = datetime.now()
    q = Task.query.filter_by(student_id=sid)
    if not include_done:
        q = q.filter_by(done=False)
    return [t.to_dict(now) for t in q.order_by(Task.due_at).all()]


def weekday_vn(dt=None):
    return (dt or datetime.now()).isoweekday() + 1


def get_schedule(sid, day=None):
    q = ScheduleItem.query.filter_by(student_id=sid)
    if day is not None:
        q = q.filter_by(day=day)
    return [s.as_tuple() for s in q.order_by(ScheduleItem.day, ScheduleItem.start).all()]


def set_event_registered(sid, event_id, registered):
    """Trả về Event hoặc None. Chỉ ghi vào bản ghi đăng ký của chính sinh viên sid."""
    e = db.session.get(Event, event_id)
    if not e:
        return None
    row = EventRegistration.query.filter_by(student_id=sid, event_id=event_id).first()
    if registered and not row:
        db.session.add(EventRegistration(student_id=sid, event_id=event_id))
    elif not registered and row:
        db.session.delete(row)
    db.session.commit()
    return e


@app.context_processor
def inject_user():
    return dict(user=get_user(g.student.id)) if g.student else {}


# ---------------------------------------------------------------- trang
@app.route("/")
def overview():
    sid, now = g.student.id, datetime.now()
    tasks = get_tasks(sid)
    return render_template("overview.html", tasks=tasks[:3], all_count=len(tasks),
                           today=get_schedule(sid, weekday_vn(now)), now=now)


@app.route("/bai-tap")
def assignments():
    sid = g.student.id
    return render_template("assignments.html", tasks=get_tasks(sid), sources=SOURCES, done=done_count(sid))


@app.route("/tro-ly-ai")
def assistant():
    return render_template("assistant.html")


WEEKDAYS_VN = ["Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy", "Chủ nhật"]
RANKS = ((90, "Xuất sắc"), (80, "Tốt"), (65, "Khá"), (50, "Trung bình"), (35, "Yếu"))
EXCELLENT = 90


def rank_of(score):
    return next((name for lim, name in RANKS if score >= lim), "Kém")


def conduct_overview(sid):
    """Gom toàn bộ số liệu cho trang Điểm rèn luyện (đều theo sinh viên sid)."""
    today = datetime.now().date()
    criteria = get_criteria(sid)
    by_id = {c["id"]: c for c in criteria}
    for c in criteria:
        c["code"] = "TC%d" % c["id"]
        c["missing"] = c["max"] - c["now"]
        c["pct"] = round(100 * c["now"] / c["max"]) if c["max"] else 0
    total = sum(c["now"] for c in criteria)
    max_total = sum(c["max"] for c in criteria)

    reg_ids = {r.event_id for r in EventRegistration.query.filter_by(student_id=sid)}
    events = []
    for e in Event.query.order_by(Event.date, Event.id):
        c = by_id.get(e.crit)
        events.append(dict(
            id=e.id, name=e.name, date=e.date.strftime("%d/%m/%Y"), weekday=WEEKDAYS_VN[e.date.weekday()],
            place=e.place or "", pts=e.pts, crit=e.crit, crit_code=c["code"] if c else "",
            crit_name=c["name"] if c else "", registered=e.id in reg_ids, past=e.date < today, gain=0))

    # Điểm dự kiến: cộng các sự kiện đã đăng ký chưa diễn ra, không vượt trần từng tiêu chí
    proj = {c["id"]: c["now"] for c in criteria}
    for ev in events:
        if ev["registered"] and ev["crit"] in proj:
            if ev["past"]:
                ev["gain"] = ev["pts"]          # đã diễn ra: coi như đã nằm trong điểm hiện tại
            else:
                add = max(0, min(ev["pts"], by_id[ev["crit"]]["max"] - proj[ev["crit"]]))
                proj[ev["crit"]] += add
                ev["gain"] = add
    # Điểm cộng thêm thực tế nếu đăng ký các sự kiện còn lại
    for ev in events:
        if not ev["registered"] and ev["crit"] in proj:
            ev["gain"] = max(0, min(ev["pts"], by_id[ev["crit"]]["max"] - proj[ev["crit"]]))

    projected = sum(proj.values())
    weakest = max(criteria, key=lambda c: c["missing"], default=None)
    if weakest and weakest["missing"] <= 0:
        weakest = None
    return dict(
        criteria=criteria, total=total, max_total=max_total, rank=rank_of(total),
        projected=projected, projected_rank=rank_of(projected), gap=max(0, EXCELLENT - total),
        weakest=weakest, rank_of=rank_of,
        history=[e for e in events if e["registered"]][::-1],
        upcoming=[e for e in events if e["registered"] and not e["past"]],
        suggestions=sorted([e for e in events if not e["registered"] and not e["past"] and e["gain"] > 0],
                           key=lambda e: -e["gain"])[:4],
        now=datetime.now())


@app.route("/diem-ren-luyen")
def activities():
    return render_template("activities.html", **conduct_overview(g.student.id))


@app.route("/thoi-khoa-bieu")
def schedule():
    sid, now = g.student.id, datetime.now()
    monday = now - timedelta(days=now.weekday())
    week = {d: (monday + timedelta(days=d - 2)).strftime("%d/%m") for d in range(2, 8)}
    return render_template("schedule.html", days=range(2, 8), items=get_schedule(sid),
                           today=weekday_vn(now), week=week,
                           week_range="%s - %s" % (week[2], week[7]), now=now)


# ---------------------------------------------------------------- API ghi dữ liệu (UI dùng trực tiếp)
@app.post("/api/tasks/<int:task_id>/done")
def api_task_done(task_id):
    sid = g.student.id
    # lọc theo student_id: sinh viên A đoán id bài của B cũng nhận 404
    t = Task.query.filter_by(id=task_id, student_id=sid).first_or_404()
    t.done = bool((request.get_json(silent=True) or {}).get("done", True))
    t.done_at = datetime.now() if t.done else None
    db.session.commit()
    return jsonify(ok=True, done=t.done, done_count=done_count(sid))


@app.post("/api/events/<int:event_id>/register")
def api_event_register(event_id):
    flag = bool((request.get_json(silent=True) or {}).get("registered", True))
    if not set_event_registered(g.student.id, event_id, flag):
        return jsonify(ok=False, error="not_found"), 404
    return jsonify(ok=True, registered=flag)


# ---------------------------------------------------------------- AGENT
def _parse_day(s):
    s = (s or "today").lower().strip()
    if s in ("today", "hôm nay", "nay"):
        return weekday_vn()
    if s in ("tomorrow", "ngày mai", "mai"):
        return weekday_vn(datetime.now() + timedelta(days=1))
    if "chủ nhật" in s or s == "cn":
        return 8
    digits = "".join(ch for ch in s if ch.isdigit())
    if digits and 2 <= int(digits) <= 8:
        return int(digits)
    return None


def make_agent_tools(sid, actions):
    """Công cụ agent được gọi. `sid` được CỐ ĐỊNH trong closure từ session đăng nhập:
    AI không có tham số student_id nên không thể (kể cả bị prompt injection) đọc/ghi dữ liệu người khác."""

    def list_tasks(include_done: bool = False) -> dict:
        """Liệt kê bài tập/bài thi/deadline của sinh viên, sắp theo hạn nộp.
        include_done=True để lấy cả bài đã hoàn thành. Mỗi bài có id, mã môn, tên, hạn, trạng thái."""
        return {"tasks": [dict(id=t["id"], code=t["code"], course=t["course"], title=t["title"],
                               kind=t["kind"], weight_percent=t["weight"], due=t["due"],
                               remaining=t["label"], source=t["source_name"], done=t["done"])
                          for t in get_tasks(sid, include_done)]}

    def set_task_done(task_id: int, done: bool = True) -> dict:
        """Đánh dấu một bài tập là đã hoàn thành (done=True) hoặc chưa hoàn thành (done=False).
        CHỈ gọi khi sinh viên yêu cầu rõ ràng. Lấy task_id từ list_tasks."""
        t = Task.query.filter_by(id=task_id, student_id=sid).first()
        if not t:
            return {"ok": False, "error": "Không tìm thấy bài tập với id này"}
        t.done = done
        t.done_at = datetime.now() if done else None
        db.session.commit()
        actions.append({"type": "reload"})
        return {"ok": True, "task": t.title, "done": t.done}

    def get_class_schedule(day: str = "today") -> dict:
        """Lấy thời khóa biểu của một ngày. day: 'today', 'tomorrow', hoặc '2'..'7' (Thứ 2..Thứ 7), '8' = Chủ nhật."""
        d = _parse_day(day)
        if d is None:
            return {"ok": False, "error": "Ngày không hợp lệ"}
        return {"day": "Thứ %d" % d if d < 8 else "Chủ nhật",
                "classes": [dict(start=s[1], end=s[2], subject=s[3], code=s[4], room=s[5])
                            for s in get_schedule(sid, d)]}

    def get_conduct_summary() -> dict:
        """Tổng quan điểm rèn luyện: điểm hiện tại/tối đa từng tiêu chí và còn thiếu bao nhiêu."""
        rows = get_criteria(sid)
        return {"total": sum(c["now"] for c in rows), "max_total": sum(c["max"] for c in rows),
                "criteria": [dict(c, missing=c["max"] - c["now"]) for c in rows]}

    def list_events() -> dict:
        """Liệt kê hoạt động/sự kiện có thể tham gia để cộng điểm rèn luyện, kèm id, điểm cộng, ngày, trạng thái đăng ký."""
        crit = {c["id"]: c for c in get_criteria(sid)}
        out = []
        for e in get_events(sid):
            c = crit.get(e["crit"])
            out.append(dict(id=e["id"], name=e["name"], date=e["date"], place=e["place"],
                            points=e["pts"], criterion=c["name"] if c else "",
                            room_left_in_criterion=(c["max"] - c["now"]) if c else 0,
                            registered=e["registered"]))
        return {"events": out}

    def register_event(event_id: int, register: bool = True) -> dict:
        """Đăng ký (register=True) hoặc hủy đăng ký (False) một sự kiện. CHỈ gọi khi sinh viên yêu cầu rõ ràng.
        Lấy event_id từ list_events."""
        e = set_event_registered(sid, event_id, register)
        if not e:
            return {"ok": False, "error": "Không tìm thấy sự kiện với id này"}
        actions.append({"type": "reload"})
        return {"ok": True, "event": e.name, "registered": register}

    def search_knowledge_base(query: str) -> dict:
        """Tra cứu kho kiến thức (sổ tay sinh viên, quy chế) theo từ khóa."""
        low = (query or "").lower()
        hits = [k.to_dict() for k in KBEntry.query.all() if any(w in low for w in k.keys)]
        return {"results": [dict(source=h["src"], content=h["ans"]) for h in hits]}

    def navigate_to(page: str) -> dict:
        """Chuyển sinh viên sang một trang. page là một trong: overview, assignments, assistant, activities, schedule."""
        if page not in PAGES:
            return {"ok": False, "error": "Trang không hợp lệ", "valid": list(PAGES)}
        actions.append({"type": "navigate", "url": url_for(page), "label": PAGES[page]})
        return {"ok": True, "page": PAGES[page]}

    return [list_tasks, set_task_done, get_class_schedule, get_conduct_summary,
            list_events, register_event, search_knowledge_base, navigate_to]


@app.post("/api/agent")
@app.post("/api/chat")
def agent():
    sid = g.student.id  # luôn lấy từ session, KHÔNG đọc từ body request
    data = request.get_json(silent=True) or {}
    msg = (data.get("q") or "").strip()[:2000]
    if not msg:
        return jsonify(ans="Bạn hãy nhập câu hỏi nhé.", src="", actions=[]), 400

    page = data.get("page") or {}
    page_ctx = dict(endpoint=str(page.get("endpoint", ""))[:40], path=str(page.get("path", ""))[:100],
                    title=str(page.get("title", ""))[:100])
    page_ctx["name"] = PAGES.get(page_ctx["endpoint"], "")

    low = msg.lower()
    kb_hits = [k.to_dict() for k in KBEntry.query.all() if any(w in low for w in k.keys)]
    actions = []

    try:
        ans = gemini_bot.ask(msg, data.get("history"), get_user(sid),
                             tasks=get_tasks(sid)[:5], today_schedule=get_schedule(sid, weekday_vn()),
                             kb_hits=kb_hits, page=page_ctx, tools=make_agent_tools(sid, actions))
    except Exception:
        db.session.rollback()
        app.logger.exception("Gemini error")
        return jsonify(ans="Trợ lý đang bận hoặc gặp sự cố kết nối. Bạn thử lại sau ít phút nhé.", src="", actions=[]), 502

    nav = [a for a in actions if a["type"] == "navigate"]
    final = nav[-1:] or ([{"type": "reload"}] if actions else [])
    return jsonify(ans=ans, src=", ".join(k["src"] for k in kb_hits), actions=final)


if __name__ == "__main__":
    app.run(debug=True)
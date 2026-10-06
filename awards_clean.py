"""Làm sạch dữ liệu học bổng do extension gửi lên. Dữ liệu từ client luôn bị coi là không đáng tin:
chỉ lấy các trường trong danh sách trắng, ép kiểu, cắt độ dài, đổi HTML mô tả thành chữ thuần, chỉ giữ link https.
"""
import re
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser

VN = timezone(timedelta(hours=7))


class _Text(HTMLParser):
    BLOCK = {"p", "br", "div", "li", "tr", "h1", "h2", "h3", "h4", "h5", "ul", "ol", "table"}
    SKIP = {"script", "style"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out, self.links, self._skip = [], [], 0

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self._skip += 1
        if tag in self.BLOCK:
            self.out.append("\n")
        if tag == "a":
            href = dict(attrs).get("href") or ""
            if href.startswith("https://"):
                self.links.append(href)

    def handle_endtag(self, tag):
        if tag in self.SKIP and self._skip:
            self._skip -= 1
        if tag in self.BLOCK:
            self.out.append("\n")

    def handle_data(self, data):
        if not self._skip:
            self.out.append(data)


def html_to_text(s, limit=6000):
    """HTML -> (chữ thuần, danh sách link https). Không bao giờ trả HTML thô ra giao diện."""
    p = _Text()
    try:
        p.feed(str(s or ""))
    except Exception:
        return "", []
    text = "".join(p.out).replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\s*\n\s*", "\n", text).strip()
    return text[:limit], p.links


def _ms(v):
    try:
        v = int(v)
    except (TypeError, ValueError):
        return None
    if v <= 0:
        return None
    try:
        return datetime.fromtimestamp(v / 1000, VN).replace(tzinfo=None)   # giờ Việt Nam, không múi giờ
    except (OverflowError, OSError, ValueError):
        return None


def _s(v, n):
    return "" if v is None or v == -1 else str(v).strip()[:n]


def _strs(v, n=10, m=120):
    if not isinstance(v, list):
        return []
    return [str(x).strip()[:m] for x in v[:n] if isinstance(x, (str, int)) and str(x).strip()]


def _https(urls, cap=10):
    out = []
    for u in urls:
        if isinstance(u, str) and u.startswith("https://") and len(u) <= 600 and u not in out:
            out.append(u)
    return out[:cap]


def find_awards(obj, depth=0):
    """Tìm mảng các object có 'id' và 'name' trong JSON trả về (không cần biết khóa bao ngoài tên gì)."""
    if isinstance(obj, list):
        return [x for x in obj if isinstance(x, dict) and "id" in x and "name" in x]
    if isinstance(obj, dict) and depth < 4:
        best = []
        for v in obj.values():
            r = find_awards(v, depth + 1)
            if len(r) > len(best):
                best = r
        return best
    return []


def clean_award(raw):
    """Trả về dict các trường đã làm sạch (khớp cột bảng Award) hoặc None nếu dữ liệu không hợp lệ."""
    if not isinstance(raw, dict):
        return None
    try:
        ext_id = str(int(raw["id"]))
    except (KeyError, TypeError, ValueError):
        return None
    name = _s(raw.get("name"), 255)
    if not name:
        return None

    value = _s(raw.get("awardValueRange"), 120)
    amount = raw.get("awardValue")
    if not value and isinstance(amount, (int, float)) and not isinstance(amount, bool) and amount > 0:
        value = "{:,}".format(int(amount)).replace(",", ".") + " đ"

    desc, links = html_to_text(raw.get("description"))
    return dict(
        ext_id=ext_id,
        name=name,
        kind=", ".join(_strs(raw.get("awardNames"))) or _s(raw.get("awardName"), 120),
        partners=", ".join(_strs(raw.get("partnerNames"), 5)),
        value_text=value,
        num_text=_s(raw.get("awardNumRange") or raw.get("awardNum"), 40),
        register_from=_ms(raw.get("registerFrom")),
        register_to=_ms(raw.get("registerTo")),
        semester=_s(raw.get("semester"), 10),
        student_years=_strs(raw.get("studentYears"), 20, 8),
        doc_urls=_https(_strs(raw.get("docUrls"), 10, 600) + links + [raw.get("applyLink")]),
        description=desc,
        available=bool(raw.get("_availableForRegistering")),
    )
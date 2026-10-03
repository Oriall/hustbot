const $ = (id) => document.getElementById(id);
const say = (t) => ($("msg").textContent = t);

chrome.storage.local.get(["server"], (v) => { $("server").value = v.server || "http://localhost:5000"; });

// Hàm này được chèn vào trang qldt. Với mỗi ngày T2..CN của tuần hiện tại: chuyển đúng tháng (nếu tuần vắt qua 2 tháng),
// bấm đúng ô ngày, chờ khung "Thông tin chi tiết" đổi nội dung rồi đọc.
async function collect() {
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const waitFor = async (fn, ms) => {
    const end = Date.now() + ms;
    while (Date.now() < end) { if (fn()) return true; await sleep(100); }
    return false;
  };
  const panel = () => {
    const t = document.body.innerText, i = t.lastIndexOf("Thông tin chi tiết");
    if (i < 0) return "";
    const s = t.slice(i + "Thông tin chi tiết".length), j = s.indexOf("ĐẠI HỌC BÁCH KHOA HÀ NỘI");
    return (j >= 0 ? s.slice(0, j) : s).trim();
  };
  const header = () => {
    const m = document.body.innerText.match(/Tháng\s+(\d{1,2}),\s*(\d{4})/);
    return m ? { y: +m[2], m: +m[1] } : null;
  };
  const getCells = () => {                       // các ô số ngày trong lưới lịch tháng, theo thứ tự dòng
    const leaves = [...document.querySelectorAll("body *")]
      .filter((e) => e.children.length === 0 && /^\d{1,2}$/.test(e.textContent.trim()));
    for (const el of leaves) {
      for (let p = el.parentElement; p && p !== document.body; p = p.parentElement) {
        const inside = leaves.filter((c) => p.contains(c));
        if (inside.length >= 28 && inside.length <= 42) return inside;
        if (inside.length > 42) break;
      }
    }
    return [];
  };
  const gotoMonth = async (y, m) => {
    for (let i = 0; i < 4; i++) {
      const h = header();
      if (!h) return false;
      const cur = h.y * 12 + h.m, diff = y * 12 + m - cur;
      if (diff === 0) return true;
      const btn = [...document.querySelectorAll("body *")]
        .find((e) => e.children.length === 0 && e.textContent.trim() === (diff < 0 ? "‹" : "›"));
      if (!btn) return false;
      btn.click();
      await waitFor(() => { const n = header(); return n && n.y * 12 + n.m !== cur; }, 2000);
      await sleep(200);
    }
    return false;
  };

  const out = { texts: [], mode: "day", log: [] };
  const first = panel();
  const now = new Date();
  const monday = new Date(now.getFullYear(), now.getMonth(), now.getDate() - ((now.getDay() + 6) % 7));
  const seen = new Set();
  let prev = first, ok = 0;

  const count = (t) => (t.match(/\[\s*\d{1,2}:\d{2}\s*-\s*\d{1,2}:\d{2}\s*\]/g) || []).length;
  const findCell = (d) => {
    const cells = getCells();
    const idx = cells.findIndex((c, k) => {
      const v = +c.textContent.trim();
      const other = (k < 7 && v > 20) || (k >= 28 && v < 14);      // ngày tháng trước/sau hiện trên lưới
      return v === d.getDate() && !other;
    });
    return idx < 0 ? null : cells[idx];
  };
  // Lịch của mỗi tháng được tải bất đồng bộ: tới khi một ngày trong tháng có tiết, mới tin kết quả "trống".
  const loaded = new Set();

  for (let i = 0; i < 7; i++) {
    const d = new Date(monday.getFullYear(), monday.getMonth(), monday.getDate() + i);
    const label = (i < 6 ? "T" + (i + 2) : "CN") + " " + d.getDate() + "/" + (d.getMonth() + 1);
    if (!(await gotoMonth(d.getFullYear(), d.getMonth() + 1))) { out.log.push(label + ": không mở được tháng"); continue; }
    const key = d.getFullYear() * 12 + d.getMonth();
    const tries = loaded.has(key) ? 1 : 4;
    let t = "", n = 0, clicked = false;
    for (let a = 0; a < tries; a++) {
      const cell = findCell(d);
      if (!cell) break;
      cell.click();
      clicked = true;
      if (tries > 1) {
        await waitFor(() => count(panel()) > 0, 700 + 500 * a);   // chờ dữ liệu tháng về
      } else {
        await sleep(300);
        await waitFor(() => panel() !== prev, 700);
      }
      t = panel();
      n = count(t);
      if (n > 0) { loaded.add(key); break; }
    }
    if (!clicked) { out.log.push(label + ": không thấy ô ngày"); continue; }
    prev = t; ok++;
    out.log.push(label + ": " + n);
    if (t && !seen.has(t)) { seen.add(t); out.texts.push(t); }
  }
  if (ok === 0 && first) out.texts = [first];          // không bấm được ô nào: chỉ lấy ngày đang chọn
  out.mode = ok === 7 ? "week" : "day";
  return out;
}

$("send").onclick = async () => {
  const server = $("server").value.trim().replace(/\/$/, ""), token = $("token").value.trim();
  if (!server || !token) return say("Nhập địa chỉ HUSTBot và mã ghép nối.");
  chrome.storage.local.set({ server });

  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  let host = "";
  try { host = new URL(tab.url).hostname; } catch (e) { }
  if (host !== "qldt.hust.edu.vn") return say("Hãy mở trang Thời khoá biểu của qldt.hust.edu.vn rồi bấm lại.");

  say("Đang đọc lịch học (khoảng 10 giây)…");
  let res;
  try {
    const r = await chrome.scripting.executeScript({ target: { tabId: tab.id }, func: collect });
    res = r[0].result;
  } catch (e) { return say("Không đọc được trang này."); }
  if (!res || !res.texts.length) return say('Không thấy khung chi tiết. Hãy mở tab "Lịch" rồi thử lại.\n' + (res ? res.log.join(" • ") : ""));

  say("Đang gửi…");
  try {
    const r = await fetch(server + "/api/ext/timetable", {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: "Bearer " + token },
      body: JSON.stringify({ texts: res.texts, mode: res.mode }),
    });
    const d = await r.json();
    if (!r.ok || !d.ok) return say((d.error || "Lỗi " + r.status) + "\nTrang: " + res.log.join(" • "));
    $("token").value = "";
    const names = { 2: "T2", 3: "T3", 4: "T4", 5: "T5", 6: "T6", 7: "T7", 8: "CN" };
    const byDay = Object.keys(d.by_day || {}).map((k) => names[k] + ":" + d.by_day[k]).join(" ");
    say("Đã cập nhật " + d.synced + " tiết (" + (res.mode === "week" ? "cả tuần" : "chưa đủ 7 ngày, đã gộp thêm") + ").\n" +
        "Trang đọc được: " + res.log.join(" • ") + "\nServer lưu: " + byDay);
  } catch (e) { say("Không kết nối được máy chủ HUSTBot."); }
};
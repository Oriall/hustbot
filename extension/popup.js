const $ = (id) => document.getElementById(id);
const say = (t) => ($("msg").textContent = t);
const store = chrome.storage.local;
const session = chrome.storage.session || chrome.storage.local;   // mã ghép nối chỉ giữ tới khi đóng trình duyệt

store.get(["server", "uid"], (v) => {
  $("server").value = v.server || "http://localhost:5000";
  $("uid").value = v.uid || "";
});
session.get(["token"], (v) => { if (v.token) $("token").value = v.token; });
$("token").addEventListener("input", () => session.set({ token: $("token").value.trim() }));

// ----------------------------------------------------------------- tiện ích dùng chung
function creds() {
  const server = $("server").value.trim().replace(/\/$/, ""), token = $("token").value.trim();
  if (!server || !token) { say("Nhập địa chỉ HUSTBot và mã ghép nối (tạo trên web HUSTBot, hiệu lực 10 phút)."); return null; }
  store.set({ server });
  session.set({ token });
  return { server, token };
}

async function activeTab() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  let host = "";
  try { host = new URL(tab.url).hostname; } catch (e) { }
  return { tab, host };
}

async function post(c, path, body) {
  let r;
  try {
    r = await fetch(c.server + path, {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: "Bearer " + c.token },
      body: JSON.stringify(body),
    });
  } catch (e) { throw new Error("Không kết nối được máy chủ HUSTBot (" + c.server + ")."); }
  let d = {};
  try { d = await r.json(); } catch (e) { }
  return { ok: r.ok && d.ok === true, status: r.status, d };
}

// bắt mọi lỗi để popup luôn hiện thông báo thay vì im lặng
const run = (fn) => async () => {
  try { await fn(); } catch (e) { say("Lỗi: " + ((e && e.message) || e)); }
};

// ----------------------------------------------------------------- THỜI KHÓA BIỂU (qldt.hust.edu.vn)
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
  const getCells = () => {
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
      const other = (k < 7 && v > 20) || (k >= 28 && v < 14);
      return v === d.getDate() && !other;
    });
    return idx < 0 ? null : cells[idx];
  };
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
        await waitFor(() => count(panel()) > 0, 700 + 500 * a);
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
  if (ok === 0 && first) out.texts = [first];
  out.mode = ok === 7 ? "week" : "day";
  return out;
}

$("send").onclick = run(async () => {
  const c = creds(); if (!c) return;
  const { tab, host } = await activeTab();
  if (host !== "qldt.hust.edu.vn") return say("Hãy mở trang Thời khoá biểu của qldt.hust.edu.vn rồi bấm lại.");

  say("Đang đọc lịch học (khoảng 10 giây)…");
  const r = await chrome.scripting.executeScript({ target: { tabId: tab.id }, func: collect });
  const res = r[0] && r[0].result;
  if (!res || !res.texts.length) return say('Không thấy khung chi tiết. Hãy mở tab "Lịch" rồi thử lại.\n' + (res ? res.log.join(" • ") : ""));

  say("Đang gửi…");
  const { ok, status, d } = await post(c, "/api/ext/timetable", { texts: res.texts, mode: res.mode });
  if (!ok) return say((d.error || "Lỗi " + status) + "\nTrang: " + res.log.join(" • "));
  const names = { 2: "T2", 3: "T3", 4: "T4", 5: "T5", 6: "T6", 7: "T7", 8: "CN" };
  const byDay = Object.keys(d.by_day || {}).map((k) => names[k] + ":" + d.by_day[k]).join(" ");
  say("Đã cập nhật " + d.synced + " tiết (" + (res.mode === "week" ? "cả tuần" : "chưa đủ 7 ngày, đã gộp thêm") + ").\n" +
    "Trang đọc được: " + res.log.join(" • ") + "\nServer lưu: " + byDay);
});

// ----------------------------------------------------------------- HỌC BỔNG
// Cách 1: gọi ngay trong tab đang mở (chỉ chạy được nếu đang ở student.hust.edu.vn).
// Cách 2 (dự phòng, như code cũ của bạn): gọi từ chính extension. Extension có host_permissions
// của student.hust.edu.vn nên tự gửi kèm cookie đăng nhập, dùng được khi bạn đang ở tab qldt.
async function fetchAwards(url) {
  try {
    const r = await fetch(url, { credentials: "include", headers: { Accept: "application/json" } });
    const text = await r.text();
    let data = null;
    try { data = JSON.parse(text); } catch (e) { }
    return { status: r.status, data, head: text.slice(0, 120) };
  } catch (e) {
    return { status: 0, data: null, head: String(e) };
  }
}

function detectUid() {
  for (const e of performance.getEntriesByType("resource")) {
    const m = e.name.match(/[?&]userIds?=(\d{5,20})/);
    if (m) return m[1];
  }
  return "";
}

$("sendAwards").onclick = run(async () => {
  const c = creds(); if (!c) return;
  const { tab, host } = await activeTab();
  if (host !== "qldt.hust.edu.vn" && host !== "student.hust.edu.vn") {
    return say("Hãy mở trang qldt.hust.edu.vn hoặc student.hust.edu.vn (đã đăng nhập) rồi bấm lại.");
  }

  let uid = $("uid").value.trim();
  if (!/^\d{5,20}$/.test(uid)) {
    try {
      const r = await chrome.scripting.executeScript({ target: { tabId: tab.id }, func: detectUid });
      uid = ((r[0] && r[0].result) || "").trim();
    } catch (e) { }
    if (uid) $("uid").value = uid;
  }
  if (!/^\d{5,20}$/.test(uid)) {
    return say("Chưa tự tìm được userIds. Hãy tải lại trang student.hust.edu.vn rồi bấm lại, hoặc nhập tay (F12 → Network → request awards → số sau userIds=).");
  }
  store.set({ uid });

  say("Đang lấy danh sách học bổng…");
  const url = "https://student.hust.edu.vn/api/v1/awards?includeUnit=true&type=get_by_time&userIds=" + encodeURIComponent(uid);

  let res = null;
  try {
    const r = await chrome.scripting.executeScript({ target: { tabId: tab.id }, func: fetchAwards, args: [url] });
    res = r[0] && r[0].result;
  } catch (e) { }
  if (!res || res.status !== 200 || !res.data) {      // bị chặn / lỗi: gọi từ chính extension
    res = await fetchAwards(url);
  }

  if (!res || res.status !== 200 || !res.data) {
    return say("API học bổng trả về HTTP " + (res ? res.status : "?") +
      (res && res.status === 0 ? " (bị chặn hoặc lỗi mạng: " + res.head + ")" : "") +
      (res && res.status === 200 ? " nhưng không phải JSON" : "") +
      ".\nNếu là 401/403: hãy đăng nhập lại student.hust.edu.vn rồi thử lại.");
  }
  if (res.data.payload && Object.keys(res.data).length === 1) return say("API trả về dữ liệu mã hóa (payload), cần cách khác.");

  say("Đang gửi…");
  const { ok, status, d } = await post(c, "/api/ext/awards", { response: res.data });
  if (!ok) return say(d.error || "Lỗi " + status);
  const tot = typeof res.data.total === "number" ? res.data.total : null;
  say("Đã cập nhật " + d.synced + " học bổng (" + d.open + " đang mở đăng ký)." +
    (tot !== null && tot !== d.synced ? "\nLưu ý: cổng báo tổng " + tot + " nhưng chỉ nhận được " + d.synced + " (có thể có phân trang)." : ""));
});

// ----------------------------------------------------------------- CHƯƠNG TRÌNH ĐÀO TẠO (ctt-sis.hust.edu.vn)
// Chạy trong tab ctt-sis. Thử đọc bảng ngay trên trang đang mở; nếu không có thì tải StudentProgram.aspx.
// Chỉ lấy các ô của bảng học phần, không lấy tên, MSSV hay cookie.
async function readProgram() {
  function extract(doc) {
    const t = doc.querySelector('table[id$="gvStudentProgram_DXMainTable"]');
    if (!t) {
      const ids = [...doc.querySelectorAll('table[id$="DXMainTable"]')].map((x) => x.id).slice(0, 5);
      return { error: "Không thấy bảng chương trình đào tạo.", ids };
    }
    const txt = (n) => (n.textContent || "").replace(/\s+/g, " ").trim();
    const hr = t.querySelector('tr[id$="DXHeadersRow0"]');
    if (!hr) return { error: "Không thấy hàng tiêu đề của bảng." };
    const headers = [...hr.children].map(txt);
    const rows = [];
    t.querySelectorAll("tr.dxgvGroupRow, tr.dxgvDataRow").forEach((tr) => {
      const cells = [...tr.children];
      if (tr.classList.contains("dxgvGroupRow")) {
        const text = cells.map(txt).find((x) => x) || "";
        if (text) rows.push(["g", text.slice(0, 300)]);
      } else {
        const o = {};
        headers.forEach((h, i) => {
          const td = cells[i];
          if (!h || !td) return;
          o[h] = h === "Bắt buộc" ? (td.querySelector('[class*="CheckBoxChecked"]') ? "1" : "0") : txt(td).slice(0, 300);
        });
        rows.push(["d", o]);
      }
    });
    return { headers: headers.filter(Boolean), rows };
  }
  let res = extract(document);
  if (!res.error) return res;
  try {
    const r = await fetch("/Students/StudentProgram.aspx", { credentials: "include" });
    if (!r.ok) return { error: "HTTP " + r.status };
    res = extract(new DOMParser().parseFromString(await r.text(), "text/html"));
  } catch (e) { return { error: String(e) }; }
  return res;
}

$("sendProgram").onclick = run(async () => {
  const c = creds(); if (!c) return;
  const { tab, host } = await activeTab();
  if (host !== "ctt-sis.hust.edu.vn") return say("Hãy mở một trang của ctt-sis.hust.edu.vn (đã đăng nhập) rồi bấm lại.");

  say("Đang đọc chương trình đào tạo…");
  const r = await chrome.scripting.executeScript({ target: { tabId: tab.id }, func: readProgram });
  const res = r[0] && r[0].result;
  if (!res) return say("Không đọc được dữ liệu.");
  if (res.error) return say(res.error + (res.ids && res.ids.length ? "\nBảng tìm thấy: " + res.ids.join(", ") : ""));
  const nData = res.rows.filter((x) => x[0] === "d").length;
  if (!nData) return say("Bảng không có dòng học phần nào (các nhóm có thể đang thu gọn). Hãy mở trang Chương trình đào tạo, bung các nhóm rồi bấm lại.");

  say("Đang gửi " + nData + " học phần…");
  const { ok, status, d } = await post(c, "/api/ext/program", res);
  if (!ok) return say(d.error || "Lỗi " + status);
  say("Đã cập nhật " + d.synced + " học phần. Đã đạt " + d.earned + " TC" +
    (d.cpa_est !== null && d.cpa_est !== undefined ? ", CPA ước tính " + d.cpa_est : "") + ".");
});
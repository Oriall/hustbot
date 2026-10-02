/* Agent HUSTBot luôn hiện diện: giữ hội thoại qua các trang bằng sessionStorage */
(function () {
    var root = document.getElementById('ag');
    if (!root) return;

    var $ = function (id) { return document.getElementById(id); };
    var fab = $('ag-fab'), panel = $('ag-panel'), log = $('ag-log'), q = $('ag-q'),
        send = $('ag-send'), chipsBox = $('ag-chips');
    var KEY = 'hustbot.agent.v1', MAX_MSGS = 40, busy = false;
    var endpoint = root.getAttribute('data-page') || '';

    var GREETING = 'Chào bạn, mình là HUSTBot. Mình xem được trang bạn đang mở và có thể tra bài tập, lịch học, điểm rèn luyện hoặc làm giúp vài thao tác. Bạn cần gì?';
    var CHIPS = {
        overview: ['Hôm nay mình cần làm gì?', 'Deadline nào gấp nhất?', 'Lịch học hôm nay'],
        assignments: ['Bài nào nên làm trước?', 'Đánh dấu bài gấp nhất là đã xong', 'Tóm tắt yêu cầu bài thi sắp tới'],
        activities: ['Mình còn thiếu điểm ở đâu?', 'Nên đăng ký sự kiện nào?', 'Đăng ký giúp mình sự kiện hiến máu'],
        schedule: ['Ngày mai mình học gì?', 'Tuần này có tiết thực hành nào?', 'Mở trang bài tập']
    };

    /* ---------- trạng thái ---------- */
    function load() {
        try {
            var s = JSON.parse(sessionStorage.getItem(KEY));
            if (s && Array.isArray(s.msgs)) return s;
        } catch (e) { }
        return { open: false, msgs: [] };
    }
    var state = load();
    function save() {
        try { sessionStorage.setItem(KEY, JSON.stringify({ open: state.open, msgs: state.msgs.slice(-MAX_MSGS) })); } catch (e) { }
    }

    /* ---------- hiển thị ---------- */
    function esc(s) { return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;'); }
    function inline(s) { return esc(s).replace(/\*\*(.+?)\*\*/g, '<b>$1</b>').replace(/`([^`]+)`/g, '<code>$1</code>'); }
    function md(text) {
        var out = [], list = null;
        function close() { if (list) { out.push('</' + list + '>'); list = null; } }
        text.split('\n').forEach(function (ln) {
            var ul = ln.match(/^\s*[-*•]\s+(.*)/), ol = ln.match(/^\s*\d+[.)]\s+(.*)/);
            if (ul || ol) {
                var t = ul ? 'ul' : 'ol';
                if (list !== t) { close(); out.push('<' + t + '>'); list = t; }
                out.push('<li>' + inline((ul || ol)[1]) + '</li>');
            } else if (ln.trim() === '') { close(); }
            else { close(); out.push('<p>' + inline(ln) + '</p>'); }
        });
        close();
        return out.join('');
    }
    function down() { log.scrollTop = log.scrollHeight; }

    function bubble(role, text, extra) {
        var d = document.createElement('div');
        d.className = 'ag-m ' + (role === 'user' ? 'u' : 'b');
        if (role === 'user') { d.textContent = text; }
        else {
            d.innerHTML = md(text);
            if (extra && extra.src) { var s = document.createElement('small'); s.className = 'src'; s.textContent = 'Nguồn: ' + extra.src; d.appendChild(s); }
            if (extra && extra.note) { var n = document.createElement('small'); n.className = 'act'; n.textContent = extra.note; d.appendChild(n); }
        }
        log.appendChild(d); down();
        return d;
    }

    function typing() {
        var d = document.createElement('div');
        d.className = 'ag-m b';
        d.innerHTML = '<span class="ag-typing"><i></i><i></i><i></i></span>';
        log.appendChild(d); down();
        return d;
    }

    function renderAll() {
        log.innerHTML = '';
        bubble('model', GREETING);
        state.msgs.forEach(function (m) { bubble(m.role, m.text, m); });
    }

    function renderChips() {
        chipsBox.innerHTML = '';
        if (state.msgs.length > 0) return; // chỉ gợi ý khi mới bắt đầu
        (CHIPS[endpoint] || []).forEach(function (t) {
            var b = document.createElement('button');
            b.className = 'chip'; b.textContent = t;
            b.addEventListener('click', function () { ask(t); });
            chipsBox.appendChild(b);
        });
    }

    /* ---------- đóng/mở ---------- */
    function setOpen(v, focus) {
        state.open = v; panel.hidden = !v;
        fab.setAttribute('aria-expanded', v ? 'true' : 'false');
        save();
        if (v) { down(); if (focus !== false) q.focus(); }
    }

    /* ---------- gửi tin ---------- */
    function setBusy(v) { busy = v; send.disabled = v; }

    function runActions(actions) {
        (actions || []).forEach(function (a) {
            if (a.type === 'navigate' && a.url) setTimeout(function () { location.href = a.url; }, 900);
            else if (a.type === 'reload') setTimeout(function () { location.reload(); }, 900);
        });
    }

    function actionNote(actions) {
        if (!actions || !actions.length) return '';
        var a = actions[0];
        return a.type === 'navigate' ? '→ Đang chuyển tới ' + (a.label || 'trang khác') + '…' : '↻ Đang cập nhật trang…';
    }

    function ask(text) {
        var v = (text || q.value).trim();
        if (!v || busy) return;
        if (!state.open) setOpen(true, false);
        q.value = ''; q.style.height = 'auto';
        chipsBox.innerHTML = '';

        var history = state.msgs.slice(-24).map(function (m) { return { role: m.role, text: m.text }; });
        state.msgs.push({ role: 'user', text: v });
        bubble('user', v); save(); setBusy(true);
        var wait = typing();

        fetch('/api/agent', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ q: v, history: history, page: { endpoint: endpoint, path: location.pathname, title: document.title } })
        })
            .then(function (r) { return r.json().then(function (d) { return { ok: r.ok, d: d }; }); })
            .then(function (res) {
                wait.remove();
                var note = res.ok ? actionNote(res.d.actions) : '';
                var m = { role: 'model', text: res.d.ans, src: res.d.src || '', note: note };
                if (res.ok) state.msgs.push(m); else state.msgs.pop(); // lỗi thì không lưu vào lịch sử
                bubble('model', m.text, m); save();
                if (res.ok) runActions(res.d.actions);
            })
            .catch(function () { wait.remove(); state.msgs.pop(); save(); bubble('model', 'Không kết nối được máy chủ. Bạn thử lại sau nhé.'); })
            .finally(function () { setBusy(false); if (state.open) q.focus(); });
    }

    /* ---------- sự kiện ---------- */
    fab.addEventListener('click', function () { setOpen(!state.open); });
    $('ag-close').addEventListener('click', function () { setOpen(false); });
    $('ag-clear').addEventListener('click', function () { state.msgs = []; save(); renderAll(); renderChips(); });
    send.addEventListener('click', function () { ask(); });
    q.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); ask(); }
    });
    q.addEventListener('input', function () {
        q.style.height = 'auto'; q.style.height = Math.min(q.scrollHeight, 110) + 'px';
    });
    document.addEventListener('keydown', function (e) {
        if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') { e.preventDefault(); setOpen(!state.open); }
        else if (e.key === 'Escape' && state.open) setOpen(false);
    });

    // Thanh tìm kiếm trên cùng: Enter để hỏi agent
    var topSearch = document.querySelector('header.top .search input');
    if (topSearch) {
        topSearch.addEventListener('keydown', function (e) {
            if (e.key === 'Enter' && topSearch.value.trim()) { e.preventDefault(); var t = topSearch.value; topSearch.value = ''; ask(t); }
        });
    }

    /* ---------- khởi tạo ---------- */
    renderAll(); renderChips();
    panel.hidden = !state.open;
    fab.setAttribute('aria-expanded', state.open ? 'true' : 'false');
    if (state.open) down();
})();
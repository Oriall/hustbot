/* Kết nối LMS: modal + trạng thái. Dùng chung mọi trang (nạp từ base.html). */
(function () {
    'use strict';
    var dlg = document.getElementById('cn-dlg');
    if (!dlg) return;

    var PROV = 'qldt';
    var $ = function (id) { return document.getElementById(id); };
    var all = function (sel, fn) { Array.prototype.forEach.call(document.querySelectorAll(sel), fn); };
    var conn = null, pairTimer = null, pollTimer = null;

    function api(method, url, body) {
        return fetch(url, {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            body: body ? JSON.stringify(body) : undefined
        }).then(function (r) {
            return r.json().catch(function () { return {}; })
                .then(function (d) { return { ok: r.ok, status: r.status, d: d }; });
        });
    }

    function ago(iso) {
        if (!iso) return 'chưa đồng bộ';
        var m = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 60000));
        if (m < 1) return 'vừa xong';
        if (m < 60) return m + ' phút trước';
        if (m < 1440) return Math.floor(m / 60) + ' giờ trước';
        return Math.floor(m / 1440) + ' ngày trước';
    }

    function describe(c) {
        if (!c) return ['none', 'Chưa kết nối'];
        if (c.status === 'ok') return ['ok', 'Đã kết nối • ' + ago(c.last_sync)];
        if (c.status === 'expired') return ['warn', 'Phiên hết hạn, hãy kết nối lại'];
        return ['err', 'Lỗi đồng bộ' + (c.error ? ': ' + c.error : '')];
    }

    function paint() {
        var d = describe(conn);
        all('[data-cn-dot]', function (el) { el.dataset.state = d[0]; });
        all('[data-cn-text]', function (el) { el.textContent = d[1]; });
        all('[data-cn-open]', function (el) { el.textContent = conn ? 'Quản lý' : 'Kết nối'; });
        $('cn-sync').hidden = true;
        $('cn-off').hidden = !conn;
    }

    function refresh() {
        return api('GET', '/api/connections').then(function (r) {
            if (r.ok && Array.isArray(r.d)) {
                conn = r.d.filter(function (c) { return c.provider === PROV; })[0] || null;
                paint();
            }
            return conn;
        });
    }

    function msg(text, kind) {
        var el = $('cn-msg');
        el.textContent = text || '';
        el.className = 'cn-msg ' + (kind || '');
        el.hidden = !text;
    }

    function setBusy(btn, busy) { btn.disabled = busy; btn.classList.toggle('busy', busy); }
    function reload() { location.reload(); }

    /* ---------- mở / đóng ---------- */
    function open() {
        msg('');
        refresh();
        if (!dlg.open) dlg.showModal();
    }
    $('cn-close').addEventListener('click', function () { dlg.close(); });
    dlg.addEventListener('click', function (e) { if (e.target === dlg) dlg.close(); });  // bấm nền mờ
    all('[data-cn-open]', function (el) { el.addEventListener('click', open); });
    var side = $('cn-side');
    if (side) {
        side.addEventListener('click', open);
        side.addEventListener('keydown', function (e) { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); open(); } });
    }

    /* ---------- mã ghép nối cho extension ---------- */
    function stopPair() { clearInterval(pairTimer); clearInterval(pollTimer); pairTimer = pollTimer = null; }
    function resetCode() {
        $('cn-code').textContent = '••••••••';
        $('cn-code').classList.remove('live');
        $('cn-copy').disabled = true;
        $('cn-timer').textContent = '';
    }

    function startTimer(sec) {
        var end = Date.now() + sec * 1000;
        function tick() {
            var left = Math.round((end - Date.now()) / 1000);
            if (left <= 0) { stopPair(); resetCode(); msg('Mã đã hết hạn, hãy tạo mã mới.', 'err'); return; }
            $('cn-timer').textContent = 'Còn ' + Math.floor(left / 60) + ':' + ('0' + (left % 60)).slice(-2);
        }
        tick();
        pairTimer = setInterval(tick, 1000);
    }

    // Sau khi tạo mã, hỏi server mỗi 3s: extension đã gửi cookie chưa?
    function startPoll(base) {
        pollTimer = setInterval(function () {
            refresh().then(function (c) {
                var now = c ? c.last_sync + '|' + c.status : '';
                if (!now || now === base) return;
                stopPair(); resetCode();
                if (c.status === 'ok') { msg('Kết nối thành công! Đang tải lại dữ liệu…', 'ok'); setTimeout(reload, 1200); }
                else msg(describe(c)[1], 'err');
            });
        }, 3000);
    }

    $('cn-pair').addEventListener('click', function () {
        var btn = this, base = conn ? conn.last_sync + '|' + conn.status : '';
        stopPair(); msg('');
        setBusy(btn, true);
        api('POST', '/api/connections/pair').then(function (r) {
            setBusy(btn, false);
            if (!r.ok || !r.d.token) { msg('Không tạo được mã, bạn thử lại nhé.', 'err'); return; }
            $('cn-code').textContent = r.d.token;
            $('cn-code').classList.add('live');
            $('cn-copy').disabled = false;
            startTimer(r.d.expires_in || 600);
            startPoll(base);
        }).catch(function () { setBusy(btn, false); msg('Không kết nối được máy chủ.', 'err'); });
    });

    $('cn-copy').addEventListener('click', function () {
        var t = $('cn-code').textContent, b = this;
        function done() { b.lastChild.textContent = 'Đã chép'; setTimeout(function () { b.lastChild.textContent = 'Chép'; }, 1500); }
        if (navigator.clipboard) navigator.clipboard.writeText(t).then(done);
        else { var r = document.createRange(); r.selectNode($('cn-code')); getSelection().removeAllRanges(); getSelection().addRange(r); document.execCommand('copy'); done(); }
    });

    /* ---------- dán cookie thủ công ---------- */
    $('cn-paste').addEventListener('click', function () {
        var btn = this, v = $('cn-cookie').value.trim();
        if (!v) { msg('Hãy dán token hoặc cookie vào ô phía trên.', 'err'); return; }
        setBusy(btn, true); msg('Đang kiểm tra phiên đăng nhập…');
        api('POST', '/api/connections/' + PROV, { cookie: v }).then(function (r) {
            setBusy(btn, false);
            if (r.ok && r.d.ok) {
                $('cn-cookie').value = '';
                msg('Đã kết nối, đồng bộ ' + r.d.synced + ' bài. Đang tải lại…', 'ok');
                refresh(); setTimeout(reload, 1200);
            } else if (r.d.status === 'expired') {
                msg('Token/cookie này chưa đăng nhập được Cổng QLĐT (sai hoặc đã hết hạn).', 'err'); refresh();
            } else if (r.d.status === 'error') {
                msg('LMS trả lỗi khi đồng bộ, xem trạng thái ở trên.', 'err'); refresh();
            } else {
                msg(r.d.error || 'Không kết nối được.', 'err');
            }
        }).catch(function () { setBusy(btn, false); msg('Không kết nối được máy chủ.', 'err'); });
    });

    /* ---------- đồng bộ / ngắt kết nối ---------- */
    // Trả về {text, reload} để nút "Đồng bộ tức thì" ở trang Tổng quan dùng lại
    function syncNow() {
        setTimeout(open, 300);
        return Promise.resolve({ text: 'Gửi lịch bằng extension', reload: false });
    }

    $('cn-sync').addEventListener('click', function () {
        var btn = this;
        setBusy(btn, true); msg('Đang đồng bộ…');
        syncNow().then(function (r) {
            setBusy(btn, false);
            msg(r.text, r.reload ? 'ok' : 'err');
            if (r.reload) setTimeout(reload, 1000);
        });
    });

    $('cn-off').addEventListener('click', function () {
        if (!confirm('Ngắt kết nối Cổng QLĐT? Token và thời khóa biểu đã đồng bộ sẽ bị xóa.')) return;
        var btn = this;
        setBusy(btn, true);
        api('DELETE', '/api/connections/' + PROV).then(function (r) {
            setBusy(btn, false);
            if (!r.ok) { msg('Không ngắt được kết nối.', 'err'); return; }
            conn = null; paint(); stopPair(); resetCode();
            msg('Đã ngắt kết nối và xóa thời khóa biểu đã đồng bộ.', 'ok');
            setTimeout(reload, 900);
        });
    });

    dlg.addEventListener('close', function () { $('cn-cookie').value = ''; });

    window.HBConnect = { open: open, syncNow: syncNow, refresh: refresh };
    refresh();
})();
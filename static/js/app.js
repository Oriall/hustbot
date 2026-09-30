const $ = (s, r = document) => r.querySelector(s), $$ = (s, r = document) => [...r.querySelectorAll(s)];

// Thông báo đẩy (Notification API) - nhắc bài sắp đến hạn
$('#btn-notify')?.addEventListener('click', async () => {
  if (!('Notification' in window)) return alert('Trình duyệt không hỗ trợ thông báo.');
  if (await Notification.requestPermission() === 'granted') {
    new Notification('HUSTBot', { body: 'Đã bật nhắc nhở bài tập sắp đến hạn.' });
    $('#btn-notify').textContent = 'Đã bật thông báo';
  }
});

// Trang bài tập: lọc nguồn / trạng thái / mã môn, sắp xếp, panel chi tiết, đếm ngược
if ($('#detail')) {
  let timer, src = 'all', st = 'all', kw = '';
  const pad = n => String(n).padStart(2, '0');
  const show = id => {
    const t = TASKS.find(x => x.id == id); if (!t) return;
    $$('#list .card').forEach(c => c.classList.toggle('on', c.dataset.id == id));
    const wt = t.weight ? ` (${t.weight}%)` : '';
    $('#detail').innerHTML = `
      <div class="dh"><div class="between"><div class="tags"><span class="pill">${t.kind}${wt}</span><span class="tag s-${t.source}"><i class="sd"></i>${t.source_name}</span></div>
        <div class="tags"><button class="ibtn" title="Chia sẻ"><span class="icon">share</span></button><button class="ibtn" title="Ưu tiên"><span class="icon">bookmark</span></button></div></div>
        <h2 class="lg">${t.title}</h2>
        <p class="muted"><b class="code">${t.code}</b> - ${t.course} - Mã lớp: ${t.cls} - ${t.dept}</p>
        <p class="muted"><span class="icon sm">person</span> Giảng viên: ${t.teacher}</p></div>
      <div class="count"><div class="between"><div><small>Thời gian còn lại</small><p class="muted">Hạn chót: ${t.due}</p></div>
        <div class="num" id="cd">--:--:--</div></div><div class="prog"><div id="pg"></div></div></div>
      <div class="specs">${t.specs.map(s => `<div class="spec"><small>${s[0]}</small><b>${s[1]}</b><small>${s[2]}</small></div>`).join('')}</div>
      <div class="digest"><div class="between"><b><span class="icon sm">neurology</span> HUSTBot tóm tắt yêu cầu</b><span class="tag ok">Tự động trích xuất</span></div>
        ${t.digest.map(d => `<div><b class="dt">${d[0]}</b><ul>${d[1].map(x => `<li>${x}</li>`).join('')}</ul></div>`).join('')}
        ${t.formulas.length ? `<div><b class="dt">Công thức cần nhớ</b><div class="code-box">${t.formulas.map(f => `<div class="between"><span>${f[0]}</span><b>${f[1]}</b></div>`).join('')}</div></div>` : ''}</div>
      <div class="digest"><b><span class="icon sm">notifications_active</span> Nhắc hẹn cá nhân</b>
        <div class="rem"><label><input type="checkbox" checked> Thông báo trình duyệt (-1h)</label><label><input type="checkbox" checked> Thông báo trình duyệt (-15 phút)</label><label><input type="checkbox"> Telegram Bot</label></div></div>
      <div class="between"><div class="tags"><button class="btn"><span class="icon">psychology</span>Hỏi AI giải thích dạng đề</button><button class="btn" id="done" title="Đánh dấu đã nộp"><span class="icon">check</span></button></div>
        <a class="btn primary cta" href="#">${t.cta}<span class="icon">open_in_new</span></a></div>`;
    $('#done').onclick = e => e.currentTarget.classList.toggle('primary');
    clearInterval(timer);
    const due = new Date(t.due_iso), tick = () => {
      const s = Math.max(0, Math.floor((due - new Date()) / 1000));
      $('#cd').textContent = `${pad(Math.floor(s / 3600))}:${pad(Math.floor(s % 3600 / 60))}:${pad(s % 60)}`;
      $('#pg').style.width = Math.min(100, 100 - s / (7 * 86400) * 100) + '%'; };
    tick(); timer = setInterval(tick, 1000);
  };
  const apply = () => {
    $$('#list .card').forEach(c => {
      const t = TASKS.find(x => x.id == c.dataset.id);
      c.hidden = (src !== 'all' && t.source !== src) || (st === 'soon' && t.mins >= 1440) || (kw && !t.code.toLowerCase().includes(kw));
    });
    $$('#list .grp').forEach(g => g.hidden = !$$('.card:not([hidden])', g).length);
  };
  const seg = (sel, fn) => $$(sel + ' button').forEach(b => b.onclick = () => { $$(sel + ' button').forEach(x => x.classList.toggle('on', x === b)); fn(b); apply(); });
  seg('#tabs', b => src = b.dataset.src);
  seg('#status', b => st = b.dataset.st);
  $('#kw').oninput = e => { kw = e.target.value.trim().toLowerCase(); apply(); };
  $('#sort').onchange = e => $$('#list .grp').forEach(g => {
    const key = c => { const t = TASKS.find(x => x.id == c.dataset.id); return e.target.value === 'weight' ? -t.weight : e.target.value === 'code' ? t.code : t.mins; };
    $$('.card', g).sort((a, b) => key(a) > key(b) ? 1 : -1).forEach(c => g.append(c)); });
  $$('#list .card').forEach(c => c.onclick = () => show(c.dataset.id));
  show(TASKS[0]?.id);
}

// Trang chatbot
if ($('#log')) {
  const add = (txt, who, src) => { const d = document.createElement('div'); d.className = 'msg ' + who;
    d.textContent = txt; if (src) d.innerHTML += `<small>Nguồn: ${src}</small>`; $('#log').append(d); d.scrollIntoView(); };
  const ask = async q => { if (!q.trim()) return; add(q, 'me'); $('#q').value = '';
    const r = await (await fetch('/api/chat', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ q }) })).json();
    add(r.ans, 'bot', r.src); };
  $('#send').onclick = () => ask($('#q').value);
  $('#q').onkeydown = e => e.key === 'Enter' && ask($('#q').value);
  $$('.chip').forEach(c => c.onclick = () => ask(c.textContent));
}

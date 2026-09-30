// Tính điểm rèn luyện theo sự kiện đã đăng ký; tiêu chí đầy điểm thì ẩn sự kiện
const crit = Object.fromEntries($$('.crit').map(c => [c.dataset.id, { el: c, now: +c.dataset.now, max: +c.dataset.max, add: 0 }]));
function render() {
  let total = 0;
  Object.values(crit).forEach(c => {
    const v = Math.min(c.max, c.now + c.add); total += v;
    $('.val', c.el).textContent = v + '/' + c.max;
    $('.bar div', c.el).style.width = (v / c.max * 100) + '%';
  });
  $('#total').textContent = 'Dự kiến: ' + total + '/100';
  $$('.ev').forEach(e => {
    const c = crit[e.dataset.crit], done = e.classList.contains('joined');
    e.hidden = !done && c.now + c.add >= c.max;
    $('.p', e).textContent = e.dataset.pts;
  });
}
$$('.ev .reg').forEach(b => b.onclick = () => {
  const e = b.closest('.ev'), c = crit[e.dataset.crit], p = +e.dataset.pts;
  const joined = e.classList.toggle('joined'); c.add += joined ? p : -p;
  b.classList.toggle('primary', joined); render();
});
render();

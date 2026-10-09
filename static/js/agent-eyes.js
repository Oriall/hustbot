(function () {
  var ag = document.getElementById('ag'), fab = document.getElementById('ag-fab'),
      log = document.getElementById('ag-log');
  if (!ag || !fab) return;

  var raf = 0;
  document.addEventListener('mousemove', function (e) {
    if (raf) return;
    raf = requestAnimationFrame(function () {
      raf = 0;
      var r = fab.getBoundingClientRect(),
          dx = e.clientX - (r.left + r.width / 2), dy = e.clientY - (r.top + r.height / 2),
          d = Math.hypot(dx, dy) || 1, k = Math.min(1, d / 220);
      ag.style.setProperty('--ex', (dx / d * k).toFixed(2));
      ag.style.setProperty('--ey', (dy / d * k).toFixed(2));
    });
  }, { passive: true });

  // đang "gõ" (có dấu ba chấm) -> trạng thái thinking
  if (log) new MutationObserver(function () {
    ag.dataset.state = log.querySelector('.ag-typing') ? 'thinking' : 'idle';
  }).observe(log, { childList: true, subtree: true });
})();
(function () {
  var log = document.getElementById('ag-log');
  if (!log) return;

  function life(m) {
    var n = (m.textContent || '').length;
    return m.classList.contains('u')
      ? 3500
      : Math.min(4500 + n * 55, 22000);   // bot: dài thì ở lâu hơn
  }

  function vanish(m) {
    m.classList.add('out');
    setTimeout(function () { m.classList.add('gone'); }, 720);
  }

  function schedule(m) {
    clearTimeout(m._t);
    m._len = (m.textContent || '').length;
    m._t = setTimeout(function () {
      // còn đang gõ / đang stream chữ -> hoãn lại
      var now = (m.textContent || '').length;
      if (m.querySelector('.ag-typing') || now !== m._len) return schedule(m);
      vanish(m);
    }, life(m));
  }

  function watch(m) {
    if (m._w) return;
    m._w = true;
    schedule(m);
    // rê chuột vào thì giữ lại, rời ra thì đếm lại
    m.addEventListener('mouseenter', function () {
      clearTimeout(m._t);
      m.classList.remove('out');
    });
    m.addEventListener('mouseleave', function () { schedule(m); });
  }

  new MutationObserver(function (list) {
    list.forEach(function (r) {
      r.addedNodes.forEach(function (n) {
        if (n.nodeType === 1 && n.classList.contains('ag-m')) watch(n);
      });
    });
  }).observe(log, { childList: true });

  // nút "cuộc trò chuyện mới" / đóng panel: không cần xử lý thêm
})();
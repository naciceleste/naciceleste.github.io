/* Cielo animado de fondo (canvas 2D). Si falla, queda el cielo CSS de siempre. */
(function () {
  var sky = document.querySelector(".sky");
  if (!sky || !window.requestAnimationFrame) return;
  var c = document.createElement("canvas");
  c.className = "cielo-canvas";
  var ctx = c.getContext && c.getContext("2d");
  if (!ctx) return;
  sky.appendChild(c);
  document.documentElement.classList.add("cielo-on");
  var root = document.documentElement;
  var rm = window.matchMedia("(prefers-reduced-motion: reduce)");
  var W = 0, H = 0, dpr = 1, stars = [], raf = 0, last = 0;
  function dark() { return root.getAttribute("data-theme") === "dark"; }
  function make() {
    dpr = Math.min(window.devicePixelRatio || 1, 2);
    W = window.innerWidth; H = window.innerHeight;
    c.width = Math.round(W * dpr); c.height = Math.round(H * dpr);
    c.style.width = W + "px"; c.style.height = H + "px";
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    var n = Math.round(W * H / (W < 700 ? 9000 : 6500));
    n = Math.min(n, W < 700 ? 70 : 180);
    stars = [];
    for (var i = 0; i < n; i++) {
      var big = Math.random() < 0.12;
      stars.push({ x: Math.random() * W, y: Math.random() * H,
        r: big ? 1.6 + Math.random() * 1.4 : 0.5 + Math.random() * 1.1,
        big: big, ph: Math.random() * 6.28, sp: 0.4 + Math.random() * 1.2,
        vx: (Math.random() - 0.5) * 4, vy: -1 - Math.random() * 4,
        hue: Math.random() < 0.35 ? 1 : 0 });
    }
  }
  function draw(t) {
    var d = dark(), s = t / 1000;
    ctx.clearRect(0, 0, W, H);
    /* deriva de color suave según el scroll */
    var max = Math.max(1, document.documentElement.scrollHeight - H);
    var p = Math.min(1, (window.scrollY || 0) / max);
    ctx.fillStyle = d ? "rgba(" + Math.round(60 + 60 * p) + ",40," + Math.round(140 - 30 * p) + ",0.18)"
                      : "rgba(255," + Math.round(200 + 30 * (1 - p)) + ",240," + (0.10 * p).toFixed(3) + ")";
    ctx.fillRect(0, 0, W, H);
    for (var i = 0; i < stars.length; i++) {
      var st = stars[i];
      var a = rm.matches ? 0.75 : 0.35 + 0.65 * (0.5 + 0.5 * Math.sin(st.ph + s * st.sp));
      var col = d ? (st.hue ? "190,215,255" : "255,255,255") : (st.hue ? "150,200,255" : "255,255,255");
      ctx.globalAlpha = a * (d ? 1 : 0.9);
      ctx.fillStyle = "rgb(" + col + ")";
      if (st.big) {
        ctx.shadowColor = "rgba(" + col + ",.9)"; ctx.shadowBlur = d ? 8 : 6;
        /* destello de 4 puntas */
        var r = st.r * 2.4;
        ctx.beginPath();
        ctx.moveTo(st.x, st.y - r); ctx.quadraticCurveTo(st.x, st.y, st.x + r, st.y);
        ctx.quadraticCurveTo(st.x, st.y, st.x, st.y + r); ctx.quadraticCurveTo(st.x, st.y, st.x - r, st.y);
        ctx.quadraticCurveTo(st.x, st.y, st.x, st.y - r); ctx.fill();
        ctx.shadowBlur = 0;
      } else {
        ctx.beginPath(); ctx.arc(st.x, st.y, st.r, 0, 6.283); ctx.fill();
      }
    }
    ctx.globalAlpha = 1;
  }
  function step(t) {
    raf = 0;
    var dt = last ? Math.min(0.1, (t - last) / 1000) : 0; last = t;
    for (var i = 0; i < stars.length; i++) {
      var st = stars[i]; st.x += st.vx * dt; st.y += st.vy * dt;
      if (st.y < -5) { st.y = H + 5; st.x = Math.random() * W; }
      if (st.x < -5) st.x = W + 5; else if (st.x > W + 5) st.x = -5;
    }
    draw(t);
    start();
  }
  function start() {
    if (raf || document.hidden || rm.matches) return;
    raf = requestAnimationFrame(step);
  }
  function stop() { if (raf) cancelAnimationFrame(raf); raf = 0; last = 0; }
  function redraw() { draw(performance.now()); }
  document.addEventListener("visibilitychange", function () { document.hidden ? stop() : start(); });
  var rt; window.addEventListener("resize", function () { clearTimeout(rt); rt = setTimeout(function () { make(); redraw(); }, 150); });
  window.addEventListener("scroll", function () { if (rm.matches) redraw(); }, { passive: true });
  if (rm.addEventListener) rm.addEventListener("change", function () { stop(); redraw(); start(); });
  new MutationObserver(redraw).observe(root, { attributes: true, attributeFilter: ["data-theme"] });
  make(); redraw(); start();
})();

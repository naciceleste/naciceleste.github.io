/* @naciceleste — versión 2: cuadrícula de imágenes estilo portafolio.
   - Twitter/X: imagen enlazada directo desde pbs.twimg.com (dato guardado en media.js)
   - Instagram: embed oficial (iframe) recortado para que solo se vea la imagen
   Nada se descarga ni se aloja aquí. */
(function () {
  "use strict";
  var CFG = window.SITE_CONFIG || {}, USER = CFG.username || "naciceleste", PROFILES = CFG.profiles || {};
  var MEDIA = window.POST_MEDIA || {};
  var RAW = Array.isArray(window.POSTS) ? window.POSTS : [];
  var TZ = "America/Costa_Rica";
  var IG_W = 640;          // ancho al que se dibuja el embed de Instagram antes de escalarlo
  var IG_HEADER = 54;      // alto del encabezado del embed (avatar + usuario)
  var IG_FOOTER = 154;     // alto del pie del embed (me gusta, comentarios…)
  var LABEL = { x: "Twitter", instagram: "Instagram", youtube: "YouTube" };
  var $ = function (s) { return document.querySelector(s); };

  /* ---------- links ---------- */
  function parse(url) {
    var u; try { u = new URL(String(url).trim()); } catch (e) { return null; }
    var host = u.hostname.replace(/^(www\.|m\.|mobile\.)/, ""), parts = u.pathname.split("/").filter(Boolean);
    if (host === "x.com" || host === "twitter.com") {
      var i = parts.indexOf("status");
      if (i > 0 && /^\d+$/.test(parts[i + 1] || "")) return { network: "x", id: parts[i + 1], user: parts[0], url: "https://x.com/" + parts[0] + "/status/" + parts[i + 1] };
    }
    if (host === "instagram.com") {
      for (var j = 0; j < parts.length - 1; j++) if (/^(p|reel|reels|tv)$/.test(parts[j])) {
        var k = parts[j] === "reels" ? "reel" : parts[j];
        return { network: "instagram", id: parts[j + 1], url: "https://www.instagram.com/" + k + "/" + parts[j + 1] + "/" };
      }
    }
    if (/(^|\.)youtube\.com$|^youtu\.be$/.test(host)) {
      var id = host === "youtu.be" ? parts[0] : (u.searchParams.get("v") || (/^(shorts|embed|live)$/.test(parts[0] || "") ? parts[1] : null));
      if (id) return { network: "youtube", id: id, url: "https://www.youtube.com/watch?v=" + id };
    }
    return null;
  }

  /* ---------- fechas de publicación ---------- */
  // X: el id del tuit lleva la hora de publicación (snowflake)
  function xDate(id) { try { return new Date(Number((BigInt(id) >> 22n) + 1288834974657n)); } catch (e) { return null; } }
  // Instagram: el código del post lleva la hora en que se creó el medio (aprox., minutos/horas antes de publicar)
  function igDate(code) {
    try {
      var A = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_", n = 0n;
      for (var i = 0; i < code.length && i < 11; i++) n = n * 64n + BigInt(A.indexOf(code[i]));
      return new Date(Number((n >> 23n) + 1314220021721n));
    } catch (e) { return null; }
  }
  function ddmmaa(d) {
    try {
      var p = {}; new Intl.DateTimeFormat("es-CR", { timeZone: TZ, day: "2-digit", month: "2-digit", year: "2-digit" })
        .formatToParts(d).forEach(function (x) { p[x.type] = x.value; });
      return p.day + "/" + p.month + "/" + p.year;
    } catch (e) { return ""; }
  }
  function addedDate(s) { var m = /^(\d{4})-(\d{1,2})-(\d{1,2})/.exec(s || ""); return m ? new Date(+m[1], +m[2] - 1, +m[3]).getTime() : 0; }

  var posts = RAW.map(function (e, idx) {
    e = typeof e === "string" ? { url: e } : (e || {});
    var p = e.url && parse(e.url); if (!p) return null;
    var m = MEDIA[p.network + ":" + p.id] || null;
    var date = m && m.date ? new Date(m.date) : (p.network === "x" ? xDate(p.id) : p.network === "instagram" ? igDate(p.id) : null);
    return { idx: idx, added: addedDate(e.date), network: p.network, id: p.id, url: p.url, user: p.user, media: m, date: date,
      approx: !(m && m.date) && p.network === "instagram" };
  }).filter(Boolean);
  // mi lista de YouTube (youtube.js): se suman como mosaicos, sin repetir los que ya están en posts.js
  (function () {
    var Y = (window.YOUTUBE && window.YOUTUBE.videos) || [], have = {};
    posts.forEach(function (p) { if (p.network === "youtube") have[p.id] = p; });
    Y.forEach(function (v, i) {
      var pub = /^\d{4}-\d{2}-\d{2}/.test(v.published || "") ? new Date(v.published + "T12:00:00Z") : null;
      var old = have[v.id];
      if (old) { old.title = v.title; old.channel = v.channel; old.short = !!v.short; old.date = old.date || pub; return; }
      posts.push({ idx: 100000 + i, added: addedDate(v.added), network: "youtube", id: v.id, title: v.title, channel: v.channel,
        short: !!v.short, date: pub, url: v.short ? "https://www.youtube.com/shorts/" + v.id : "https://www.youtube.com/watch?v=" + v.id });
    });
  })();
  posts.sort(function (a, b) { return b.added - a.added || a.idx - b.idx; });

  /* ---------- encabezado ---------- */
  var state = "all";
  function header() {
    var main = (PROFILES.instagram && PROFILES.instagram.url) || (PROFILES.x && PROFILES.x.url) || "#";
    var nm = $("#name"); nm.textContent = "@" + USER; nm.href = main; nm.target = "_blank"; nm.rel = "noopener";
    var f = $("#filters"), has = {};
    posts.forEach(function (p) { has[p.network] = 1; });
    [["all", "Todo"], ["x", "Twitter"], ["instagram", "Instagram"], ["youtube", "YouTube"]].forEach(function (c) {
      if (c[0] !== "all" && !has[c[0]]) return;
      var b = document.createElement("button"); b.type = "button"; b.textContent = c[1]; b.dataset.f = c[0];
      b.setAttribute("aria-pressed", String(state === c[0]));
      b.onclick = function () { state = c[0]; apply(); };
      f.appendChild(b);
    });
    var pr = $("#profiles");
    [["x", "Twitter"], ["instagram", "Instagram"], ["youtube", "YouTube"]].forEach(function (c) {
      var p = PROFILES[c[0]]; if (!p) return;
      if (p.enabled === false) { var s = document.createElement("span"); s.className = "soon"; s.innerHTML = c[1] + "<small>pronto</small>"; pr.appendChild(s); return; }
      var a = document.createElement("a"); a.href = p.url; a.target = "_blank"; a.rel = "noopener"; a.textContent = c[1] + " ↗"; pr.appendChild(a);
    });
  }
  function apply() {
    document.querySelectorAll("#filters button").forEach(function (b) { b.setAttribute("aria-pressed", String(b.dataset.f === state)); });
    var n = 0;
    tiles.forEach(function (t) { var ok = state === "all" || t.post.network === state; t.el.hidden = !ok; if (ok) n++; });
    $("#empty").hidden = n > 0;
    tiles.forEach(function (t) { if (!t.el.hidden && t.fit) t.fit(); });
  }

  /* ---------- mosaicos ---------- */
  var tiles = [];
  function textTile(el, text, who) {
    var d = document.createElement("div"); d.className = "text-tile";
    var q = document.createElement("q"); q.textContent = text || "Ver publicación";
    var s = document.createElement("span"); s.textContent = who ? "@" + who : "";
    d.appendChild(q); d.appendChild(s); el.appendChild(d);
  }

  function mountX(t) {
    var m = t.post.media, el = t.el;
    if (m && m.image) {
      var img = new Image();
      img.alt = (m.text || "Publicación de @" + (m.author || t.post.user)) + " (Twitter)";
      img.decoding = "async"; img.loading = "lazy";
      img.src = m.image + (/pbs\.twimg\.com\/media\//.test(m.image) ? "?name=medium" : "");
      if (m.w && m.h && (m.w / m.h > 2.6)) img.className = "contain";   // tiras muy anchas: no recortar
      else if (m.focus && m.w && m.h) {                                  // usar el recorte 16:9 que sugiere X
        var fx = m.w > m.focus.w ? m.focus.x / (m.w - m.focus.w) * 100 : 50;
        var fy = m.h > m.focus.h ? m.focus.y / (m.h - m.focus.h) * 100 : 50;
        img.style.objectPosition = fx.toFixed(1) + "% " + fy.toFixed(1) + "%";
      } else if (m.w && m.h && m.h > m.w) img.style.objectPosition = "50% 35%";
      img.onload = function () { img.classList.add("on"); };
      img.onerror = function () { img.remove(); textTile(el, m.text, m.author || t.post.user); };
      el.insertBefore(img, el.firstChild);
    } else textTile(el, m && m.text, (m && m.author) || t.post.user);
  }

  function mountIG(t) {
    var m = t.post.media || {}, el = t.el;
    var box = document.createElement("div"); box.className = "ig";
    var f = document.createElement("iframe");
    f.src = "https://www.instagram.com/p/" + encodeURIComponent(t.post.id) + "/embed/";
    f.title = "Publicación de Instagram" + (m.author ? " de @" + m.author : "");
    f.loading = "lazy"; f.scrolling = "no"; f.tabIndex = -1; f.setAttribute("aria-hidden", "true");
    f.width = IG_W; f.height = 1400;
    box.appendChild(f); el.insertBefore(box, el.firstChild);

    var ratio = m.w && m.h ? m.h / m.w : 1.25;                 // alto/ancho del contenido real
    var mediaH = IG_W * (m.kind === "video" ? Math.min(ratio, 1.25) : Math.min(ratio, 1.34)); // caja de medios del embed
    t.measure = function (h) { if (h > IG_HEADER + IG_FOOTER + 100) { mediaH = h - IG_HEADER - IG_FOOTER; fit(); } };
    function fit() {
      var W = el.clientWidth, H = el.clientHeight; if (!W || !H) return;
      // rectángulo del contenido dentro de la caja (los reels vienen con bandas negras)
      var cw = IG_W, ch = IG_W * ratio;
      if (ch > mediaH) { ch = mediaH; cw = mediaH / ratio; }
      var cx = (IG_W - cw) / 2, cy = IG_HEADER + (mediaH - ch) / 2;
      var s = Math.max(W / cw, H / ch) * 1.02;                // "cover" + un pelín para esconder bordes
      // en contenido vertical, enfocar un poco más arriba (caras, texto) sin salirse del borde
      var fy = ch * s > H ? 0.42 : 0.5;
      var ty = H / 2 - s * (cy + ch * fy);
      ty = Math.min(-s * cy, Math.max(H - s * (cy + ch), ty));
      var tx = W / 2 - s * (cx + cw / 2);
      f.style.transform = "translate(" + tx.toFixed(1) + "px," + ty.toFixed(1) + "px) scale(" + s.toFixed(4) + ")";
    }
    t.fit = fit; t.frame = f;
    f.addEventListener("load", function () { setTimeout(function () { f.classList.add("on"); }, 400); });
    fit();
  }

  function mountYT(t) {
    var p = t.post, base = "https://i.ytimg.com/vi/" + encodeURIComponent(p.id) + "/";
    var tries = p.short ? ["oardefault.jpg", "hqdefault.jpg"] : ["maxresdefault.jpg", "hqdefault.jpg"], k = 0, bg = null;
    var img = new Image(); img.loading = "lazy"; img.decoding = "async"; img.alt = p.title ? p.title + " (YouTube)" : "Video de YouTube";
    function next() { if (k < tries.length) img.src = base + tries[k++]; }
    img.onload = function () {
      if (img.naturalWidth <= 120 && k < tries.length) return next();   // miniatura "no disponible"
      img.classList.add("on"); if (bg) { bg.src = img.src; bg.classList.add("on"); }
    };
    img.onerror = next;
    if (p.short) {   // Short: póster 9:16 al centro sobre su miniatura desenfocada
      t.el.classList.add("short");
      bg = new Image(); bg.alt = ""; bg.className = "bg"; bg.loading = "lazy";
      var pf = document.createElement("div"); pf.className = "poster"; pf.appendChild(img);
      t.el.insertBefore(pf, t.el.firstChild); t.el.insertBefore(bg, t.el.firstChild);
    } else t.el.insertBefore(img, t.el.firstChild);
    next();
  }

  // Instagram avisa el alto real de su embed con postMessage → afinamos el recorte
  window.addEventListener("message", function (e) {
    if (!/^https:\/\/www\.instagram\.com$/.test(e.origin)) return;
    var d = e.data; if (typeof d === "string") { try { d = JSON.parse(d); } catch (x) { return; } }
    if (!d || d.type !== "MEASURE" || !d.details) return;
    tiles.forEach(function (t) { if (t.frame && t.frame.contentWindow === e.source && t.measure) t.measure(d.details.height); });
  });

  function build() {
    var g = $("#grid");
    posts.forEach(function (p) {
      var a = document.createElement("a");
      a.className = "tile"; a.href = p.url; a.target = "_blank"; a.rel = "noopener"; a.dataset.net = p.network;
      var label = LABEL[p.network], when = p.date ? ddmmaa(p.date) : "";
      a.setAttribute("aria-label", (p.title ? p.title + " — " + (p.channel || label) : label) + (when ? ", " + when : "") + " — abrir publicación original");
      var o = document.createElement("div"); o.className = "over" + (p.title ? " yt" : "");
      o.innerHTML = "<h2></h2><p></p>";
      o.firstChild.textContent = p.title || label;
      o.lastChild.textContent = p.title ? (p.channel || label) + (when ? " · " + when : "") : when;
      if (p.approx && when) o.lastChild.title = "fecha aproximada";
      a.appendChild(o); g.appendChild(a);
      tiles.push({ el: a, post: p, done: false });
    });
    var mount = function (t) { if (t.done) return; t.done = true;
      (t.post.network === "x" ? mountX : t.post.network === "instagram" ? mountIG : mountYT)(t); };
    if ("IntersectionObserver" in window) {
      var io = new IntersectionObserver(function (es) { es.forEach(function (e) {
        if (!e.isIntersecting) return; var t = tiles.find(function (x) { return x.el === e.target; });
        if (t) { mount(t); io.unobserve(e.target); } }); }, { rootMargin: "800px 0px" });
      tiles.forEach(function (t) { io.observe(t.el); });
    } else tiles.forEach(mount);
    if ("ResizeObserver" in window) { var ro = new ResizeObserver(function () { tiles.forEach(function (t) { if (t.fit) t.fit(); }); }); ro.observe(g); }
    else window.addEventListener("resize", function () { tiles.forEach(function (t) { if (t.fit) t.fit(); }); });
  }

  header(); build(); apply();
  var up = $("#up"), top = $(".top");
  up.onclick = function () { window.scrollTo({ top: 0, behavior: "smooth" }); };
  window.addEventListener("scroll", function () { up.hidden = scrollY < 700; top.classList.toggle("compact", scrollY > 40); }, { passive: true });
})();

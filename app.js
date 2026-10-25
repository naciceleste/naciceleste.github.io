/* ☁️ El búnker de Ⱥrmin — lógica (sin build, sin dependencias) */
(function () {
  "use strict";

  var CFG = window.SITE_CONFIG || {};
  var RAW = Array.isArray(window.POSTS) ? window.POSTS : [];
  var USER = CFG.username || "naciceleste";
  var PROFILES = CFG.profiles || {};

  var NETS = {
    x:         { label: "Twitter",   icon: "i-x",         open: "Ver en Twitter" },
    instagram: { label: "Instagram", icon: "i-instagram", open: "Ver en Instagram" },
    youtube:   { label: "YouTube",   icon: "i-youtube",   open: "Ver en YouTube" },
    tiktok:    { label: "TikTok",    icon: "i-tiktok",    open: "Ver en TikTok" },
    substack:  { label: "Substack",  icon: "i-substack",  open: "Leer en Substack" }
  };
  var CARDS = window.POST_CARDS || {};

  var $ = function (s, r) { return (r || document).querySelector(s); };
  function el(tag, attrs, html) {
    var n = document.createElement(tag);
    if (attrs) for (var k in attrs) {
      if (attrs[k] == null) continue;
      if (k === "class") n.className = attrs[k]; else n.setAttribute(k, attrs[k]);
    }
    if (html != null) n.innerHTML = html;
    return n;
  }
  function icon(id) { return '<svg aria-hidden="true"><use href="#' + id + '"/></svg>'; }
  function esc(s) { return String(s).replace(/[&<>"']/g, function (c) { return ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]; }); }

  /* ---------- detectar red e id a partir del link ---------- */
  function parse(url) {
    var u;
    try { u = new URL(String(url).trim()); } catch (e) { return null; }
    var host = u.hostname.replace(/^(www\.|m\.|mobile\.)/, "");
    var parts = u.pathname.split("/").filter(Boolean);

    if (host === "x.com" || host === "twitter.com") {
      var i = parts.indexOf("status");
      if (i > 0 && /^\d+$/.test(parts[i + 1] || "")) {
        return { network: "x", id: parts[i + 1], url: "https://x.com/" + parts[0] + "/status/" + parts[i + 1] };
      }
      return null;
    }
    if (host === "instagram.com") {
      for (var j = 0; j < parts.length - 1; j++) {
        var kind = parts[j];
        if (kind === "p" || kind === "reel" || kind === "reels" || kind === "tv") {
          var k = kind === "reels" ? "reel" : kind;
          return { network: "instagram", id: parts[j + 1], url: "https://www.instagram.com/" + k + "/" + parts[j + 1] + "/" };
        }
      }
      return null;
    }
    if (host === "youtube.com" || host === "youtu.be" || host === "youtube-nocookie.com" || host === "music.youtube.com") {
      var id = null, short = false;
      if (host === "youtu.be") id = parts[0];
      else if (u.searchParams.get("v")) id = u.searchParams.get("v");
      else if (/^(shorts|embed|live|v)$/.test(parts[0] || "")) { id = parts[1]; short = parts[0] === "shorts"; }
      if (id && /^[\w-]{6,}$/.test(id)) {
        return { network: "youtube", id: id, short: short,
          url: short ? "https://www.youtube.com/shorts/" + id : "https://www.youtube.com/watch?v=" + id };
      }
      return null;
    }
    if (host === "tiktok.com") {
      var v = parts.findIndex(function (x) { return x === "video" || x === "photo"; });
      if (v > 0 && /^\d+$/.test(parts[v + 1] || "")) {
        return { network: "tiktok", id: parts[v + 1], user: parts[0], url: "https://www.tiktok.com/" + parts[0] + "/" + parts[v] + "/" + parts[v + 1] };
      }
      return null;
    }
    if (host === "substack.com" || /\.substack\.com$/.test(host)) {
      var path = u.pathname.replace(/\/+$/, "");
      if (/^\/(p\/[^\/]+|@[^\/]+\/note\/[^\/]+|note\/[^\/]+|home\/post\/[^\/]+)$/.test(path)) {
        return { network: "substack", id: host + path, url: "https://" + host + path };
      }
      return null;
    }
    return null;
  }

  function parseDate(s) {
    if (!s) return null;
    var m = /^(\d{4})-(\d{1,2})-(\d{1,2})/.exec(String(s));
    var d = m ? new Date(+m[1], +m[2] - 1, +m[3]) : new Date(s);
    return isNaN(d) ? null : d;
  }
  function fmtDate(d) {
    try { return d.toLocaleDateString("es-CR", { day: "numeric", month: "short", year: "numeric" }).replace(/\./g, ""); }
    catch (e) { return d.toISOString().slice(0, 10); }
  }

  var posts = RAW.map(function (entry, idx) {
    var e = typeof entry === "string" ? { url: entry } : (entry || {});
    var p = e.url ? parse(e.url) : null;
    if (!p) { console.warn("[muro] No reconozco este link, lo salto:", e.url || entry); return null; }
    if (e.network && NETS[e.network] && e.network !== p.network) console.warn("[muro] La red indicada no coincide con el link:", e.url);
    return {
      idx: idx, network: p.network, id: p.id, short: !!p.short, url: p.url,
      note: e.note || "", tags: Array.isArray(e.tags) ? e.tags : (e.tags ? String(e.tags).split(",") : []),
      date: parseDate(e.date),
      pin: (+e.pin >= 1 && +e.pin <= 3) ? Math.round(+e.pin) : 0
    };
  }).filter(Boolean);
  posts.forEach(function (p) { p.tags = p.tags.map(function (t) { return String(t).trim().replace(/^#/, ""); }).filter(Boolean); });
  // más nuevos primero; misma fecha → se respeta el orden del archivo (el de arriba primero)
  posts.sort(function (a, b) {
    // fijados (1, 2, 3) siempre primero, en ese orden
    if (a.pin || b.pin) return (a.pin || 99) - (b.pin || 99);
    var da = a.date ? a.date.getTime() : 0, db = b.date ? b.date.getTime() : 0;
    return db - da || a.idx - b.idx;
  });

  /* ---------- encabezado ---------- */
  function renderHeader() {
    if (CFG.title) { $("#site-title").textContent = CFG.title; document.title = CFG.title + " · @" + USER; }
    $("#tagline").textContent = CFG.tagline || "";
    var main = (PROFILES.x && PROFILES.x.url) || "https://x.com/" + USER;
    ["#handle", "#footer-handle"].forEach(function (s) {
      var a = $(s); a.textContent = "@" + USER; a.href = main; a.target = "_blank"; a.rel = "noopener";
    });
    var nav = $("#socials");
    Object.keys(NETS).forEach(function (net) {
      var prof = PROFILES[net];
      if (!prof) return;
      var inner = '<span class="ico">' + icon(NETS[net].icon) + "</span><span>" + NETS[net].label + "</span>";
      if (prof.enabled === false) {
        if (prof.showSoon === false) return;
        nav.appendChild(el("span", { class: "social soon", "data-net": net, title: NETS[net].label + ": muy pronto" },
          inner + '<span class="soon-tag">pronto</span>'));
      } else {
        nav.appendChild(el("a", { class: "social", "data-net": net, href: prof.url, target: "_blank", rel: "noopener",
          "aria-label": "@" + USER + " en " + NETS[net].label }, inner));
      }
    });
  }

  /* ---------- filtros ---------- */
  var state = { net: "all", tag: null, allTags: false };

  function renderChips() {
    var box = $("#chips");
    box.innerHTML = "";
    var counts = { all: posts.length, x: 0, instagram: 0, youtube: 0, tiktok: 0, substack: 0 };
    posts.forEach(function (p) { counts[p.network]++; });
    var list = [["all", "Todos", "i-all"], ["x", "Twitter", "i-x"], ["instagram", "Instagram", "i-instagram"], ["youtube", "YouTube", "i-youtube"], ["tiktok", "TikTok", "i-tiktok"], ["substack", "Substack", "i-substack"]];
    list.forEach(function (c) {
      if ((c[0] === "tiktok" || c[0] === "substack") && !counts[c[0]]) return;   // solo aparecen cuando hay posts
      var b = el("button", { class: "chip", type: "button", "data-filter": c[0], "aria-pressed": String(state.net === c[0]) },
        icon(c[2]) + "<span>" + c[1] + "</span>" + (counts[c[0]] ? '<span class="n">' + counts[c[0]] + "</span>" : ""));
      b.addEventListener("click", function () { setNet(c[0]); });
      box.appendChild(b);
    });
  }

  function setNet(net) {
    state.net = net;
    var h = net === "all" ? "" : "#" + net;
    if (location.hash !== h) history.replaceState(null, "", h || location.pathname + location.search);
    applyFilter();
  }
  function setTag(tag) { state.tag = tag; applyFilter(); window.scrollTo({ top: $(".toolbar").offsetTop - 20, behavior: "smooth" }); }

  /* ---------- fila de etiquetas (solo aparece si algún post tiene tags) ---------- */
  // los números cuentan los posts de la red elegida arriba
  function renderTagRow() {
    var row = $("#tag-row");
    var all = {}, counts = {};
    posts.forEach(function (p) {
      p.tags.forEach(function (t) {
        all[t] = true;
        if (state.net === "all" || p.network === state.net) counts[t] = (counts[t] || 0) + 1;
      });
    });
    var names = Object.keys(all);
    row.hidden = !names.length;
    if (!names.length) { row.innerHTML = ""; return; }
    names.sort(function (a, b) { return (counts[b] || 0) - (counts[a] || 0) || a.localeCompare(b, "es"); });
    var vis = names.filter(function (t) { return (counts[t] || 0) > 0 || state.tag === t; });
    var TOP = 10, over = vis.length > TOP;
    var show = vis;
    if (over && !state.allTags) {
      show = vis.slice(0, TOP);
      if (state.tag && show.indexOf(state.tag) === -1) show.push(state.tag);   // la etiqueta elegida siempre se ve
    }
    row.classList.toggle("open", over && state.allTags);
    row.innerHTML = "";
    show.forEach(function (t) {
      var n = counts[t] || 0, on = state.tag === t;
      var b = el("button", { class: "tag-pill", type: "button", "aria-pressed": String(on),
        title: on ? "Quitar el filtro #" + t : "Ver solo #" + t },
        '<span class="h">#</span>' + esc(t) + '<span class="n">' + n + "</span>" + (on ? '<span class="x" aria-hidden="true">✕</span>' : ""));
      b.addEventListener("click", function () { setTag(on ? null : t); });
      row.appendChild(b);
    });
    if (over) {
      var more = el("button", { class: "tag-more", type: "button", "aria-expanded": String(!!state.allTags) },
        state.allTags ? "Ver menos ▴" : "Ver todas (" + vis.length + ") ▾");
      more.addEventListener("click", function () { state.allTags = !state.allTags; renderTagRow(); });
      row.appendChild(more);
    }
    var act = row.querySelector('[aria-pressed="true"]');
    if (act && act.scrollIntoView && row.scrollWidth > row.clientWidth) row.scrollLeft = act.offsetLeft - row.clientWidth / 2 + act.offsetWidth / 2;
  }

  function applyFilter() {
    document.querySelectorAll(".chip").forEach(function (b) { b.setAttribute("aria-pressed", String(b.dataset.filter === state.net)); });
    var shown = 0;
    cards.forEach(function (c) {
      var ok = (state.net === "all" || c.post.network === state.net) && (!state.tag || c.post.tags.indexOf(state.tag) !== -1);
      c.node.hidden = !ok;
      if (ok) { shown++; }
    });
    var at = $("#active-tag");
    if (state.tag) {
      at.hidden = false;
      at.innerHTML = "<span>Mostrando la etiqueta</span>";
      var btn = el("button", { type: "button", "aria-label": "Quitar etiqueta" }, "#" + esc(state.tag) + " ✕");
      btn.addEventListener("click", function () { setTag(null); });
      at.appendChild(btn);
    } else at.hidden = true;
    renderTagRow();

    var count = $("#count");
    if (!posts.length) count.textContent = "";
    else if (shown === posts.length) count.textContent = shown + (shown === 1 ? " cosita guardada ♡" : " cositas guardadas ♡");
    else count.textContent = shown + " de " + posts.length + (posts.length === 1 ? " cosita" : " cositas");

    var empty = $("#empty");
    empty.hidden = shown > 0;
    if (!shown) {
      var t = $("#empty-title"), p = $("#empty-text");
      if (!posts.length) {
        t.textContent = "Este cielito todavía está despejado";
        p.textContent = "Muy pronto van a ir apareciendo aquí las cositas que más me gustan de Twitter, Instagram y YouTube. ¡Vuelve en un ratito! ☁️";
      } else if (state.net === "youtube" && PROFILES.youtube && PROFILES.youtube.enabled === false) {
        t.textContent = "YouTube viene en camino";
        p.textContent = "Todavía no he guardado videos, pero muy pronto se llena esta nube ✨";
      } else {
        t.textContent = "Por aquí no hay nada todavía";
        p.textContent = "Prueba con otro filtro, que las demás nubes sí tienen cositas ☁️";
      }
    }
    scheduleLayout();
  }

  /* ---------- tarjetas ---------- */
  var cards = [];
  function buildCard(post, i) {
    var n = NETS[post.network];
    var card = el("article", { class: "card" + (post.pin ? " pinned" : ""), "data-net": post.network });
    card.style.animationDelay = Math.min(i, 8) * 60 + "ms";
    var top = el("div", { class: "card-top" },
      '<span class="badge ' + post.network + '"><span class="dot">' + icon(n.icon) + "</span>" + n.label + "</span>" +
      (post.pin ? '<span class="pin" title="Post fijado">📌 Fijado</span>' : "") +
      (post.date ? '<time class="date" datetime="' + post.date.toISOString().slice(0, 10) + '">' + fmtDate(post.date) + "</time>" : ""));
    var embed = el("div", { class: "embed" },
      '<div class="loading"><svg class="puff" viewBox="0 0 200 100"><use href="#cloud-shape"/></svg>cargando…</div>');
    card.appendChild(top);
    card.appendChild(embed);
    if (post.note) card.appendChild(el("p", { class: "note" }, esc(post.note)));
    if (post.tags.length) {
      var tags = el("div", { class: "tags" });
      post.tags.forEach(function (t) {
        var b = el("button", { class: "tag", type: "button" }, "#" + esc(t));
        b.addEventListener("click", function () { setTag(t); });
        tags.appendChild(b);
      });
      card.appendChild(tags);
    }
    card.appendChild(el("div", { class: "card-foot" },
      '<a class="open" href="' + esc(post.url) + '" target="_blank" rel="noopener">' + n.open + icon("i-arrow") + "</a>"));
    return { node: card, embed: embed, post: post, loaded: false };
  }

  /* ---------- carga perezosa de embeds ---------- */
  var scripts = {};
  function loadScript(src) {
    if (!scripts[src]) scripts[src] = new Promise(function (res, rej) {
      var s = document.createElement("script");
      s.src = src; s.async = true; s.charset = "utf-8";
      s.onload = res; s.onerror = rej;
      document.body.appendChild(s);
    });
    return scripts[src];
  }

  function fallback(c, why) {
    var n = NETS[c.post.network];
    c.embed.classList.remove("ready"); c.embed.classList.add("failed");
    c.embed.innerHTML = "";
    c.embed.appendChild(el("a", { class: "fallback", href: c.post.url, target: "_blank", rel: "noopener" },
      '<span class="big badge ' + c.post.network + '">' + icon(n.icon) + "</span>" +
      "<strong>" + n.open + "</strong><small>" + (why || "Este post no se pudo mostrar aquí, pero puedes verlo en su lugar original.") + "</small>"));
    scheduleLayout();
  }
  function ready(c) { c.embed.classList.add("ready"); var l = c.embed.querySelector(".loading"); if (l) l.remove(); scheduleLayout(); }

  function mount(c) {
    if (c.loaded) return; c.loaded = true;
    var p = c.post, box = c.embed;
    if (p.network === "x") {
      loadScript("https://platform.twitter.com/widgets.js").then(function () {
        var tw = window.twttr;
        return tw.ready ? new Promise(function (r) { tw.ready(r); }) : tw;
      }).then(function (tw) {
        var holder = el("div", { class: "tw-holder" });
        box.appendChild(holder);
        c.theme = theme();
        return tw.widgets.createTweet(p.id, holder, { dnt: true, align: "center", conversation: "none", lang: "es", theme: c.theme });
      }).then(function (node) {
        if (node) { ready(c); if (c.theme !== theme()) rethemeX(c); }
        else fallback(c, "Puede que el post se haya borrado o sea privado.");
      }).catch(function () { fallback(c, "No se pudo cargar el visor de Twitter (¿bloqueador de anuncios?)."); });
    } else if (p.network === "instagram") {
      var bq = el("blockquote", { class: "instagram-media", "data-instgrm-permalink": p.url + "?utm_source=ig_embed", "data-instgrm-version": "14" },
        '<a href="' + esc(p.url) + '" target="_blank" rel="noopener">Ver esta publicación en Instagram</a>');
      box.appendChild(bq);
      loadScript("https://www.instagram.com/embed.js").then(function () {
        if (window.instgrm) window.instgrm.Embeds.process();
        var t0 = Date.now();
        (function check() {
          var f = box.querySelector("iframe.instagram-media");
          if (f && f.classList.contains("instagram-media-rendered") && f.offsetHeight > 80) ready(c);
          else if (Date.now() - t0 > 15000) fallback(c, "Instagram no permitió mostrar este post aquí (puede ser privado, borrado o con el embed desactivado).");
          else setTimeout(check, 400);
        })();
      }).catch(function () { fallback(c, "No se pudo cargar el visor de Instagram (¿bloqueador de anuncios?)."); });
    } else if (p.network === "tiktok") {
      var tw2 = el("div", { class: "tt" });
      var tf = el("iframe", {
        src: "https://www.tiktok.com/player/v1/" + encodeURIComponent(p.id) + "?description=1&music_info=1&rel=0",
        title: "Video de TikTok", loading: "lazy",
        allow: "fullscreen; encrypted-media; picture-in-picture", allowfullscreen: ""
      });
      tf.addEventListener("load", function () { ready(c); });
      tw2.appendChild(tf); box.appendChild(tw2);
      setTimeout(function () { ready(c); }, 4000);
    } else if (p.network === "substack") {
      var d = CARDS[p.url] || {};
      var slug = decodeURIComponent((p.url.split("/").pop() || "")).replace(/[-_]+/g, " ");
      var title = d.title || (slug && slug.charAt(0).toUpperCase() + slug.slice(1)) || "Publicación en Substack";
      var a = el("a", { class: "sub-card", href: p.url, target: "_blank", rel: "noopener" },
        (d.image ? '<span class="sub-img"><img src="' + esc(d.image) + '" alt="" loading="lazy" referrerpolicy="no-referrer"/></span>' : "") +
        '<span class="sub-body">' +
          '<span class="sub-site">' + icon("i-substack") + esc(d.site || "Substack") + "</span>" +
          '<strong class="sub-title">' + esc(title) + "</strong>" +
          (d.desc ? '<span class="sub-desc">' + esc(d.desc) + "</span>" : "") +
        "</span>");
      var im = a.querySelector("img");
      if (im) { im.addEventListener("load", scheduleLayout); im.addEventListener("error", function () { var w = im.parentNode; w.parentNode.removeChild(w); scheduleLayout(); }); }
      box.appendChild(a); ready(c);
    } else if (p.network === "youtube") {
      var wrap = el("div", { class: "yt" + (p.short ? " short" : "") });
      var f = el("iframe", {
        src: "https://www.youtube-nocookie.com/embed/" + encodeURIComponent(p.id) + "?rel=0&modestbranding=1",
        title: "Video de YouTube", loading: "lazy",
        allow: "accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share",
        referrerpolicy: "strict-origin-when-cross-origin", allowfullscreen: ""
      });
      f.addEventListener("load", function () { ready(c); });
      wrap.appendChild(f); box.appendChild(wrap);
      setTimeout(function () { ready(c); }, 4000);
    }
  }

  /* ---------- modo claro / oscuro ---------- */
  function theme() { return document.documentElement.getAttribute("data-theme") === "dark" ? "dark" : "light"; }
  // vuelve a dibujar un tuit con el tema actual (el nuevo se arma escondido y reemplaza al viejo, sin saltos)
  function rethemeX(c) {
    var tw = window.twttr, old = c.embed.querySelector(".tw-holder");
    if (!tw || !tw.widgets || !old || c.rendering) return;
    c.rendering = true; c.theme = theme();
    var holder = el("div", { class: "tw-holder pending" });
    c.embed.appendChild(holder);
    tw.widgets.createTweet(c.post.id, holder, { dnt: true, align: "center", conversation: "none", lang: "es", theme: c.theme })
      .then(function (node) {
        c.rendering = false;
        if (node) { old.remove(); holder.classList.remove("pending"); } else holder.remove();
        scheduleLayout();
        if (c.theme !== theme()) rethemeX(c);
      }, function () { c.rendering = false; holder.remove(); });
  }
  function applyTheme(t, save) {
    document.documentElement.setAttribute("data-theme", t);
    var meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.setAttribute("content", t === "dark" ? "#0d1233" : "#cfe8ff");
    var b = $("#theme-toggle");
    if (b) { b.setAttribute("aria-label", t === "dark" ? "Cambiar a modo claro" : "Cambiar a modo oscuro"); b.title = b.getAttribute("aria-label"); }
    if (save) { try { localStorage.setItem("tema", t); } catch (e) {} }
    cards.forEach(function (c) { if (c.post.network === "x" && c.embed.classList.contains("ready") && c.theme !== t) rethemeX(c); });
  }
  function themeToggle() {
    applyTheme(theme(), false);
    $("#theme-toggle").addEventListener("click", function () { applyTheme(theme() === "dark" ? "light" : "dark", true); });
  }

  /* ---------- masonry (grid + row-span; nunca mueve iframes en el DOM) ---------- */
  var ROW = 4, rafId = 0;
  function layout() {
    rafId = 0;
    var wall = $("#wall");
    var gap = parseFloat(getComputedStyle(wall).getPropertyValue("--gap")) || 22;
    cards.forEach(function (c) {
      if (c.node.hidden) return;
      var h = c.node.getBoundingClientRect().height;
      c.node.style.gridRowEnd = "span " + Math.max(1, Math.ceil((h + gap) / ROW));
    });
  }
  function scheduleLayout() { if (!rafId) rafId = requestAnimationFrame(layout); }

  function renderWall() {
    var wall = $("#wall");
    posts.forEach(function (p, i) { var c = buildCard(p, i); cards.push(c); wall.appendChild(c.node); });
    if ("ResizeObserver" in window) {
      var ro = new ResizeObserver(scheduleLayout);
      cards.forEach(function (c) { ro.observe(c.node); });
    } else setInterval(scheduleLayout, 1000);
    window.addEventListener("resize", scheduleLayout);

    if ("IntersectionObserver" in window) {
      var io = new IntersectionObserver(function (entries) {
        entries.forEach(function (e) {
          if (e.isIntersecting) { var c = cards.find(function (x) { return x.node === e.target; }); if (c) { mount(c); io.unobserve(e.target); } }
        });
      }, { rootMargin: "700px 0px" });
      cards.forEach(function (c) { io.observe(c.node); });
    } else cards.forEach(mount);
  }

  /* ---------- radio lofi (transmisión en vivo de YouTube; se enciende solo con el botón) ---------- */
  function radio() {
    var box = $("#radio"); if (!box) return;
    var IDS = ["5yx6BWlEVcY", "jiua2V9q9V0", "i6WzngxTnBA", "7NOSDKb0HlU"], which = 0, player = null, playing = false, loading = false, vol = 40;
    var fab = $("#radio-fab"), panel = $("#radio-panel"), btn = $("#radio-play"), range = $("#radio-vol"), status = $("#radio-status");
    try { var sv = parseInt(localStorage.getItem("radioVol"), 10); if (sv >= 0 && sv <= 100) vol = sv; } catch (e) {}
    range.value = vol;

    function paint() {
      box.classList.toggle("on", playing);
      btn.setAttribute("aria-pressed", String(playing));
      btn.querySelector(".lbl").textContent = loading ? "Cargando…" : playing ? "Pausar" : "Escuchar radio lofi";
      btn.querySelector(".ico").textContent = playing ? "❚❚" : "▶";
      fab.setAttribute("aria-label", playing ? "Radio lofi sonando, abrir controles" : "Abrir radio lofi");
      status.textContent = loading ? "Conectando con la transmisión…" : playing ? "En vivo ahora ♪" : "Música para acompañar la visita ☁️";
    }
    function build() {
      loading = true; paint();
      var go = function () {
        player = new YT.Player("radio-yt", {
          width: "240", height: "135", videoId: IDS[which],
          playerVars: { autoplay: 1, controls: 0, playsinline: 1, rel: 0, modestbranding: 1, disablekb: 1, iv_load_policy: 3 },
          events: {
            onReady: function (e) { e.target.setVolume(vol); e.target.playVideo(); },
            onStateChange: function (e) {
              if (e.data === 1) { loading = false; playing = true; }
              else if (e.data === 2 || e.data === 0) { loading = false; playing = false; }
              paint();
            },
            onError: function () {
              if (which < IDS.length - 1) { which++; player.loadVideoById(IDS[which]); }
              else { loading = false; playing = false; status.textContent = "La radio no está disponible ahora mismo."; box.classList.remove("on"); }
            }
          }
        });
      };
      if (window.YT && YT.Player) go();
      else {
        window.onYouTubeIframeAPIReady = go;
        loadScript("https://www.youtube.com/iframe_api").catch(function () { loading = false; paint(); status.textContent = "No se pudo cargar la radio (¿bloqueador de anuncios?)."; });
      }
    }
    btn.addEventListener("click", function () {
      if (!player) { build(); return; }
      if (playing) player.pauseVideo(); else player.playVideo();
    });
    range.addEventListener("input", function () {
      vol = +range.value; if (player && player.setVolume) player.setVolume(vol);
      try { localStorage.setItem("radioVol", String(vol)); } catch (e) {}
    });
    function toggle(open) {
      var o = open == null ? panel.hidden : open;
      panel.hidden = !o; fab.setAttribute("aria-expanded", String(o)); box.classList.toggle("open", o);
    }
    fab.addEventListener("click", function () { toggle(); });
    $("#radio-close").addEventListener("click", function () { toggle(false); fab.focus(); });
    paint();
  }


  /* ---------- botón volver arriba ---------- */
  function topButton() {
    var b = $("#to-top");
    b.addEventListener("click", function () { window.scrollTo({ top: 0, behavior: "smooth" }); });
    window.addEventListener("scroll", function () { b.hidden = window.scrollY < 900; }, { passive: true });
  }

  renderHeader();
  themeToggle();
  var h = location.hash.replace("#", "");
  if (NETS[h]) state.net = h;
  renderChips();
  renderWall();
  applyFilter();
  topButton();
  radio();
})();

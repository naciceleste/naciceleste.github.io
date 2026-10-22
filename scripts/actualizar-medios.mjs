#!/usr/bin/env node
/* ☁️ Actualiza media.js con la info pública de cada post de posts.js.
   Guarda SOLO enlaces (URLs de las imágenes en los servidores de cada red),
   fechas y medidas. NO descarga ni guarda ninguna imagen.

   Uso:  node scripts/actualizar-medios.mjs        (Node 18 o más nuevo)
   En GitHub se corre solo con la Action .github/workflows/medios.yml */
import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const ctx = { window: {} };
vm.runInNewContext(fs.readFileSync(path.join(root, "posts.js"), "utf8"), ctx);
const posts = (ctx.window.POSTS || []).map((e) => (typeof e === "string" ? { url: e } : e)).filter((e) => e && e.url);

const mediaFile = path.join(root, "media.js");
let old = {};
if (fs.existsSync(mediaFile)) {
  const c = { window: {} };
  try { vm.runInNewContext(fs.readFileSync(mediaFile, "utf8"), c); old = c.window.POST_MEDIA || {}; } catch {}
}

const UA_BROWSER = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36";
const UA_BOT = "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)";
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function key(url) {
  const u = new URL(url.trim());
  const host = u.hostname.replace(/^(www\.|m\.|mobile\.)/, "");
  const parts = u.pathname.split("/").filter(Boolean);
  if (host === "x.com" || host === "twitter.com") {
    const i = parts.indexOf("status");
    if (i > 0 && /^\d+$/.test(parts[i + 1] || "")) return { net: "x", id: parts[i + 1] };
  }
  if (host === "instagram.com") {
    for (let j = 0; j < parts.length - 1; j++) if (/^(p|reel|reels|tv)$/.test(parts[j])) return { net: "instagram", id: parts[j + 1] };
  }
  return null;
}

async function xInfo(id) {
  const token = ((Number(id) / 1e15) * Math.PI).toString(36).replace(/(0+|\.)/g, "");
  const r = await fetch(`https://cdn.syndication.twimg.com/tweet-result?id=${id}&lang=es&token=${token}`, { headers: { "User-Agent": UA_BROWSER } });
  if (!r.ok) throw new Error("syndication HTTP " + r.status);
  const t = await r.json();
  if (!t || !t.id_str) throw new Error("tweet no disponible (" + (t && t.__typename) + ")");
  const src = t.mediaDetails && t.mediaDetails.length ? t : (t.quoted_tweet && t.quoted_tweet.mediaDetails ? t.quoted_tweet : t);
  const m = (src.mediaDetails || [])[0];
  const out = {
    network: "x",
    date: t.created_at,                       // fecha real de publicación (UTC)
    author: t.user && t.user.screen_name,
    text: (t.text || "").replace(/https:\/\/t\.co\/\w+/g, "").trim().slice(0, 280)
  };
  if (m && m.media_url_https) {
    out.image = m.media_url_https;            // pbs.twimg.com: enlace estable, no caduca
    out.kind = m.type;                        // photo | video | animated_gif
    if (m.original_info) {
      out.w = m.original_info.width; out.h = m.original_info.height;
      const f = (m.original_info.focus_rects || [])[0];   // recorte 16:9 sugerido por X
      if (f) out.focus = { x: f.x, y: f.y, w: f.w, h: f.h };
    }
    if (src !== t) out.fromQuote = true;
  } else if (t.card && t.card.binding_values && t.card.binding_values.thumbnail_image_large) {
    const v = t.card.binding_values.thumbnail_image_large.image_value;
    out.image = v.url; out.kind = "card"; out.w = v.width; out.h = v.height;
  } else out.kind = "text";
  return out;
}

async function igInfo(code) {
  const out = { network: "instagram" };
  // medidas y tipo desde la página pública del embed
  const e = await fetch(`https://www.instagram.com/p/${code}/embed/`, { headers: { "User-Agent": UA_BOT } });
  if (e.ok) {
    const h = (await e.text()).replace(/\\"/g, '"');
    const d = /"dimensions":\{"height":(\d+),"width":(\d+)\}/.exec(h);
    if (d) { out.h = +d[1]; out.w = +d[2]; }
    const ty = /"__typename":"(Graph\w+)"/.exec(h);
    if (ty) out.kind = ty[1] === "GraphVideo" ? "video" : ty[1] === "GraphSidecar" ? "carousel" : "photo";
    const own = /"owner":\{[^}]*?"username":"([\w.]+)"/.exec(h);
    if (own) out.author = own[1];
  }
  // fecha real de publicación (taken_at) desde la página pública del post
  const p = await fetch(`https://www.instagram.com/p/${code}/`, { headers: { "User-Agent": UA_BOT, "Accept-Language": "es" } });
  if (p.ok) {
    const h = await p.text();
    const t = /"taken_at":(\d{9,11})/.exec(h);
    if (t) out.date = new Date(+t[1] * 1000).toISOString();
    if (!out.author) { const a = /- ([\w.]+) on [A-Z][a-z]+ \d/.exec(h); if (a) out.author = a[1]; }
  }
  if (!out.date) out.dateApprox = true;      // la página usará la fecha aproximada del código del post
  return out;
}

const result = {};
let fresh = 0;
for (const p of posts) {
  let k; try { k = key(p.url); } catch { k = null; }
  if (!k) continue;
  const id = `${k.net}:${k.id}`;
  const prev = old[id] || {};
  try {
    const info = k.net === "x" ? await xInfo(k.id) : await igInfo(k.id);
    // Nunca perder datos buenos: lo nuevo solo reemplaza lo que sí se pudo obtener
    const merged = { ...prev };
    for (const [f, v] of Object.entries(info)) if (v !== undefined && v !== null && v !== "") merged[f] = v;
    if (prev.date && !info.date) { merged.date = prev.date; delete merged.dateApprox; }
    if (info.date) delete merged.dateApprox;
    result[id] = merged;
    if (k.net === "x" || info.date || info.w) fresh++;
    console.log("✓", id, merged.kind || "", merged.date || "(sin fecha)", info.date || info.image ? "" : "(datos anteriores conservados)");
  } catch (err) {
    if (old[id]) { result[id] = old[id]; console.warn("! ", id, "falló, conservo lo anterior:", err.message); }
    else console.warn("✗", id, err.message);
  }
  await sleep(600);
}

// Si no se pudo obtener nada nuevo (red caída, bloqueo…), no tocar media.js
if (fresh === 0 && Object.keys(old).length) {
  console.warn("\nNo se obtuvo ningún dato nuevo; media.js se deja como estaba.");
  process.exit(0);
}

const body = "/* Archivo generado por scripts/actualizar-medios.mjs — no hace falta editarlo a mano.\n" +
  "   Solo contiene enlaces (no imágenes), fechas de publicación y medidas. */\n" +
  "window.POST_MEDIA = " + JSON.stringify(result, null, 2) + ";\n";
fs.writeFileSync(mediaFile, body);
console.log(`\nListo: ${Object.keys(result).length} posts en media.js`);

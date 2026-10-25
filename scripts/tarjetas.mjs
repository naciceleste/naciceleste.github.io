#!/usr/bin/env node
/* ☁️ Genera tarjetas.js con los datos públicos (título, imagen, resumen) de los posts de Substack
   que están en posts.js. Guarda solo texto y enlaces; no descarga imágenes.
   Uso: node scripts/tarjetas.mjs   (Node 18 o más nuevo) */
import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const ctx = { window: {} };
vm.runInNewContext(fs.readFileSync(path.join(root, "posts.js"), "utf8"), ctx);
const posts = (ctx.window.POSTS || []).map((e) => (typeof e === "string" ? { url: e } : e)).filter((e) => e && e.url);

const file = path.join(root, "tarjetas.js");
let old = {};
if (fs.existsSync(file)) {
  const c = { window: {} };
  try { vm.runInNewContext(fs.readFileSync(file, "utf8"), c); old = c.window.POST_CARDS || {}; } catch {}
}

function substackUrl(raw) {
  try {
    const u = new URL(String(raw).trim());
    const host = u.hostname.replace(/^(www\.|m\.|mobile\.)/, "");
    if (host !== "substack.com" && !host.endsWith(".substack.com")) return null;
    const p = u.pathname.replace(/\/+$/, "");
    if (!/^\/(p\/[^/]+|@[^/]+\/note\/[^/]+|note\/[^/]+|home\/post\/[^/]+)$/.test(p)) return null;
    return "https://" + host + p;
  } catch { return null; }
}
const meta = (html, prop) => {
  const re = new RegExp(`<meta[^>]+(?:property|name)=["']${prop}["'][^>]*>`, "i");
  const m = html.match(re);
  const c = m && m[0].match(/content=["']([^"']*)["']/i);
  return c ? c[1].replace(/&amp;/g, "&").replace(/&quot;/g, '"').replace(/&#x27;|&#39;/g, "'").replace(/&lt;/g, "<").replace(/&gt;/g, ">").trim() : "";
};

const result = {};
let changed = false;
for (const p of posts) {
  const url = substackUrl(p.url);
  if (!url) continue;
  try {
    const r = await fetch(url, { headers: { "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36", "Accept-Language": "es,en;q=0.8" } });
    if (!r.ok) throw new Error("HTTP " + r.status);
    const html = await r.text();
    const card = {
      title: meta(html, "og:title"),
      desc: meta(html, "og:description").slice(0, 300),
      image: meta(html, "og:image"),
      site: meta(html, "og:site_name")
    };
    if (!card.title) throw new Error("sin título");
    result[url] = { ...(old[url] || {}), ...Object.fromEntries(Object.entries(card).filter(([, v]) => v)) };
    console.log("✓", url, "-", card.title);
  } catch (e) {
    if (old[url]) { result[url] = old[url]; console.warn("! ", url, "falló, conservo lo anterior:", e.message); }
    else console.warn("✗", url, e.message);
  }
}
const body = "/* Generado por scripts/tarjetas.mjs — no hace falta editarlo a mano. */\nwindow.POST_CARDS = " + JSON.stringify(result, null, 2) + ";\n";
if (!fs.existsSync(file) || fs.readFileSync(file, "utf8") !== body) { fs.writeFileSync(file, body); console.log("tarjetas.js actualizado"); }

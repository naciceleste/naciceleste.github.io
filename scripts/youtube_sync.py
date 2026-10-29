#!/usr/bin/env python3
"""Sincroniza la lista pública "Biblioteca" de YouTube con youtube.js.

- Lee el feed RSS público de la lista (sin login ni API key).
- Solo AGREGA videos nuevos; nunca borra los que ya estaban (el feed muestra máximo ~15).
- Detecta Shorts: https://www.youtube.com/shorts/<id> responde 200 si es Short, redirige si no.
- Si hubo cambios: commit + push (salvo --no-push). Si no, no toca nada.

Uso:  python3 scripts/youtube_sync.py            # sincroniza, commit y push si hay nuevos
      python3 scripts/youtube_sync.py --no-push  # solo actualiza el archivo
      python3 scripts/youtube_sync.py --dry-run  # solo muestra qué agregaría
"""
import json, os, subprocess, sys, urllib.request, urllib.error, http.client
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta

PLAYLIST = "PLJ-DohLIgv3w"
FEED = "https://www.youtube.com/feeds/videos.xml?playlist_id=" + PLAYLIST
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "youtube.js")
NS = {"a": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015",
      "media": "http://search.yahoo.com/mrss/"}
UA = {"User-Agent": "Mozilla/5.0 (biblioteca-naciceleste youtube_sync)", "Accept-Language": "es"}
HEADER = ("/* Archivo generado por scripts/youtube_sync.py — no hace falta editarlo a mano.\n"
          "   Videos de mi lista pública \"Biblioteca\" de YouTube (solo datos y enlaces, sin imágenes).\n"
          "   Los nuevos se agregan arriba; los viejos nunca se borran. */\n"
          "window.YOUTUBE = ")


def today_cr():
    return (datetime.now(timezone.utc) - timedelta(hours=6)).strftime("%Y-%m-%d")   # Costa Rica (UTC-6)


def load():
    if not os.path.exists(DATA):
        return {"playlist": PLAYLIST, "url": "https://www.youtube.com/playlist?list=" + PLAYLIST, "videos": []}
    txt = open(DATA, encoding="utf-8").read()
    body = txt[txt.index("window.YOUTUBE =") + len("window.YOUTUBE ="):].strip().rstrip(";")
    return json.loads(body)


def save(data):
    with open(DATA, "w", encoding="utf-8") as f:
        f.write(HEADER + json.dumps(data, ensure_ascii=False, indent=2) + ";\n")


def fetch_feed():
    req = urllib.request.Request(FEED, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        root = ET.fromstring(r.read())
    out = []
    for e in root.findall("a:entry", NS):
        vid = e.findtext("yt:videoId", namespaces=NS)
        if not vid:
            continue
        out.append({
            "id": vid,
            "title": (e.findtext("a:title", namespaces=NS) or "").strip(),
            "channel": (e.findtext("a:author/a:name", namespaces=NS) or "").strip(),
            "channelUrl": (e.findtext("a:author/a:uri", namespaces=NS) or "").strip(),
            "published": (e.findtext("a:published", namespaces=NS) or "")[:10],
        })
    return out


def is_short(vid):
    """True si /shorts/<id> responde 200 (Short); False si redirige (video normal); None si no se pudo saber."""
    for _ in range(3):
        try:
            c = http.client.HTTPSConnection("www.youtube.com", timeout=20)
            c.request("HEAD", "/shorts/" + vid, headers=UA)
            s = c.getresponse().status
            c.close()
            if s == 200:
                return True
            if 300 <= s < 400:
                return False
        except Exception:
            pass
    return None


def git(*args, check=True):
    return subprocess.run(["git", "-C", ROOT] + list(args), check=check, capture_output=True, text=True)


def main():
    dry = "--dry-run" in sys.argv
    push = "--no-push" not in sys.argv and not dry
    try:
        feed = fetch_feed()
    except Exception as ex:
        print("No se pudo leer el feed (%s). No se cambió nada." % ex)
        return 1
    data = load()
    known = {v["id"] for v in data["videos"]}
    new = []
    for v in feed:
        if v["id"] in known:
            continue
        s = is_short(v["id"])
        v["short"] = bool(s)
        v["added"] = today_cr()
        new.append(v)
        known.add(v["id"])
    print("Feed: %d videos · en el archivo: %d · nuevos: %d" % (len(feed), len(data["videos"]), len(new)))
    for v in new:
        print("  + %s%s · %s · %s" % (v["id"], " (Short)" if v["short"] else "", v["channel"], v["title"][:70]))
    if not new or dry:
        print("Agregaría: %d (dry-run)" % len(new) if new else "Agregados: 0 (no hay videos nuevos)")
        return 0
    if push:
        git("pull", "--rebase", "--autostash", check=False)
        data = load()   # releer por si el pull trajo cambios
        ids = {v["id"] for v in data["videos"]}
        new = [v for v in new if v["id"] not in ids]
        if not new:
            print("Agregados: 0 (ya estaban en el remoto)")
            return 0
    data["videos"] = new + data["videos"]   # los nuevos arriba, en el orden del feed
    save(data)
    print("Agregados: %d" % len(new))
    if push:
        git("add", "youtube.js")
        git("commit", "-m", "YouTube: %d video%s nuevo%s de la lista" % (len(new), "" if len(new) == 1 else "s", "" if len(new) == 1 else "s"))
        r = git("push", check=False)
        if r.returncode != 0:
            print("No se pudo hacer push:\n" + r.stderr)
            return 2
        print("Commit y push listos.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

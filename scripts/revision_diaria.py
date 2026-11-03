#!/usr/bin/env python3
"""Rebuild posts/news from exported sheet rows (Python stdlib + node + git).

python3 scripts/revision_diaria.py --posts posts.json --temas temas.json --dry-run
Without --temas (or if missing), reuse previous topics and their item counts.
--no-push still writes and commits; --dry-run never writes or invokes git.
Duplicate URLs/pins: the last sheet row wins. Empty cells clear tags/note/pin.
Medios accepts known outlet names or domains, separated by commas/semicolons.
Unknown notes are reported, never guessed into domains. News shortfalls are
reported, never filled with stale/unverified articles. All limits are wall time.
"""

import argparse
import base64
from collections import Counter, deque
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
import html
import json
import multiprocessing
from pathlib import Path
import re
import subprocess
import sys
import threading
import time
import unicodedata
from urllib.parse import urlencode, urlsplit, urlunsplit, parse_qsl
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
WORK_SECONDS = 220
HARD_SECONDS = 240
HTTP_TIMEOUT = 7
WORKERS = 16
GOOGLE_SLOTS = threading.BoundedSemaphore(4)
RATE_LOCK = threading.Lock()
RATE_LIMITED = set()
HEADER = '/* Generado por la revisión diaria (8 p. m.). No editar a mano. */'
BLOCKED_DOMAINS = frozenset({
    'elpais.com.uy', 'elobservador.com.uy', 'ladiaria.com.uy', 'nacion.com',
    'lanacion.com.ar', 'clarin.com', 'elpais.com', 'elmundo.es',
    'wsj.com', 'ft.com', 'nytimes.com', 'bloomberg.com',
})
REGIONS = {'AR': 'Argentina', 'UY': 'Uruguay', 'CR': 'Costa Rica',
           'ES': 'España', 'MUNDO': ''}
REGION_ORDER = ('AR', 'UY', 'CR', 'MUNDO', 'ES')
OUTLETS = {
    'infobae': 'infobae.com', 'tn': 'tn.com.ar', 'perfil': 'perfil.com',
    'clarin': 'clarin.com', 'la nacion ar': 'lanacion.com.ar',
    'pagina 12': 'pagina12.com.ar', 'pagina/12': 'pagina12.com.ar',
    'ambito': 'ambito.com', 'ole': 'ole.com.ar', 'tyc sports': 'tycsports.com',
    'montevideo portal': 'montevideo.com.uy', 'subrayado': 'subrayado.com.uy',
    'teledoce': 'teledoce.com', 'el observador': 'elobservador.com.uy',
    'el pais uy': 'elpais.com.uy', 'la diaria': 'ladiaria.com.uy',
    'tenfield': 'tenfield.com.uy', 'caras y caretas': 'carasycaretas.com.uy',
    'crhoy': 'crhoy.com', 'teletica': 'teletica.com', 'delfino': 'delfino.cr',
    'la nacion cr': 'nacion.com', 'la teja': 'lateja.cr',
    'el observador cr': 'observador.cr', 'amelia rueda': 'ameliarueda.com',
    'diario extra': 'diarioextra.com', 'semanario universidad': 'semanariouniversidad.com',
    'bbc': 'bbc.com', 'bbc mundo': 'bbc.com', 'el pais': 'elpais.com',
    'el mundo': 'elmundo.es', 'europa press': 'europapress.es',
    '20minutos': '20minutos.es', 'rtve': 'rtve.es', 'eldiario': 'eldiario.es',
    'el confidencial': 'elconfidencial.com', 'expansion': 'expansion.com',
    'xataka': 'xataka.com', 'hipertextual': 'hipertextual.com',
    'vatican news': 'vaticannews.va', 'diariobitcoin': 'diariobitcoin.com',
    'criptonoticias': 'criptonoticias.com', 'cointelegraph': 'cointelegraph.com',
    'coindesk': 'coindesk.com', 'techcrunch': 'techcrunch.com',
}
UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/130.0 Safari/537.36'
STOP_WORDS = set('de la el los las un una unos unas y o en por para con del al que se su sus a ante tras es como mas no lo le ha sobre este esta entre'.split())


def norm(value):
    return ''.join(c for c in unicodedata.normalize('NFKD', str(value).lower())
                   if not unicodedata.combining(c))


def cell(value):
    return '' if value is None else str(value).strip()


def today_cr():
    return datetime.now(ZoneInfo('America/Costa_Rica')).date().isoformat()


def js_load(sources):
    """Evaluate and validate complete files, in an isolated window-only VM."""
    code = r'''
const vm = require('vm'), fs = require('fs');
const input = JSON.parse(fs.readFileSync(0, 'utf8'));
const result = {};
for (const [name, source] of Object.entries(input)) {
  const ctx = {window: {}};
  vm.runInNewContext(source, ctx, {timeout: 1000, filename: name + '.js'});
  const value = ctx.window[name];
  const fail = () => { throw Error('Estructura inválida: ' + name); };
  if (name === 'POSTS') {
    if (!Array.isArray(value)) fail();
    for (const p of value) {
      if (typeof p !== 'string' && (!p || typeof p.url !== 'string')) fail();
    }
  } else {
    if (!value || Object.keys(value).sort().join() !== 'actualizado,items' ||
        typeof value.actualizado !== 'string' || !Array.isArray(value.items)) fail();
    for (const item of value.items) {
      if (!item || Object.keys(item).sort().join() !== 'medio,region,tema,titulo,url' ||
          !Object.values(item).every(v => typeof v === 'string')) fail();
    }
  }
  result[name] = value;
}
process.stdout.write(JSON.stringify(result));
'''
    proc = subprocess.run(['node', '-e', code], input=json.dumps(sources),
                          text=True, capture_output=True, timeout=8)
    if proc.returncode:
        raise ValueError('node: ' + proc.stderr.strip()[:1500])
    return json.loads(proc.stdout)


def js_tokens(source):
    """Positions of JS data tokens, excluding comments/whitespace and strings' contents."""
    pattern = r'\s+|//[^\r\n]*|/\*[\s\S]*?\*/|"(?:\\[\s\S]|[^"\\])*"|\'(?:\\[\s\S]|[^\'\\])*\'|[A-Za-z_$][\w$]*|.'
    for match in re.finditer(pattern, source):
        token = match.group()
        if token.isspace() or token.startswith(('//', '/*')):
            continue
        yield token, match.start(), match.end()


def posts_layout(source):
    tokens = list(js_tokens(source))
    start = next((i + 4 for i in range(len(tokens) - 4)
                  if [t[0] for t in tokens[i:i + 5]] == ['window', '.', 'POSTS', '=', '[']), None)
    if start is None:
        raise ValueError('No se encontró window.POSTS = [')
    depth, entry, spans = 0, None, []
    for token, left, right in tokens[start + 1:]:
        if depth == 0 and token in (',', ']'):
            if entry is not None:
                spans.append((entry, end))
                entry = None
            if token == ']':
                return tokens[start][1], left, spans
            continue
        if entry is None:
            entry = left
        if token in ('[', '{', '('):
            depth += 1
        elif token in (']', '}', ')'):
            depth -= 1
        end = right
    raise ValueError('POSTS sin cierre')


def host(url):
    return (urlsplit(url).hostname or '').lower().removeprefix('www.')


def blocked(url):
    domain = host(url)
    return any(domain == d or domain.endswith('.' + d) for d in BLOCKED_DOMAINS)


def request(url, deadline, data=None, *, redirect_only=False):
    domain = host(url)
    acquired = False
    try:
        if domain == 'news.google.com':
            acquired = GOOGLE_SLOTS.acquire(timeout=max(0, deadline - time.monotonic()))
            if not acquired:
                raise TimeoutError('Presupuesto de tiempo agotado')
        with RATE_LOCK:
            if domain in RATE_LIMITED:
                raise ValueError('HTTP 429: solicitudes suspendidas para ' + domain)
        try:
            return _request(url, deadline, data, redirect_only=redirect_only)
        except HTTPError as exc:
            if exc.code == 429:
                limited = host(exc.geturl()) or domain
                with RATE_LOCK:
                    RATE_LIMITED.add(limited)
                    # Google redirects throttled News requests to google.com/sorry.
                    RATE_LIMITED.add(domain)
                exc.close()
                raise ValueError('HTTP 429: solicitudes suspendidas para ' + limited) from exc
            raise
    finally:
        if acquired:
            GOOGLE_SLOTS.release()


def _request(url, deadline, data=None, *, redirect_only=False):
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise TimeoutError('Presupuesto de tiempo agotado')
    if urlsplit(url).scheme not in ('http', 'https'):
        raise ValueError('URL no HTTP(S)')
    headers = {'User-Agent': UA, 'Accept-Language': 'es-419,es;q=0.9',
               'Accept-Encoding': 'identity'}
    if data is not None:
        headers['Content-Type'] = 'application/x-www-form-urlencoded;charset=UTF-8'
    try:
        response = urlopen(Request(url, data=data, headers=headers),
                           timeout=min(HTTP_TIMEOUT, remaining))
    except HTTPError as exc:
        if not redirect_only:
            raise
        # A TikTok video may block embedding clients after successfully redirecting.
        final = exc.geturl()
        exc.close()
        return final, ''
    with response:
        if redirect_only:
            return response.geturl(), ''
        if response.status != 200:
            raise ValueError('HTTP ' + str(response.status))
        return response.geturl(), response.read(2_000_000).decode('utf-8', 'replace')


def parallel(jobs, function, deadline):
    """Results keyed by input index; deterministic callers ignore completion order."""
    results = {}
    pool = ThreadPoolExecutor(max_workers=WORKERS)
    futures = {pool.submit(function, job): i for i, job in enumerate(jobs)}
    try:
        for future in as_completed(futures, timeout=max(0.01, deadline - time.monotonic())):
            try:
                results[futures[future]] = (future.result(), None)
            except Exception as exc:
                results[futures[future]] = (None, str(exc))
    except TimeoutError:
        pass
    finally:
        for future, index in futures.items():
            if index not in results:
                future.cancel()
                results[index] = (None, 'Tiempo agotado')
        pool.shutdown(wait=False, cancel_futures=True)
    return results


def social_url(url, deadline=None):
    parts = urlsplit(url)
    domain = host(url)
    if parts.scheme not in ('http', 'https') or parts.username or parts.password:
        raise ValueError('URL inválida: se requiere http(s)')
    if domain in ('vm.tiktok.com', 'vt.tiktok.com'):
        if deadline is None:
            raise ValueError('Enlace corto sin resolver')
        final, _ = request(url, deadline, redirect_only=True)
        if host(final) not in ('tiktok.com', 'm.tiktok.com'):
            raise ValueError('TikTok corto no redirigió a un video')
        return social_url(final)
    if domain in ('x.com', 'twitter.com', 'mobile.twitter.com', 'mobile.x.com'):
        match = re.fullmatch(r'/([\w]+)/status/(\d+)(?:/(?:photo|video)/\d+)?/?', parts.path)
        if match:
            return 'https://x.com/' + match[1] + '/status/' + match[2]
        raise ValueError('X/Twitter: se requiere un enlace status')
    if domain == 'instagram.com':
        match = re.fullmatch(r'/(p|reel|tv)/([\w-]+)/?', parts.path)
        if match:
            return 'https://www.instagram.com/' + match[1] + '/' + match[2] + '/'
        raise ValueError('Instagram: se requiere p/reel/tv')
    if domain in ('tiktok.com', 'm.tiktok.com'):
        match = re.fullmatch(r'/(@[^/]+)/video/(\d+)/?', parts.path)
        if match:
            return 'https://www.tiktok.com/' + match[1] + '/video/' + match[2]
        raise ValueError('TikTok: se requiere un enlace completo /@usuario/video/id')
    if domain in ('youtube.com', 'youtu.be', 'm.youtube.com'):
        raise ValueError('YouTube excluido de POSTS')
    if domain == 'substack.com' or domain.endswith('.substack.com'):
        raise ValueError('Substack excluido de POSTS')
    raise ValueError('Dominio no admitido: ' + domain)


def social_key(url):
    try:
        canonical = social_url(url)
        if host(canonical) == 'x.com':
            return 'x:' + canonical.rsplit('/', 1)[1]
        return canonical
    except ValueError:
        return url


def render_entry(post, sample):
    quote = "'" if re.search(r"\burl\s*:\s*'", sample) else '"'
    def encode(value):
        if isinstance(value, str):
            result = json.dumps(value, ensure_ascii=False)
            if quote == "'":
                result = "'" + result[1:-1].replace('\\"', '"').replace("'", "\\'") + "'"
            return result
        if isinstance(value, list):
            sep = ', ' if re.search(r'["\'], ["\']', sample) else ','
            return '[' + sep.join(encode(v) for v in value) + ']'
        return json.dumps(value, ensure_ascii=False)
    keys = ['url', 'date', 'note', 'tags', 'pin']
    keys += [k for k in post if k not in keys]
    return '{ ' + ', '.join(k + ': ' + encode(post[k]) for k in keys if k in post) + ' }'


def rebuild_posts(source, previous, rows, today, deadline, report):
    if not isinstance(rows, list):
        raise ValueError('--posts debe contener una lista de filas')
    opening, closing, spans = posts_layout(source)
    if len(spans) != len(previous):
        raise ValueError('No se pudo asociar el formato de POSTS a sus entradas')
    old, raw = {}, {}
    for post, (left, right) in zip(previous, spans):
        value = {'url': post} if isinstance(post, str) else post
        key = social_key(value['url'])
        old[key], raw[key] = value, source[left:right]
    jobs = []
    for index, row in enumerate(rows, 1):
        if not isinstance(row, list) or not 1 <= len(row) <= 6:
            report['skipped_links'].append({'row': index, 'url': '', 'reason': 'Fila inválida (1–6 columnas)'})
            continue
        if index == 1 and norm(cell(row[0])) == 'link':
            continue
        row = row + [''] * (6 - len(row))
        if not any(cell(c) for c in row):
            continue
        jobs.append((index, row))
    resolved = parallel(jobs, lambda job: social_url(cell(job[1][0]), deadline), deadline)
    entries, seen, pins = [], set(), set()
    for i in reversed(range(len(jobs))):
        row_index, row = jobs[i]
        url, error = resolved[i]
        key = social_key(url) if url else None
        if error or key in seen:
            report['skipped_links'].append({'row': row_index, 'url': cell(row[0]),
                                            'reason': error or 'URL duplicada; prevalece la última fila'})
            continue
        seen.add(key)
        post = dict(old.get(key, {}))
        post.update(url=url, date=post.get('date') or today)
        for field in ('note', 'tags', 'pin'):
            post.pop(field, None)
        tags = list(dict.fromkeys(cell(t).replace('#', '').strip() for t in row[1:4]))
        tags = [t for t in tags if t]
        if cell(row[4]):
            post['note'] = cell(row[4])
        if tags:
            post['tags'] = tags
        pin = cell(row[5])
        if pin in ('1', '2', '3') and pin not in pins:
            post['pin'] = int(pin)
            pins.add(pin)
        elif pin:
            report['warnings'].append({'row': row_index, 'reason': 'Fijar inválido o duplicado: ' + pin})
        entries.append(post)
    new = {social_key(p['url']): p for p in entries}
    report['posts'] = {
        'added': [p['url'] for k, p in new.items() if k not in old],
        'removed': [p['url'] for k, p in old.items() if k not in new],
        'changed': [p['url'] for k, p in new.items() if k in old and p != old[k]],
        'reordered': list(new) != [k for k in old if k in new],
        'total': len(entries),
    }
    if entries == previous:
        return source
    sample = next((raw[k] for k in raw if raw[k].startswith('{')), '')
    indent_match = re.search(r'\n([ \t]+)\{', source[opening:closing])
    indent = indent_match[1] if indent_match else '  '
    newline = '\r\n' if '\r\n' in source else '\n'
    prefix = source[opening + 1:spans[0][0]] if spans else newline + indent
    rendered = [raw[social_key(p['url'])] if p == old.get(social_key(p['url']))
                else render_entry(p, sample) for p in entries]
    trailing = bool(spans and ',' in source[spans[-1][1]:closing])
    body = prefix + (',' + newline + indent).join(rendered)
    if rendered and trailing:
        body += ','
    body += newline
    return source[:opening + 1] + body + source[closing:]


def load_topics(path, previous):
    if path is None or not path.exists():
        counts = Counter((i['region'], i['tema']) for i in previous['items'])
        return [{'row': n, 'region': r, 'tema': t, 'count': c, 'media': ''}
                for n, ((r, t), c) in enumerate(counts.items(), 1)], 40
    data = json.loads(path.read_text(encoding='utf-8-sig'))
    if not isinstance(data, dict) or not isinstance(data.get('rows'), list):
        raise ValueError('--temas debe contener {rows: [...], max: G2}')
    maximum = data.get('max', 40)
    maximum = 40 if maximum in (None, '') else min(40, max(0, int(maximum)))
    topics = []
    for index, row in enumerate(data['rows'], 1):
        if not isinstance(row, list) or len(row) != 5:
            raise ValueError('Fila de temas inválida: ' + str(index))
        if index == 1 and norm(row[0]) == 'activo':
            continue
        if norm(cell(row[0])) not in ('1', 'true', 'si', 'x', 'yes', 'activo'):
            continue
        region, topic = cell(row[1]).upper(), cell(row[2])
        if not region or not topic:
            raise ValueError('Región/tema vacío en fila ' + str(index))
        count = max(0, int(row[3] or 0))
        topics.append({'row': index, 'region': region, 'tema': topic,
                       'count': count, 'media': cell(row[4])})
    return topics, maximum


def outlet_domains(topic, previous, report):
    mapping = dict(OUTLETS)
    for item in previous['items']:
        mapping.setdefault(norm(item['medio']), host(item['url']))
    if topic['region'] == 'UY':
        mapping['el pais'] = 'elpais.com.uy'
    mapping['la nacion'] = 'nacion.com' if topic['region'] == 'CR' else 'lanacion.com.ar'
    domains = []
    for value in re.split(r'[,;|\n]+', topic['media']):
        value = value.strip()
        if not value:
            continue
        domain = mapping.get(norm(value))
        if not domain:
            candidate = re.sub(r'^site:', '', value)
            if re.fullmatch(r'(?:https?://)?(?:[\w-]+\.)+[a-zA-Z]{2,}(?:/[^\s]*)?', candidate):
                domain = host(candidate if '://' in candidate else 'https://' + candidate)
        if domain:
            domains.append(domain)
        else:
            # Also recognize names embedded in notes, e.g. "priorizar TN y Infobae".
            remaining, found = norm(value), False
            for name in sorted(mapping, key=len, reverse=True):
                pattern = r'(?<!\w)' + re.escape(name) + r'(?!\w)'
                if re.search(pattern, remaining):
                    domains.append(mapping[name])
                    remaining = re.sub(pattern, ' ', remaining)
                    found = True
            if not found:
                report['warnings'].append({'row': topic['row'], 'reason': 'Medio/nota sin dominio reconocido: ' + value})
    return list(dict.fromkeys(domains))


def clean_title(title, outlet):
    title = html.unescape(re.sub(r'<[^>]+>', '', title))
    title = re.sub(r'^\s*VIDEO\s*[|:–—-]\s*', '', title, flags=re.I)
    if outlet:
        title = re.sub(r'\s+[-–—|]\s*' + re.escape(outlet) + r'\s*$', '', title, flags=re.I)
    title = re.sub(r'\s+', ' ', title).strip()
    if len(title) > 110:
        title = title[:109].rsplit(' ', 1)[0].rstrip(' ,;:–—-') + '…'
    return title


def title_tokens(title):
    return set(re.findall(r'[a-z0-9]+', norm(title))) - STOP_WORDS


def similar(a, b, threshold=0.45):
    return bool(a and b and len(a & b) >= min(3, len(a), len(b))
                and len(a & b) / len(a | b) >= threshold)


def fetch_rss(job, now, deadline):
    topic, query = job
    gl = topic['region'] if topic['region'] in ('AR', 'UY', 'CR', 'ES') else 'US'
    params = urlencode({'q': query + ' when:36h', 'hl': 'es-419', 'gl': gl, 'ceid': gl + ':es-419'})
    _, body = request('https://news.google.com/rss/search?' + params, deadline)
    items, skipped = [], []
    for entry in ET.fromstring(body).findall('.//item'):
        try:
            date = parsedate_to_datetime(entry.findtext('pubDate', ''))
            if date.tzinfo is None:
                date = date.replace(tzinfo=timezone.utc)
            if not now - timedelta(hours=36) <= date <= now:
                continue
        except (TypeError, ValueError, OverflowError):
            continue
        source = entry.find('source')
        outlet = source.text if source is not None and source.text else ''
        source_url = source.get('url', '') if source is not None else ''
        if blocked(source_url):
            skipped.append({'url': entry.findtext('link', ''), 'topic': topic['tema'],
                            'reason': 'Dominio bloqueado/paywall: ' + host(source_url)})
            continue
        title = clean_title(entry.findtext('title', ''), outlet)
        link = entry.findtext('link', '')
        if title and link and outlet:
            items.append({'titulo': title, 'medio': outlet, 'url': link,
                          'region': topic['region'], 'tema': topic['tema'],
                          '_tokens': title_tokens(title), '_outlet': host(source_url) or norm(outlet),
                          '_time': date.timestamp()})
    return {'items': items, 'skipped': skipped}


def decode_google(url, deadline):
    """Legacy base64 URLs, redirects, then the signed RPC used in /workspace/news/gn.py."""
    if host(url) != 'news.google.com':
        return url
    match = re.search(r'/(?:articles|read)/([^/?]+)', urlsplit(url).path)
    if not match:
        raise ValueError('Enlace Google News no reconocido')
    article = match[1]
    try:
        decoded = base64.urlsafe_b64decode(article + '=' * (-len(article) % 4))
        legacy = re.search(rb'https?://[^\x00-\x20\x7f-\xff]+', decoded)
        if legacy:
            return legacy[0].decode()
    except ValueError:
        pass
    final, page = request('https://news.google.com/articles/' + article, deadline)
    if host(final) != 'news.google.com':
        return final
    signature = re.search(r'data-n-a-sg=["\']([^"\']+)', page)
    timestamp = re.search(r'data-n-a-ts=["\'](\d+)', page)
    if not signature or not timestamp:
        final, page = request('https://news.google.com/rss/articles/' + article, deadline)
        if host(final) != 'news.google.com':
            return final
        signature = re.search(r'data-n-a-sg=["\']([^"\']+)', page)
        timestamp = re.search(r'data-n-a-ts=["\'](\d+)', page)
    if not signature or not timestamp:
        raise ValueError('Google News no entregó firma de decodificación')
    args = ['garturlreq', [['X', 'X', ['X', 'X'], None, None, 1, 1, 'US:es-419',
                            None, 1, None, None, None, None, None, 0, 1],
                           'X', 'X', 1, [1, 1, 1], 1, 1, None, 0, 0, None, 0],
            article, int(timestamp[1]), html.unescape(signature[1])]
    payload = urlencode({'f.req': json.dumps([[['Fbv4je', json.dumps(args)]]])}).encode()
    _, body = request('https://news.google.com/_/DotsSplashUi/data/batchexecute', deadline, payload)
    # Batchexecute may include an anti-XSSI line and length prefixes.
    for line in body.splitlines():
        if not line.startswith('['):
            continue
        try:
            for result in json.loads(line):
                if isinstance(result, list) and len(result) > 2 and result[1] == 'Fbv4je':
                    value = json.loads(result[2])
                    if value[0] == 'garturlres' and value[1].startswith(('https://', 'http://')):
                        return value[1]
        except (ValueError, TypeError, IndexError):
            continue
    raise ValueError('No se pudo decodificar Google News')


def canonical_news(url):
    p = urlsplit(url)
    query = [(k, v) for k, v in parse_qsl(p.query, keep_blank_values=True)
             if not k.lower().startswith('utm_') and k.lower() not in ('fbclid', 'gclid', 'oc')]
    return urlunsplit((p.scheme, p.netloc.lower(), p.path, urlencode(query), ''))


def verify_article(item, deadline):
    url = decode_google(item['url'], deadline)
    if blocked(url):
        raise ValueError('Dominio bloqueado/paywall: ' + host(url))
    final, body = request(url, deadline)
    if host(final) in ('news.google.com', 'consent.google.com') or blocked(final):
        raise ValueError('Redirección bloqueada/paywall: ' + host(final))
    if re.search(r'isAccessibleForFree["\']?\s*:\s*(?:false|["\']false["\'])', body, re.I):
        raise ValueError('Artículo de pago (isAccessibleForFree=false)')
    if re.search(r'<title[^>]*>\s*(?:just a moment|access denied|robot or human|attention required|captcha|403 forbidden)', body, re.I):
        raise ValueError('Página bloqueada/antibot')
    if re.search(r'/(?:login|signin|subscribe|suscripcion|consent)(?:/|$)', urlsplit(final).path, re.I):
        raise ValueError('Redirección a acceso/suscripción')
    if urlsplit(final).path in ('', '/') and urlsplit(url).path not in ('', '/'):
        raise ValueError('Redirección a portada en lugar del artículo')
    return canonical_news(final)


def rebuild_news(topics, maximum, previous, today, deadline, report):
    now = datetime.now(timezone.utc)
    jobs, owners = [], []
    for index, topic in enumerate(topics):
        if not topic['count'] or not maximum:
            continue
        base = topic['tema']
        location = REGIONS.get(topic['region'], topic['region'])
        if location:
            base += ' ' + location
        domains = outlet_domains(topic, previous, report)
        queries = [base]
        if domains:
            queries.append(base + ' (' + ' OR '.join('site:' + d for d in domains) + ')')
        for query in queries:
            jobs.append((topic, query))
            owners.append(index)
    rss = parallel(jobs, lambda job: fetch_rss(job, now, deadline), min(deadline, time.monotonic() + 45))
    candidates = [[] for _ in topics]
    for index, (feed, error) in sorted(rss.items()):
        if error:
            report['errors'].append({'stage': 'rss', 'topic': jobs[index][0]['tema'], 'reason': error})
        else:
            candidates[owners[index]].extend(feed['items'])
            report['skipped_links'].extend(feed['skipped'])
    for index, items in enumerate(candidates):
        unique = {i['url']: i for i in items}
        items = list(unique.values())
        for item in items:
            item['_coverage'] = len({other['_outlet'] for other in items
                                     if similar(item['_tokens'], other['_tokens'])})
        candidates[index] = sorted(items, key=lambda i: (-i['_coverage'], -i['_time'], i['url']))[:60]
    selected = [[] for _ in topics]
    cache, seen_urls, seen_titles = {}, set(), []
    positions = [0] * len(topics)
    # Each round verifies a small batch per topic, avoiding one topic monopolizing workers.
    while time.monotonic() < deadline:
        batch, refs = [], []
        for index, topic in enumerate(topics):
            remaining = min(topic['count'], maximum) - len(selected[index])
            if remaining <= 0:
                continue
            start = positions[index]
            chunk = candidates[index][start:start + min(4, remaining + 1)]
            positions[index] += len(chunk)
            batch.extend(chunk)
            refs.extend([index] * len(chunk))
        if not batch:
            break
        pending = list({i['url']: i for i in batch if i['url'] not in cache}.values())
        checked = parallel(pending, lambda item: verify_article(item, deadline), deadline)
        for n, result in checked.items():
            cache[pending[n]['url']] = result
        for index, item in zip(refs, batch):
            url, error = cache[item['url']]
            if error:
                report['skipped_links'].append({'url': item['url'], 'topic': item['tema'], 'reason': error})
                continue
            if len(selected[index]) >= min(topics[index]['count'], maximum):
                continue
            key = re.sub(r'^https?://(?:www\.)?', '', url).rstrip('/')
            if key in seen_urls or any(similar(item['_tokens'], t, 0.8) for t in seen_titles):
                report['skipped_links'].append({'url': url, 'topic': item['tema'],
                                                'reason': 'Noticia duplicada (URL o título similar)'})
                continue
            seen_urls.add(key)
            seen_titles.append(item['_tokens'])
            selected[index].append({k: url if k == 'url' else item[k]
                                    for k in ('titulo', 'medio', 'url', 'region', 'tema')})
        if 'news.google.com' in RATE_LIMITED:
            break
    for domain in sorted(RATE_LIMITED):
        report['errors'].append({'stage': 'http', 'reason': 'HTTP 429: solicitudes suspendidas para ' + domain})
    output, capacity = [], maximum
    for topic, items in zip(topics, selected):
        kept = items[:capacity]
        capacity -= len(kept)
        output.extend(kept)
        result = {'row': topic['row'], 'region': topic['region'], 'tema': topic['tema'],
                  'requested': topic['count'], 'verified': len(items), 'filled': len(kept)}
        report['news_per_topic'].append(result)
        if len(kept) < topic['count']:
            if capacity == 0:
                reason = 'límite G2'
            elif 'news.google.com' in RATE_LIMITED:
                reason = 'Google News limitó las solicitudes (HTTP 429)'
            elif time.monotonic() >= deadline:
                reason = 'tiempo agotado'
            else:
                reason = 'sin suficientes noticias recientes, únicas y accesibles'
            report['topics_unfilled'].append({**result, 'reason': reason})
    groups = {}
    for item in output:
        groups.setdefault(item['region'], deque()).append(item)
    order = list(REGION_ORDER) + [r for r in groups if r not in REGION_ORDER]
    interleaved = []
    while any(groups.values()):
        for region in order:
            if groups.get(region):
                interleaved.append(groups[region].popleft())
    report['news_total'] = len(interleaved)
    return {'actualizado': today, 'items': interleaved}


def empty_report(dry_run):
    return {'dry_run': dry_run, 'posts': {}, 'skipped_links': [], 'news_per_topic': [],
            'topics_unfilled': [], 'errors': [], 'warnings': [], 'changed_files': []}


def build(args, report):
    deadline = time.monotonic() + WORK_SECONDS
    originals = {name: (ROOT / name).read_bytes().decode('utf-8')
                 for name in ('posts.js', 'noticias.js')}
    previous = js_load({'POSTS': originals['posts.js'], 'NOTICIAS': originals['noticias.js']})
    rows = json.loads(Path(args.posts).read_text(encoding='utf-8-sig'))
    topics, maximum = load_topics(Path(args.temas) if args.temas else None, previous['NOTICIAS'])
    today = today_cr()
    posts = rebuild_posts(originals['posts.js'], previous['POSTS'], rows, today, deadline, report)
    news = rebuild_news(topics, maximum, previous['NOTICIAS'], today, deadline, report)
    comment = re.match(r'\s*(/\*[\s\S]*?\*/)', originals['noticias.js'])
    news_source = (comment[1] if comment else HEADER) + '\nwindow.NOTICIAS = ' + json.dumps(news, ensure_ascii=False, indent=1) + ';\n'
    sources = {'posts.js': posts, 'noticias.js': news_source}
    validated = js_load({'POSTS': posts, 'NOTICIAS': news_source})
    assert len(validated['NOTICIAS']['items']) <= maximum
    assert all(len(i['titulo']) <= 110 for i in news['items'])
    pins = [p['pin'] for p in validated['POSTS'] if isinstance(p, dict) and 'pin' in p]
    assert len(pins) == len(set(pins)) <= 3 and all(p in (1, 2, 3) for p in pins)
    report['validation'] = 'node vm: OK (POSTS y NOTICIAS)'
    report['changed_files'] = [name for name in sources if sources[name] != originals[name]]
    return originals, sources


def worker(args, pipe):
    report = empty_report(args.dry_run)
    try:
        originals, sources = build(args, report)
        pipe.send((report, originals, sources))
    except Exception as exc:
        report['errors'].append({'stage': 'build', 'reason': str(exc)})
        pipe.send((report, None, None))
    finally:
        pipe.close()


def publish(originals, sources, report, no_push, deadline):
    changed = report['changed_files']
    if not changed:
        report['git'] = 'sin cambios'
        return
    if any(e.get('stage') == 'http' and 'news.google.com' in e.get('reason', '')
           for e in report.get('errors', [])):
        raise RuntimeError('Google News limitó las solicitudes; se conserva el contenido previo y no se hace commit')
    def git(*command, timeout=8):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError('Tiempo global agotado antes de git ' + command[0])
        result = subprocess.run(['git', *command], cwd=ROOT, capture_output=True,
                                text=True, timeout=min(timeout, remaining))
        if result.returncode:
            raise RuntimeError('git ' + command[0] + ': ' + result.stderr.strip())
        return result.stdout
    # Never include pre-existing edits, even in the two generated files.
    if git('status', '--porcelain', '--', *changed).strip():
        raise RuntimeError('Hay cambios locales previos en archivos de destino; no se sobrescriben')
    for name in changed:
        if (ROOT / name).read_bytes().decode('utf-8') != originals[name]:
            raise RuntimeError('El archivo cambió durante la revisión: ' + name)
    for name in changed:
        (ROOT / name).write_bytes(sources[name].encode('utf-8'))
    git('add', '--', *changed)
    git('commit', '--only', '-m', 'Actualiza posts y noticias', '--', *changed, timeout=12)
    report['git'] = 'commit creado'
    if not no_push:
        git('push', timeout=18)
        report['git'] = 'commit y push realizados'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--posts', required=True, help='JSON de filas de posts')
    parser.add_argument('--temas', help='JSON {rows, max}; si falta reutiliza noticias.js')
    parser.add_argument('--dry-run', action='store_true', help='Valida y reporta sin escribir ni hacer commit/push')
    parser.add_argument('--no-push', action='store_true', help='Escribe y hace commit, pero no push')
    args = parser.parse_args(argv)
    started = time.monotonic()
    # A process boundary also bounds stalled DNS, slow-drip HTTP and executor teardown.
    parent, child = multiprocessing.Pipe(duplex=False)
    process = multiprocessing.Process(target=worker, args=(args, child), daemon=True)
    process.start()
    child.close()
    report, originals, sources = empty_report(args.dry_run), None, None
    try:
        if parent.poll(HARD_SECONDS):
            report, originals, sources = parent.recv()
        else:
            report['errors'].append({'stage': 'deadline', 'reason': 'Límite global de 240 s; no se escribió nada'})
    except EOFError:
        report['errors'].append({'stage': 'worker', 'reason': 'El proceso terminó sin resultado'})
    finally:
        parent.close()
        process.join(timeout=0.1)
        if process.is_alive():
            process.terminate()
            process.join(timeout=1)
    if sources is not None and not args.dry_run:
        try:
            publish(originals, sources, report, args.no_push, started + 290)
        except Exception as exc:
            report['errors'].append({'stage': 'publish', 'reason': str(exc)})
    report['elapsed_seconds'] = round(time.monotonic() - started, 2)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if sources is None or any(e['stage'] == 'publish' for e in report['errors']) else 0


if __name__ == '__main__':
    sys.exit(main())

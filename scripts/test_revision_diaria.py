"""Offline regression tests. Run: python3 -B -m unittest discover -s scripts -p 'test_revision_diaria.py'."""
import base64
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
import json
from pathlib import Path
import subprocess
import tempfile
import time
import unittest
from unittest.mock import patch

import revision_diaria as r


class PostsTests(unittest.TestCase):
    def test_current_file_round_trip_and_dates(self):
        source = (r.ROOT / 'posts.js').read_text()
        posts = r.js_load({'POSTS': source})['POSTS']
        rows = [[p['url'], *(p.get('tags', []) + [''] * (3 - len(p.get('tags', [])))),
                 p.get('note', ''), p.get('pin', '')] for p in reversed(posts)]
        report = r.empty_report(True)
        rebuilt = r.rebuild_posts(source, posts, rows, '2099-01-01', time.monotonic() + 5, report)
        self.assertEqual(rebuilt, source)
        self.assertEqual(report['posts']['changed'], [])

    def test_order_pins_duplicates_and_outside_bytes(self):
        source = ('/* POSTS = [ example ] */\r\nwindow.SITE_CONFIG = {title: "untouched"};\r\n'
                  'window.POSTS = [\r\n  // keep intro\r\n'
                  '  { url: "https://x.com/a/status/1", date: "2020-01-01", tags: ["old"] }\r\n'
                  '];\r\nwindow.AFTER = "[untouched]";\r\n')
        old = r.js_load({'POSTS': source})['POSTS']
        rows = [['Link', 'Etiqueta1', 'Etiqueta2', 'Etiqueta3', 'Nota especial', 'Fijar'],
                ['https://twitter.com/a/status/1?x=1', '#viejo', '', '', '', 1],
                ['https://x.com/new/status/2', '#dos', '', '', '', 1],
                ['https://www.instagram.com/tv/AbC', '#tv', '', '', '', 2],
                ['https://x.com/a/status/1', '#nuevo', '#nuevo', '', 'comillas " ] },', 1],
                ['https://youtu.be/abc', '', '', '', '', ''],
                ['https://blog.substack.com/p/abc', '', '', '', '', '']]
        report = r.empty_report(True)
        result = r.rebuild_posts(source, old, rows, '2026-11-02', time.monotonic() + 5, report)
        a, b, _ = r.posts_layout(source)
        c, d, _ = r.posts_layout(result)
        self.assertEqual(source[:a + 1], result[:c + 1])
        self.assertEqual(source[b:], result[d:])
        posts = r.js_load({'POSTS': result})['POSTS']
        self.assertEqual([p['url'] for p in posts], [rows[4][0], 'https://www.instagram.com/tv/AbC/', rows[2][0]])
        self.assertEqual(posts[0]['date'], '2020-01-01')
        self.assertEqual(posts[1]['date'], '2026-11-02')
        self.assertEqual(posts[0]['tags'], ['nuevo'])
        self.assertEqual([p.get('pin') for p in posts], [1, 2, None])
        self.assertEqual(len(report['skipped_links']), 3)
        self.assertEqual(len(report['warnings']), 1)

    def test_social_urls_and_short_redirect(self):
        with patch.object(r, 'request', return_value=('https://www.tiktok.com/@test/video/123?foo=1', '')):
            self.assertEqual(r.social_url('https://vm.tiktok.com/abc/', time.monotonic() + 5),
                             'https://www.tiktok.com/@test/video/123')
        for url in ['https://x.com/user', 'https://www.tiktok.com/@user',
                    'https://instagram.com/stories/user/123', 'https://x.com.evil.test/a/status/1',
                    'ftp://x.com/a/status/1']:
            with self.subTest(url=url), self.assertRaises(ValueError):
                r.social_url(url)

    def test_node_rejects_wrong_news_shape(self):
        with self.assertRaises(ValueError):
            r.js_load({'NOTICIAS': 'window.NOTICIAS = {items: []};'})


class NewsTests(unittest.TestCase):
    def topic(self, name='Tema', region='AR', count=2):
        return {'row': 1, 'region': region, 'tema': name, 'count': count, 'media': ''}

    def test_fallback_topics_and_cap(self):
        previous = {'items': [{'region': 'UY', 'tema': 'Orsi'}, {'region': 'UY', 'tema': 'Orsi'},
                              {'region': 'AR', 'tema': 'Orsi'}]}
        topics, maximum = r.load_topics(None, previous)
        self.assertEqual([(t['region'], t['count']) for t in topics], [('UY', 2), ('AR', 1)])
        self.assertEqual(maximum, 40)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'temas.json'
            path.write_text(json.dumps({'max': 99, 'rows': [
                ['Activo', 'Región', 'Tema', 'Cuántas', 'Medios o notas'],
                [False, 'AR', 'No', 10, ''], ['sí', 'CR', 'Sí', 3, '']]}))
            topics, maximum = r.load_topics(path, previous)
            self.assertEqual(maximum, 40)
            self.assertEqual([t['tema'] for t in topics], ['Sí'])

    def test_rss_age_locale_paywall_and_cleanup(self):
        now = datetime.now(timezone.utc)
        dates = [now - timedelta(hours=35), now - timedelta(hours=37), now + timedelta(hours=1), now]
        entries = ''.join('<item><title>VIDEO | Nuevo anuncio regional - Medio</title>'
                          '<link>https://example.test/%d</link><pubDate>%s</pubDate>'
                          '<source url="https://%s">Medio</source></item>' %
                          (i, format_datetime(date), 'elpais.com.uy' if i == 3 else 'example.test')
                          for i, date in enumerate(dates))
        with patch.object(r, 'request', return_value=('', '<rss><channel>' + entries + '</channel></rss>')) as request:
            feed = r.fetch_rss((self.topic(region='MUNDO'), 'test'), now, time.monotonic() + 5)
        self.assertEqual(len(feed['items']), 1)
        self.assertEqual(len(feed['skipped']), 1)
        self.assertEqual(feed['items'][0]['titulo'], 'Nuevo anuncio regional')
        self.assertIn('hl=es-419&gl=US&ceid=US%3Aes-419', request.call_args.args[0])
        self.assertIn('when%3A36h', request.call_args.args[0])
        self.assertLessEqual(len(r.clean_title('Palabra ' * 100, '')), 110)

    def test_google_legacy_redirect_and_signed_rpc(self):
        url = 'https://example.test/articulo'
        article = base64.urlsafe_b64encode(b'\x08\x13\x22' + url.encode() + b'\xd2\x01\x00').decode().rstrip('=')
        self.assertEqual(r.decode_google('https://news.google.com/rss/articles/' + article, time.monotonic() + 5), url)
        with patch.object(r, 'request', return_value=(url, '')):
            self.assertEqual(r.decode_google('https://news.google.com/articles/AU_yqL', time.monotonic() + 5), url)
        response = ")]}'\n\n123\n" + json.dumps([['wrb.fr', 'Fbv4je', json.dumps(['garturlres', url])]])
        with patch.object(r, 'request', side_effect=[
            ('https://news.google.com/articles/AU_yqL', '<div data-n-a-sg="sig" data-n-a-ts="123">'),
            ('', response)]) as request:
            self.assertEqual(r.decode_google('https://news.google.com/articles/AU_yqL', time.monotonic() + 5), url)
            self.assertEqual(len(request.call_args.args), 3)

    def test_verified_url_and_soft_blocks(self):
        item = {'url': 'https://example.test/article'}
        with patch.object(r, 'request', return_value=('https://example.test/article?utm_source=rss&story=1', '<html>ok</html>')):
            self.assertEqual(r.verify_article(item, time.monotonic() + 5), 'https://example.test/article?story=1')
        for url, body in [('https://example.test/article', '<title>Just a moment...</title>'),
                          ('https://example.test/article', '{"isAccessibleForFree": false}'),
                          ('https://example.test/login', ''), ('https://example.test/', ''),
                          ('https://elpais.com.uy/article', '')]:
            with self.subTest(url=url, body=body), patch.object(r, 'request', return_value=(url, body)), self.assertRaises(ValueError):
                r.verify_article(item, time.monotonic() + 5)

    def test_coverage_priority_counts_dedupe_interleave_and_trim(self):
        topics = [self.topic('Argentina', 'AR', 2), self.topic('Uruguay', 'UY', 2),
                  self.topic('España', 'ES', 2)]
        titles = ['Gobierno anuncia nuevo plan económico nacional',
                  'Gobierno presenta nuevo plan económico nacional',
                  'Científicos descubren planeta lejano con océanos',
                  'Deportista consigue récord histórico mundial']
        def feed(job, now, deadline):
            topic, query = job
            items = []
            for i, title in enumerate(titles):
                # Region-specific words avoid deduping genuinely different test stories.
                title = title if topic['region'] == 'AR' else topic['tema'] + ' ' + title.replace('Gobierno', 'Presidente')
                items.append({'titulo': title, 'medio': 'Outlet' + str(i),
                              'url': 'https://example.test/' + topic['region'] + str(i),
                              'region': topic['region'], 'tema': topic['tema'],
                              '_tokens': r.title_tokens(title), '_outlet': str(i), '_time': i})
            return {'items': items, 'skipped': []}
        report = r.empty_report(True)
        with patch.object(r, 'fetch_rss', side_effect=feed), patch.object(r, 'verify_article', side_effect=lambda i, d: i['url']):
            news = r.rebuild_news(topics, 3, {'items': []}, '2026-11-02', time.monotonic() + 5, report)
        self.assertEqual(len(news['items']), 3)
        self.assertEqual([i['region'] for i in news['items']], ['AR', 'UY', 'AR'])
        self.assertTrue(news['items'][0]['url'].endswith('AR1'))
        self.assertEqual([t['filled'] for t in report['news_per_topic']], [2, 1, 0])
        self.assertEqual(report['topics_unfilled'][-1]['reason'], 'límite G2')

    def test_outlet_names_generate_site_queries(self):
        topic = self.topic()
        topic['media'] = 'Infobae; TN; https://example.test; nota desconocida'
        report = r.empty_report(True)
        self.assertEqual(r.outlet_domains(topic, {'items': []}, report), ['infobae.com', 'tn.com.ar', 'example.test'])
        self.assertEqual(len(report['warnings']), 1)
        with patch.object(r, 'fetch_rss', return_value={'items': [], 'skipped': []}) as fetch:
            r.rebuild_news([topic], 40, {'items': []}, '2026-11-02', time.monotonic() + 5, report)
        queries = [call.args[0][1] for call in fetch.call_args_list]
        self.assertTrue(any('site:infobae.com OR site:tn.com.ar' in q for q in queries))

    def test_429_stops_further_requests_to_host(self):
        url = 'https://news.google.com/articles/example'
        error = r.HTTPError('https://www.google.com/sorry/index', 429, 'Too Many Requests', {}, None)
        with patch.object(r, 'RATE_LIMITED', set()), patch.object(r, '_request', side_effect=error) as request:
            for _ in range(2):
                with self.assertRaisesRegex(ValueError, 'HTTP 429'):
                    r.request(url, time.monotonic() + 5)
            self.assertEqual(request.call_count, 1)
            self.assertIn('news.google.com', r.RATE_LIMITED)


class PublicationTests(unittest.TestCase):
    def test_rate_limited_news_does_not_publish_incomplete_run(self):
        report = {'changed_files': ['noticias.js'], 'errors': [
            {'stage': 'http', 'reason': 'HTTP 429: solicitudes suspendidas para news.google.com'}]}
        with patch.object(r.subprocess, 'run') as run, self.assertRaises(RuntimeError):
            r.publish({}, {}, report, False, time.monotonic() + 5)
        run.assert_not_called()

    def test_unchanged_does_not_run_git(self):
        with patch.object(r.subprocess, 'run') as run:
            r.publish({}, {}, {'changed_files': []}, False, time.monotonic() + 5)
        run.assert_not_called()

    def test_commit_scoped_and_no_push(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'posts.js').write_text('old')
            result = subprocess.CompletedProcess([], 0, '', '')
            with patch.object(r, 'ROOT', root), patch.object(r.subprocess, 'run', return_value=result) as run:
                report = {'changed_files': ['posts.js']}
                r.publish({'posts.js': 'old'}, {'posts.js': 'new'}, report, True, time.monotonic() + 5)
            commands = [c.args[0] for c in run.call_args_list]
            self.assertFalse(any('push' in c for c in commands))
            commit = next(c for c in commands if 'commit' in c)
            self.assertIn('--only', commit)
            self.assertEqual(commit[-2:], ['--', 'posts.js'])

    def test_dry_run_never_publishes_or_changes_content(self):
        # Run the real CLI, including its process boundary and Node validation,
        # with zero news requested so this regression test requires no network.
        before = {name: (r.ROOT / name).read_bytes() for name in ('posts.js', 'noticias.js')}
        with tempfile.TemporaryDirectory() as tmp:
            posts, temas = Path(tmp) / 'posts.json', Path(tmp) / 'temas.json'
            posts.write_text('[]')
            temas.write_text('{"rows": [], "max": 0}')
            result = subprocess.run(['python3', '-B', str(r.ROOT / 'scripts/revision_diaria.py'),
                                     '--posts', str(posts), '--temas', str(temas), '--dry-run'],
                                    capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report['changed_files'], ['posts.js', 'noticias.js'])
        self.assertNotIn('git', report)
        for name, body in before.items():
            self.assertEqual((r.ROOT / name).read_bytes(), body)


if __name__ == '__main__':
    unittest.main()

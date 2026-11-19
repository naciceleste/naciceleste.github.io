"""Offline regression tests. Run: python3 -B -m unittest discover -s scripts -p 'test_revision_diaria.py'."""
import base64
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
import html
import json
from pathlib import Path
import subprocess
import tempfile
import time
import unittest
from unittest.mock import Mock, patch
from urllib.parse import parse_qsl, urlencode, urlsplit

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
    def setUp(self):
        self.rate_patch = patch.object(r, 'RATE_LIMITED', set())
        self.rate_patch.start()
        self.addCleanup(self.rate_patch.stop)

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
        self.assertEqual(feed['items'][0]['_source'], 'google')
        self.assertIn('hl=es-419&gl=US&ceid=US%3Aes-419', request.call_args.args[0])
        self.assertIn('when%3A36h', request.call_args.args[0])
        self.assertLessEqual(len(r.clean_title('Palabra ' * 100, '')), 110)

    def wrapper(self, url):
        return 'http://www.bing.com/news/apiclick.aspx?' + urlencode({'ref': 'FexRss', 'url': url})

    def test_bing_rss_age_source_unwrap_paywall_and_locale(self):
        now = datetime(2026, 11, 18, 12, tzinfo=timezone.utc)
        dates = [now, now - timedelta(hours=36), now - timedelta(hours=36, seconds=1),
                 now + timedelta(seconds=1), now, now, now, now, now]
        entries = []
        for i, date in enumerate(dates):
            link = self.wrapper('https://elpais.com.uy/article' if i == 4 else 'https://example.test/' + str(i))
            if i == 0:
                link = self.wrapper('https://www.msn.com/redirect?' + urlencode({'url': link}))
            entries.append('<item><title>%s</title><link>%s</link><pubDate>%s</pubDate>%s</item>' % (
                '' if i == 6 else 'VIDEO | Nuevo anuncio regional del Tema - Medio',
                '' if i == 7 else html.escape(link),
                'invalid' if i == 8 else format_datetime(date),
                '' if i == 5 else '<b:Source>Medio</b:Source>'))
        body = '<rss xmlns:b="https://www.bing.com/news/search?arbitrary=namespace"><channel>' + ''.join(entries) + '</channel></rss>'
        query = 'Tema Argentina (site:example.test)'
        markets = {'AR': 'AR', 'ARGENTINA': 'AR', 'UY': 'UY', 'URUGUAY': 'UY',
                   'CR': 'CR', 'COSTA RICA': 'CR', 'ES': 'ES', 'ESPAÑA': 'ES',
                   'MUNDO': 'US', 'OTRO': 'US'}
        for region, cc in markets.items():
            with self.subTest(region=region), patch.object(r, 'request', return_value=('', body)) as request:
                feed = r.fetch_bing_rss((self.topic(region=region), query), now, time.monotonic() + 5)
            params = dict(parse_qsl(urlsplit(request.call_args.args[0]).query))
            self.assertEqual(params, {'q': query, 'format': 'rss', 'setlang': 'es', 'cc': cc,
                                      'mkt': 'es-' + cc, 'qft': 'sortbydate="1"'})
            self.assertNotIn('when:36h', params['q'])
            self.assertEqual([i['url'] for i in feed['items']], ['https://example.test/0', 'https://example.test/1'])
            self.assertTrue(all(i['_source'] == 'bing' and i['region'] == region for i in feed['items']))
            self.assertEqual(feed['items'][0]['titulo'], 'Nuevo anuncio regional del Tema')
            self.assertEqual(feed['items'][0]['medio'], 'Medio')
            self.assertEqual(feed['items'][0]['_outlet'], 'example.test')
            self.assertEqual(feed['items'][0]['_tokens'], r.title_tokens('Nuevo anuncio regional del Tema'))
            self.assertEqual(feed['items'][0]['_time'], now.timestamp())
            self.assertEqual(feed['skipped'], [{'url': 'https://elpais.com.uy/article', 'topic': 'Tema',
                                              'reason': 'Dominio bloqueado/paywall: elpais.com.uy'}])

    def test_spanish_and_topic_filters(self):
        topic = self.topic('Luis Alberto Lacalle', 'UY')
        self.assertTrue(r.looks_spanish('Yamandú Orsi hablará ante más de 500 empresarios'))
        self.assertTrue(r.looks_spanish('Nvidia le cierra la puerta a Jensen Huang: no regresará como CEO'))
        self.assertFalse(r.looks_spanish('The S&P 500 Just Ended a Run of 155 Trading Days'))
        self.assertFalse(r.looks_spanish('ASUS Announces Availability of the ProArt GR1X'))
        self.assertFalse(r.looks_spanish('Grok Botが承認なしに業務アプリへアクセスしようとした31回'))
        self.assertFalse(r.looks_spanish('特斯拉时代广场投放FSD广告 Grok Bot亮相Sphere'))
        self.assertFalse(r.looks_spanish('Gestora de genro de Trump anuncia aporte de US$ 33,5 milhões no Nubank'))
        self.assertFalse(r.looks_spanish('Stock Market Today, Nov. 18: S&P 500 Breaks Key Support as Fed Minutes Signal More Rate Hikes Ahead'))
        self.assertFalse(r.looks_spanish('Do que o Flamengo precisa para ser campeão do Brasileirão no Nubank Parque? Veja cenário'))
        self.assertTrue(r.mentions_topic(self.topic('Javier Milei'), 'Javier Milei negó una interna con Patricia Bullrich'))
        self.assertTrue(r.mentions_topic(self.topic('Ratings TV'), 'Rating: cuánto midió el amistoso entre la Selección'))
        self.assertTrue(r.mentions_topic(self.topic('S&P 500', 'MUNDO'), 'S&P 500 suma cinco días de pérdidas'))
        self.assertTrue(r.mentions_topic(self.topic('Agentes IA', 'MUNDO'), 'Bancos responsabilizan a clientes por el uso de agentes de IA'))
        self.assertTrue(r.mentions_topic(self.topic('Selección Uruguaya', 'UY'), 'La selección de Uruguay ganó de visitante'))
        self.assertFalse(r.mentions_topic(self.topic('Banco Central', 'CR'), 'Argentina goleó 7-0 a Costa Rica y cerró el año'))
        self.assertFalse(r.mentions_topic(self.topic('Paxos', 'MUNDO'), 'Las islas Jónicas presentan en Barcelona su apuesta turística'))
        self.assertFalse(r.mentions_topic(self.topic('Hermes Agent', 'MUNDO'), 'ASUS anuncia la disponibilidad del ProArt GR1X'))
        self.assertFalse(r.mentions_topic(topic, 'El gobierno anunció una nueva medida económica'))

    def test_bing_skips_non_spanish_and_off_topic(self):
        now = datetime(2026, 11, 18, 12, tzinfo=timezone.utc)
        entries = ''.join(
            '<item><title>%s</title><link>%s</link><pubDate>%s</pubDate><b:Source>Medio</b:Source></item>' % (
                html.escape(title), html.escape(self.wrapper('https://example.test/%d' % i)), format_datetime(now))
            for i, title in enumerate([
                'Javier Milei anunció una nueva medida económica',
                'The president announced a new economic plan today',
                'Wall Street cerró mixto tras las minutas de la Fed',
            ]))
        body = '<rss xmlns:b="https://www.bing.com/news/search"><channel>' + entries + '</channel></rss>'
        with patch.object(r, 'request', return_value=('', body)):
            feed = r.fetch_bing_rss((self.topic('Javier Milei'), 'Javier Milei Argentina'), now, time.monotonic() + 5)
        self.assertEqual([i['titulo'] for i in feed['items']], ['Javier Milei anunció una nueva medida económica'])
        self.assertEqual([s['reason'] for s in feed['skipped']],
                         ['Titular no está en español', 'Titular no menciona el tema'])

    def test_verify_article_unwraps_bing_before_request(self):
        url = 'https://example.test/article?utm_source=bing'
        with patch.object(r, 'request', return_value=(url, '<title>Noticia</title>')) as request:
            self.assertEqual(r.verify_article({'url': self.wrapper(url)}, time.monotonic() + 5),
                             'https://example.test/article')
        self.assertEqual(request.call_args.args[0], url)
        with patch.object(r, 'request') as request, self.assertRaisesRegex(ValueError, 'Dominio bloqueado'):
            r.verify_article({'url': self.wrapper('https://elpais.com.uy/article')}, time.monotonic() + 5)
        request.assert_not_called()

    def feed(self, topic, count=2, start=0):
        titles = ['Gobierno anuncia nuevo plan económico nacional',
                  'Científicos descubren planeta lejano con océanos',
                  'Deportista consigue récord histórico mundial']
        return {'items': [{'titulo': titles[i], 'medio': 'Medio',
                           'url': 'https://example.test/' + str(i),
                           'region': topic['region'], 'tema': topic['tema'],
                           '_tokens': r.title_tokens(titles[i]), '_outlet': 'example.test', '_time': i}
                          for i in range(start, start + count)], 'skipped': []}

    def test_automatic_bing_for_google_error_empty_and_too_few(self):
        topic = self.topic()
        cases = [(ValueError('HTTP 429: news.google.com'), 'bing'),
                 (ValueError('HTTP 403: bloqueado'), 'bing'),
                 (self.feed(topic, 0), 'bing'), (self.feed(topic, 1), 'google+bing'),
                 (self.feed(topic, 1)['items'] * 2, 'google+bing')]
        for google, source in cases:
            if isinstance(google, list):
                google = {'items': google, 'skipped': []}
            report = r.empty_report(True)
            with self.subTest(google=google), patch.object(r, 'fetch_rss') as fetch, \
                    patch.object(r, 'fetch_bing_rss', return_value=self.feed(topic)) as bing, \
                    patch.object(r, 'verify_article', side_effect=lambda i, d: i['url']):
                if isinstance(google, Exception):
                    fetch.side_effect = google
                else:
                    fetch.return_value = google
                news = r.rebuild_news([topic], 40, {'items': []}, '2026-11-18', time.monotonic() + 5, report)
            bing.assert_called_once()
            self.assertEqual(len(news['items']), 2)
            self.assertEqual(report['news_per_topic'][0]['source'], source)
            self.assertTrue(report['fallback_used'])
            self.assertEqual(report['topics_unfilled'], [])
            self.assertTrue(all(set(i) == {'titulo', 'medio', 'url', 'region', 'tema'} for i in news['items']))

    def test_enough_google_candidates_do_not_query_bing(self):
        topic = self.topic()
        report = r.empty_report(True)
        with patch.object(r, 'fetch_rss', return_value=self.feed(topic)), \
                patch.object(r, 'fetch_bing_rss') as bing, \
                patch.object(r, 'verify_article', side_effect=lambda i, d: i['url']):
            r.rebuild_news([topic], 40, {'items': []}, '2026-11-18', time.monotonic() + 5, report)
        bing.assert_not_called()
        self.assertFalse(report['fallback_used'])
        self.assertEqual(report['news_per_topic'][0]['source'], 'google')

    def test_google_verification_can_take_multiple_batches_without_bing(self):
        topic = self.topic(count=6)
        feed = self.feed(topic, 1)
        feed['items'] = [{**feed['items'][0], 'url': 'https://example.test/' + str(i),
                          'titulo': 'Noticia ' + str(i), '_tokens': {str(i)}} for i in range(6)]
        report = r.empty_report(True)
        with patch.object(r, 'fetch_rss', return_value=feed), patch.object(r, 'fetch_bing_rss') as bing, \
                patch.object(r, 'verify_article', side_effect=lambda i, d: i['url']):
            news = r.rebuild_news([topic], 40, {'items': []}, '2026-11-18', time.monotonic() + 5, report)
        bing.assert_not_called()
        self.assertEqual(len(news['items']), 6)

    def test_bing_is_queried_only_for_short_topics(self):
        topics = [self.topic('Economía', count=1), self.topic('Ciencia', region='URUGUAY', count=1)]
        report = r.empty_report(True)
        def google(job, now, deadline):
            return self.feed(job[0], 1 if job[0]['tema'] == 'Economía' else 0)
        with patch.object(r, 'fetch_rss', side_effect=google), \
                patch.object(r, 'fetch_bing_rss', return_value=self.feed(topics[1], 1, 1)) as bing, \
                patch.object(r, 'verify_article', side_effect=lambda i, d: i['url']):
            r.rebuild_news(topics, 40, {'items': []}, '2026-11-18', time.monotonic() + 5, report)
        bing.assert_called_once()
        self.assertEqual(bing.call_args.args[0], (topics[1], 'Ciencia URUGUAY'))
        self.assertEqual([t['source'] for t in report['news_per_topic']], ['google', 'bing'])

    def test_fallback_dedupes_canonical_urls_and_similar_titles(self):
        topic = self.topic(count=3)
        google = self.feed(topic, 1)
        bing = self.feed(topic, 2, 1)
        bing['items'].append({**bing['items'][0], 'url': 'https://example.test/duplicate-title'})
        report = r.empty_report(True)
        def verify(item, deadline):
            return google['items'][0]['url'] if item['url'].endswith('/2') else item['url']
        with patch.object(r, 'fetch_rss', return_value=google), \
                patch.object(r, 'fetch_bing_rss', return_value=bing), \
                patch.object(r, 'verify_article', side_effect=verify):
            news = r.rebuild_news([topic], 40, {'items': []}, '2026-11-18', time.monotonic() + 5, report)
        self.assertEqual(len(news['items']), 2)
        self.assertEqual(report['topics_unfilled'][0]['filled'], 2)
        self.assertEqual(len(report['skipped_links']), 2)
        self.assertTrue(all('duplicada' in s['reason'] for s in report['skipped_links']))

    def test_solo_respaldo_skips_google(self):
        topic = self.topic()
        report = r.empty_report(True)
        with patch.object(r, 'fetch_rss') as google, \
                patch.object(r, 'fetch_bing_rss', return_value=self.feed(topic)) as bing, \
                patch.object(r, 'verify_article', side_effect=lambda i, d: i['url']):
            r.rebuild_news([topic], 40, {'items': []}, '2026-11-18', time.monotonic() + 5, report,
                           solo_respaldo=True)
        google.assert_not_called()
        bing.assert_called_once()
        self.assertEqual(report['news_per_topic'][0]['source'], 'bing')
        self.assertTrue(report['fallback_used'])

    def test_bing_after_google_verification_fails(self):
        topic = self.topic(count=1)
        google = self.feed(topic)
        bing_feed = self.feed(topic, 1, 2)
        for limited in (False, True):
            report = r.empty_report(True)
            r.RATE_LIMITED.clear()
            def verify(item, deadline):
                if item['_source'] == 'google':
                    if limited:
                        r.RATE_LIMITED.add('news.google.com')
                    raise ValueError('HTTP 429' if limited else 'Página bloqueada/antibot')
                return item['url']
            with self.subTest(limited=limited), patch.object(r, 'fetch_rss', return_value=google), \
                    patch.object(r, 'fetch_bing_rss', return_value=bing_feed) as bing, \
                    patch.object(r, 'verify_article', side_effect=verify):
                news = r.rebuild_news([topic], 40, {'items': []}, '2026-11-18', time.monotonic() + 5, report)
            bing.assert_called_once()
            self.assertEqual(news['items'][0]['url'], bing_feed['items'][0]['url'])
            self.assertEqual(report['news_per_topic'][0]['source'], 'bing')

    def test_rate_limited_google_skips_wrappers_but_verifies_direct_urls(self):
        topic = self.topic()
        google = self.feed(topic)
        google['items'][0]['url'] = 'https://news.google.com/articles/skip'
        r.RATE_LIMITED.add('news.google.com')
        report = r.empty_report(True)
        with patch.object(r, 'fetch_rss', return_value=google), \
                patch.object(r, 'fetch_bing_rss', return_value=self.feed(topic, 1, 2)), \
                patch.object(r, 'verify_article', side_effect=lambda i, d: i['url']) as verify:
            r.rebuild_news([topic], 40, {'items': []}, '2026-11-18', time.monotonic() + 5, report)
        self.assertTrue(all(r.host(c.args[0]['url']) != 'news.google.com' for c in verify.call_args_list))
        self.assertEqual(report['news_per_topic'][0]['source'], 'google+bing')

    def test_shortfalls_after_bing_are_honest(self):
        topic = self.topic()
        for bing_limited in (False, True):
            r.RATE_LIMITED.clear()
            r.RATE_LIMITED.add('news.google.com')
            if bing_limited:
                r.RATE_LIMITED.add('bing.com')
            report = r.empty_report(True)
            with patch.object(r, 'fetch_rss', side_effect=ValueError('HTTP 429')), \
                    patch.object(r, 'fetch_bing_rss', return_value=self.feed(topic, 0)):
                r.rebuild_news([topic], 40, {'items': []}, '2026-11-18', time.monotonic() + 5, report)
            self.assertEqual(report['news_per_topic'][0]['source'], 'ninguna')
            self.assertEqual(report['news_total'], 0)
            self.assertEqual(report['topics_unfilled'][0]['reason'],
                             'Google News y Bing News limitaron las solicitudes (HTTP 429)' if bing_limited
                             else 'sin suficientes noticias recientes, únicas y accesibles')

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
        with patch.object(r, 'fetch_rss', side_effect=feed), patch.object(r, 'fetch_bing_rss') as bing, \
                patch.object(r, 'verify_article', side_effect=lambda i, d: i['url']):
            news = r.rebuild_news(topics, 3, {'items': []}, '2026-11-02', time.monotonic() + 5, report)
        bing.assert_not_called()
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
        with patch.object(r, 'fetch_rss', return_value={'items': [], 'skipped': []}) as fetch, \
                patch.object(r, 'fetch_bing_rss', return_value={'items': [], 'skipped': []}) as bing:
            r.rebuild_news([topic], 40, {'items': []}, '2026-11-02', time.monotonic() + 5, report)
        queries = [call.args[0][1] for call in fetch.call_args_list]
        self.assertTrue(any('site:infobae.com OR site:tn.com.ar' in q for q in queries))
        self.assertEqual(sorted(queries), sorted(call.args[0][1] for call in bing.call_args_list))

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
    def test_rate_limited_news_can_publish_after_fallback(self):
        report = {'changed_files': ['noticias.js'], 'fallback_used': True, 'errors': [
            {'stage': 'http', 'reason': 'HTTP 429: solicitudes suspendidas para news.google.com'}]}
        result = subprocess.CompletedProcess([], 0, '', '')
        with patch.object(r.Path, 'read_bytes', return_value=b'old'), \
                patch.object(r.Path, 'write_bytes') as write, \
                patch.object(r.subprocess, 'run', return_value=result) as run:
            r.publish({'noticias.js': 'old'}, {'noticias.js': 'new'}, report, True, time.monotonic() + 5)
        write.assert_called_once_with(b'new')
        self.assertTrue(any('commit' in c.args[0] for c in run.call_args_list))
        self.assertEqual(report['git'], 'commit creado')

    def test_solo_respaldo_cli_and_environment(self):
        for value, flag, expected in [('', False, False), ('0', False, False), ('false', False, False),
                                      ('1', False, True), ('TrUe', False, True), ('SI', False, True),
                                      ('YeS', False, True), ('0', True, True)]:
            parent, child = Mock(), Mock()
            parent.recv.return_value = (r.empty_report(True), {}, {})
            with self.subTest(value=value, flag=flag), \
                    patch.dict(r.os.environ, {'REVISION_SOLO_RESPALDO': value}), \
                    patch.object(r.multiprocessing, 'Pipe', return_value=(parent, child)), \
                    patch.object(r.multiprocessing, 'Process') as process, patch('builtins.print'):
                argv = ['--posts', 'unused.json', '--dry-run'] + (['--solo-respaldo'] if flag else [])
                self.assertEqual(r.main(argv), 0)
                self.assertEqual(process.call_args.kwargs['args'][0].solo_respaldo, expected)

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

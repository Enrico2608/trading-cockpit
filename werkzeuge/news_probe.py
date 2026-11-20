"""Probe: Welche Quellen für ForexFactory (nächste Woche) und Schlagzeilen sind aus GitHub Actions erreichbar?"""
import json, re, time, urllib.request, urllib.parse, xml.etree.ElementTree as ET
UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36'
def hole(url, kopf=None):
    t = time.time()
    try:
        r = urllib.request.urlopen(urllib.request.Request(url, headers=dict({'User-Agent': UA, 'Accept-Language': 'de-DE,de;q=0.9,en;q=0.8'}, **(kopf or {}))), timeout=25)
        return r.status, r.headers.get('Content-Type', ''), r.read(), round(time.time() - t, 2)
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get('Content-Type', ''), e.read()[:3000], round(time.time() - t, 2)
    except Exception as e:
        return 0, '', repr(e).encode(), round(time.time() - t, 2)
def rss(roh):
    try:
        root = ET.fromstring(re.sub(rb'^\s*<\?xml[^>]*\?>', b'', roh))
    except Exception as e:
        return {'fehler': repr(e)[:200]}
    items = root.findall('.//item') or root.findall('.//{http://www.w3.org/2005/Atom}entry')
    out = []
    for it in items[:6]:
        g = lambda tag: (it.findtext(tag) or '').strip()
        out.append({'titel': g('title')[:160], 'quelle': g('source')[:60], 'zeit': g('pubDate') or g('{http://www.w3.org/2005/Atom}updated'), 'link': g('link')[:160]})
    return {'n': len(items), 'erste': out}
erg = {}
ff = ['https://nfs.faireconomy.media/ff_calendar_thisweek.xml', 'https://nfs.faireconomy.media/ff_calendar_thisweek.json',
      'https://nfs.faireconomy.media/ff_calendar_nextweek.xml', 'https://nfs.faireconomy.media/ff_calendar_nextweek.json',
      'https://www.forexfactory.com/calendar?week=next', 'https://www.forexfactory.com/ff_calendar_nextweek.xml']
for u in ff:
    s, ct, b, dt = hole(u)
    txt = b.decode('utf-8', 'replace')
    erg[u] = {'status': s, 'ct': ct, 'bytes': len(b), 'sek': dt, 'events': txt.count('<event>') or txt.count('"title"'), 'calendar__row': txt.count('calendar__row'),
              'anfang': txt[:300], 'daten': sorted(set(re.findall(r'(\d{2}-\d{2}-\d{4})', txt)))[:10] + sorted(set(re.findall(r'"date":"(\d{4}-\d{2}-\d{2})', txt)))[:10]}
    time.sleep(3)
gn = lambda q, de=True: 'https://news.google.com/rss/search?' + urllib.parse.urlencode({'q': q + ' when:2d', 'hl': 'de' if de else 'en-US', 'gl': 'DE' if de else 'US', 'ceid': 'DE:de' if de else 'US:en'})
news = {'gn_gold': gn('Goldpreis'), 'gn_silber': gn('Silberpreis'), 'gn_oel': gn('Ölpreis'), 'gn_wallstreet': gn('Wall Street Nasdaq'), 'gn_nvidia': gn('Nvidia Aktie'),
        'gn_bitcoin': gn('Bitcoin'), 'gn_hyperliquid_de': gn('Hyperliquid'), 'gn_hyperliquid_en': gn('Hyperliquid', False), 'gn_krypto': gn('Krypto Börse'),
        'cointelegraph_de': 'https://de.cointelegraph.com/rss', 'btc_echo': 'https://www.btc-echo.de/feed/', 'finanzen_net': 'https://www.finanzen.net/rss/news',
        'investing_de': 'https://de.investing.com/rss/news.rss', 'coindesk': 'https://www.coindesk.com/arc/outboundfeeds/rss/',
        'yahoo_nvda': 'https://feeds.finance.yahoo.com/rss/2.0/headline?s=NVDA&region=US&lang=en-US', 'handelsblatt': 'https://www.handelsblatt.com/contentexport/feed/finanzen',
        'tagesschau_wirtschaft': 'https://www.tagesschau.de/wirtschaft/index~rss2.xml', 'fxstreet': 'https://www.fxstreet.com/rss/news', 'kitco': 'https://www.kitco.com/rss/KitcoNews.xml',
        'theblock': 'https://www.theblock.co/rss.xml', 'decrypt': 'https://decrypt.co/feed'}
for k, u in news.items():
    s, ct, b, dt = hole(u)
    erg[k] = dict({'url': u, 'status': s, 'ct': ct, 'bytes': len(b), 'sek': dt}, **(rss(b) if s == 200 else {'anfang': b[:200].decode('utf-8', 'replace')}))
    time.sleep(1)
json.dump(erg, open('dump/news_probe.json', 'w'), ensure_ascii=False, indent=1)
print(json.dumps({k: (v.get('status'), v.get('n', v.get('events'))) for k, v in erg.items()}, indent=0))

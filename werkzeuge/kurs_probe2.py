"""Probe 2: freie Echtzeit-Quellen mit CORS (Swissquote, Pyth, gold-api) und ob Dukascopy den laufenden Tag schon liefert."""
import json, time, urllib.request, urllib.error, datetime, lzma, struct
AUS = []
def log(*a):
    s = ' '.join(str(x) for x in a); print(s, flush=True); AUS.append(s)
def hole(url, headers=None):
    h = {'User-Agent': 'Mozilla/5.0', 'Origin': 'https://enrico2608.github.io'}; h.update(headers or {})
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=20) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read()
    except Exception as e:
        return None, {}, repr(e).encode()
def cors(h): return {k: v for k, v in h.items() if k.lower().startswith('access-control-allow-origin')}
jetzt = datetime.datetime.now(datetime.timezone.utc); log('Zeit', jetzt.isoformat())
# Pyth: Liste der Kursreihen (Metalle, Rohstoffe, Indizes, Krypto), aktuelle Kurse und Strom (SSE)
ids = {}
for q, art in (('XAU/USD', 'metal'), ('XAG/USD', 'metal'), ('WTI', 'commodities'), ('USOIL', 'commodities'), ('SPX', 'equity'), ('US500', 'equity'), ('NDX', 'equity'), ('US100', 'equity'), ('DJI', 'equity'), ('US30', 'equity'), ('BTC/USD', 'crypto')):
    st, h, b = hole('https://hermes.pyth.network/v2/price_feeds?query=' + urllib.request.quote(q) + '&asset_type=' + art)
    try:
        j = json.loads(b)
        log('Pyth Suche', q, art, st, [(x['attributes'].get('symbol'), x['attributes'].get('description', '')[:40]) for x in j][:6])
        for x in j[:6]: ids[x['attributes'].get('symbol')] = x['id']
    except Exception:
        log('Pyth Suche', q, st, b[:120])
wahl = [k for k in ids if k and any(t in k for t in ('XAU/USD', 'XAG/USD', 'WTI', 'USOIL', 'SPX', 'US500', 'NDX', 'US100', 'DJI', 'US30', 'BTC/USD'))][:14]
if wahl:
    st, h, b = hole('https://hermes.pyth.network/v2/updates/price/latest?parsed=true&' + '&'.join('ids[]=' + ids[k] for k in wahl))
    try:
        j = json.loads(b)
        for x in j.get('parsed', []):
            name = [k for k in wahl if ids[k].endswith(x['id'][-20:])]
            pr = x['price']; log('Pyth Kurs', name, int(pr['price']) * 10 ** pr['expo'], 'conf', int(pr['conf']) * 10 ** pr['expo'], 'Zeit', datetime.datetime.fromtimestamp(pr['publish_time'], datetime.timezone.utc).strftime('%H:%M:%S'))
    except Exception:
        log('Pyth latest', st, cors(h), b[:200])
st, h, b = hole('https://benchmarks.pyth.network/v1/shims/tradingview/history?symbol=Metal.XAU%2FUSD&resolution=60&from=' + str(int(time.time()) - 7200) + '&to=' + str(int(time.time())))
log('Pyth Benchmarks', st, cors(h), b[:200])
# Dukascopy: läuft der heutige Tag schon? (Monat 0-basiert)
d = jetzt.date(); basis = 'https://datafeed.dukascopy.com/datafeed/XAUUSD/%04d/%02d/%02d/' % (d.year, d.month - 1, d.day)
st, h, b = hole(basis + 'BID_candles_min_1.bi5'); log('Dukascopy heute Minutenkerzen', st, len(b), cors(h))
for stunde in range(max(0, jetzt.hour - 3), jetzt.hour + 1):
    st, h, b = hole(basis + '%02dh_ticks.bi5' % stunde); log('Dukascopy heute Ticks %02d Uhr UTC' % stunde, st, len(b))
open('dump/kurs_probe2.txt', 'w').write('\n'.join(AUS) + '\n')

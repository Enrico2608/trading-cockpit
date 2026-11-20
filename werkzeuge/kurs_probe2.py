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
for inst in ('XAU/USD', 'XAG/USD', 'BTC/USD', 'US500/USD', 'SPX500/USD', 'NAS100/USD', 'USOIL/USD', 'WTI/USD'):
    st, h, b = hole('https://forex-data-feed.swissquote.com/public-quotes/bboquotes/instrument/' + inst)
    try:
        j = json.loads(b); erst = j[0]; sp = erst['spreadProfilePrices'][0]
        log('Swissquote', inst, st, cors(h), 'Plattformen', len(j), 'bid', sp.get('bid'), 'ask', sp.get('ask'), 'ts', erst.get('ts'))
    except Exception:
        log('Swissquote', inst, st, cors(h), b[:100])
for i in range(3):
    st, h, b = hole('https://api.gold-api.com/price/XAU')
    try: j = json.loads(b); log('gold-api XAU', st, cors(h), j.get('price'), j.get('updatedAt'))
    except Exception: log('gold-api', st, b[:80])
    time.sleep(4)
st, h, b = hole('https://hermes.pyth.network/v2/price_feeds?query=XAU&asset_type=metal'); log('Pyth Hermes Liste', st, cors(h), b[:200])
st, h, b = hole('https://benchmarks.pyth.network/v1/shims/tradingview/history?symbol=Metal.XAU%2FUSD&resolution=60&from=%d&to=%d' % (int(time.time()) - 7200, int(time.time())))
log('Pyth Benchmarks', st, cors(h), b[:200])
# Dukascopy: läuft der heutige Tag schon? (Monat 0-basiert)
d = jetzt.date(); basis = 'https://datafeed.dukascopy.com/datafeed/XAUUSD/%04d/%02d/%02d/' % (d.year, d.month - 1, d.day)
st, h, b = hole(basis + 'BID_candles_min_1.bi5'); log('Dukascopy heute Minutenkerzen', st, len(b), cors(h))
for stunde in range(max(0, jetzt.hour - 3), jetzt.hour + 1):
    st, h, b = hole(basis + '%02dh_ticks.bi5' % stunde); log('Dukascopy heute Ticks %02d Uhr UTC' % stunde, st, len(b))
open('dump/kurs_probe2.txt', 'w').write('\n'.join(AUS) + '\n')

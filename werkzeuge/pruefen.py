import json, lzma, os, struct, time, datetime, urllib.request, urllib.parse
os.makedirs('dump', exist_ok=True)
UA = 'trading-cockpit-kurse/1.0 (privates Cockpit; https://github.com/Enrico2608/trading-cockpit)'
ORIGIN = 'https://enrico2608.github.io'
bericht = {}
def hole(url, roh=False, versuche=1, pause=5):
    for v in range(versuche):
        req = urllib.request.Request(url, headers={'User-Agent': UA, 'Origin': ORIGIN})
        try:
            with urllib.request.urlopen(req, timeout=40) as r:
                body = r.read()
                info = {'status': r.status, 'bytes': len(body), 'acao': r.headers.get('Access-Control-Allow-Origin'), 'versuch': v + 1}
                return info, (body if roh else body.decode('utf-8', 'replace'))
        except urllib.error.HTTPError as e:
            info = {'status': e.code, 'acao': e.headers.get('Access-Control-Allow-Origin'), 'versuch': v + 1, 'text': e.read()[:200].decode('utf-8', 'replace')}
            if e.code in (429, 503) and v + 1 < versuche: time.sleep(pause * (v + 1)); continue
            return info, None
        except Exception as e:
            return {'fehler': repr(e)[:200]}, None
jetzt = int(time.time())
B = 'https://benchmarks.pyth.network'
for name, url in [
    ('cfg', B + '/v1/shims/tradingview/config'),
    ('sym', B + '/v1/shims/tradingview/symbols?symbol=Metal.XAU/USD'),
    ('hist_btc', B + '/v1/shims/tradingview/history?symbol=Crypto.BTC/USD&resolution=60&from=%d&to=%d' % (jetzt - 86400, jetzt)),
    ('hist_xau_raw', B + '/v1/shims/tradingview/history?symbol=Metal.XAU/USD&resolution=60&from=%d&to=%d' % (jetzt - 3 * 86400, jetzt)),
    ('hist_xau_D', B + '/v1/shims/tradingview/history?symbol=Metal.XAU/USD&resolution=1D&from=%d&to=%d' % (jetzt - 30 * 86400, jetzt)),
    ('hist_xau_alt', B + '/v1/shims/tradingview/history?symbol=Metal.XAU/USD&resolution=1D&from=%d&to=%d' % (1420070400, 1514764800)),
    ('bench_feeds', B + '/v1/price_feeds/?query=XAU'),
    ('hermes_latest', 'https://hermes.pyth.network/v2/updates/price/latest?ids[]=0x765d2ba906dbc32ca17cc11f5310a89e9ee1f6420508c63861f2f8ba4ee34bb2&ids[]=0xf2fb02c32b055c805e7238d628e5e9dadef274376114eb1f012337cabe93871e&parsed=true'),
    ('binance_xau', 'https://fapi.binance.com/fapi/v1/klines?symbol=XAUUSDT&interval=1h&limit=3'),
    ('bybit_xau', 'https://api.bybit.com/v5/market/kline?category=linear&symbol=XAUUSDT&interval=60&limit=3'),
]:
    info, b = hole(url)
    bericht[name] = info
    if b: bericht[name + '_text'] = b[:900]
    time.sleep(0.5)
# SSE kurz anzapfen
try:
    req = urllib.request.Request('https://hermes.pyth.network/v2/updates/price/stream?ids[]=0x765d2ba906dbc32ca17cc11f5310a89e9ee1f6420508c63861f2f8ba4ee34bb2&parsed=true&benchmarks_only=false', headers={'User-Agent': UA, 'Origin': ORIGIN, 'Accept': 'text/event-stream'})
    with urllib.request.urlopen(req, timeout=20) as r:
        bericht['sse'] = {'status': r.status, 'acao': r.headers.get('Access-Control-Allow-Origin'), 'typ': r.headers.get('Content-Type')}
        t0 = time.time(); stueck = b''
        while time.time() - t0 < 4:
            z = r.readline()
            if not z: break
            stueck += z
        bericht['sse_text'] = stueck[:700].decode('utf-8', 'replace')
except Exception as e:
    bericht['sse'] = repr(e)[:200]
# Dukascopy langsam mit Wiederholung
def bi5(sym, pfad):
    info, b = hole('https://datafeed.dukascopy.com/datafeed/%s/%s' % (sym, pfad), roh=True, versuche=4, pause=8)
    if not b: return info, None
    try:
        roh = lzma.decompress(b) if b else b''
        rec = [struct.unpack('>IIIIIf', roh[i:i + 24]) for i in range(0, len(roh), 24)]
        return dict(info, n=len(rec)), rec
    except Exception as e:
        return dict(info, fehler=repr(e)[:200]), None
for sym, pfad in [('XAUUSD', '2015/00/BID_candles_hour_1.bi5'), ('XAUUSD', '2026/09/BID_candles_hour_1.bi5'), ('XAUUSD', '2026/10/BID_candles_hour_1.bi5'),
                  ('XAUUSD', '2026/10/18/BID_candles_min_1.bi5'), ('XAGUSD', '2015/00/BID_candles_hour_1.bi5'), ('LIGHTCMDUSD', '2015/00/BID_candles_hour_1.bi5'),
                  ('USATECHIDXUSD', '2015/00/BID_candles_hour_1.bi5'), ('BTCUSD', '2017/04/BID_candles_hour_1.bi5'), ('XAUUSD', '2015/BID_candles_day_1.bi5')]:
    info, rec = bi5(sym, pfad)
    key = 'duka_%s_%s' % (sym, pfad.replace('/', '_'))
    bericht[key] = info
    if rec:
        nz = [r for r in rec if r[5] > 0]
        bericht[key + '_probe'] = {'erste_mit_volumen': nz[:2], 'letzte': rec[-1:], 'n_volumen': len(nz)}
    time.sleep(2)
json.dump(bericht, open('dump/pruefen.json', 'w'), indent=1, default=str)

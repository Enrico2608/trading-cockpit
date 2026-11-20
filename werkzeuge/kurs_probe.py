"""Probe: Wie weit liegen die Hyperliquid-Kurse von den Kassakursen (TradingView-Feeds) weg, und erlaubt OANDA Abrufe aus dem Browser (CORS)?"""
import json, time, urllib.request, urllib.error, datetime

AUS = []
def log(*a):
    s = ' '.join(str(x) for x in a); print(s, flush=True); AUS.append(s)

def hole(url, data=None, headers=None, methode=None):
    h = {'User-Agent': 'Mozilla/5.0', 'Content-Type': 'application/json'}
    h.update(headers or {})
    req = urllib.request.Request(url, data=json.dumps(data).encode() if data is not None else None, headers=h, method=methode)
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read()
    except Exception as e:
        return None, {}, repr(e).encode()

log('Zeit', datetime.datetime.now(datetime.timezone.utc).isoformat())
# 1) OANDA: CORS-Vorabfrage und Antwort ohne Schlüssel
for host in ('api-fxpractice.oanda.com', 'api-fxtrade.oanda.com', 'stream-fxpractice.oanda.com'):
    pfad = '/v3/instruments/XAU_USD/candles?granularity=H1&count=2&price=B' if not host.startswith('stream') else '/v3/accounts/101-001-0000000-001/pricing/stream?instruments=XAU_USD'
    st, h, _ = hole('https://' + host + pfad, headers={'Origin': 'https://enrico2608.github.io', 'Access-Control-Request-Method': 'GET', 'Access-Control-Request-Headers': 'authorization,accept-datetime-format'}, methode='OPTIONS')
    log('OANDA', host, 'OPTIONS', st, {k: v for k, v in h.items() if k.lower().startswith('access-control')})
    st, h, b = hole('https://' + host + pfad, headers={'Origin': 'https://enrico2608.github.io'})
    log('OANDA', host, 'GET ohne Schlüssel', st, {k: v for k, v in h.items() if k.lower().startswith('access-control')}, b[:120])
# 2) Hyperliquid gegen Kassakurse
mids_main = json.loads(hole('https://api.hyperliquid.xyz/info', {'type': 'allMids'})[2])
mids_xyz = json.loads(hole('https://api.hyperliquid.xyz/info', {'type': 'allMids', 'dex': 'xyz'})[2])
log('HL', {k: mids_xyz.get(k) for k in ('xyz:GOLD', 'xyz:SILVER', 'xyz:CL', 'xyz:XYZ100', 'xyz:SP500')}, 'BTC', mids_main.get('BTC'), 'PAXG', mids_main.get('PAXG'))
for sym in ('XAU', 'XAG', 'BTC'):
    st, h, b = hole('https://api.gold-api.com/price/' + sym)
    log('gold-api', sym, st, b[:160])
# Yahoo (nur zum Vergleich, serverseitig): Kassa-Indizes und Futures
for sym in ('GC=F', 'SI=F', 'CL=F', '^NDX', 'NQ=F', '^GSPC', 'ES=F', '^DJI', 'YM=F'):
    st, h, b = hole('https://query1.finance.yahoo.com/v8/finance/chart/' + urllib.request.quote(sym) + '?interval=1m&range=1d')
    try:
        j = json.loads(b); m = j['chart']['result'][0]['meta']; log('Yahoo', sym, m.get('regularMarketPrice'), m.get('currency'))
    except Exception:
        log('Yahoo', sym, st, b[:80])
# Coinbase / Bitstamp für Bitcoin
st, h, b = hole('https://api.exchange.coinbase.com/products/BTC-USD/ticker'); log('Coinbase BTC', st, b[:120])
st, h, b = hole('https://www.bitstamp.net/api/v2/ticker/btcusd/', headers={'Origin': 'https://enrico2608.github.io'}); log('Bitstamp BTC', st, {k: v for k, v in h.items() if k.lower().startswith('access-control')}, b[:120])
open('dump/kurs_probe.txt', 'w').write('\n'.join(AUS) + '\n')

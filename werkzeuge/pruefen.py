import json, os, time, urllib.request, urllib.parse
os.makedirs('dump', exist_ok=True)
UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36'
ORIGIN = 'https://enrico2608.github.io'
bericht = {}
def hole(url, daten=None, kopf=None):
    h = {'User-Agent': UA, 'Origin': ORIGIN}
    if kopf: h.update(kopf)
    req = urllib.request.Request(url, data=daten, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            body = r.read()
            return {'status': r.status, 'bytes': len(body), 'acao': r.headers.get('Access-Control-Allow-Origin'), 'typ': r.headers.get('Content-Type')}, body
    except urllib.error.HTTPError as e:
        return {'status': e.code, 'acao': e.headers.get('Access-Control-Allow-Origin'), 'text': e.read()[:200].decode('utf-8', 'replace')}, None
    except Exception as e:
        return {'fehler': repr(e)[:200]}, None
for name, url in [
    ('swissquote', 'https://forex-data-feed.swissquote.com/public-quotes/bboquotes/instrument/XAU/USD'),
    ('goldapi', 'https://api.gold-api.com/price/XAU'),
    ('metalslive', 'https://api.metals.live/v1/spot/gold'),
    ('goldprice', 'https://data-asg.goldprice.org/dbXRates/USD'),
    ('binance_vision_fut', 'https://data.binance.vision/data/futures/um/daily/klines/XAUUSDT/1h/XAUUSDT-1h-2026-11-18.zip'),
    ('binance_vision_fut_paxg', 'https://data.binance.vision/data/futures/um/daily/klines/PAXGUSDT/1h/PAXGUSDT-1h-2026-11-18.zip'),
    ('binance_vision_xag', 'https://data.binance.vision/data/futures/um/daily/klines/XAGUSDT/1h/XAGUSDT-1h-2026-11-18.zip'),
    ('kraken_paxg', 'https://api.kraken.com/0/public/Ticker?pair=PAXGUSD'),
    ('okx_xau', 'https://www.okx.com/api/v5/market/ticker?instId=XAU-USDT-SWAP'),
    ('okx_xaut', 'https://www.okx.com/api/v5/market/ticker?instId=XAUT-USDT-SWAP'),
    ('bitget_xau', 'https://api.bitget.com/api/v2/mix/market/ticker?symbol=XAUUSDT&productType=USDT-FUTURES'),
    ('gate_xau', 'https://api.gateio.ws/api/v4/futures/usdt/tickers?contract=XAU_USDT'),
    ('mexc_xau', 'https://contract.mexc.com/api/v1/contract/ticker?symbol=XAUT_USDT'),
    ('kucoin_xau', 'https://api-futures.kucoin.com/api/v1/ticker?symbol=XAUTUSDTM'),
]:
    info, b = hole(url)
    bericht[name] = info
    if b: bericht[name + '_text'] = b[:500].decode('utf-8', 'replace') if not url.endswith('.zip') else 'zip %d Bytes' % len(b)
    time.sleep(0.4)
# Hyperliquid: alle Gold-Märkte über alle Perp-DEXe
def hl(body):
    info, b = hole('https://api.hyperliquid.xyz/info', json.dumps(body).encode(), {'Content-Type': 'application/json'})
    return json.loads(b) if b else None
try:
    dexe = [None] + [d['name'] for d in (hl({'type': 'perpDexs'}) or []) if d and d.get('name')]
    funde = []
    for dex in dexe:
        r = hl({'type': 'metaAndAssetCtxs', 'dex': dex} if dex else {'type': 'metaAndAssetCtxs'})
        if not r: continue
        meta, ctx = r[0], r[1]
        for u, c in zip(meta.get('universe', []), ctx):
            n = u.get('name', '')
            if any(w in n.upper() for w in ('GOLD', 'XAU', 'PAXG', 'SILVER', 'XAG')):
                funde.append({'dex': dex, 'name': n, 'mark': c.get('markPx'), 'oracle': c.get('oraclePx'), 'mid': c.get('midPx'), 'vol24': c.get('dayNtlVlm'), 'oi': c.get('openInterest'), 'delisted': u.get('isDelisted')})
        time.sleep(0.2)
    bericht['hl_gold'] = funde
    bericht['hl_dexe'] = dexe
except Exception as e:
    bericht['hl_gold'] = repr(e)
json.dump(bericht, open('dump/pruefen.json', 'w'), indent=1, default=str)

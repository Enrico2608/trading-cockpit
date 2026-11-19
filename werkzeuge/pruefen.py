import json, lzma, os, struct, time, datetime, urllib.request, urllib.parse
os.makedirs('dump', exist_ok=True)
UA = 'trading-cockpit-kurse/1.0 (privates Cockpit; https://github.com/Enrico2608/trading-cockpit)'
ORIGIN = 'https://enrico2608.github.io'
bericht = {}
def hole(url, roh=False):
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Origin': ORIGIN})
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            body = r.read()
            info = {'status': r.status, 'bytes': len(body), 'acao': r.headers.get('Access-Control-Allow-Origin'), 'typ': r.headers.get('Content-Type')}
            return info, (body if roh else body.decode('utf-8', 'replace'))
    except urllib.error.HTTPError as e:
        return {'status': e.code, 'acao': e.headers.get('Access-Control-Allow-Origin')}, None
    except Exception as e:
        return {'fehler': repr(e)[:200]}, None
# --- Pyth
for q in ('XAU', 'XAG'):
    info, b = hole('https://hermes.pyth.network/v2/price_feeds?query=%s&asset_type=metal' % q)
    bericht['hermes_' + q] = info
    if b:
        try: bericht['hermes_' + q + '_feeds'] = [{'id': f['id'], 'attr': f.get('attributes')} for f in json.loads(b)][:6]
        except Exception as e: bericht['hermes_' + q + '_feeds'] = repr(e)
info, b = hole('https://hermes.pyth.network/v2/price_feeds?asset_type=commodities')
bericht['hermes_comm'] = info
if b:
    try: bericht['hermes_comm_feeds'] = [{'id': f['id'], 'sym': f.get('attributes', {}).get('symbol'), 'desc': f.get('attributes', {}).get('description')} for f in json.loads(b)][:40]
    except Exception as e: bericht['hermes_comm_feeds'] = repr(e)
jetzt = int(time.time())
for sym in ('Metal.XAU/USD', 'Metal.XAG/USD'):
    for res in ('60', '240', '1D'):
        url = 'https://benchmarks.pyth.network/v1/shims/tradingview/history?' + urllib.parse.urlencode({'symbol': sym, 'resolution': res, 'from': jetzt - 6 * 86400 if res != '1D' else jetzt - 40 * 86400, 'to': jetzt})
        info, b = hole(url)
        k = sym.split('.')[1].replace('/', '') + '_' + res
        bericht['bench_' + k] = info
        if b:
            try:
                d = json.loads(b)
                t = d.get('t') or []
                bericht['bench_' + k + '_daten'] = {'s': d.get('s'), 'n': len(t), 'erste': [datetime.datetime.utcfromtimestamp(x).isoformat() for x in t[:3]], 'letzte': [datetime.datetime.utcfromtimestamp(x).isoformat() for x in t[-3:]], 'c': (d.get('c') or [])[-3:]}
            except Exception as e: bericht['bench_' + k + '_daten'] = repr(e) + b[:200]
info, b = hole('https://benchmarks.pyth.network/v1/shims/tradingview/history?' + urllib.parse.urlencode({'symbol': 'Metal.XAU/USD', 'resolution': '1D', 'from': int(datetime.datetime(2015, 1, 1).timestamp()), 'to': int(datetime.datetime(2023, 1, 1).timestamp())}))
bericht['bench_alt'] = info
if b:
    try: d = json.loads(b); bericht['bench_alt_daten'] = {'s': d.get('s'), 'n': len(d.get('t') or []), 'erste': datetime.datetime.utcfromtimestamp(d['t'][0]).isoformat() if d.get('t') else None}
    except Exception as e: bericht['bench_alt_daten'] = repr(e) + b[:200]
# --- Dukascopy
def bi5(sym, pfad):
    info, b = hole('https://datafeed.dukascopy.com/datafeed/%s/%s' % (sym, pfad), roh=True)
    if not b: return info, None
    try:
        roh = lzma.decompress(b)
        rec = [struct.unpack('>IIIIIf', roh[i:i + 24]) for i in range(0, len(roh), 24)]
        return dict(info, n=len(rec)), rec
    except Exception as e:
        return dict(info, fehler=repr(e)[:200]), None
for sym in ('XAUUSD', 'XAGUSD', 'LIGHTCMDUSD', 'USA500IDXUSD', 'USATECHIDXUSD', 'USA30IDXUSD', 'BTCUSD'):
    for pfad in ('2015/00/BID_candles_hour_1.bi5', '2026/09/BID_candles_hour_1.bi5', '2026/10/BID_candles_hour_1.bi5', '2026/10/18/BID_candles_min_1.bi5'):
        info, rec = bi5(sym, pfad)
        key = 'duka_%s_%s' % (sym, pfad.replace('/', '_'))
        bericht[key] = info
        if rec:
            nz = [r for r in rec if r[5] > 0]
            bericht[key + '_probe'] = {'erste': rec[:2], 'erste_mit_volumen': nz[:2], 'n_volumen': len(nz)}
        time.sleep(0.3)
# --- Coinbase 1 Std 2015
info, b = hole('https://api.exchange.coinbase.com/products/BTC-USD/candles?granularity=3600&start=2015-07-20T00:00:00Z&end=2015-07-31T00:00:00Z')
bericht['coinbase_1h_2015'] = info
if b:
    try: d = json.loads(b); bericht['coinbase_1h_2015_daten'] = {'n': len(d), 'probe': d[:2]}
    except Exception as e: bericht['coinbase_1h_2015_daten'] = repr(e) + b[:200]
json.dump(bericht, open('dump/pruefen.json', 'w'), indent=1, default=str)
print(json.dumps(bericht, indent=1, default=str)[:3000])

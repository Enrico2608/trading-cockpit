"""Probe 3: Hyperliquid-Orakelpreis vs. Mittelkurs vs. Kassakurs (Swissquote) – wer liegt am nächsten an TradingView?"""
import json, time, urllib.request, datetime
AUS = []
def log(*a):
    s = ' '.join(str(x) for x in a); print(s, flush=True); AUS.append(s)
def post(body):
    req = urllib.request.Request('https://api.hyperliquid.xyz/info', data=json.dumps(body).encode(), headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read())
def sq(inst):
    with urllib.request.urlopen(urllib.request.Request('https://forex-data-feed.swissquote.com/public-quotes/bboquotes/instrument/' + inst, headers={'User-Agent': 'Mozilla/5.0'}), timeout=20) as r:
        j = json.loads(r.read())
    out = []
    for p in j:
        for sp in p.get('spreadProfilePrices', []):
            out.append((p.get('topo', {}).get('platform'), sp.get('spreadProfile'), sp.get('bid'), sp.get('ask')))
    return out
for runde in range(4):
    meta, ctxs = post({'type': 'metaAndAssetCtxs', 'dex': 'xyz'})
    namen = [u['name'] for u in meta['universe']]
    werte = {}
    for n, c in zip(namen, ctxs):
        if n in ('xyz:GOLD', 'xyz:SILVER', 'xyz:CL', 'xyz:XYZ100', 'xyz:SP500'):
            werte[n] = (c.get('oraclePx'), c.get('markPx'), c.get('midPx'))
    g = sq('XAU/USD'); s = sq('XAG/USD')
    log(datetime.datetime.now(datetime.timezone.utc).strftime('%H:%M:%S'), 'HL (Orakel, Mark, Mitte):', json.dumps(werte))
    log('   Swissquote Gold:', g[:4]); log('   Swissquote Silber:', s[:2])
    time.sleep(10)
open('dump/kurs_probe3.txt', 'w').write('\n'.join(AUS) + '\n')

"""Probe: kommen bei Hyperliquid Live-Kerzen für xyz:GOLD & Co. per WebSocket an, und wie sehen sie aus?"""
import asyncio, json, time, urllib.request, datetime

AUS = []
def log(*a):
    s = ' '.join(str(x) for x in a)
    print(s, flush=True)
    AUS.append(s)

def post(body):
    req = urllib.request.Request('https://api.hyperliquid.xyz/info', data=json.dumps(body).encode(), headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read())

def zeit(ms):
    return datetime.datetime.fromtimestamp(ms / 1000, datetime.timezone.utc).strftime('%d.%m. %H:%M:%S')

async def ws_test(sekunden=150):
    import websockets
    t0 = time.time()
    zaehler = {}
    async with websockets.connect('wss://api.hyperliquid.xyz/ws', ping_interval=None) as ws:
        abos = [('xyz:GOLD', '1m'), ('xyz:GOLD', '1h'), ('xyz:GOLD', '1d'), ('PAXG', '1h'), ('BTC', '1h'), ('xyz:SILVER', '1h'), ('xyz:XYZ100', '1h')]
        for coin, iv in abos:
            await ws.send(json.dumps({'method': 'subscribe', 'subscription': {'type': 'candle', 'coin': coin, 'interval': iv}}))
        await ws.send(json.dumps({'method': 'subscribe', 'subscription': {'type': 'trades', 'coin': 'xyz:GOLD'}}))
        naechster_ping = t0 + 30
        while time.time() - t0 < sekunden:
            if time.time() > naechster_ping:
                await ws.send(json.dumps({'method': 'ping'})); naechster_ping += 30
                log('%6.1f s  → ping gesendet' % (time.time() - t0))
            try:
                roh = await asyncio.wait_for(ws.recv(), 5)
            except asyncio.TimeoutError:
                continue
            m = json.loads(roh)
            ch = m.get('channel')
            if ch == 'candle':
                d = m['data']; k = (d.get('s'), d.get('i'))
                zaehler[k] = zaehler.get(k, 0) + 1
                if zaehler[k] <= 3 or zaehler[k] % 25 == 0:
                    log('%6.1f s  candle s=%r i=%r t=%s c=%s n=%s (Nr. %d)' % (time.time() - t0, d.get('s'), d.get('i'), zeit(d.get('t', 0)), d.get('c'), d.get('n'), zaehler[k]))
            elif ch == 'trades':
                zaehler[('trades', '')] = zaehler.get(('trades', ''), 0) + len(m.get('data') or [])
                if zaehler[('trades', '')] <= 3:
                    log('%6.1f s  trades %s' % (time.time() - t0, json.dumps(m.get('data'))[:200]))
            elif ch == 'subscriptionResponse':
                log('%6.1f s  Abo bestätigt: %s' % (time.time() - t0, json.dumps(m.get('data'))[:160]))
            else:
                log('%6.1f s  %s: %s' % (time.time() - t0, ch, json.dumps(m)[:200]))
    log('Zähler je (Coin, Intervall) in %d s: %s' % (sekunden, json.dumps({'%s|%s' % k: v for k, v in zaehler.items()})))

async def ruhe_test(sekunden=100):
    import websockets
    t0 = time.time()
    try:
        async with websockets.connect('wss://api.hyperliquid.xyz/ws', ping_interval=None) as ws:
            await ws.send(json.dumps({'method': 'subscribe', 'subscription': {'type': 'candle', 'coin': 'xyz:GOLD', 'interval': '1d'}}))
            while time.time() - t0 < sekunden:
                roh = await asyncio.wait_for(ws.recv(), sekunden)
            log('Ruhetest: Verbindung nach %d s noch offen (ohne Ping)' % sekunden)
    except Exception as e:
        log('Ruhetest: nach %.0f s beendet: %r' % (time.time() - t0, e))

def main():
    log('Start', datetime.datetime.now(datetime.timezone.utc).isoformat())
    jetzt = int(time.time() * 1000)
    for coin in ['xyz:GOLD', 'PAXG', 'xyz:SILVER']:
        try:
            k = post({'type': 'candleSnapshot', 'req': {'coin': coin, 'interval': '1m', 'startTime': jetzt - 10 * 60000, 'endTime': jetzt + 60000}})
            log('REST %s 1m: %d Kerzen, letzte %s' % (coin, len(k), json.dumps(k[-1]) if k else '-'))
        except Exception as e:
            log('REST %s 1m: Fehler %r' % (coin, e))
    try:
        mids = post({'type': 'allMids', 'dex': 'xyz'})
        log('allMids xyz: GOLD=%s SILVER=%s XYZ100=%s (%d Einträge)' % (mids.get('xyz:GOLD'), mids.get('xyz:SILVER'), mids.get('xyz:XYZ100'), len(mids)))
    except Exception as e:
        log('allMids xyz: Fehler %r' % (e,))
    asyncio.run(ws_test())
    asyncio.run(ruhe_test())
    open('dump/hl_probe.txt', 'w').write('\n'.join(AUS) + '\n')

if __name__ == '__main__':
    main()

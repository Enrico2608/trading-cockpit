"""Probe 4: WebSocket activeAssetCtx (Orakelpreis) für xyz:GOLD, xyz:SP500 und BTC – Format und Takt."""
import asyncio, json, time, datetime
AUS = []
def log(*a):
    s = ' '.join(str(x) for x in a); print(s, flush=True); AUS.append(s)
async def main():
    import websockets
    t0 = time.time(); n = {}
    async with websockets.connect('wss://api.hyperliquid.xyz/ws', ping_interval=None) as ws:
        for c in ('xyz:GOLD', 'xyz:SP500', 'BTC'):
            await ws.send(json.dumps({'method': 'subscribe', 'subscription': {'type': 'activeAssetCtx', 'coin': c}}))
        while time.time() - t0 < 40:
            try:
                m = json.loads(await asyncio.wait_for(ws.recv(), 10))
            except asyncio.TimeoutError:
                continue
            ch = m.get('channel')
            if ch in ('activeAssetCtx', 'activeSpotAssetCtx'):
                d = m['data']; c = d.get('coin'); n[c] = n.get(c, 0) + 1
                if n[c] <= 3 or n[c] % 10 == 0:
                    ctx = d.get('ctx', {})
                    log('%5.1f s' % (time.time() - t0), ch, c, 'oracle', ctx.get('oraclePx'), 'mark', ctx.get('markPx'), 'mid', ctx.get('midPx'), 'Nr.', n[c], 'Felder', sorted(ctx)[:12])
            else:
                log('%5.1f s' % (time.time() - t0), ch, json.dumps(m)[:200])
    log('Zähler in 40 s:', n)
asyncio.run(main())
open('dump/kurs_probe4.txt', 'w').write('\n'.join(AUS) + '\n')

import json, os, urllib.request, urllib.parse, datetime, time
os.makedirs('dump', exist_ok=True)
UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36'
def hole(params):
    url = 'https://www.tradays.com/de/economic-calendar/widget/content?' + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'X-Requested-With': 'XMLHttpRequest', 'Referer': 'https://www.tradays.com/de/economic-calendar/widget?mode=2&dateFormat=DMY'})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            body = r.read().decode('utf-8')
        d = json.loads(body)
        ts = sorted(x['ReleaseDate'] for x in d)
        f = lambda x: datetime.datetime.fromtimestamp(x / 1000, tz=datetime.timezone.utc).isoformat()
        return {'n': len(d), 'von': f(ts[0]) if ts else None, 'bis': f(ts[-1]) if ts else None, 'imp': sorted(set(x['Importance'] for x in d)), 'cur': sorted(set(x['CurrencyCode'] for x in d))}, d
    except Exception as e:
        return {'fehler': repr(e)[:300]}, None
tests = {
  'woche_1': dict(date_mode=1, **{'from': '2026-11-16T00:00:00', 'to': '2026-11-22T23:59:59'}, importance=12, currencies=3),
  'sechs_wochen_1': dict(date_mode=1, **{'from': '2026-11-16T00:00:00', 'to': '2026-12-27T23:59:59'}, importance=12, currencies=3),
  'sechs_wochen_0': dict(date_mode=0, **{'from': '2026-11-16T00:00:00', 'to': '2026-12-27T23:59:59'}, importance=12, currencies=3),
  'sechs_wochen_3': dict(date_mode=3, **{'from': '2026-11-16T00:00:00', 'to': '2026-12-27T23:59:59'}, importance=12, currencies=3),
  'naechste_1': dict(date_mode=1, **{'from': '2026-11-23T00:00:00', 'to': '2026-11-29T23:59:59'}, importance=12, currencies=3),
  'dez_1': dict(date_mode=1, **{'from': '2026-12-07T00:00:00', 'to': '2026-12-13T23:59:59'}, importance=12, currencies=3),
  'feiertage': dict(date_mode=1, **{'from': '2026-11-23T00:00:00', 'to': '2026-11-29T23:59:59'}, importance=1, currencies=3),
}
bericht = {}
for name, p in tests.items():
    bericht[name], d = hole(p)
    if d is not None: json.dump(d, open('dump/' + name + '.json', 'w'), ensure_ascii=False)
    time.sleep(1.5)
json.dump(bericht, open('dump/bericht.json', 'w'), indent=1)
print(json.dumps(bericht, indent=1))

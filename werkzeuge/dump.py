import json, os, re, urllib.request
os.makedirs('dump', exist_ok=True)
UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36'
def hole(url, name, data=None, extra=None):
    h = {'User-Agent': UA, 'Accept-Language': 'de-DE,de;q=0.9'}
    if extra: h.update(extra)
    try:
        req = urllib.request.Request(url, data=data, headers=h)
        with urllib.request.urlopen(req, timeout=30) as r:
            body = r.read()
            open('dump/' + name, 'wb').write(body[:3_000_000])
            return {'status': r.status, 'bytes': len(body), 'typ': r.headers.get('Content-Type')}
    except Exception as e:
        return {'fehler': repr(e)[:300]}
bericht = {}
w = urllib.request.urlopen(urllib.request.Request('https://www.tradays.com/de/economic-calendar/widget?mode=2&dateFormat=DMY', headers={'User-Agent': UA}), timeout=30).read().decode('utf-8')
js = re.findall(r'src="(/c/js/widgets/calendar/[^"]+)"', w)
bericht['js'] = js
for k, pfad in enumerate(js):
    bericht['js%d' % k] = hole('https://www.tradays.com' + pfad, 'widget%d.js' % k)
json.dump(bericht, open('dump/bericht.json', 'w'), indent=1)
print(json.dumps(bericht, indent=1))

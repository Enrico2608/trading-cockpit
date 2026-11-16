import json, os, urllib.request, time
os.makedirs('dump', exist_ok=True)
UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36'
urls = {
  'tradays_de': 'https://www.tradays.com/de/economic-calendar',
  'tradays_en': 'https://www.tradays.com/en/economic-calendar',
  'mql5_de': 'https://www.mql5.com/de/economic-calendar',
  'widget_de': 'https://www.tradays.com/de/economic-calendar/widget?mode=2&dateFormat=DMY',
  'ff_this': 'https://nfs.faireconomy.media/ff_calendar_thisweek.json',
  'ff_next': 'https://nfs.faireconomy.media/ff_calendar_nextweek.json',
}
bericht = {}
for name, url in urls.items():
    try:
        req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept-Language': 'de-DE,de;q=0.9', 'Accept': 'text/html,application/json;q=0.9,*/*;q=0.8'})
        with urllib.request.urlopen(req, timeout=30) as r:
            body = r.read()
            bericht[name] = {'status': r.status, 'bytes': len(body), 'typ': r.headers.get('Content-Type'), 'cors': r.headers.get('Access-Control-Allow-Origin'), 'final': r.geturl()}
            open('dump/' + name + ('.json' if name.startswith('ff') else '.html'), 'wb').write(body[:3_000_000])
    except Exception as e:
        bericht[name] = {'fehler': repr(e)[:300]}
    time.sleep(1)
json.dump(bericht, open('dump/bericht.json', 'w'), indent=1)
print(json.dumps(bericht, indent=1))

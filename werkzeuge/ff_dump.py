import json, os, urllib.request
os.makedirs('dump', exist_ok=True)
UA = 'trading-cockpit-termine/1.0 (privates Cockpit, 1 Abruf am Tag; https://github.com/Enrico2608/trading-cockpit)'
for name, url in (('ff_this.json', 'https://nfs.faireconomy.media/ff_calendar_thisweek.json'), ('ff_this.xml', 'https://nfs.faireconomy.media/ff_calendar_thisweek.xml')):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': UA}), timeout=30) as r:
            body = r.read()
            open('dump/' + name, 'wb').write(body)
            print(name, r.status, len(body), dict(r.headers))
    except Exception as e:
        print(name, 'Fehler', repr(e))

"""Probe 2: Aufbau der ForexFactory-Kalenderseite (nächste Woche) – eingebettete Daten finden."""
import json, re, urllib.request
UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36'
out = {}
for wo in ('next', 'this'):
    try:
        r = urllib.request.urlopen(urllib.request.Request('https://www.forexfactory.com/calendar?week=' + wo, headers={'User-Agent': UA, 'Accept-Language': 'en-US,en;q=0.9'}), timeout=30)
        html = r.read().decode('utf-8', 'replace'); st = r.status
    except Exception as e:
        out[wo] = {'fehler': repr(e)}; continue
    i = html.find('calendarComponentStates')
    stellen = [m.start() for m in re.finditer(r'calendarComponentStates', html)][:5]
    ev = re.search(r'"events":\[(\{.*?\})\s*,\s*\{', html, re.S)
    namen = re.findall(r'"name":"([^"]{3,80})"', html)[:40]
    out[wo] = {'status': st, 'laenge': len(html), 'stellen': stellen, 'ausschnitt': html[i - 200:i + 2500] if i >= 0 else '',
               'erstes_event': ev.group(1)[:2500] if ev else '', 'namen': namen,
               'schluessel': sorted(set(re.findall(r'"(\w+)":', html[i:i + 200000])))[:200] if i >= 0 else [],
               'tz': re.findall(r'(timezone[^,;]{0,80})', html, re.I)[:8], 'datelines': re.findall(r'"dateline":(\d+)', html)[:6]}
json.dump(out, open('dump/ff_seite.json', 'w'), ensure_ascii=False, indent=1)
print({k: (v.get('status'), v.get('laenge'), len(v.get('namen', []))) for k, v in out.items()})

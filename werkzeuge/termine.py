#!/usr/bin/env python3
"""Wichtige Wirtschaftstermine für Enricos Trading-Cockpit.

Holt aus dem Wirtschaftskalender von Tradays (MetaQuotes) alle Termine mit Wichtigkeit
„hoch“ oder „mittel“ für USA, Eurozone, Deutschland und weltweite Termine (z. B. IEA-Ölbericht),
von Montag dieser Woche bis WOCHEN Wochen voraus. Meldungen, die zur selben Minute aus demselben
Land kommen, werden zu einer Zeile zusammengefasst (die wichtigste zuerst). Uhrzeiten in deutscher
Zeit. Ergebnis: termine.json für die Website (das Cockpit lädt die Datei beim Öffnen).

Aufruf:  python3 termine.py ZIEL.json              lädt bei Tradays
         python3 termine.py ZIEL.json --datei X    nimmt eine gespeicherte Tradays-Antwort (zum Testen)

Die Datei wird nur neu geschrieben, wenn sich Termine geändert haben (sonst kein neuer Commit).
"""
import datetime
import json
import sys
import time
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo

BERLIN = ZoneInfo('Europe/Berlin')
DATEN = 'https://www.tradays.com/de/economic-calendar/widget/content'
SEITE = 'https://www.tradays.com/de/economic-calendar/widget?mode=2&dateFormat=DMY'
LINK = 'https://www.tradays.com/de/economic-calendar/'
UA = 'trading-cockpit-termine/1.0 (privates Cockpit, 1 Abruf am Tag; https://github.com/Enrico2608/trading-cockpit)'
WOCHEN = 7
WICHTIG = {'high': 'hoch', 'medium': 'mittel'}     # niedrig und Feiertage bleiben draußen
RANG = {'hoch': 2, 'mittel': 1}
LAENDER = {840: 'USA', 999: 'Eurozone', 276: 'Deutschland', 0: 'Welt'}
WAEHRUNGEN = 1 | 2                                 # Tradays-Filter: USD = 1, EUR = 2
WICHTIGKEIT = 4 | 8                                # Tradays-Filter: mittel = 4, hoch = 8
# Tradays-Übersetzungen, die in die Irre führen (nach dem englischen Kürzel in der Adresse)
TITEL = {
    'united-states/retail-sales-ex-autos-mm': 'Kern-Einzelhandelsumsatz (ohne Autos) m/m',
    'united-states/retail-control-mm': 'Einzelhandel Kontrollgruppe m/m',
    'united-states/cftc-sp-500-non-commercial-net-positions': 'CFTC S&P 500, nichtkommerzielle Nettopositionen',
}
ENERGIE = ('crude', 'oil', 'rig-count', 'opec', 'gasoline', 'distillate', 'cushing', 'heating', 'natural-gas')


def maerkte(kuerzel):
    k = kuerzel.rsplit('/', 1)[-1]
    if k.startswith('cftc-'):
        for wort, key in (('gold', 'GOLD'), ('silver', 'SILBER'), ('crude', 'USOIL'), ('oil', 'USOIL'), ('sp-500', 'SP500'),
                          ('nasdaq', 'NASDAQ'), ('djia', 'DOW'), ('dow', 'DOW'), ('bitcoin', 'BTC')):
            if wort in k:
                return [key]
        return ['ALLE']
    if any(w in k for w in ENERGIE):
        return ['USOIL']
    return ['ALLE']


def zeitraum(jetzt):
    heute = jetzt.astimezone(BERLIN).date()
    von = heute - datetime.timedelta(days=heute.weekday())
    return von, von + datetime.timedelta(days=7 * WOCHEN - 1)


def laden(von, bis):
    params = {'date_mode': 1, 'from': (von - datetime.timedelta(days=1)).isoformat() + 'T00:00:00',
              'to': (bis + datetime.timedelta(days=1)).isoformat() + 'T23:59:59', 'importance': WICHTIGKEIT, 'currencies': WAEHRUNGEN}
    url = DATEN + '?' + urllib.parse.urlencode(params)
    fehler = None
    for versuch in range(3):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': UA, 'X-Requested-With': 'XMLHttpRequest', 'Referer': SEITE,
                                                       'Accept': 'application/json'})
            with urllib.request.urlopen(req, timeout=40) as r:
                return json.loads(r.read().decode('utf-8'))
        except Exception as e:  # noqa: BLE001 – nach kurzer Pause erneut versuchen
            fehler = e
            time.sleep(10 * (versuch + 1))
    raise SystemExit('Tradays nicht erreichbar: %r' % (fehler,))


def umwandeln(daten, von, bis):
    gruppen = {}
    for e in daten:
        land = LAENDER.get(e.get('Country'))
        wichtig = WICHTIG.get(e.get('Importance'))
        if land is None or wichtig is None or e.get('EventType') == 2 or not e.get('ReleaseDate'):
            continue
        t = datetime.datetime.fromtimestamp(e['ReleaseDate'] / 1000, tz=datetime.timezone.utc)
        modus = e.get('TimeMode', 0)
        if modus in (1, 2):        # ganztägig bzw. Uhrzeit noch offen: Kalendertag
            datum, zeit = t.date(), None
        else:
            tb = t.astimezone(BERLIN)
            datum, zeit = tb.date(), tb.strftime('%H:%M')
        if not (von <= datum <= bis):
            continue
        kuerzel = str(e.get('Url') or '').split('/widget/', 1)[-1].strip('/')
        titel = TITEL.get(kuerzel) or ' '.join(str(e.get('EventName') or '').split())
        if not titel:
            continue
        g = gruppen.setdefault((datum.isoformat(), zeit or '', land, modus), [])
        g.append({'id': e.get('Id'), 'titel': titel, 'wichtig': wichtig, 'kuerzel': kuerzel, 'maerkte': maerkte(kuerzel), 'n': len(g)})
    termine = []
    for (datum, zeit, land, modus), liste in gruppen.items():
        liste.sort(key=lambda x: (-RANG[x['wichtig']], x['n']))
        erste, titel = liste[0], []
        for x in liste:
            if x['titel'] not in titel:
                titel.append(x['titel'])
        ms = sorted({m for x in liste for m in x['maerkte']})
        termine.append({
            'id': 'td-%s' % erste['id'],
            'datum': datum,
            'zeit': zeit or None,
            'zeitart': {1: 'ganztägig', 2: 'offen', 3: 'vorläufig'}.get(modus, ''),
            'titel': titel[0],
            'weitere': titel[1:],
            'land': land,
            'maerkte': ['ALLE'] if 'ALLE' in ms else ms,
            'wichtig': erste['wichtig'],
            'quelle': 'Tradays',
            'url': LINK + erste['kuerzel'] if erste['kuerzel'] else 'https://www.tradays.com/de/economic-calendar',
        })
    termine.sort(key=lambda t: (t['datum'], t['zeit'] or '', ['USA', 'Eurozone', 'Deutschland', 'Welt'].index(t['land'])))
    return termine


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    ziel = sys.argv[1]
    jetzt = datetime.datetime.now(datetime.timezone.utc)
    von, bis = zeitraum(jetzt)
    if '--datei' in sys.argv:
        daten = json.load(open(sys.argv[sys.argv.index('--datei') + 1], encoding='utf-8'))
    else:
        daten = laden(von, bis)
    if not isinstance(daten, list) or len(daten) < 10:
        raise SystemExit('Antwort von Tradays sieht nicht nach Terminen aus (%s Einträge) – alte Datei bleibt.' % (len(daten) if isinstance(daten, list) else '?'))
    termine = umwandeln(daten, von, bis)
    if len(termine) < 10 or not any(t['wichtig'] == 'hoch' for t in termine):
        raise SystemExit('Zu wenige Termine (%d) – alte Datei bleibt.' % len(termine))
    neu = {
        'stand': jetzt.astimezone(BERLIN).isoformat(timespec='seconds'),
        'quelle': 'Tradays',
        'quelle_url': 'https://www.tradays.com/de/economic-calendar',
        'hinweis': 'Wichtige Termine (hoch und mittel) aus dem Tradays-Wirtschaftskalender für USA, Eurozone und Deutschland, '
                   'Uhrzeiten in deutscher Zeit. Wird täglich automatisch aktualisiert.',
        'von': von.isoformat(),
        'bis': bis.isoformat(),
        'termine': termine,
    }
    try:
        alt = json.load(open(ziel, encoding='utf-8'))
        if alt.get('von') == neu['von'] and alt.get('termine') == neu['termine']:
            print('Termine unverändert (%d Zeilen, %s bis %s).' % (len(termine), neu['von'], neu['bis']))
            return
    except (OSError, ValueError):
        pass
    with open(ziel, 'w', encoding='utf-8') as f:
        json.dump(neu, f, ensure_ascii=False, indent=1)
        f.write('\n')
    print('%d Termine geschrieben (%s bis %s, davon %d hoch).' % (len(termine), neu['von'], neu['bis'], sum(t['wichtig'] == 'hoch' for t in termine)))


if __name__ == '__main__':
    main()

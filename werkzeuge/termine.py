#!/usr/bin/env python3
"""Wichtige Wirtschaftstermine für Enricos Trading-Cockpit – aus Tradays und ForexFactory.

Tradays (MetaQuotes): Wichtigkeit „hoch“ und „mittel“ für USA, Eurozone, Deutschland und weltweite Termine
(z. B. IEA-Ölbericht), von Montag dieser Woche bis WOCHEN Wochen voraus.
ForexFactory: Impact „High“ und „Medium“ für USD und EUR (deutsche Daten als Deutschland, französische, italienische
und spanische bleiben draußen). Laufende Woche aus dem Feed von ForexFactory, die nächste Woche von der Kalenderseite
(eingebettete Daten; höchstens alle 6 Stunden abgerufen, dazwischen aus der letzten Datei).

Betroffene Märkte je Termin (statt „alle“): US-Daten → Gold, Silber, Nasdaq, S&P 500, Dow, Bitcoin, HYPE; Fed-Zinsentscheid
→ alle acht; Energie (EIA, API, OPEC, Bohrtürme) → Öl; Eurozone/Deutschland → Gold und Silber; CFTC je Kontrakt.

Meldungen, die zur selben Minute aus demselben Land kommen, werden zu einer Zeile zusammengefasst (die wichtigste
zuerst). Die Wichtigkeit einer Zeile ist die höhere der beiden Quellen. Uhrzeiten in deutscher Zeit.
Ergebnis: termine.json für die Website (das Cockpit lädt die Datei beim Öffnen).

Aufruf:  python3 termine.py ZIEL.json
         python3 termine.py ZIEL.json --datei TRADAYS.json --ff-datei FF.xml --ff-seite FF.html   (gespeicherte Antworten, zum Testen)

Die Datei wird nur neu geschrieben, wenn sich Termine geändert haben (sonst kein neuer Commit).
Ist ForexFactory nicht erreichbar, kommen nur die Tradays-Termine (und umgekehrt bleibt ohne Tradays die alte Datei).
"""
import datetime
import json
import re
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from zoneinfo import ZoneInfo

BERLIN = ZoneInfo('Europe/Berlin')
UTC = datetime.timezone.utc
UA = 'trading-cockpit-termine/1.1 (privates Cockpit, werktags alle 2 Stunden; https://github.com/Enrico2608/trading-cockpit)'
UA_SEITE = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36'
WOCHEN = 7
RANG = {'hoch': 2, 'mittel': 1}
LAND_REIHE = ['USA', 'Eurozone', 'Deutschland', 'Welt']

# ---------------------------------------------------------------- Tradays
TD_DATEN = 'https://www.tradays.com/de/economic-calendar/widget/content'
TD_SEITE = 'https://www.tradays.com/de/economic-calendar/widget?mode=2&dateFormat=DMY'
TD_LINK = 'https://www.tradays.com/de/economic-calendar/'
TD_WICHTIG = {'high': 'hoch', 'medium': 'mittel'}     # niedrig und Feiertage bleiben draußen
TD_LAENDER = {840: 'USA', 999: 'Eurozone', 276: 'Deutschland', 0: 'Welt'}
TD_WAEHRUNGEN = 1 | 2                                 # Tradays-Filter: USD = 1, EUR = 2
TD_WICHTIGKEIT = 4 | 8                                # Tradays-Filter: mittel = 4, hoch = 8
# Tradays-Übersetzungen, die in die Irre führen (nach dem englischen Kürzel in der Adresse)
TD_TITEL = {
    'united-states/retail-sales-ex-autos-mm': 'Kern-Einzelhandelsumsatz (ohne Autos) m/m',
    'united-states/retail-control-mm': 'Einzelhandel Kontrollgruppe m/m',
    'united-states/cftc-sp-500-non-commercial-net-positions': 'CFTC S&P 500, nichtkommerzielle Nettopositionen',
}
ENERGIE = ('crude', 'oil', 'rig-count', 'opec', 'gasoline', 'distillate', 'cushing', 'heating', 'natural-gas')

# ---------------------------------------------------------------- ForexFactory
FF_FEED = 'https://nfs.faireconomy.media/ff_calendar_thisweek.xml'
FF_SEITE = 'https://www.forexfactory.com/calendar?week=next'
FF_WICHTIG = {'High': 'hoch', 'Medium': 'mittel'}     # Low, Holiday und Non-Economic bleiben draußen
FF_OHNE = ('French ', 'Italian ', 'Spanish ')
FF_SEITE_ALTER = 6 * 3600                              # Kalenderseite höchstens alle 6 Stunden abrufen

# ---------------------------------------------------------------- Betroffene Märkte
ALLE_MAERKTE = ['GOLD', 'SILBER', 'USOIL', 'BTC', 'HYPE', 'NASDAQ', 'SP500', 'DOW']
US_DATEN = ['GOLD', 'SILBER', 'BTC', 'HYPE', 'NASDAQ', 'SP500', 'DOW']   # US-Konjunktur, Inflation, Fed-Reden: alle außer Öl
EURO_DATEN = ['GOLD', 'SILBER']                                          # Eurozone/Deutschland: über den Dollar (EUR/USD)
ZINSENTSCHEID = re.compile(r'zinsentscheid|interest-rate-decision|federal-funds-rate|fomc-statement|fomc-press|fed-chair|federal funds rate|fomc statement|fomc press', re.I)


def hole(url, kopf, versuche=3):
    fehler = None
    for versuch in range(versuche):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=dict({'User-Agent': UA}, **kopf)), timeout=40) as r:
                return r.read()
        except Exception as e:  # noqa: BLE001 – nach kurzer Pause erneut versuchen
            fehler = e
            time.sleep(10 * (versuch + 1))
    raise RuntimeError('%s nicht erreichbar: %r' % (url.split('/')[2], fehler))


def maerkte_land(land, text):
    """Betroffene Märkte nach Land und Art des Termins (Text: Tradays-Kürzel oder ForexFactory-Titel)."""
    if land == 'USA':
        return list(ALLE_MAERKTE) if ZINSENTSCHEID.search(text) else list(US_DATEN)
    if land in ('Eurozone', 'Deutschland'):
        return list(EURO_DATEN)
    return list(ALLE_MAERKTE)


def maerkte_td(kuerzel, land='USA'):
    k = kuerzel.rsplit('/', 1)[-1]
    if k.startswith('cftc-'):
        for wort, key in (('gold', 'GOLD'), ('silver', 'SILBER'), ('crude', 'USOIL'), ('oil', 'USOIL'), ('sp-500', 'SP500'),
                          ('nasdaq', 'NASDAQ'), ('djia', 'DOW'), ('dow', 'DOW'), ('bitcoin', 'BTC')):
            if wort in k:
                return [key]
        return list(EURO_DATEN) if land in ('Eurozone', 'Deutschland') else list(US_DATEN)
    if any(w in k for w in ENERGIE):
        return ['USOIL']
    return maerkte_land(land, kuerzel)


def maerkte_ff(titel, land='USA'):
    t = titel.lower()
    if any(w in t for w in ('crude oil', 'natural gas', 'opec', 'oil inventories', 'rig count')):
        return ['USOIL']
    return maerkte_land(land, titel)


def zeitraum(jetzt):
    heute = jetzt.astimezone(BERLIN).date()
    von = heute - datetime.timedelta(days=heute.weekday())
    return von, von + datetime.timedelta(days=7 * WOCHEN - 1)


def td_laden(von, bis):
    params = {'date_mode': 1, 'from': (von - datetime.timedelta(days=1)).isoformat() + 'T00:00:00',
              'to': (bis + datetime.timedelta(days=1)).isoformat() + 'T23:59:59', 'importance': TD_WICHTIGKEIT, 'currencies': TD_WAEHRUNGEN}
    roh = hole(TD_DATEN + '?' + urllib.parse.urlencode(params), {'X-Requested-With': 'XMLHttpRequest', 'Referer': TD_SEITE, 'Accept': 'application/json'})
    return json.loads(roh.decode('utf-8'))


def td_meldungen(daten, von, bis):
    """Tradays-Antwort → einzelne Meldungen {datum, zeit, modus, land, titel, wichtig, url, maerkte, id, n}."""
    out = []
    for n, e in enumerate(daten):
        land = TD_LAENDER.get(e.get('Country'))
        wichtig = TD_WICHTIG.get(e.get('Importance'))
        if land is None or wichtig is None or e.get('EventType') == 2 or not e.get('ReleaseDate'):
            continue
        t = datetime.datetime.fromtimestamp(e['ReleaseDate'] / 1000, tz=UTC)
        modus = {1: 'ganztägig', 2: 'offen', 3: 'vorläufig'}.get(e.get('TimeMode', 0), '')
        if modus in ('ganztägig', 'offen'):        # Kalendertag ohne Uhrzeit
            datum, zeit = t.date(), None
        else:
            tb = t.astimezone(BERLIN)
            datum, zeit = tb.date(), tb.strftime('%H:%M')
        if not (von <= datum <= bis):
            continue
        kuerzel = str(e.get('Url') or '').split('/widget/', 1)[-1].strip('/')
        titel = TD_TITEL.get(kuerzel) or ' '.join(str(e.get('EventName') or '').split())
        if titel:
            out.append({'quelle': 'Tradays', 'datum': datum.isoformat(), 'zeit': zeit, 'modus': modus, 'land': land, 'titel': titel,
                        'wichtig': wichtig, 'url': TD_LINK + kuerzel if kuerzel else 'https://www.tradays.com/de/economic-calendar',
                        'maerkte': maerkte_td(kuerzel, land), 'id': 'td-%s' % e.get('Id'), 'n': n})
    return out


def ff_meldungen(roh, von, bis):
    """ForexFactory-XML (Zeiten in UTC) → einzelne Meldungen wie bei Tradays."""
    text = re.sub(r'^\s*<\?xml[^>]*\?>', '', roh.decode('cp1252', errors='replace'))
    out = []
    for n, e in enumerate(ET.fromstring(text).findall('event')):
        f = {c.tag: ' '.join((c.text or '').split()) for c in e}
        wichtig = FF_WICHTIG.get(f.get('impact'))
        titel = f.get('title', '')
        if not wichtig or not titel:
            continue
        land = {'USD': 'USA', 'All': 'Welt'}.get(f.get('country'))
        if f.get('country') == 'EUR':
            if titel.startswith(FF_OHNE):
                continue
            land = 'Deutschland' if titel.startswith('German ') else 'Eurozone'
        if not land:
            continue
        try:
            tag = datetime.datetime.strptime(f.get('date', ''), '%m-%d-%Y').date()
        except ValueError:
            continue
        m = re.fullmatch(r'(\d{1,2}):(\d{2})(am|pm)', f.get('time', '').lower())
        if m:
            h = int(m.group(1)) % 12 + (12 if m.group(3) == 'pm' else 0)
            tb = datetime.datetime(tag.year, tag.month, tag.day, h, int(m.group(2)), tzinfo=UTC).astimezone(BERLIN)
            datum, zeit, modus = tb.date(), tb.strftime('%H:%M'), ''
        else:
            datum, zeit, modus = tag, None, 'ganztägig' if 'all day' in f.get('time', '').lower() else 'offen'
        if not (von <= datum <= bis):
            continue
        url = f.get('url', '') if f.get('url', '').startswith('https://www.forexfactory.com/') else 'https://www.forexfactory.com/calendar'
        nummer = re.search(r'/calendar/(\d+)', url)
        out.append({'quelle': 'ForexFactory', 'datum': datum.isoformat(), 'zeit': zeit, 'modus': modus, 'land': land, 'titel': titel,
                    'wichtig': wichtig, 'url': url, 'maerkte': maerkte_ff(titel, land),
                    'id': 'ff-%s-%s-%s' % (datum.isoformat(), (zeit or 'tag').replace(':', ''), nummer.group(1) if nummer else n), 'n': n})
    return out


def ff_seite_tage(html):
    """Eingebettete Kalenderdaten der ForexFactory-Seite: window.calendarComponentStates[1] = { days: [...] }."""
    i = html.find('calendarComponentStates[1]')
    j = html.find('days: [', i if i >= 0 else 0)
    if j < 0:
        raise ValueError('keine Kalenderdaten auf der Seite')
    j += len('days: ')
    tiefe, im_text, esc, k = 0, False, False, j
    for k in range(j, len(html)):
        ch = html[k]
        if im_text:
            if esc:
                esc = False
            elif ch == '\\':
                esc = True
            elif ch == '"':
                im_text = False
        elif ch == '"':
            im_text = True
        elif ch == '[':
            tiefe += 1
        elif ch == ']':
            tiefe -= 1
            if tiefe == 0:
                break
    return json.loads(html[j:k + 1])


def ff_seite_meldungen(html, von, bis):
    """ForexFactory-Kalenderseite → Meldungen wie beim Feed (Zeitpunkt aus „dateline“, UTC)."""
    out = []
    for tag in ff_seite_tage(html):
        for n, e in enumerate(tag.get('events') or []):
            wichtig = {'high': 'hoch', 'medium': 'mittel'}.get(str(e.get('impactName') or '').lower())
            titel = ' '.join(str(e.get('name') or '').replace('\\/', '/').split())
            if not wichtig or not titel:
                continue
            land = {'USD': 'USA', 'All': 'Welt'}.get(e.get('currency'))
            if e.get('currency') == 'EUR':
                if titel.startswith(FF_OHNE):
                    continue
                land = 'Deutschland' if titel.startswith('German ') else 'Eurozone'
            if not land:
                continue
            zeitlabel = str(e.get('timeLabel') or '').strip().lower()
            if re.fullmatch(r'\d{1,2}:\d{2}(am|pm)', zeitlabel) and not e.get('timeMasked') and isinstance(e.get('dateline'), (int, float)):
                tb = datetime.datetime.fromtimestamp(e['dateline'], tz=UTC).astimezone(BERLIN)
                datum, zeit, modus = tb.date(), tb.strftime('%H:%M'), ''
            else:
                try:
                    datum = datetime.datetime.strptime(str(e.get('date') or ''), '%b %d, %Y').date()
                except ValueError:
                    continue
                zeit, modus = None, 'ganztägig' if 'all day' in zeitlabel else 'offen'
            if not (von <= datum <= bis):
                continue
            solo = str(e.get('soloUrl') or '')
            url = 'https://www.forexfactory.com' + solo if solo.startswith('/calendar/') else 'https://www.forexfactory.com/calendar?week=next'
            out.append({'quelle': 'ForexFactory', 'datum': datum.isoformat(), 'zeit': zeit, 'modus': modus, 'land': land, 'titel': titel,
                        'wichtig': wichtig, 'url': url, 'maerkte': maerkte_ff(titel, land),
                        'id': 'ff-%s-%s-%s' % (datum.isoformat(), (zeit or 'tag').replace(':', ''), e.get('id') or n), 'n': 1000 + n})
    return out


NAMEN_OHNE = {'Index', 'President', 'Präsident', 'Speaks', 'Sales', 'Rate', 'Bank', 'Meeting', 'Member', 'Governor', 'Gouverneur',
              'Chairman', 'Chair', 'Board', 'Minutes', 'Protokoll', 'Change', 'Prices', 'Price', 'Final', 'Flash', 'Prelim'}


def namen(titel):
    return {w for w in re.findall(r'[A-ZÄÖÜ][a-zäöüß]{3,}', titel) if w not in NAMEN_OHNE}


def minuten(zeit):
    return int(zeit[:2]) * 60 + int(zeit[3:]) if zeit else None


def zusammenfassen(meldungen):
    gruppen = {}
    for x in meldungen:
        art = 'zeit' if x['zeit'] else x['modus']
        gruppen.setdefault((x['datum'], x['zeit'] or '', x['land'], art), []).append(x)
    # Reden u. Ä. mit leicht anderer Uhrzeit (z. B. Lagarde 09:15 bei ForexFactory, 09:30 bei Tradays): gleicher Tag, gleiches
    # Land, höchstens 30 Minuten Abstand und derselbe Name im Titel → eine Zeile (ForexFactory-Zeit steht dann dabei)
    for key in [k for k, v in gruppen.items() if k[1] and all(x['quelle'] == 'ForexFactory' for x in v)]:
        ff = gruppen[key]
        for k2, v2 in gruppen.items():
            if k2 == key or k2[0] != key[0] or k2[2] != key[2] or not k2[1] or abs(minuten(k2[1]) - minuten(key[1])) > 30:
                continue
            td = [x for x in v2 if x['quelle'] == 'Tradays']
            if td and any(namen(a['titel']) & namen(b['titel']) for a in ff for b in td):
                v2.extend(dict(x, zeit_ff=x['zeit']) for x in ff)
                del gruppen[key]
                break
    termine = []
    for (datum, zeit, land, art), liste in gruppen.items():
        liste.sort(key=lambda x: (x['quelle'] != 'Tradays', -RANG[x['wichtig']], x['n']))
        td = [x for x in liste if x['quelle'] == 'Tradays']
        ff = sorted([x for x in liste if x['quelle'] == 'ForexFactory'], key=lambda x: (-RANG[x['wichtig']], x['n']))
        haupt = td or ff
        titel = []
        for x in haupt:
            if x['titel'] not in titel:
                titel.append(x['titel'])
        ff_zeile = []
        if td:
            for x in ff:
                if x['titel'] not in [y['titel'] for y in ff_zeile]:
                    ff_zeile.append(dict({'titel': x['titel'], 'wichtig': x['wichtig']}, **({'zeit': x['zeit_ff']} if x.get('zeit_ff') else {})))
        links = []
        for x in (td[:1] + ff[:1]):
            links.append({'text': x['quelle'], 'url': x['url']})
        ms = [m for m in ALLE_MAERKTE if any(m in x['maerkte'] or 'ALLE' in x['maerkte'] for x in liste)]
        vorlaeufig = any(x['modus'] == 'vorläufig' for x in td)
        termine.append({
            'id': haupt[0]['id'],
            'datum': datum,
            'zeit': zeit or None,
            'zeitart': 'vorläufig' if zeit and vorlaeufig else ('' if zeit else art),
            'titel': titel[0],
            'weitere': titel[1:],
            'ff': ff_zeile,
            'land': land,
            'maerkte': ms,
            'wichtig': 'hoch' if any(x['wichtig'] == 'hoch' for x in liste) else 'mittel',
            'quelle': links[0]['text'],
            'url': links[0]['url'],
            'links': links,
            'kalender': True,
        })
    termine.sort(key=lambda t: (t['datum'], t['zeit'] or '', LAND_REIHE.index(t['land'])))
    return termine


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    ziel = sys.argv[1]
    jetzt = datetime.datetime.now(UTC)
    von, bis = zeitraum(jetzt)
    arg = lambda name: sys.argv[sys.argv.index(name) + 1] if name in sys.argv else None
    try:
        daten = json.load(open(arg('--datei'), encoding='utf-8')) if arg('--datei') else td_laden(von, bis)
    except Exception as e:  # noqa: BLE001
        raise SystemExit('Tradays: %s – alte Datei bleibt.' % e)
    if not isinstance(daten, list) or len(daten) < 10:
        raise SystemExit('Antwort von Tradays sieht nicht nach Terminen aus (%s Einträge) – alte Datei bleibt.' % (len(daten) if isinstance(daten, list) else '?'))
    meldungen = td_meldungen(daten, von, bis)
    ff_ok, ff_anzahl = False, 0
    try:
        roh = open(arg('--ff-datei'), 'rb').read() if arg('--ff-datei') else hole(FF_FEED, {'Accept': 'application/xml'})
        ff = ff_meldungen(roh, von, bis)
        ff_ok, ff_anzahl = True, len(ff)
        meldungen += ff
    except Exception as e:  # noqa: BLE001 – ohne ForexFactory weiter
        print('ForexFactory: %s – nur Tradays.' % e)
    # Nächste Woche: Kalenderseite von ForexFactory (der Feed hat nur die laufende Woche)
    try:
        alt = json.load(open(ziel, encoding='utf-8'))
    except (OSError, ValueError):
        alt = {}
    zwischen = alt.get('ff_naechste') if isinstance(alt.get('ff_naechste'), dict) else {}
    ff_naechste, ff_naechste_stand = [], ''
    gespeichert = zwischen.get('meldungen') if isinstance(zwischen.get('meldungen'), list) else []
    try:
        alter = (jetzt - datetime.datetime.fromisoformat(zwischen['stand'])).total_seconds() if zwischen.get('stand') else 1e9
    except (TypeError, ValueError):
        alter = 1e9
    naechste_von = von + datetime.timedelta(days=6)   # ForexFactory-Woche: Sonntag bis Samstag
    if gespeichert and alter < FF_SEITE_ALTER and not arg('--ff-seite'):
        ff_naechste, ff_naechste_stand = [x for x in gespeichert if isinstance(x, dict) and x.get('datum', '') >= naechste_von.isoformat()], zwischen['stand']
    else:
        try:
            html = open(arg('--ff-seite'), encoding='utf-8').read() if arg('--ff-seite') else hole(FF_SEITE, {'Accept': 'text/html', 'User-Agent': UA_SEITE, 'Accept-Language': 'en-US,en;q=0.9'}).decode('utf-8', 'replace')
            ff_naechste = [x for x in ff_seite_meldungen(html, von, bis) if x['datum'] >= naechste_von.isoformat()]
            ff_naechste_stand = jetzt.astimezone(BERLIN).isoformat(timespec='seconds')
        except Exception as e:  # noqa: BLE001 – ohne die nächste Woche weiter
            print('ForexFactory nächste Woche: %s' % e)
            ff_naechste = [x for x in gespeichert if isinstance(x, dict) and x.get('datum', '') >= naechste_von.isoformat()]
            ff_naechste_stand = zwischen.get('stand', '') if ff_naechste else ''
    vorhanden = {x['id'] for x in meldungen}
    meldungen += [x for x in ff_naechste if x.get('id') not in vorhanden]
    termine = zusammenfassen(meldungen)
    if len(termine) < 10 or not any(t['wichtig'] == 'hoch' for t in termine):
        raise SystemExit('Zu wenige Termine (%d) – alte Datei bleibt.' % len(termine))
    neu = {
        'stand': jetzt.astimezone(BERLIN).isoformat(timespec='seconds'),
        'quelle': 'Tradays und ForexFactory' if ff_ok else 'Tradays',
        'quellen': {'tradays': True, 'forexfactory': ff_ok},
        'hinweis': 'Wichtige Termine (hoch und mittel) aus den Wirtschaftskalendern von Tradays und ForexFactory für USA, '
                   'Eurozone und Deutschland, Uhrzeiten in deutscher Zeit, mit den betroffenen Märkten. ForexFactory: laufende '
                   'und nächste Woche. Wird werktags alle 2 Stunden automatisch aktualisiert.',
        'ff_wochen': (1 if ff_ok else 0) + (1 if ff_naechste else 0),
        'von': von.isoformat(),
        'bis': bis.isoformat(),
        'termine': termine,
        'ff_naechste': {'stand': ff_naechste_stand, 'meldungen': ff_naechste},
    }
    if alt.get('von') == neu['von'] and alt.get('termine') == neu['termine'] and alt.get('ff_naechste') == neu['ff_naechste']:
        print('Termine unverändert (%d Zeilen, %s bis %s).' % (len(termine), neu['von'], neu['bis']))
        return
    with open(ziel, 'w', encoding='utf-8') as f:
        json.dump(neu, f, ensure_ascii=False, indent=1)
        f.write('\n')
    print('%d Termine geschrieben (%s bis %s, davon %d hoch; ForexFactory: %s, nächste Woche %d Meldungen).' % (
        len(termine), neu['von'], neu['bis'], sum(t['wichtig'] == 'hoch' for t in termine), '%d Meldungen' % ff_anzahl if ff_ok else 'nicht erreichbar', len(ff_naechste)))


if __name__ == '__main__':
    main()

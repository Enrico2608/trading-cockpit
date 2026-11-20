#!/usr/bin/env python3
"""Schlagzeilen je Markt für Enricos Trading-Cockpit – aus Google News (deutsch, Suche je Thema, letzte 2 Tage).

Gruppen: Aktienmarkt (Nasdaq · S&P 500 · Dow, Nvidia), Kryptomarkt (Bitcoin, Hyperliquid, Krypto-Börsen),
Rohstoffe (Gold, Silber, Öl). Je Thema die neuesten Meldungen (Titel, Quelle, Zeit, Link) – nur die Überschrift,
kein Artikeltext. Doppelte Meldungen (gleicher Titel) erscheinen nur einmal. Werbeseiten (Vergleich, Bonus …) fliegen raus.
Für Hyperliquid kommt die englische Suche dazu, wenn es auf Deutsch zu wenig gibt.

Aufruf:  python3 schlagzeilen.py ZIEL.json
         python3 schlagzeilen.py ZIEL.json --dateien ORDNER   (gespeicherte Antworten THEMA.xml, zum Testen)
Die Datei wird nur geschrieben, wenn genug Meldungen da sind (sonst bleibt die alte).
"""
import datetime
import email.utils
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from zoneinfo import ZoneInfo

BERLIN = ZoneInfo('Europe/Berlin')
UTC = datetime.timezone.utc
UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36'
JE_THEMA = 4
MAX_ALTER = datetime.timedelta(hours=48)
GRUPPEN = [
    ('aktien', 'Aktienmarkt', [
        ('indizes', 'Nasdaq · S&P 500 · Dow', ['NASDAQ', 'SP500', 'DOW'], 'Wall Street OR Nasdaq OR "S&P 500" OR "Dow Jones"', None),
        ('nvidia', 'Nvidia', ['NASDAQ'], 'Nvidia', None),
    ]),
    ('krypto', 'Kryptomarkt', [
        ('bitcoin', 'Bitcoin', ['BTC'], 'Bitcoin', None),
        ('hyperliquid', 'Hyperliquid (HYPE)', ['HYPE'], 'Hyperliquid', 'Hyperliquid'),
        ('boersen', 'Krypto-Börsen & Plattformen', [], 'Binance OR Coinbase OR Kraken OR Krypto-Börse', None),
    ]),
    ('rohstoffe', 'Rohstoffe', [
        ('gold', 'Gold', ['GOLD'], 'Goldpreis OR Gold-Preis OR "Gold-Kurs"', None),
        ('silber', 'Silber', ['SILBER'], 'Silberpreis OR Silber-Preis OR "Silber-Kurs"', None),
        ('oel', 'Öl', ['USOIL'], 'Ölpreis OR OPEC OR "Brent" OR "WTI"', None),
    ]),
]
# Werbe- und Vergleichsseiten, automatische Kursmeldungen („Goldpreis bei 3.232,10 Euro je Feinunze“) – keine Nachrichten
WERBUNG = re.compile(r'\b(vergleich|anbieter im test|bonus|gutschein|erfahrungen|so kaufen|kaufen: anleitung|bis \d[\d.]* ?€ schutz|testsieger)\b'
                     r'|\bbei [\d.,]+ (euro|dollar|us-dollar) je (feinunze|unze|barrel)', re.I)
QUELLEN_OHNE = re.compile(r'tixio|dosya haber|shattered', re.I)
ENGLISCH = re.compile(r'\b(the|and|of|to|for|with|has|this|its|after|as|from|could|will)\b', re.I)


def englisch(titel):
    return len(ENGLISCH.findall(titel)) >= 2


def adresse(q, deutsch=True):
    return 'https://news.google.com/rss/search?' + urllib.parse.urlencode({
        'q': q + ' when:2d', 'hl': 'de' if deutsch else 'en-US', 'gl': 'DE' if deutsch else 'US', 'ceid': 'DE:de' if deutsch else 'US:en'})


def hole(url, versuche=3):
    fehler = None
    for versuch in range(versuche):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': UA, 'Accept-Language': 'de-DE,de;q=0.9,en;q=0.7'}), timeout=30) as r:
                return r.read()
        except Exception as e:  # noqa: BLE001
            fehler = e
            time.sleep(5 * (versuch + 1))
    raise RuntimeError('Google News nicht erreichbar: %r' % fehler)


def meldungen(roh, jetzt):
    root = ET.fromstring(re.sub(rb'^\s*<\?xml[^>]*\?>', b'', roh))
    out = []
    for it in root.findall('.//item'):
        titel = ' '.join((it.findtext('title') or '').split())
        quelle = ' '.join((it.findtext('source') or '').split())
        link = (it.findtext('link') or '').strip()
        if quelle and titel.endswith(' - ' + quelle):
            titel = titel[:-len(' - ' + quelle)].rstrip()
        try:
            zeit = email.utils.parsedate_to_datetime(it.findtext('pubDate') or '').astimezone(UTC)
        except (TypeError, ValueError):
            continue
        if len(titel) < 20 or not link.startswith('https://') or WERBUNG.search(titel) or QUELLEN_OHNE.search(quelle) \
                or jetzt - zeit > MAX_ALTER or zeit - jetzt > datetime.timedelta(hours=2):
            continue
        out.append({'titel': titel[:220], 'quelle': quelle[:60] or 'Google News', 'zeit': zeit.astimezone(BERLIN).isoformat(timespec='minutes'), 'url': link[:600]})
    return out


def schluessel(titel):
    return re.sub(r'[^a-z0-9äöüß]+', ' ', titel.lower()).strip()[:90]


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    ziel = sys.argv[1]
    ordner = sys.argv[sys.argv.index('--dateien') + 1] if '--dateien' in sys.argv else None
    jetzt = datetime.datetime.now(UTC)
    gesehen, gruppen, gesamt, fehler = set(), [], 0, []
    for gid, gname, themen in GRUPPEN:
        liste = []
        for tid, tname, maerkte, q, q_en in themen:
            try:
                roh = open(os.path.join(ordner, tid + '.xml'), 'rb').read() if ordner else hole(adresse(q))
                ms = meldungen(roh, jetzt)
                if q_en and len(ms) < JE_THEMA:
                    roh_en = open(os.path.join(ordner, tid + '_en.xml'), 'rb').read() if ordner else hole(adresse(q_en, False))
                    ms += meldungen(roh_en, jetzt)
            except Exception as e:  # noqa: BLE001 – ein Thema darf fehlen
                fehler.append('%s: %s' % (tid, e))
                ms = []
            ms.sort(key=lambda x: x['zeit'], reverse=True)
            ms.sort(key=lambda x: englisch(x['titel']))   # deutsche Meldungen zuerst (stabil: innerhalb nach Zeit)
            auswahl = []
            for x in ms:
                k = schluessel(x['titel'])
                if k in gesehen:
                    continue
                gesehen.add(k)
                auswahl.append(x)
                if len(auswahl) >= JE_THEMA:
                    break
            gesamt += len(auswahl)
            liste.append({'id': tid, 'name': tname, 'maerkte': maerkte, 'meldungen': auswahl})
            if not ordner:
                time.sleep(1.5)
        gruppen.append({'id': gid, 'name': gname, 'themen': liste})
    for f in fehler:
        print('Fehler', f)
    if gesamt < 8:
        raise SystemExit('Nur %d Schlagzeilen – alte Datei bleibt.' % gesamt)
    neu = {
        'stand': jetzt.astimezone(BERLIN).isoformat(timespec='seconds'),
        'quelle': 'Google News',
        'hinweis': 'Schlagzeilen der letzten 48 Stunden aus Google News (deutsch) je Markt – nur Überschrift, Quelle und Link. '
                   'Wird werktags alle 2 Stunden automatisch aktualisiert.',
        'gruppen': gruppen,
    }
    try:
        alt = json.load(open(ziel, encoding='utf-8'))
        if alt.get('gruppen') == neu['gruppen']:
            print('Schlagzeilen unverändert (%d).' % gesamt)
            return
    except (OSError, ValueError):
        pass
    with open(ziel, 'w', encoding='utf-8') as f:
        json.dump(neu, f, ensure_ascii=False, indent=1)
        f.write('\n')
    print('%d Schlagzeilen geschrieben.' % gesamt)


if __name__ == '__main__':
    main()

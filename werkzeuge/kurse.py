#!/usr/bin/env python3
"""Kursarchiv für den Backtest und „Mein Chart“ in Enricos Trading-Cockpit.

Stundenkerzen ab 2015 für Gold, Silber, Öl (WTI), S&P 500, Nasdaq 100 und Dow Jones aus dem frei zugänglichen
Historien-Datenfeed von Dukascopy (Bid-Kurse, Zeiten in UTC) und für Bitcoin von Coinbase (BTC-USD, ab Juli 2015).
4 Std, Tag, Woche und Monat baut das Cockpit selbst aus den Stunden (Tag = Handelstag bis 17 Uhr New York).

Ablage auf der Website (Branch gh-pages):
  kurse/index.json                      Übersicht: je Markt Quelle, Nachkommastellen, von/bis, Dateiliste
  kurse/<MARKT>/<JJJJ>.json             abgeschlossene Jahre
  kurse/<MARKT>/<JJJJ-MM>.json          Monate des laufenden Jahres (der laufende Monat bis gestern)
Dateiformat (kompakt, ganze Zahlen in 1/10^nk): t0 = erste Zeit (Unix-Sek.), T = Stunden seit der vorigen Kerze,
O = Eröffnung − voriger Schluss (erste: Eröffnung), C = Schluss − Eröffnung, H = Hoch − max(O, C), L = min(O, C) − Tief.

Aufruf:  python3 kurse.py ZIELORDNER [--nur GOLD,SILBER] [--minuten 100] [--bis-jahr 2015]
         python3 kurse.py ZIELORDNER --nur-index        (nur index.json neu schreiben)
Jeder Lauf holt nur, was fehlt; nach --minuten hört er sauber auf (der nächste Lauf macht weiter).
"""
import datetime
import json
import lzma
import os
import struct
import sys
import time
import urllib.error
import urllib.request

UTC = datetime.timezone.utc
UA = 'trading-cockpit-kurse/1.0 (privates Cockpit, wenige Abrufe am Tag; https://github.com/Enrico2608/trading-cockpit)'
DUKA = 'https://datafeed.dukascopy.com/datafeed/'
START = datetime.date(2015, 1, 1)
MAERKTE = {
    'GOLD': {'duka': 'XAUUSD', 'faktor': 1000, 'nk': 2, 'name': 'Dukascopy XAU/USD (Spot, Bid)'},
    'SILBER': {'duka': 'XAGUSD', 'faktor': 1000, 'nk': 3, 'name': 'Dukascopy XAG/USD (Spot, Bid)'},
    'USOIL': {'duka': 'LIGHTCMDUSD', 'faktor': 1000, 'nk': 2, 'name': 'Dukascopy WTI Light Crude (CFD, Bid)'},
    'SP500': {'duka': 'USA500IDXUSD', 'faktor': 1000, 'nk': 1, 'name': 'Dukascopy S&P 500 (CFD, Bid)'},
    'NASDAQ': {'duka': 'USATECHIDXUSD', 'faktor': 1000, 'nk': 1, 'name': 'Dukascopy Nasdaq 100 (CFD, Bid)'},
    'DOW': {'duka': 'USA30IDXUSD', 'faktor': 1000, 'nk': 1, 'name': 'Dukascopy Dow Jones (CFD, Bid)'},
    'BTC': {'coinbase': 'BTC-USD', 'nk': 2, 'name': 'Coinbase BTC-USD', 'start': datetime.date(2015, 7, 20)},
}


class Stopp(Exception):
    pass


ENDE = [None]


ABSTAND = {'datafeed.dukascopy.com': float(os.environ.get('KURSE_ABSTAND', '8')), 'api.exchange.coinbase.com': 0.4}
ZULETZT = {}
STATISTIK = {'ok': 0, 'wiederholt': 0}


def hole(url, versuche=6):
    """Höflich abrufen: je Server fester Abstand zwischen Abrufen, bei 429/503/Abbruch lange Pausen."""
    server = url.split('/')[2]
    pause = 45
    for v in range(versuche):
        if ENDE[0] and time.time() > ENDE[0]:
            raise Stopp()
        warte = ABSTAND.get(server, 1) - (time.time() - ZULETZT.get(server, 0))
        if warte > 0:
            time.sleep(warte)
        ZULETZT[server] = time.time()
        try:
            req = urllib.request.Request(url, headers={'User-Agent': UA})
            with urllib.request.urlopen(req, timeout=45) as r:
                daten = r.read()
            STATISTIK['ok'] += 1
            return daten
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if e.code not in (429, 500, 502, 503, 504):
                raise
            grund = 'HTTP %d' % e.code
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as e:
            grund = type(e).__name__
        STATISTIK['wiederholt'] += 1
        print('    %s: %s – Pause %d s (%s)' % (time.strftime('%H:%M:%S'), grund, pause, url.split('/datafeed/')[-1][:60]), flush=True)
        time.sleep(pause)
        pause = min(pause * 2, 300)
    raise RuntimeError('nicht erreichbar: ' + url)


def bi5(daten, basis, faktor):
    """Dukascopy-Kerzendatei (LZMA, je 24 Bytes: Sek., Eröffnung, Schluss, Tief, Hoch, Volumen) → Kerzen mit Umsatz."""
    if not daten:
        return []
    roh = lzma.decompress(daten)
    out = []
    for i in range(0, len(roh) - 23, 24):
        sek, o, c, l, h, vol = struct.unpack('>IIIIIf', roh[i:i + 24])
        if vol <= 0:
            continue                     # geschlossene Stunden (Wochenende, Feiertage) liefert Dukascopy als flache Kerzen ohne Umsatz
        out.append((basis + sek, o / faktor, h / faktor, l / faktor, c / faktor))
    return out


def stunden(minuten):
    out, akt = [], None
    for t, o, h, l, c in minuten:
        s = t - t % 3600
        if akt and akt[0] == s:
            akt[2] = max(akt[2], h); akt[3] = min(akt[3], l); akt[4] = c
        else:
            akt = [s, o, h, l, c]
            out.append(akt)
    return [tuple(x) for x in out]


def duka_monat(sym, faktor, j, m):
    basis = int(datetime.datetime(j, m, 1, tzinfo=UTC).timestamp())
    return bi5(hole('%s%s/%04d/%02d/BID_candles_hour_1.bi5' % (DUKA, sym, j, m - 1)), basis, faktor)


def duka_tag(sym, faktor, d):
    basis = int(datetime.datetime(d.year, d.month, d.day, tzinfo=UTC).timestamp())
    return stunden(bi5(hole('%s%s/%04d/%02d/%02d/BID_candles_min_1.bi5' % (DUKA, sym, d.year, d.month - 1, d.day)), basis, faktor))


def coinbase(produkt, ab, bis):
    """Stundenkerzen [ab, bis) in Blöcken zu 300."""
    out, t = [], ab
    while t < bis:
        e = min(t + 300 * 3600, bis)
        url = 'https://api.exchange.coinbase.com/products/%s/candles?granularity=3600&start=%s&end=%s' % (
            produkt, datetime.datetime.fromtimestamp(t, UTC).strftime('%Y-%m-%dT%H:%M:%SZ'), datetime.datetime.fromtimestamp(e - 1, UTC).strftime('%Y-%m-%dT%H:%M:%SZ'))
        j = json.loads(hole(url) or b'[]')
        for r in j:
            tt, lo, hi, op, cl, vol = r[:6]
            if ab <= tt < bis and op > 0 and lo > 0 and hi >= lo:
                out.append((int(tt), float(op), float(hi), float(lo), float(cl)))
        t = e
    out.sort()
    return [k for i, k in enumerate(out) if i == 0 or k[0] != out[i - 1][0]]


# ---------------------------------------------------------------- Dateien
def kodieren(key, nk, kerzen):
    f = 10 ** nk
    T, O, H, L, C = [], [], [], [], []
    vt, vc = None, 0
    for t, o, h, l, c in kerzen:
        oi, hi, li, ci = round(o * f), round(h * f), round(l * f), round(c * f)
        hi, li = max(hi, oi, ci), min(li, oi, ci)
        T.append(0 if vt is None else (t - vt) // 3600)
        O.append(oi - vc); C.append(ci - oi); H.append(hi - max(oi, ci)); L.append(min(oi, ci) - li)
        vt, vc = t, ci
    return {'k': key, 'nk': nk, 't0': kerzen[0][0] if kerzen else None, 'T': T, 'O': O, 'H': H, 'L': L, 'C': C}


def dekodieren(d):
    f = 10 ** d['nk']
    out, t, vc = [], d['t0'], 0
    for i in range(len(d['T'])):
        t += d['T'][i] * 3600
        o = vc + d['O'][i]; c = o + d['C'][i]; h = max(o, c) + d['H'][i]; l = min(o, c) - d['L'][i]
        out.append((t, o / f, h / f, l / f, c / f))
        vc = c
    return out


def schreiben(pfad, key, nk, kerzen):
    os.makedirs(os.path.dirname(pfad), exist_ok=True)
    with open(pfad, 'w') as f:
        json.dump(kodieren(key, nk, kerzen), f, separators=(',', ':'))


def lesen(pfad):
    try:
        return dekodieren(json.load(open(pfad)))
    except (OSError, ValueError, KeyError):
        return None


def monate(von, bis):
    j, m = von.year, von.month
    while (j, m) <= (bis.year, bis.month):
        yield j, m
        j, m = (j + 1, 1) if m == 12 else (j, m + 1)


def ts(j, m, t):
    return int(datetime.datetime(j, m, t, tzinfo=UTC).timestamp())


def monat_vollstaendig(k, j, m):
    return bool(k) and k[-1][0] >= ts(j + (m == 12), m % 12 + 1, 1) - 4 * 86400   # letzte Kerze in den letzten Tagen des Monats


def monat_daten(key, cfg, ordner, j, m, gestern):
    """(Kerzen, neu_geholt) eines Monats bis gestern – eine vorhandene Monatsdatei wird nur fortgesetzt."""
    mp = os.path.join(ordner, '%04d-%02d.json' % (j, m))
    alt = lesen(mp) or []
    laufend = (j, m) == (gestern.year, gestern.month)
    if alt and not laufend and monat_vollstaendig(alt, j, m):
        return alt, False
    k = monat_holen(key, cfg, j, m, gestern, alt)
    return (k or []), (k or []) != alt


def markt_aktualisieren(ziel, key, cfg, heute, bis_jahr):
    """Fehlende Monate holen. True, wenn etwas neu geschrieben wurde."""
    ordner = os.path.join(ziel, key)
    os.makedirs(ordner, exist_ok=True)
    start = cfg.get('start', START)
    gestern = heute - datetime.timedelta(days=1)
    neu = False
    for j in range(start.year, min(gestern.year, bis_jahr) + 1):
        erste = max(start, datetime.date(j, 1, 1))
        if j < gestern.year:                         # abgeschlossenes Jahr → eine Jahresdatei
            jahr_pfad = os.path.join(ordner, '%d.json' % j)
            if os.path.exists(jahr_pfad):
                continue
            alle = []
            for (jj, m) in monate(erste, datetime.date(j, 12, 1)):
                k, geholt = monat_daten(key, cfg, ordner, jj, m, gestern)
                if geholt and k:                         # Zwischenstand, falls die Zeit vor dem Jahresende abläuft
                    schreiben(os.path.join(ordner, '%04d-%02d.json' % (jj, m)), key, cfg['nk'], k)
                    neu = True
                alle.extend(k)
            if alle:
                schreiben(jahr_pfad, key, cfg['nk'], alle)
                neu = True
                print('  %s %d: %d Stundenkerzen' % (key, j, len(alle)), flush=True)
            for m in range(1, 13):
                mp = os.path.join(ordner, '%04d-%02d.json' % (j, m))
                if os.path.exists(mp):
                    os.remove(mp)
            continue
        for (jj, m) in monate(erste, datetime.date(j, gestern.month, 1)):   # laufendes Jahr → Monatsdateien
            k, geholt = monat_daten(key, cfg, ordner, jj, m, gestern)
            if geholt and k:
                schreiben(os.path.join(ordner, '%04d-%02d.json' % (jj, m)), key, cfg['nk'], k)
                neu = True
    return neu


def monat_holen(key, cfg, j, m, gestern, alt=None):
    """Kerzen eines Monats bis einschließlich gestern (UTC); alt = schon vorhandene Kerzen dieses Monats."""
    anfang = datetime.date(j, m, 1)
    if anfang > gestern:
        return None
    ende = datetime.date(j + (m == 12), m % 12 + 1, 1) - datetime.timedelta(days=1)
    bis = min(ende, gestern)
    if 'coinbase' in cfg:
        ab = max(ts(j, m, 1), int(datetime.datetime.combine(cfg.get('start', START), datetime.time(), UTC).timestamp()))
        if alt:
            ab = max(ab, alt[-1][0] - 3 * 3600)
        neu = coinbase(cfg['coinbase'], ab, ts(bis.year, bis.month, bis.day) + 86400)
        return sorted({k[0]: k for k in list(alt or []) + neu}.values())
    sym, faktor = cfg['duka'], cfg['faktor']
    if ende <= gestern and not alt:
        k = duka_monat(sym, faktor, j, m)
        if k:
            return k
    # laufender Monat (oder Monatsdatei noch nicht veröffentlicht): Tag für Tag aus den Minutenkerzen
    k, tag = list(alt or []), anfang
    if k:
        tag = max(anfang, datetime.datetime.fromtimestamp(k[-1][0], UTC).date())   # letzten Tag noch einmal (evtl. unvollständig)
        k = [x for x in k if x[0] < ts(tag.year, tag.month, tag.day)]
    while tag <= bis:
        if tag.weekday() != 5:                       # samstags handelt keiner dieser Märkte
            k.extend(duka_tag(sym, faktor, tag))
        tag += datetime.timedelta(days=1)
    return k


def index_schreiben(ziel):
    idx = {'stand': datetime.datetime.now(UTC).isoformat(timespec='seconds'), 'quelle_url': {'Dukascopy': 'https://www.dukascopy.com/swiss/english/marketwatch/historical/', 'Coinbase': 'https://www.coinbase.com/'},
           'maerkte': {}}
    for key, cfg in MAERKTE.items():
        ordner = os.path.join(ziel, key)
        if not os.path.isdir(ordner):
            continue
        dateien = sorted(f[:-5] for f in os.listdir(ordner) if f.endswith('.json'))
        if not dateien:
            continue
        erste, letzte = lesen(os.path.join(ordner, dateien[0] + '.json')), lesen(os.path.join(ordner, dateien[-1] + '.json'))
        if not erste or not letzte:
            continue
        idx['maerkte'][key] = {'quelle': cfg['name'], 'nk': cfg['nk'], 'von': erste[0][0], 'bis': letzte[-1][0], 'dateien': dateien}
    try:
        alt = json.load(open(os.path.join(ziel, 'index.json')))
        if alt.get('maerkte') == idx['maerkte']:
            return alt                   # nichts Neues: Stand bleibt, kein Commit
    except (OSError, ValueError):
        pass
    with open(os.path.join(ziel, 'index.json'), 'w') as f:
        json.dump(idx, f, ensure_ascii=False, indent=1)
    return idx


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    ziel = sys.argv[1]
    arg = lambda n, d=None: sys.argv[sys.argv.index(n) + 1] if n in sys.argv else d
    if '--nur-index' in sys.argv:                    # nur kurse/index.json aus den vorhandenen Dateien neu schreiben
        idx = index_schreiben(ziel)
        print('Index: ' + ', '.join(sorted(idx['maerkte'])))
        return
    nur = arg('--nur')
    ENDE[0] = time.time() + 60 * float(arg('--minuten', '100'))
    bis_jahr = int(arg('--bis-jahr', '9999'))
    heute = datetime.datetime.now(UTC).date()
    os.makedirs(ziel, exist_ok=True)
    geaendert = False
    for key, cfg in MAERKTE.items():
        if nur and key not in nur.split(','):
            continue
        try:
            t0 = time.time()
            n = markt_aktualisieren(ziel, key, cfg, heute, bis_jahr)
            geaendert = geaendert or n
            print('%s: %s (%.0f s)' % (key, 'neu' if n else 'aktuell', time.time() - t0), flush=True)
        except Stopp:
            print('%s: Zeit um – der nächste Lauf macht weiter.' % key, flush=True)
            break
        except Exception as e:  # noqa: BLE001 – andere Märkte trotzdem
            print('%s: Fehler %r' % (key, e), flush=True)
    print('Abrufe: %(ok)d ok, %(wiederholt)d Wiederholungen' % STATISTIK, flush=True)
    idx = index_schreiben(ziel)
    for key, m in idx['maerkte'].items():
        print('  %-7s %s bis %s, %d Dateien' % (key, datetime.datetime.fromtimestamp(m['von'], UTC).date(), datetime.datetime.fromtimestamp(m['bis'], UTC), len(m['dateien'])))


if __name__ == '__main__':
    main()

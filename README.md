# trading-cockpit
Die Website liegt (verschlüsselt) im Branch `gh-pages`.

`werkzeuge/termine.py` holt jeden Morgen per GitHub Actions (`.github/workflows/termine.yml`) die wichtigen
Wirtschaftstermine (Wichtigkeit hoch und mittel; USA, Eurozone, Deutschland, weltweit) aus den Kalendern von
[Tradays](https://www.tradays.com/de/economic-calendar) (laufende Woche + 6 Wochen) und
[ForexFactory](https://www.forexfactory.com/calendar) (laufende Woche) und legt sie als `termine.json`
auf die Website. Das Cockpit lädt die Datei beim Öffnen und zeigt die Termine mit Quelle an.

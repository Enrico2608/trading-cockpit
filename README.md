# trading-cockpit
Die Website liegt (verschlüsselt) im Branch `gh-pages`.

`werkzeuge/termine.py` holt jeden Morgen per GitHub Actions (`.github/workflows/termine.yml`) die wichtigen
Wirtschaftstermine (Wichtigkeit hoch und mittel; USA, Eurozone, Deutschland, weltweit) aus dem
[Tradays-Wirtschaftskalender](https://www.tradays.com/de/economic-calendar) und legt sie als `termine.json`
auf die Website. Das Cockpit lädt die Datei beim Öffnen und zeigt die Termine mit Quelle an.

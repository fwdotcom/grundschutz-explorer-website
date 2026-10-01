# Release-Schritte

Bereitet ein Release der Projektwebsite vor: Version prüfen, Changelog abschließen, `security.txt` erneuern und
Screenshots der App aufnehmen. Committet, getaggt und veröffentlicht wird nicht; das bleibt Handarbeit.

Die Schritte sind dieselben wie im App-Repo (`scripts/release/` im Grundschutz++ Explorer) und dort ausführlich
beschrieben. Übernommen sind nur die allgemeinen Teile; alles Projektspezifische steht in `release.toml` und
`project/`.

```
release.py        Runner: führt die Schritte aus steps/ der Reihe nach aus
release.toml      Projektkonfiguration, ein Abschnitt je Schritt
steps/            die Schritte, je eine Datei NN-name.py
lib/              gemeinsame Bausteine
project/          Projektspezifisches: Screenshot-Szenen und Testdaten
```

## Aufruf

Voraussetzung ist Python ab 3.11. Für die Screenshots zusätzlich einmalig:

```sh
pip install -r scripts/release/requirements.txt
python -m playwright install chromium
```

Release vorbereiten:

```sh
python scripts/release/release.py 1.1.0
python scripts/release/release.py 1.1.0 --skip screenshots   # ohne neue Screenshots
python scripts/release/release.py --list
```

Danach die Änderungen prüfen (`git status`, `git diff`), committen und das Release `v<VERSION>` auf GitHub
veröffentlichen; der Workflow `deploy.yml` deployt die Seite über GitHub Pages.

### Nur Screenshots erneuern

```sh
python scripts/release/release.py --only screenshots
```

Ohne Version laufen nur die gewählten Schritte; Changelog und `security.txt` bleiben unverändert. Die neuen Bilder
unter `www/media/screens/` committen und pushen. Ein Push deployt nicht: die Bilder gehen mit dem nächsten Release
online, oder sofort über den Workflow **Deploy** → „Run workflow“ (deployt den Stand des gewählten Branches,
also auch alle anderen Änderungen darauf).

## Die Schritte

| Schritt           | Zweck                                                                             |
| ----------------- | --------------------------------------------------------------------------------- |
| `10-version`      | Format der Version prüfen (sie steht nur im Changelog, `files` ist deshalb leer)  |
| `20-changelog`    | Abschnitt „Unveröffentlicht“ abschließen; eine ältere Version wird abgelehnt      |
| `30-security-txt` | `Expires` in `www/.well-known/security.txt` auf heute + 1 Jahr setzen             |
| `40-screenshots`  | Screenshots der App nach `www/media/screens/manifest.json` aufnehmen              |

Wie im App-Repo arbeitet `release.py` die Dateien `steps/NN-name.py` in Nummernfolge ab (wie `run-parts` unter
Linux). Ein Schritt lässt sich einzeln aufrufen, abschalten (umbenennen, z. B. in `.py.off`) oder ergänzen; seine
Parameter liest er aus dem gleichnamigen Abschnitt von `release.toml`. Die Einzelheiten stehen jeweils am Anfang
der Datei.

Ändert sich ein Schritt im App-Repo, die Datei hierher übernehmen; `lib/` und `steps/` sollen in beiden Repos
gleich bleiben.

## Screenshots

Aufgenommen wird die veröffentlichte App unter `https://app.grundschutz-explorer.de/` (`url` in `[screenshots]`);
die Bilder zeigen also die App-Version, die gerade online ist. Das App-Repo wird nicht gebraucht. Eine App-Änderung
vor ihrem Deployment lässt sich aufnehmen, indem man die App lokal ausliefert und die Adresse übergibt, z. B.:

```sh
python -m http.server 8000 -d ../gsexplorer/src
RELEASE_SCREENSHOTS_URL=http://localhost:8000/ python scripts/release/release.py --only screenshots
```

Die Testdaten liegen in `project/`: der Anwenderkatalog in `project/testdaten/` und `project/testdata.py`, beides
Kopien aus dem App-Repo (Stand des Katalogs: 10.09.2026, bewusst fest, damit die Bilder gleich bleiben).

Welche Bilder die Website braucht, legt `www/media/screens/manifest.json` fest:

```json
{
  "schema": 1,
  "shots": [{ "file": "oberflaeche.webp", "scene": "website-oberflaeche", "width": 1920, "height": 1200 }]
}
```

- `file`: Dateiname unter `www/media/screens/` (Kleinbuchstaben, Ziffern, Bindestriche, `.webp` oder `.png`)
- `scene`: Szene aus `project/scenes.py`; verfügbar sind `website-oberflaeche`, `website-filter-zielobjekte`,
  `website-detail-notizen`, `website-detail-aenderungen` und `website-kataloge-laden`
- `width`, `height`: Bildmaße in Pixeln, wie sie in `www/index.html` an den `<img>` stehen. Passt ein Bild nicht
  dazu, bricht der Schritt ab, ohne etwas zu schreiben.

Die Szenen nutzen Speicherstruktur, Einstellungen und CSS-Selektoren der App; ändern sich diese, müssen sie in
`project/scenes.py` angepasst werden. `HEADED=1` zeigt den Browser beim Aufnehmen.

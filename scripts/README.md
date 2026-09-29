# Skripte

## Release vorbereiten

`release.py` bereitet ein Release der Projektwebseite vor:

1. Version eintragen: In `CHANGELOG.md` wird `## [Unveröffentlicht]` zu `## [<VERSION>] – <Datum>`. Das
   Changelog ist maßgeblich für die aktuelle Version. Außerdem wird `version` in `scripts/package.json` gesetzt.
2. `Expires` in `www/.well-known/security.txt` auf heute + 1 Jahr setzen.
3. Screenshots neu aufnehmen (siehe unten); fehlt `node_modules`, wird vorher `npm install` ausgeführt.

```sh
python scripts/release.py 1.1.0
python scripts/release.py 1.1.0 --keine-screenshots
```

Committet, getaggt und veröffentlicht wird nicht. Danach die Änderungen prüfen, committen und das Release
`v<VERSION>` auf GitHub veröffentlichen; der Workflow `release.yml` deployt die Seite über GitHub Pages.

## Screenshots der App

`capture-screenshots.mjs` erzeugt die Screenshots in `www/media/screens/` aus der laufenden App
([app.grundschutz-explorer.de](https://app.grundschutz-explorer.de)).

```sh
cd scripts
npm install                         # Playwright, sharp und Chromium
npm run screenshots                 # alle Screenshots
npm run screenshots -- oberflaeche  # nur einzelne (Namen ohne .webp)
```

Verfügbare Screenshots: `oberflaeche`, `filter-zielobjekte`, `detail-notizen`, `detail-aenderungen`,
`kataloge-laden`.

### Ablauf

1. Der aktuelle Grundschutz++-Anwenderkatalog wird aus der
   [Stand-der-Technik-Bibliothek](https://github.com/BSI-Bund/Stand-der-Technik-Bibliothek) des BSI geladen.
   Daraus entsteht zusätzlich ein älterer Stand, in dem DEV.4.3 noch MUSS ist und einen anderen Text hat
   (für den Reiter „Änderungen“).
2. Für jeden Screenshot startet ein frischer Browserkontext. Katalog, Listen („Audit 2026“, „Entwicklungsteam“),
   Notizen und Ansichtszustand (Filter, aufgeklappte Äste, Auswahl) werden direkt in die IndexedDB der App
   geschrieben, danach wird die Seite neu geladen.
3. Der Ausschnitt wird aufgenommen und als WebP gespeichert.
4. Die Bildmaße werden in `www/index.html` (`width`/`height` der `<img>`) nachgetragen.

### Umgebungsvariablen

| Variable  | Bedeutung                                                            |
| --------- | -------------------------------------------------------------------- |
| `APP_URL` | Adresse der App (Standard: `https://app.grundschutz-explorer.de/`)   |
| `HEADED`  | `1` startet den Browser sichtbar, zum Nachvollziehen                 |

### Hinweise

- Das Skript nutzt die Speicherstruktur (`js/storage.js`, Einstellungsschlüssel) und CSS-Selektoren der App.
  Ändern sich diese, muss es angepasst werden.

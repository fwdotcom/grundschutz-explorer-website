# Release-Schritte

Bereitet ein Release der Projektwebsite vor: Version prüfen, Changelog abschließen und `security.txt` erneuern.
Committet, getaggt und veröffentlicht wird nicht; das bleibt Handarbeit.

Die Schritte sind dieselben wie im App-Repo (`scripts/release/` im Grundschutz++ Explorer) und dort ausführlich
beschrieben. Übernommen sind nur die allgemeinen Teile; alles Projektspezifische steht in `release.toml`.

```
release.py        Runner: führt die Schritte aus steps/ der Reihe nach aus
release.toml      Projektkonfiguration, ein Abschnitt je Schritt
steps/            die Schritte, je eine Datei NN-name.py
lib/              gemeinsame Bausteine
```

## Aufruf

Voraussetzung ist Python ab 3.11; weitere Pakete braucht es nicht.

```sh
python scripts/release/release.py 1.1.0
python scripts/release/release.py --list
```

Danach die Änderungen prüfen (`git status`, `git diff`), committen und das Release `v<VERSION>` auf GitHub
veröffentlichen; der Workflow `release.yml` deployt die Seite über GitHub Pages.

## Die Schritte

| Schritt           | Zweck                                                                             |
| ----------------- | --------------------------------------------------------------------------------- |
| `10-version`      | Format der Version prüfen (sie steht nur im Changelog, `files` ist deshalb leer)  |
| `20-changelog`    | Abschnitt „Unveröffentlicht“ abschließen; eine ältere Version wird abgelehnt      |
| `30-security-txt` | `Expires` in `www/.well-known/security.txt` auf heute + 1 Jahr setzen             |

Wie im App-Repo arbeitet `release.py` die Dateien `steps/NN-name.py` in Nummernfolge ab (wie `run-parts` unter
Linux). Ein Schritt lässt sich einzeln aufrufen, abschalten (umbenennen, z. B. in `.py.off`) oder ergänzen; seine
Parameter liest er aus dem gleichnamigen Abschnitt von `release.toml`. Die Einzelheiten stehen jeweils am Anfang
der Datei.

Ändert sich ein Schritt im App-Repo, die Datei hierher übernehmen; `lib/` und `steps/` sollen in beiden Repos
gleich bleiben.

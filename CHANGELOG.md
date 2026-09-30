# Changelog

Alle nennenswerten Änderungen an der Projektwebseite des Grundschutz++ Explorers.

## [1.0.5] – 2026-09-30

- Umstellung auf modulares Release-Script

### Geändert

- Die Screenshots erzeugt jetzt das Release der App; die Seite lädt sie von app.grundschutz-explorer.de/media/website/, welche Bilder sie braucht, legt `www/media/screens/manifest.json` fest.

### Entfernt

- Skript `scripts/capture-screenshots.mjs` und die Screenshots unter `www/media/screens/`.

## [1.0.4] – 2026-09-30

### Geändert

- Screenshots für App-Version 1.1.9 geändert.

## [1.0.3] – 2026-09-29

### Geändert

- Screenshots für App-Version 1.1.8 geändert.

## [1.0.2] – 2026-09-29

### Neu

- Skript `scripts/capture-screenshots.mjs` erzeugt die Screenshots der App automatisch aus app.grundschutz-explorer.de mit dem aktuellen BSI-Katalog und festen Beispieldaten; die Bildmaße in der Startseite werden dabei nachgetragen.
- Skript `scripts/release.py` bereitet ein Release vor: Version in Changelog und `scripts/package.json` setzen, `security.txt` erneuern, Screenshots neu aufnehmen.
- Beschreibung der Skripte in `scripts/README.md`.

### Geändert

- Screenshots mit der aktuellen App-Version neu aufgenommen, in höherer Auflösung.

### Entfernt

- Ungenutzter Screenshot `listen-markierungen.webp`.

## [1.0.1] – 2026-09-29

### Geändert

- Handbuch-Links (jetzt app.grundschutz-explorer.de/manual) aktualisiert

## [1.0.0] – 2026-09-29

### Neu

- Erste Fassung der Projektwebseite unter www.grundschutz-explorer.de; die App ist nach app.grundschutz-explorer.de umgezogen.
- Startseite mit Einstieg, Kennzahlen, Funktionen, Einblicken in die Arbeit mit der App (Suchen und Filtern, Listen und Notizen, Versionsvergleich, Kataloge), Datenschutz und Zielgruppen.
- Screenshots der App mit Bildbetrachter zum Vergrößern.
- Impressum, Datenschutzerklärung und Lizenzhinweise (MIT, Open Sans, Lucide, BSI-Katalogdaten) als Dialog, direkt aufrufbar über `/#impressum`, `/#datenschutzerklaerung` und `/#lizenzen`; ohne JavaScript als Abschnitte am Seitenende.
- Helles und dunkles Design nach Systemeinstellung, umschaltbar in der Kopfzeile.
- Eigene Fehlerseite (404).
- Keine Cookies, kein Tracking, keine Inhalte von fremden Servern; strenge Content Security Policy.

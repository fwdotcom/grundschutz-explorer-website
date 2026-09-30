# Skripte

## Release vorbereiten

```sh
python scripts/release/release.py 1.1.0
```

Prüft die Version, schließt den Abschnitt „Unveröffentlicht“ im Changelog ab, setzt `Expires` in
`www/.well-known/security.txt` auf heute + 1 Jahr und nimmt die Screenshots neu auf. Committet, getaggt und
veröffentlicht wird nicht. Einzelheiten: [release/README.md](release/README.md).

## Screenshots der App

```sh
python scripts/release/release.py --only screenshots
```

Nimmt die Screenshots unter `www/media/screens/` neu auf, ohne Version, Changelog oder `security.txt` anzufassen.
Voraussetzungen, Manifest und Szenen: [release/README.md](release/README.md#screenshots).

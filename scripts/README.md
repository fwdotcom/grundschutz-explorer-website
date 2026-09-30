# Skripte

## Release vorbereiten

```sh
python scripts/release/release.py 1.1.0
```

Prüft die Version, schließt den Abschnitt „Unveröffentlicht“ im Changelog ab und setzt `Expires` in
`www/.well-known/security.txt` auf heute + 1 Jahr. Committet, getaggt und veröffentlicht wird nicht. Einzelheiten:
[release/README.md](release/README.md).

## Screenshots der App

Die Screenshots erzeugt das Release der App (Schritt `scripts/release/steps/50-screenshots.py` mit den Szenen
aus `scripts/release/project/scenes.py` im App-Repo). Sie liegen unter
`https://app.grundschutz-explorer.de/media/website/` und werden von dort eingebunden; für neue Screenshots muss die
Website deshalb nicht neu deployt werden.

Welche Bilder die Website braucht, legt sie in `www/media/screens/manifest.json` fest:

```json
{
  "schema": 1,
  "shots": [{ "file": "oberflaeche.webp", "scene": "website-oberflaeche", "width": 1920, "height": 1200 }]
}
```

- `file`: Dateiname unter `media/website/` (Kleinbuchstaben, Ziffern, Bindestriche, `.webp`)
- `scene`: Ansicht der App; verfügbar sind `website-oberflaeche`, `website-filter-zielobjekte`,
  `website-detail-notizen`, `website-detail-aenderungen` und `website-kataloge-laden`. Eine neue Ansicht muss im
  App-Repo als Szene ergänzt werden.
- `width`, `height`: Bildmaße in Pixeln, wie sie in `www/index.html` an den `<img>` stehen. Passt ein Bild nicht
  dazu, bricht das Release der App ab.

Das App-Release liest das Manifest von der veröffentlichten Website. Eine Änderung am Manifest wirkt also erst,
wenn die Website deployt ist und danach die App ein Release macht. Zum Testen vorher lässt sich das lokale
Manifest im App-Repo mit `RELEASE_SCREENSHOTS_WEBSITE_MANIFEST=<Pfad>` angeben.

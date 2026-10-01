#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Frank Winter
# SPDX-License-Identifier: MIT
"""
Nimmt Screenshots nach Manifesten auf. Allgemein verwendbar; die Szenen liefert das Projekt.

Jeder Auftrag verbindet ein Manifest (was aufgenommen wird) mit einem Zielordner (wohin). Das Manifest kann im
Projekt liegen oder von außen kommen, z. B. von der Projektwebsite:

  { "schema": 1, "shots": [ { "file": "oberflaeche.webp", "scene": "oberflaeche", "width": 1920, "height": 1200 } ] }

  file    Dateiname im Zielordner: Kleinbuchstaben, Ziffern, Bindestriche; .png oder .webp bestimmt das Format
  scene   Name einer Szene aus dem Szenen-Modul des Projekts
  width, height  optional (nur zusammen): erwartete Bildmaße; weicht ein Bild ab, bricht der Schritt ab, ohne
          etwas zu schreiben

Das Manifest wird streng geprüft. Neben die Bilder legt der Schritt eine Kopie des Manifests (manifest.json).
Bilder aus der vorigen Kopie, die im neuen Manifest fehlen, werden entfernt; andere Dateien bleiben unberührt.
Liegt das Manifest selbst als manifest.json im Zielordner (z. B. im Projekt), entfällt die Kopie; Bilder ohne
Eintrag werden dann nur gemeldet.

Szenen-Modul (Python-Datei): SCENES = {name: funktion(env) -> PNG-Bytes}, optional setup(step) -> Daten.
env hat browser (Playwright), base_url (Startseite auf dem lokalen Server), data (Ergebnis von setup) und step.

Konfiguration [screenshots]:
  scenes   Szenen-Modul, relativ zu release.toml
  serve    Ordner, den der lokale Server ausliefert (Standard: ".")
  url      statt serve: Adresse einer laufenden Instanz, z. B. der veröffentlichten App; dann kein lokaler Server
  start    Startseite relativ zu serve bzw. url (Standard: "index.html")
  quality  WebP-Qualität (Standard: 90)
  jobs     Liste von {out_dir, manifest, name?}; manifest ist eine URL oder ein Pfad relativ zum Projektordner
  only     optional: nur die Aufträge mit diesen Namen (durch Komma getrennt)

Per Umgebung: RELEASE_SCREENSHOTS_URL=<Adresse>, RELEASE_SCREENSHOTS_ONLY=website,
RELEASE_SCREENSHOTS_<NAME>_MANIFEST=<Pfad>, RELEASE_SCREENSHOTS_<NAME>_OUT_DIR=<Ordner> (NAME = name des Auftrags).

Aufruf:  python scripts/release/steps/40-screenshots.py
"""

from __future__ import annotations

import importlib.util
import json
import re
import sys
import urllib.request
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib.browser import chromium, static_server, webp  # noqa: E402
from lib.common import fail, info, load_step  # noqa: E402

SCHEMA = 1
FILE_RE = re.compile(r"^[a-z0-9][a-z0-9-]*\.(png|webp)$")
MAX_SIDE = 8192
COPY = "manifest.json"


def load_scenes(path: Path):
    if not path.is_file():
        fail(f"Szenen-Modul nicht gefunden: {path}")
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not isinstance(getattr(module, "SCENES", None), dict):
        fail(f"{path.name} definiert kein SCENES")
    return module


def read_manifest(step, source: str) -> str:
    if re.match(r"^https?://", source):
        try:
            with urllib.request.urlopen(source, timeout=30) as res:
                return res.read().decode("utf-8")
        except OSError as err:
            fail(f"Manifest nicht abrufbar ({source}): {err}")
    path = step.path(source)
    if not path.is_file():
        fail(f"Manifest nicht gefunden: {path}")
    return path.read_text(encoding="utf-8")


def parse_manifest(text: str, scenes: dict, source: str) -> list[dict]:
    try:
        manifest = json.loads(text)
    except json.JSONDecodeError as err:
        fail(f"Manifest ist kein gültiges JSON ({source}): {err}")
    if not isinstance(manifest, dict):
        fail(f"Manifest ungültig ({source}): kein JSON-Objekt")
    errors = []
    if manifest.get("schema") != SCHEMA:
        errors.append(f"schema muss {SCHEMA} sein")
    errors += [f"unbekanntes Feld „{key}“" for key in manifest if key not in ("schema", "shots")]
    shots = manifest.get("shots")
    if not isinstance(shots, list) or not shots:
        errors.append("shots muss eine nicht leere Liste sein")
        shots = []
    files = set()
    for i, shot in enumerate(shots):
        where = f"shots[{i}]"
        if not isinstance(shot, dict):
            errors.append(f"{where}: kein Objekt")
            continue
        errors += [f"{where}: unbekanntes Feld „{key}“" for key in shot if key not in ("file", "scene", "width", "height")]
        file = shot.get("file")
        if not isinstance(file, str) or not FILE_RE.match(file):
            errors.append(f"{where}: file muss {FILE_RE.pattern} entsprechen")
        elif file in files:
            errors.append(f"{where}: {file} doppelt")
        else:
            files.add(file)
        if shot.get("scene") not in scenes:
            errors.append(f"{where}: unbekannte Szene „{shot.get('scene')}“")
        dims = [shot.get(d) for d in ("width", "height")]
        if dims != [None, None]:
            for dim, value in zip(("width", "height"), dims):
                if not isinstance(value, int) or isinstance(value, bool) or not 1 <= value <= MAX_SIDE:
                    errors.append(f"{where}: {dim} muss eine ganze Zahl von 1 bis {MAX_SIDE} sein (width und height nur zusammen)")
    if errors:
        fail(f"Manifest ungültig ({source}):\n  " + "\n  ".join(errors))
    return shots


def image_size(png: bytes) -> tuple[int, int]:
    # Breite und Höhe stehen im IHDR-Block direkt nach der PNG-Signatur
    return int.from_bytes(png[16:20], "big"), int.from_bytes(png[20:24], "big")


def previous_files(out_dir: Path) -> set[str]:
    try:
        shots = json.loads((out_dir / COPY).read_text(encoding="utf-8")).get("shots", [])
        return {s["file"] for s in shots if isinstance(s, dict) and isinstance(s.get("file"), str) and FILE_RE.match(s["file"])}
    except (OSError, ValueError, AttributeError):
        return set()


def run_job(step, env, scenes: dict, job: dict, quality: int) -> None:
    name = job.get("name", "")
    key = re.sub(r"\W", "_", name).lower()

    # Überschreibung per RELEASE_SCREENSHOTS_<NAME>_<SCHLÜSSEL>, nur für benannte Aufträge
    def value(field):
        return (step.get(f"{key}_{field}") if name else None) or job.get(field)

    source, out_value = value("manifest"), value("out_dir")
    if not source or not out_value:
        fail(f"Auftrag {name or job}: manifest und out_dir sind nötig")
    out_dir = step.path(out_value)
    print(f"\n  [{name or step.rel(out_dir)}] Manifest: {source}", flush=True)
    # Liegt das Manifest schon als manifest.json im Zielordner, entfällt die Kopie
    in_place = not re.match(r"^https?://", source) and step.path(source) == out_dir / COPY
    text = read_manifest(step, source)
    shots = parse_manifest(text, scenes, source)

    # Erst alle Bilder erzeugen und prüfen, dann schreiben: bei einem Fehler bleibt der Zielordner unverändert
    images, errors = [], []
    for shot in shots:
        png = scenes[shot["scene"]](env)
        if shot["file"].endswith(".webp"):
            data, width, height = webp(png, quality)
        else:
            data, (width, height) = png, image_size(png)
        expected = (shot.get("width"), shot.get("height"))
        ok = expected == (None, None) or expected == (width, height)
        info(f"{shot['file']} ({shot['scene']}): {width}×{height}" + ("" if ok else f"  ≠ Manifest {expected[0]}×{expected[1]}"))
        if not ok:
            errors.append(f"{shot['file']}: {width}×{height} statt {expected[0]}×{expected[1]}")
        images.append((shot["file"], data))
    if errors:
        fail(
            "Bildmaße passen nicht zum Manifest – nichts geschrieben:\n  " + "\n  ".join(errors)
            + "\nSzene anpassen oder Maße im Manifest (und dort, wo die Bilder eingebunden sind) nachziehen."
        )

    out_dir.mkdir(parents=True, exist_ok=True)
    current = {f for f, _ in images}
    if in_place:
        # Ohne Kopie fehlt der vorige Stand: Bilder ohne Eintrag nur melden, nicht löschen
        for old in sorted(p.name for p in out_dir.iterdir() if FILE_RE.match(p.name) and p.name not in current):
            info(f"nicht im Manifest: {old}")
    else:
        for file in previous_files(out_dir) - current:
            (out_dir / file).unlink(missing_ok=True)
            info(f"entfernt: {file}")
    for file, data in images:
        (out_dir / file).write_bytes(data)
    if not in_place:
        (out_dir / COPY).write_text(text if text.endswith("\n") else text + "\n", encoding="utf-8", newline="")
    info(f"{len(images)} Bilder in {step.rel(out_dir)}")


def main() -> None:
    step = load_step(__file__, "Screenshots nach Manifesten aufnehmen.")
    module = load_scenes((step.config_file.parent / step.require("scenes")).resolve())
    quality = int(step.get("quality", 90))
    jobs = step.require("jobs")
    only = {n.strip() for n in str(step.get("only", "")).split(",") if n.strip()}
    if only:
        unknown = only - {job.get("name") for job in jobs}
        if unknown:
            fail(f"unbekannte Aufträge: {', '.join(sorted(unknown))}")
        jobs = [job for job in jobs if job.get("name") in only]

    data = module.setup(step) if hasattr(module, "setup") else None
    url = step.get("url")
    if url and not re.match(r"^https?://", url):
        fail(f"url muss mit http:// oder https:// beginnen: {url}")
    server = nullcontext(url.rstrip("/") + "/") if url else static_server(step.path(step.get("serve", ".")))
    with server as base, chromium() as browser:
        env = SimpleNamespace(browser=browser, base_url=base + step.get("start", "index.html"), data=data, step=step)
        for job in jobs:
            run_job(step, env, module.SCENES, job, quality)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Frank Winter
# SPDX-License-Identifier: MIT
"""
Bereitet ein Release der Projektwebseite vor: setzt die neue Version, erneuert
security.txt und nimmt die Screenshots der App neu auf.

Schritte:
  1. Version eintragen in
       CHANGELOG.md          ("## [Unveröffentlicht]" wird zu "## [<VERSION>] – <Datum>", maßgeblich)
       scripts/package.json  ("version")
  2. www/.well-known/security.txt: Expires auf heute + 1 Jahr setzen (RFC 9116)
  3. Screenshots:  npm run screenshots (im Ordner scripts)

Committet, getaggt und veröffentlicht wird nicht; das bleibt Handarbeit.

Aufruf:  python scripts/release.py 1.1.0
         python scripts/release.py 1.1.0 --keine-screenshots
Voraussetzung:  Python 3.9+, Node.js (für die Screenshots)
"""

from __future__ import annotations

import argparse
import datetime
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
CHANGELOG = ROOT / "CHANGELOG.md"
PACKAGE_JSON = SCRIPTS / "package.json"
SECURITY_TXT = ROOT / "www" / ".well-known" / "security.txt"

VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")
RELEASED_RE = re.compile(r"^## \[(\d+\.\d+\.\d+)\]", re.MULTILINE)
UNRELEASED = "## [Unveröffentlicht]"


def fail(message: str) -> None:
    print(f"Fehler: {message}", file=sys.stderr)
    sys.exit(1)


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


# Zeilenenden der Dateien (LF oder CRLF) bleiben erhalten
def read(path: Path) -> str:
    with path.open(encoding="utf-8", newline="") as f:
        return f.read()


def write(path: Path, text: str) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        f.write(text)


def replace_once(path: Path, pattern: str, replacement: str, what: str = "Versionseintrag") -> None:
    text, count = re.subn(pattern, replacement, read(path), count=1, flags=re.MULTILINE)
    if count != 1:
        fail(f"{what} nicht gefunden in {rel(path)}")
    write(path, text)


def version_key(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in version.split("."))


# Aktuelle Version: höchste veröffentlichte Version im Changelog
def current_version() -> str:
    versions = RELEASED_RE.findall(read(CHANGELOG))
    return max(versions, key=version_key) if versions else "0.0.0"


def update_changelog(version: str) -> None:
    text = read(CHANGELOG)
    if f"## [{version}]" in text:
        print(f"  {rel(CHANGELOG)}: Abschnitt [{version}] besteht bereits")
        return
    if UNRELEASED not in text:
        fail(f'{rel(CHANGELOG)} hat keinen Abschnitt "{UNRELEASED}" mit den Änderungen dieser Version')
    today = datetime.date.today().isoformat()
    write(CHANGELOG, text.replace(UNRELEASED, f"## [{version}] – {today}", 1))
    print(f"  {rel(CHANGELOG)}: [Unveröffentlicht] → [{version}] – {today}")


def set_version(version: str) -> None:
    update_changelog(version)

    replace_once(PACKAGE_JSON, r'^(  "version": ")[^"]*(",)', rf"\g<1>{version}\g<2>")
    json.loads(read(PACKAGE_JSON))  # package.json muss gültig bleiben
    print(f"  {rel(PACKAGE_JSON)}: version {version}")


# Expires ein Jahr ab heute, Mitternacht deutscher Zeit (wie bisher als UTC-Zeitpunkt 22:00 Uhr am Vortag)
def renew_security_txt() -> None:
    today = datetime.date.today()
    try:
        next_year = today.replace(year=today.year + 1)
    except ValueError:  # 29. Februar
        next_year = today.replace(year=today.year + 1, day=28)
    expires = f"{(next_year - datetime.timedelta(days=1)).isoformat()}T22:00:00.000Z"
    replace_once(SECURITY_TXT, r"^(Expires: ).*$", rf"\g<1>{expires}", "Expires")
    print(f"  {rel(SECURITY_TXT)}: Expires {expires}")


def run(*command: str, cwd: Path = ROOT) -> None:
    executable = shutil.which(command[0])
    if not executable:
        fail(f"{command[0]} wurde nicht gefunden")
    print(f"> {' '.join(command)}", flush=True)
    result = subprocess.run([executable, *command[1:]], cwd=cwd)
    if result.returncode != 0:
        fail(f"{' '.join(command)} ist fehlgeschlagen (Exit-Code {result.returncode})")


def main() -> None:
    # Umlaute und Pfeile auch in der Windows-Konsole und bei umgeleiteter Ausgabe
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    sys.stderr.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Neue Version setzen, security.txt erneuern und Screenshots aufnehmen.")
    parser.add_argument("version", help="neue Version, z. B. 1.1.0")
    parser.add_argument("--keine-screenshots", action="store_true", help="Screenshots nicht neu aufnehmen")
    args = parser.parse_args()

    version = args.version.removeprefix("v")
    if not VERSION_RE.match(version):
        fail(f"„{args.version}“ ist keine Version im Format X.Y.Z")

    current = current_version()
    if version_key(version) < version_key(current):
        fail(f"{version} ist älter als die aktuelle Version {current}")

    print(f"\n== 1/3 Version {current} → {version}")
    set_version(version)

    print("\n== 2/3 security.txt")
    renew_security_txt()

    print("\n== 3/3 Screenshots")
    if args.keine_screenshots:
        print("  übersprungen (--keine-screenshots)")
    else:
        if not (SCRIPTS / "node_modules").is_dir():
            run("npm", "install", cwd=SCRIPTS)
        run("npm", "run", "screenshots", cwd=SCRIPTS)

    print(f"\nVersion {version} ist vorbereitet. Noch zu tun:")
    print("  - Änderungen und neue Screenshots prüfen (git status, git diff)")
    print(f'  - committen, z. B. git commit -am "update version to {version}"')
    print(f"  - Release v{version} auf GitHub veröffentlichen (deployt die Seite über GitHub Pages)")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Frank Winter
# SPDX-License-Identifier: MIT
"""
Setzt Expires in security.txt (RFC 9116) neu. Allgemein verwendbar.

RFC 9116 empfiehlt, Expires höchstens ein Jahr in die Zukunft zu legen. Der Zeitpunkt ist Mitternacht UTC,
damit es nie mehr als die eingestellten Tage sind.

Konfiguration [security_txt] (alles optional):
  file  Pfad der Datei (Standard: .well-known/security.txt)
  days  Tage ab heute (Standard: 365)

Aufruf:  python scripts/release/steps/30-security-txt.py
"""

from __future__ import annotations

import datetime
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib.common import fail, info, load_step, read, write  # noqa: E402


def main() -> None:
    step = load_step(__file__, "Expires in security.txt neu setzen.")
    path = step.path(step.get("file", ".well-known/security.txt"))
    if not path.is_file():
        fail(f"{step.rel(path)} nicht gefunden")
    days = int(step.get("days", 365))

    expires = datetime.datetime.now(datetime.timezone.utc).date() + datetime.timedelta(days=days)
    value = f"{expires.isoformat()}T00:00:00.000Z"
    text, count = re.subn(r"^(Expires:[ \t]*)\S+", rf"\g<1>{value}", read(path), count=1, flags=re.MULTILINE)
    if count != 1:
        fail(f"Expires nicht gefunden in {step.rel(path)}")
    write(path, text)
    info(f"{step.rel(path)}: Expires {value}")


if __name__ == "__main__":
    main()

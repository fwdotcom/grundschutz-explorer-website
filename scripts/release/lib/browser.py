# SPDX-FileCopyrightText: 2026 Frank Winter
# SPDX-License-Identifier: MIT
"""
Bausteine für Screenshots mit Playwright: lokaler HTTP-Server für einen Ordner, Browserstart und
Speichern als WebP. Allgemein verwendbar.

Voraussetzung:  pip install playwright pillow && python -m playwright install chromium
Umgebung:       HEADED=1 startet den Browser sichtbar (zum Nachvollziehen)
"""

from __future__ import annotations

import functools
import io
import math
import os
import threading
from contextlib import contextmanager
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Iterator

# Feste Typen statt der Windows-Registry, die .js mitunter als text/plain meldet (Module laden dann nicht)
MIME = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".mjs": "application/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
    ".webp": "image/webp",
    ".png": "image/png",
    ".ico": "image/x-icon",
    ".ttf": "font/ttf",
    ".woff2": "font/woff2",
    ".csv": "text/csv; charset=utf-8",
    ".txt": "text/plain; charset=utf-8",
}


class _QuietHandler(SimpleHTTPRequestHandler):
    extensions_map = {**SimpleHTTPRequestHandler.extensions_map, **MIME}

    def log_message(self, format: str, *args) -> None:  # noqa: A002
        pass

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


@contextmanager
def static_server(directory: Path) -> Iterator[str]:
    """Liefert directory über http://127.0.0.1:<freier Port>/ aus; gibt die Basisadresse zurück."""
    handler = functools.partial(_QuietHandler, directory=str(directory))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}/"
    finally:
        server.shutdown()
        server.server_close()


@contextmanager
def chromium() -> Iterator:
    """Startet Chromium über Playwright (unsichtbar, außer HEADED=1)."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise SystemExit("Fehler: Playwright fehlt (pip install playwright && python -m playwright install chromium)")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not os.environ.get("HEADED"))
        try:
            yield browser
        finally:
            browser.close()


def _round(value: float) -> int:
    # wie Math.round in JavaScript (x,5 immer aufwärts), nicht wie round() in Python
    return math.floor(value + 0.5)


def clip(x: float, y: float, width: float, height: float) -> dict[str, int]:
    """Ausschnitt auf ganze Pixel gerundet, nicht links oder oberhalb der Seite."""
    return {"x": max(0, _round(x)), "y": max(0, _round(y)), "width": _round(width), "height": _round(height)}


def webp(png: bytes, quality: int = 90) -> tuple[bytes, int, int]:
    """PNG-Daten als WebP; liefert Daten, Breite und Höhe."""
    try:
        from PIL import Image
    except ImportError:
        raise SystemExit("Fehler: Pillow fehlt (pip install pillow)")
    with Image.open(io.BytesIO(png)) as image:
        out = io.BytesIO()
        image.save(out, "WEBP", quality=quality, method=6)
        return out.getvalue(), image.width, image.height

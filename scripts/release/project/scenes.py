# SPDX-FileCopyrightText: 2026 Frank Winter
# SPDX-License-Identifier: MIT
"""
Szenen für die Screenshots der Website (projektspezifisch, für steps/50-screenshots.py).

Eine Szene stellt einen Zustand der App her und liefert den Ausschnitt als PNG. Jede Szene beginnt in einem
frischen Browserkontext, schreibt ihre Testdaten direkt in die IndexedDB der App (über js/storage.js) und lädt neu;
den Zustand stellen gespeicherte Einstellungen her. Welche Szenen in welche Datei gehen, legt das Manifest
www/media/screens/manifest.json fest.

Aufgenommen wird die veröffentlichte App (Konfiguration [screenshots] url). Den Anwenderkatalog der Testdaten
liest testdata.py aus testdaten/ neben dieser Datei (Kopie aus dem App-Repo). Die Szenen nutzen
Speicherstruktur, Einstellungsschlüssel und CSS-Selektoren der App. Ändern sich diese, müssen sie angepasst werden.
"""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path

from project.testdata import build_comparison_catalog, load_base_catalog

PROJECT_DIR = Path(__file__).resolve().parent

CATALOG_ID = "bsi-base"
COMPARISON_ID = "test-vergleich"
LIST_AUDIT = "list-audit"
LIST_DEV = "list-team"

CATALOG_RECORD = {
    "id": CATALOG_ID,
    "title": "Anwenderkatalog Grundschutz++",
    "version": "2026-09-10",
    "sourceType": "official",
    "sourceName": "BSI Stand-der-Technik-Bibliothek",
    "importedAt": "2026-09-24T10:00:00.000Z",
}
COMPARISON_RECORD = {
    "id": COMPARISON_ID,
    "title": "Anwenderkatalog Grundschutz++ (Vergleichsversion)",
    "version": "2026.2-Testvergleich",
    "sourceType": "file",
    "sourceName": "Grundschutz++-vergleich_catalog.json",
    "importedAt": "2026-09-25T20:00:00.000Z",
}

_WRITE_DB = """async ({ records, lists, entries, settings }) => {
  const s = await import('./js/storage.js');
  await s.clearAllData();
  for (const r of records) await s.saveCatalogRecord(r);
  if (lists.length) await s.saveListData(lists, entries);
  for (const [key, value] of Object.entries(settings)) await s.saveSetting(key, value);
}"""


def setup(step) -> dict:
    base = load_base_catalog(PROJECT_DIR)
    records = [
        {**CATALOG_RECORD, "catalogData": base},
        {**COMPARISON_RECORD, "catalogData": build_comparison_catalog(base)},
    ]
    created = "2026-09-01T08:00:00.000Z"
    note_time = "2026-09-25T15:30:00.000Z"  # 17:30 Uhr in Europe/Berlin
    return {
        "records": records,
        "lists": [
            {"id": LIST_AUDIT, "name": "Audit 2026", "createdAt": created, "updatedAt": created},
            {"id": LIST_DEV, "name": "Entwicklungsteam", "createdAt": created, "updatedAt": created},
        ],
        "entries": [
            {
                "key": f"{LIST_AUDIT}|DEV.3.4",
                "listId": LIST_AUDIT,
                "controlId": "DEV.3.4",
                "note": "Passwort-Hashing nach BSI TR-02102 auf Argon2id umstellen.\nSalt mindestens 128 Bit Zufallswert.",
                "createdAt": created,
                "updatedAt": note_time,
            },
            {
                "key": f"{LIST_DEV}|DEV.4.3",
                "listId": LIST_DEV,
                "controlId": "DEV.4.3",
                "note": "SBOM-Erzeugung in die CI-Pipeline aufnehmen.",
                "createdAt": created,
                "updatedAt": note_time,
            },
        ],
        "settings": {
            "last_active_catalog_id": CATALOG_ID,
            "comparison_catalog_id": "",
            "active_list_id": LIST_AUDIT,
            "dark_mode": False,
            "high_contrast": False,
            "font_scale": 1,
        },
    }


# ---------- Seite ----------


class Page:
    """Hilfen rund um eine Seite: warten, messen, aufnehmen."""

    def __init__(self, page):
        self.page = page

    def js(self, expression, arg=None):
        return self.page.evaluate(expression, arg)

    def wait(self, ms):
        self.page.wait_for_timeout(ms)

    def box(self, selector):
        b = self.page.locator(selector).first.bounding_box()
        if not b:
            raise RuntimeError(f"Element nicht sichtbar: {selector}")
        return b

    # Zeile in der Liste zeigen (block: 'start' | 'center' | 'end')
    def scroll_row(self, id_, block="center"):
        self.page.locator(f'[id="row-{id_}"]').evaluate("(el, block) => el.scrollIntoView({ block })", block)
        self.wait(100)

    def settle(self):
        self.js("document.fonts.ready")
        # Textcursor und Hover-Zustände vermeiden
        self.page.mouse.move(0, 0)
        self.js("document.activeElement?.blur()")
        self.wait(300)


# Breite der Detailsicht (%) für die Detail-Ausschnitte, damit alle Reiter nebeneinander passen
DETAIL_PANE_WIDTH = 38

# Sichtbarer Teil des Notizfelds (CSS-Pixel); das Feld selbst ist deutlich höher
NOTE_VISIBLE_HEIGHT = 72

# Alle Bereiche der Filterleiste zugeklappt; Schlüssel wie RAIL_COLLAPSED_DEFAULT der App
# (fehlende ergänzt die App selbst)
RAIL_ALL_COLLAPSED = dict.fromkeys(
    [
        "lists",
        "practices",
        "secLevels",
        "targetObjects",
        "modalVerbs",
        "actionWords",
        "documentation",
        "tags",
        "securityTargets",
        "effort",
        "threats",
        "sourceCatalogs",
        "diffs",
    ],
    True,
)


@contextmanager
def website(env, *, viewport, scale, settings=None, with_catalog=True):
    """Frischer Kontext; mit Katalog: Testdaten schreiben und neu laden. Liefert eine Page."""
    data = env.data
    context = env.browser.new_context(
        viewport=viewport,
        device_scale_factor=scale,
        locale="de-DE",
        timezone_id="Europe/Berlin",
        color_scheme="light",
        contrast="no-preference",
        reduced_motion="reduce",
    )
    try:
        page = context.new_page()
        page.on("pageerror", lambda err: print(f"  [Seitenfehler] {err}"))
        page.goto(env.base_url, wait_until="networkidle")
        if with_catalog:
            page.evaluate(
                _WRITE_DB,
                {
                    "records": data["records"],
                    "lists": data["lists"],
                    "entries": data["entries"],
                    "settings": {**data["settings"], **(settings or {})},
                },
            )
            page.reload(wait_until="networkidle")
        s = Page(page)
        page.wait_for_selector(".list-pane" if with_catalog else ".welcome-cta")
        s.settle()
        yield s
    finally:
        context.close()


def collapse_state(**overrides):
    return {
        "railCollapsed": {},
        "expandedKeys": [],
        "selectedControlId": "",
        "listViewMode": "tree",
        "statementTermsOpen": False,
        **overrides,
    }


# Die Ausschnitte werden ungerundet übergeben; die Bildmaße im Manifest beruhen darauf
def _region(x, y, width, height):
    return {"x": x, "y": y, "width": width, "height": height}


# ---------- Szenen ----------


# Gesamtansicht: Filterleiste, Baum mit DEV.3 aufgeklappt, Detail von DEV.3.4
def website_oberflaeche(env):
    settings = {"saved_collapse_state": collapse_state(expandedKeys=["p_DEV", "sub_DEV.3"], selectedControlId="DEV.3.4")}
    with website(env, viewport={"width": 1440, "height": 900}, scale=4 / 3, settings=settings) as s:
        s.page.wait_for_selector('[id="row-DEV.3.4"].selected')
        s.scroll_row("DEV.3.4", "center")
        return s.page.screenshot()


# Filter nach Zielobjektkategorie mit übergeordneten Kategorien, flache Liste
def website_filter_zielobjekte(env):
    settings = {
        "saved_filter_state": {
            "filters": {"searchQuery": "", "subgroupFilter": "", "controlFilter": ""},
            "activeTags": [
                {
                    "key": "targetObject:Führungskräfte",
                    "category": "targetObject",
                    "value": "Führungskräfte",
                    "mode": "include",
                    "label": "Führungskräfte",
                    "categoryLabel": "Zielobjektkategorie",
                }
            ],
            "railOnlyMatching": False,
            "targetObjectInheritance": True,
        },
        "saved_collapse_state": collapse_state(railCollapsed={**RAIL_ALL_COLLAPSED, "targetObjects": False}, listViewMode="flat"),
    }
    with website(env, viewport={"width": 1280, "height": 800}, scale=2, settings=settings) as s:
        rail = s.box("aside.rail")
        pane = s.box(".list-pane")
        return s.page.screenshot(clip=_region(rail["x"], rail["y"], pane["x"] + pane["width"] - rail["x"], 517))


# Reiter „Notizen“ von DEV.3.4
def website_detail_notizen(env):
    settings = {
        "detail_pane_width": DETAIL_PANE_WIDTH,
        "saved_collapse_state": collapse_state(expandedKeys=["p_DEV", "sub_DEV.3"], selectedControlId="DEV.3.4"),
    }
    with website(env, viewport={"width": 1280, "height": 800}, scale=2, settings=settings) as s:
        s.page.click("#tab-notes")
        s.page.wait_for_selector(".notes-panel")
        s.settle()
        detail = s.box("#detail-pane")
        note = s.box(".notes-text")
        return s.page.screenshot(
            clip=_region(detail["x"], detail["y"], detail["width"], note["y"] + NOTE_VISIBLE_HEIGHT - detail["y"])
        )


# Reiter „Änderungen“ von DEV.4.3 im Vergleich mit der Vergleichsversion, bis unter den Textvergleich
def website_detail_aenderungen(env):
    settings = {
        "comparison_catalog_id": COMPARISON_ID,
        "detail_pane_width": DETAIL_PANE_WIDTH,
        "saved_collapse_state": collapse_state(expandedKeys=["p_DEV", "sub_DEV.4"], selectedControlId="DEV.4.3"),
    }
    with website(env, viewport={"width": 1280, "height": 1200}, scale=2, settings=settings) as s:
        s.page.click("#tab-diff")
        s.page.wait_for_selector("#detail-tabpanel .stack > .card")
        s.settle()
        detail = s.box("#detail-pane")
        card = s.box("#detail-tabpanel .stack > .card:nth-of-type(2)")
        return s.page.screenshot(
            clip=_region(detail["x"], detail["y"], detail["width"], card["y"] + card["height"] + 12 - detail["y"])
        )


# Dialog „Katalog laden“ auf der Startseite (ohne gespeicherten Katalog)
def website_kataloge_laden(env):
    with website(env, viewport={"width": 1280, "height": 800}, scale=2, with_catalog=False) as s:
        s.page.click(".welcome-cta")
        s.page.wait_for_selector("dialog.modal[open]")
        s.settle()
        dlg = s.box("dialog.modal[open]")
        pad = 8
        return s.page.screenshot(clip=_region(dlg["x"] - pad, dlg["y"] - pad, dlg["width"] + 2 * pad, dlg["height"] + 2 * pad))


# Namen wie bisher im App-Repo, damit das Manifest gleich bleibt
SCENES = {
    "website-oberflaeche": website_oberflaeche,
    "website-filter-zielobjekte": website_filter_zielobjekte,
    "website-detail-notizen": website_detail_notizen,
    "website-detail-aenderungen": website_detail_aenderungen,
    "website-kataloge-laden": website_kataloge_laden,
}

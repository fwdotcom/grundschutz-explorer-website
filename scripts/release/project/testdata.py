# SPDX-FileCopyrightText: 2026 Frank Winter
# SPDX-License-Identifier: MIT
"""
Testdaten der Screenshots (projektspezifisch): Anwenderkatalog aus testdaten/ und eine daraus abgeleitete
Vergleichsversion für Vergleichsmodus und Reiter „Änderungen“.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

# Anwenderkatalog aus der Stand-der-Technik-Bibliothek des BSI (Stand 10.09.2026)
BASE_CATALOG = Path("testdaten") / "Grundschutz++-resolved_catalog.json"

NS = "https://github.com/BSI-Bund/Stand-der-Technik-Bibliothek/tree/main/documentation/namespaces/"
NS_FILE = {
    "sec_level": "security_level.csv",
    "effort_level": "effort_level.csv",
    "confidentiality": "security_targets.csv",
    "integrity": "security_targets.csv",
    "availability": "security_targets.csv",
    "authenticity": "security_targets.csv",
    "threats": "basethreats.csv",
    "tags": "tags.csv",
    "target_object_categories": "target_object_categories.csv",
    "documentation": "documentation_guidelines.csv",
    "result": "result.csv",
    "action_word": "action_words.csv",
    "modal_verb": "modal_verbs.csv",
}


def load_base_catalog(root: Path) -> dict:
    return json.loads((root / BASE_CATALOG).read_text(encoding="utf-8"))


# Eigenschaften in der Form des Katalogs: [name, wert] → { name, ns, value }
def _props(pairs):
    return [{"name": n, "ns": NS + NS_FILE[n], "value": v} if n in NS_FILE else {"name": n, "value": v} for n, v in pairs]


def _new_control(id_, title, *, props, statement, statement_props, guidance):
    return {
        "id": id_,
        "class": "BSI-Stand-der-Technik-Kernel-G0",
        "title": title,
        "props": _props(props),
        "parts": [
            {"id": f"{id_}_stm", "name": "statement", "props": _props(statement_props), "prose": statement},
            {"id": f"{id_}_gdn", "name": "guidance", "prose": guidance},
        ],
    }


def _control_index(node, index=None):
    index = {} if index is None else index
    for c in node.get("controls", []):
        index[c["id"]] = (c, node)
        _control_index(c, index)
    for g in node.get("groups", []):
        _control_index(g, index)
    return index


def build_comparison_catalog(base: dict) -> dict:
    """Vergleichsversion: je zwei neue und gelöschte Anforderungen, geänderte Texte, Modalverben und Kenngrößen."""
    data = copy.deepcopy(base)
    cat = data["catalog"]
    cat["uuid"] = "4e8b3a72-9c1f-4d3b-8517-7e6d0a2c9184"
    cat["metadata"].update(
        {
            "title": "Anwenderkatalog Grundschutz++ (Vergleichsversion)",
            "last-modified": "2026-09-25T20:00:00Z",
            "version": "2026.2-Testvergleich",
            "remarks": "Modifizierter Testkatalog zur Verifikation des Differenzvergleichs (Neu, Geändert, Gelöscht, "
            "Wortvergleich) im Grundschutz++ Explorer.",
        }
    )

    index = _control_index(cat)

    def get(id_):
        if id_ not in index:
            raise RuntimeError(f"{id_} nicht im Katalog gefunden – Vergleichskatalog anpassen.")
        return index[id_]

    def part(id_, name):
        return next(p for p in get(id_)[0]["parts"] if p["name"] == name)

    def set_props(node, values):
        for name, value in values.items():
            next(p for p in node["props"] if p["name"] == name)["value"] = value

    def remove(id_):
        parent = get(id_)[1]
        parent["controls"] = [c for c in parent["controls"] if c["id"] != id_]

    # Geändert
    set_props(part("GC.1.1", "statement"), {"modal_verb": "SOLLTE"})
    part("GC.1.1", "statement")["prose"] = (
        "Governance und Compliance MUSS Verfahren und Regelungen zur Errichtung, kontinuierlichen Aufrechterhaltung "
        "sowie jährlichen Überprüfung eines ISMS nach {{ insert: param, gc.1.1-prm1 }} verankern."
    )
    part("DEV.2.1", "guidance")["prose"] += (
        " Neu hinzugefügt: Architekturentscheidungen müssen in Architecture Decision Records (ADR) nachvollziehbar "
        "festgehalten werden."
    )
    set_props(
        get("DEV.3.4")[0],
        {
            "sec_level": "erhöht",
            "effort_level": "3",
            "integrity": "2",
            "authenticity": "2",
            "threats": "G 0.19, G 0.46, G 0.47",
            "tags": "Cryptography, Passwortsicherheit, Zero Trust",
        },
    )
    set_props(part("DEV.4.3", "statement"), {"modal_verb": "MUSS"})
    part("DEV.4.3", "statement")["prose"] = (
        "Entwicklung für Anwendungen MUSS alle eingesetzten Bestandteile und Abhängigkeiten mit Hilfe einer "
        "standardisierten Software Bill of Materials (SBOM im CycloneDX- oder SPDX-Format) vor jedem Release "
        "automatisiert dokumentieren."
    )
    part("DEV.4.3", "guidance")["prose"] = (
        "Details siehe BSI TR-03183-2 sowie BSI CS 148. Anwendungen zur Modulverwaltung und Software Composition "
        "Analysis (SCA) MÜSSEN SBOMs als Teil des CI/CD-Prozesses generieren und digital signieren."
    )

    # Gelöscht
    remove("DEV.2.6.2")
    remove("DEV.4.7")

    # Neu
    get("DEV.1.1")[0]["controls"].append(
        _new_control(
            "DEV.1.1.4",
            "Verbindlichkeit und Sanktionen",
            props=[
                ["alt-identifier", "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d"],
                ["sec_level", "normal-SdT"],
                ["effort_level", "1"],
                ["confidentiality", "1"],
                ["integrity", "1"],
                ["availability", "0"],
                ["authenticity", "0"],
                ["threats", "G 0.18"],
            ],
            statement_props=[
                ["target_object_categories", "Anwendungen"],
                ["documentation", "Sicherheitsrichtlinie"],
                ["action_word", "festlegen"],
                ["modal_verb", "SOLLTE"],
            ],
            statement="Die Institution SOLLTE festlegen, welche Konsequenzen und Eskalationsschritte bei vorsätzlicher "
            "oder grob fahrlässiger Nichteinhaltung der Entwicklungsrichtlinien greifen.",
            guidance="Klare Regelungen schaffen Verbindlichkeit für Entwicklungsteams und externe Dienstleister.",
        )
    )
    get("DEV.4.3")[1]["controls"].append(
        _new_control(
            "DEV.4.12",
            "Automatisierte Schwachstellenscans in der Bereitstellungspipeline",
            props=[
                ["alt-identifier", "f47ac10b-58cc-4372-a567-0e02b2c3d479"],
                ["sec_level", "normal-SdT"],
                ["effort_level", "2"],
                ["confidentiality", "2"],
                ["integrity", "2"],
                ["availability", "1"],
                ["authenticity", "1"],
                ["threats", "G 0.14, G 0.23, G 0.39"],
                ["tags", "Secure Compiling Practices, Automatisierung, CI/CD"],
            ],
            statement_props=[
                ["target_object_categories", "Anwendungen"],
                ["documentation", "Entwicklungsdokumentation"],
                ["result", "automatisierte Prüfungen auf Sicherheitslücken und veraltete Komponenten (SAST und SCA)"],
                ["action_word", "integrieren"],
                ["modal_verb", "MUSS"],
            ],
            statement="Entwicklung für Anwendungen MUSS automatisierte Prüfungen auf Sicherheitslücken und veraltete "
            "Komponenten (SAST und SCA) in den Build- und Bereitstellungsprozess integrieren.",
            guidance="Automatisierte Scans in CI/CD-Pipelines identifizieren Schwachstellen bereits vor dem Deployment in "
            "Test- oder Produktionsumgebungen (Shift-Left). Gefundene Sicherheitslücken mit hohem Schweregrad sollten "
            "das automatische Ausrollen verhindern.",
        )
    )
    return data

/**
 * SPDX-FileCopyrightText: 2026 Frank Winter
 * SPDX-License-Identifier: MIT
 *
 * Erstellt die Screenshots der App für die Website (www/media/screens/*.webp).
 *
 * Ablauf je Screenshot: frischer Browserkontext, Katalog, Listen und Einstellungen direkt in die
 * IndexedDB der App schreiben, neu laden, Ausschnitt aufnehmen und als WebP speichern. Die Maße der
 * Bilder werden anschließend in www/index.html (width/height der <img>) nachgetragen.
 *
 * Aufruf (im Ordner scripts):
 *   npm install
 *   npm run screenshots                 # alle Screenshots
 *   npm run screenshots -- oberflaeche  # nur einzelne (Namen ohne .webp)
 *
 * Umgebungsvariablen:
 *   APP_URL   Adresse der App (Standard: https://app.grundschutz-explorer.de/)
 *   HEADED=1  Browser sichtbar starten (zum Nachvollziehen)
 */

import { chromium } from 'playwright';
import sharp from 'sharp';
import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const APP_URL = process.env.APP_URL || 'https://app.grundschutz-explorer.de/';
const CATALOG_URL =
  'https://raw.githubusercontent.com/BSI-Bund/Stand-der-Technik-Bibliothek/main/control_layer/Grundschutz%2B%2B/Grundschutz%2B%2B-resolved_catalog.json';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const OUT_DIR = path.join(ROOT, 'www', 'media', 'screens');
const INDEX_HTML = path.join(ROOT, 'www', 'index.html');

const WEBP_QUALITY = 90;

// Breite der Detailsicht (%) für die Detail-Ausschnitte, damit alle Reiter nebeneinander passen
const DETAIL_PANE_WIDTH = 38;

// Sichtbarer Teil des Notizfelds (CSS-Pixel); das Feld selbst ist deutlich höher
const NOTE_VISIBLE_HEIGHT = 72;

// Feste IDs, damit Einstellungen und Listeneinträge aufeinander verweisen können
const CATALOG_ID = 'screenshot-aktuell';
const OLD_CATALOG_ID = 'screenshot-vorher';
const LIST_AUDIT = 'screenshot-audit-2026';
const LIST_DEV = 'screenshot-entwicklungsteam';

// Muss zu RAIL_COLLAPSED_DEFAULT der App passen (fehlende Schlüssel ergänzt die App selbst)
const RAIL_ALL_COLLAPSED = {
  lists: true,
  practices: true,
  secLevels: true,
  targetObjects: true,
  modalVerbs: true,
  actionWords: true,
  documentation: true,
  tags: true,
  securityTargets: true,
  effort: true,
  threats: true,
  sourceCatalogs: true,
  diffs: true,
};

// ---------- Testdaten ----------

function listsAndEntries() {
  const created = '2026-09-01T08:00:00.000Z';
  const noteTime = '2026-09-25T15:30:00.000Z'; // 17:30 Uhr in Europe/Berlin
  return {
    lists: [
      { id: LIST_AUDIT, name: 'Audit 2026', createdAt: created, updatedAt: created },
      { id: LIST_DEV, name: 'Entwicklungsteam', createdAt: created, updatedAt: created },
    ],
    entries: [
      {
        key: `${LIST_AUDIT}|DEV.3.4`,
        listId: LIST_AUDIT,
        controlId: 'DEV.3.4',
        note: 'Passwort-Hashing nach BSI TR-02102 auf Argon2id umstellen.\nSalt mindestens 128 Bit Zufallswert.',
        createdAt: created,
        updatedAt: noteTime,
      },
      {
        key: `${LIST_DEV}|DEV.4.3`,
        listId: LIST_DEV,
        controlId: 'DEV.4.3',
        note: 'SBOM-Erzeugung in die CI-Pipeline aufnehmen.',
        createdAt: created,
        updatedAt: noteTime,
      },
    ],
  };
}

function findControl(node, id) {
  for (const c of node.controls || []) {
    if (c.id === id) return c;
    const sub = findControl(c, id);
    if (sub) return sub;
  }
  for (const g of node.groups || []) {
    const hit = findControl(g, id);
    if (hit) return hit;
  }
  return null;
}

/**
 * Älterer Stand des Katalogs als Vergleich für den Reiter "Änderungen":
 * DEV.4.3 war dort MUSS mit anderem Anforderungstext und anderer Hilfestellung.
 */
function buildOldCatalog(current) {
  const old = structuredClone(current);
  const cat = old.catalog || old;
  cat.metadata.version = '2026-06-01T08:00:00.000000+00:00';
  cat.metadata['last-modified'] = '2026-06-01T08:00:00.000000000Z';

  const ctrl = findControl(cat, 'DEV.4.3');
  if (!ctrl) throw new Error('DEV.4.3 nicht im Katalog gefunden – Testdaten anpassen.');
  const stm = ctrl.parts.find((p) => p.name === 'statement');
  const gdn = ctrl.parts.find((p) => p.name === 'guidance');
  const verb = stm.props.find((p) => p.name === 'modal_verb');
  verb.value = 'MUSS';
  stm.prose =
    'Entwicklung für Anwendungen MUSS alle eingesetzten Bestandteile und Abhängigkeiten mit Hilfe einer ' +
    'standardisierten Software Bill of Materials (SBOM im CycloneDX- oder SPDX-Format) vor jedem Release ' +
    'automatisiert dokumentieren.';
  if (gdn) gdn.prose = 'Details siehe BSI TR-03183-2.';
  return old;
}

function catalogRecord(id, data, importedAt) {
  const meta = (data.catalog || data).metadata || {};
  return {
    id,
    title: meta.title || 'Katalog',
    version: meta.version || meta['last-modified'] || '',
    sourceType: 'url',
    sourceName: CATALOG_URL,
    importedAt,
    catalogData: data,
  };
}

// ---------- Browser ----------

/**
 * Neuer Kontext mit vorbereiteten Daten. settings: Schlüssel/Werte für den Store "settings" der App.
 * withCatalog=false: leere App (Startseite).
 */
async function openApp(browser, { viewport, scale, settings = {}, withCatalog = true }, data) {
  const context = await browser.newContext({
    viewport,
    deviceScaleFactor: scale,
    locale: 'de-DE',
    timezoneId: 'Europe/Berlin',
    colorScheme: 'light',
    reducedMotion: 'reduce',
  });
  const page = await context.newPage();
  page.on('pageerror', (err) => console.warn('  [Seitenfehler]', err.message));
  await page.goto(APP_URL, { waitUntil: 'networkidle' });

  await page.evaluate(
    async ({ withCatalog, records, lists, entries, settings }) => {
      const s = await import('./js/storage.js');
      await s.clearAllData();
      if (withCatalog) {
        for (const r of records) await s.saveCatalogRecord(r);
        await s.saveListData(lists, entries);
      }
      for (const [key, value] of Object.entries(settings)) await s.saveSetting(key, value);
    },
    {
      withCatalog,
      records: data.records,
      lists: data.lists,
      entries: data.entries,
      settings: {
        dark_mode: false,
        high_contrast: false,
        font_scale: 1,
        ...(withCatalog ? { last_active_catalog_id: CATALOG_ID, comparison_catalog_id: '', active_list_id: LIST_AUDIT } : {}),
        ...settings,
      },
    }
  );

  await page.reload({ waitUntil: 'networkidle' });
  await page.waitForSelector(withCatalog ? '.list-pane' : '.welcome-cta');
  await settle(page);
  return { context, page };
}

async function settle(page) {
  await page.evaluate(() => document.fonts.ready);
  // Textcursor und Hover-Zustände vermeiden
  await page.mouse.move(0, 0);
  await page.evaluate(() => document.activeElement?.blur());
  await page.waitForTimeout(300);
}

function collapseState(overrides) {
  return {
    railCollapsed: {},
    expandedKeys: [],
    selectedControlId: '',
    listViewMode: 'tree',
    statementTermsOpen: false,
    ...overrides,
  };
}

// Zeile in der Liste zeigen (block: 'start' | 'center' | 'end')
async function scrollRow(page, id, block = 'center') {
  await page.locator(`[id="row-${id}"]`).evaluate((el, block) => el.scrollIntoView({ block }), block);
  await page.waitForTimeout(100);
}

async function box(page, selector) {
  const b = await page.locator(selector).first().boundingBox();
  if (!b) throw new Error(`Element nicht sichtbar: ${selector}`);
  return b;
}

// ---------- Screenshots ----------

const SHOTS = {
  // Gesamtansicht: Filterleiste, Baum mit DEV.3 aufgeklappt, Detail von DEV.3.4
  async oberflaeche(browser, data) {
    const { context, page } = await openApp(
      browser,
      {
        viewport: { width: 1440, height: 900 },
        scale: 4 / 3,
        settings: {
          saved_collapse_state: collapseState({ expandedKeys: ['p_DEV', 'sub_DEV.3'], selectedControlId: 'DEV.3.4' }),
        },
      },
      data
    );
    await page.waitForSelector('[id="row-DEV.3.4"].selected');
    await scrollRow(page, 'DEV.3.4', 'center');
    const png = await page.screenshot();
    await context.close();
    return png;
  },

  // Filter nach Zielobjektkategorie mit übergeordneten Kategorien, flache Liste
  async 'filter-zielobjekte'(browser, data) {
    const { context, page } = await openApp(
      browser,
      {
        viewport: { width: 1280, height: 800 },
        scale: 2,
        settings: {
          saved_filter_state: {
            filters: { searchQuery: '', subgroupFilter: '', controlFilter: '' },
            activeTags: [
              {
                key: 'targetObject:Führungskräfte',
                category: 'targetObject',
                value: 'Führungskräfte',
                mode: 'include',
                label: 'Führungskräfte',
                categoryLabel: 'Zielobjektkategorie',
              },
            ],
            railOnlyMatching: false,
            targetObjectInheritance: true,
          },
          saved_collapse_state: collapseState({
            railCollapsed: { ...RAIL_ALL_COLLAPSED, targetObjects: false },
            listViewMode: 'flat',
          }),
        },
      },
      data
    );
    const rail = await box(page, 'aside.rail');
    const pane = await box(page, '.list-pane');
    const png = await page.screenshot({
      clip: { x: rail.x, y: rail.y, width: pane.x + pane.width - rail.x, height: 517 },
    });
    await context.close();
    return png;
  },

  // Reiter "Notizen" von DEV.3.4
  async 'detail-notizen'(browser, data) {
    const { context, page } = await openApp(
      browser,
      {
        viewport: { width: 1280, height: 800 },
        scale: 2,
        settings: {
          detail_pane_width: DETAIL_PANE_WIDTH,
          saved_collapse_state: collapseState({ expandedKeys: ['p_DEV', 'sub_DEV.3'], selectedControlId: 'DEV.3.4' }),
        },
      },
      data
    );
    await page.click('#tab-notes');
    await page.waitForSelector('.notes-panel');
    await settle(page);
    const detail = await box(page, '#detail-pane');
    const note = await box(page, '.notes-text');
    const png = await page.screenshot({
      clip: { x: detail.x, y: detail.y, width: detail.width, height: note.y + NOTE_VISIBLE_HEIGHT - detail.y },
    });
    await context.close();
    return png;
  },

  // Reiter "Änderungen" von DEV.4.3 im Vergleich mit dem älteren Stand
  async 'detail-aenderungen'(browser, data) {
    const { context, page } = await openApp(
      browser,
      {
        viewport: { width: 1280, height: 1200 },
        scale: 2,
        settings: {
          comparison_catalog_id: OLD_CATALOG_ID,
          detail_pane_width: DETAIL_PANE_WIDTH,
          saved_collapse_state: collapseState({ expandedKeys: ['p_DEV', 'sub_DEV.4'], selectedControlId: 'DEV.4.3' }),
        },
      },
      data
    );
    await page.click('#tab-diff');
    await page.waitForSelector('#detail-tabpanel .stack > .card');
    await settle(page);
    const detail = await box(page, '#detail-pane');
    // Bis unter die zweite Karte (Textvergleich Anforderungstext)
    const card = await box(page, '#detail-tabpanel .stack > .card:nth-of-type(2)');
    const png = await page.screenshot({
      clip: { x: detail.x, y: detail.y, width: detail.width, height: card.y + card.height + 12 - detail.y },
    });
    await context.close();
    return png;
  },

  // Dialog "Katalog laden" auf der Startseite (ohne gespeicherten Katalog)
  async 'kataloge-laden'(browser, data) {
    const { context, page } = await openApp(
      browser,
      { viewport: { width: 1280, height: 800 }, scale: 2, withCatalog: false },
      data
    );
    await page.click('.welcome-cta');
    await page.waitForSelector('dialog.modal[open]');
    await settle(page);
    const dlg = await box(page, 'dialog.modal[open]');
    const pad = 8;
    const png = await page.screenshot({
      clip: { x: dlg.x - pad, y: dlg.y - pad, width: dlg.width + 2 * pad, height: dlg.height + 2 * pad },
    });
    await context.close();
    return png;
  },
};

// ---------- Ausgabe ----------

function updateImageSize(html, name, width, height) {
  const re = new RegExp(`(src="media/screens/${name}\\.webp"\\s+)width="\\d+"(\\s+)height="\\d+"`);
  if (!re.test(html)) {
    console.warn(`  Hinweis: ${name}.webp mit width/height nicht in index.html gefunden – Maße nicht nachgetragen.`);
    return html;
  }
  return html.replace(re, `$1width="${width}"$2height="${height}"`);
}

async function main() {
  const requested = process.argv.slice(2);
  const unknown = requested.filter((n) => !SHOTS[n]);
  if (unknown.length) {
    console.error(`Unbekannte Screenshots: ${unknown.join(', ')}\nVerfügbar: ${Object.keys(SHOTS).join(', ')}`);
    process.exit(1);
  }
  const names = requested.length ? requested : Object.keys(SHOTS);

  console.log('Lade Katalog …');
  const res = await fetch(CATALOG_URL);
  if (!res.ok) throw new Error(`Katalog nicht abrufbar: HTTP ${res.status}`);
  const current = await res.json();
  const data = {
    records: [
      catalogRecord(OLD_CATALOG_ID, buildOldCatalog(current), '2026-06-02T08:00:00.000Z'),
      catalogRecord(CATALOG_ID, current, '2026-09-11T08:00:00.000Z'),
    ],
    ...listsAndEntries(),
  };

  await mkdir(OUT_DIR, { recursive: true });
  let html = await readFile(INDEX_HTML, 'utf8');
  const browser = await chromium.launch({ headless: !process.env.HEADED });
  try {
    for (const name of names) {
      process.stdout.write(`${name} … `);
      const png = await SHOTS[name](browser, data);
      const file = path.join(OUT_DIR, `${name}.webp`);
      const { width, height } = await sharp(png).webp({ quality: WEBP_QUALITY }).toFile(file);
      html = updateImageSize(html, name, width, height);
      console.log(`${width}×${height}`);
    }
  } finally {
    await browser.close();
  }
  await writeFile(INDEX_HTML, html);
  console.log(`Fertig: ${path.relative(ROOT, OUT_DIR)}`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});

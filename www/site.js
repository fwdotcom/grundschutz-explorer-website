/*
 * SPDX-FileCopyrightText: 2026 Frank Winter
 * SPDX-License-Identifier: MIT
 *
 * Projektwebseite Grundschutz++ Explorer
 * Wird im <head> ohne defer geladen, damit das gespeicherte Farbschema vor dem ersten Zeichnen greift.
 */

(function () {
  'use strict';

  var THEME_KEY = 'gse-site-theme';
  var root = document.documentElement;

  root.classList.remove('no-js');

  // Farbschema: gespeicherte Wahl hat Vorrang vor der Systemeinstellung
  try {
    var saved = localStorage.getItem(THEME_KEY);
    if (saved === 'light' || saved === 'dark') root.setAttribute('data-theme', saved);
  } catch (e) { /* Speicher nicht verfügbar: Systemeinstellung gilt */ }

  function currentTheme() {
    var set = root.getAttribute('data-theme');
    if (set) return set;
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }

  function initThemeToggle() {
    var btn = document.querySelector('.theme-toggle');
    if (!btn) return;
    var update = function () {
      var dark = currentTheme() === 'dark';
      btn.setAttribute('aria-pressed', String(dark));
      btn.setAttribute('title', dark ? 'Helles Design' : 'Dunkles Design');
    };
    update();
    btn.addEventListener('click', function () {
      var next = currentTheme() === 'dark' ? 'light' : 'dark';
      root.setAttribute('data-theme', next);
      try { localStorage.setItem(THEME_KEY, next); } catch (e) { /* ignorieren */ }
      update();
    });
  }

  function initMenu() {
    var btn = document.querySelector('.menu-toggle');
    var nav = document.getElementById('site-nav');
    if (!btn || !nav) return;
    var close = function () {
      nav.classList.remove('open');
      btn.setAttribute('aria-expanded', 'false');
    };
    btn.addEventListener('click', function () {
      var open = nav.classList.toggle('open');
      btn.setAttribute('aria-expanded', String(open));
    });
    nav.addEventListener('click', function (e) {
      if (e.target.closest('a')) close();
    });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && nav.classList.contains('open')) { close(); btn.focus(); }
    });
  }

  function initHeader() {
    var header = document.querySelector('.site-header');
    if (!header) return;
    var onScroll = function () { header.classList.toggle('scrolled', window.scrollY > 8); };
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
  }

  function initReveal() {
    var items = document.querySelectorAll('.reveal, .hero-shot');
    if (!('IntersectionObserver' in window)) {
      items.forEach(function (el) { el.classList.add('in-view'); });
      return;
    }
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add('in-view');
          io.unobserve(entry.target);
        }
      });
    }, { rootMargin: '0px 0px -10% 0px', threshold: 0.1 });
    items.forEach(function (el) { io.observe(el); });
  }

  // Bildbetrachter: Screenshots in voller Größe
  function initLightbox() {
    var dialog = document.getElementById('lightbox');
    if (!dialog || typeof dialog.showModal !== 'function') return;
    var img = dialog.querySelector('img');
    var caption = dialog.querySelector('figcaption');
    var closeBtn = dialog.querySelector('.icon-btn');

    document.querySelectorAll('.shot-btn').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var source = btn.querySelector('img');
        img.src = source.currentSrc || source.src;
        img.alt = source.alt;
        caption.textContent = source.alt;
        dialog.showModal();
      });
    });
    closeBtn.addEventListener('click', function () { dialog.close(); });
    dialog.addEventListener('click', function (e) {
      if (e.target === dialog) dialog.close();
    });
  }

  // Impressum und Datenschutzerklärung als Dialog; direkt aufrufbar über /#impressum bzw. /#datenschutzerklaerung
  function initLegal() {
    var dialogs = document.querySelectorAll('.legal-modal');
    if (!dialogs.length || typeof dialogs[0].showModal !== 'function') return;

    var open = function (id) {
      var dialog = document.getElementById(id);
      if (!dialog || !dialog.classList.contains('legal-modal') || dialog.open) return false;
      dialog.showModal();
      dialog.querySelector('.legal-modal-body').scrollTop = 0;
      return true;
    };

    dialogs.forEach(function (dialog) {
      dialog.querySelector('.legal-modal-close').addEventListener('click', function () { dialog.close(); });
      dialog.addEventListener('click', function (e) {
        if (e.target === dialog) dialog.close();
      });
      dialog.addEventListener('close', function () {
        if (location.hash === '#' + dialog.id) history.replaceState(null, '', location.pathname + location.search);
      });
    });

    document.querySelectorAll('a[data-legal]').forEach(function (link) {
      link.addEventListener('click', function (e) {
        e.preventDefault();
        open(link.getAttribute('href').slice(1));
      });
    });

    var fromHash = function () { open(location.hash.slice(1)); };
    fromHash();
    window.addEventListener('hashchange', fromHash);
  }

  document.addEventListener('DOMContentLoaded', function () {
    initThemeToggle();
    initMenu();
    initHeader();
    initReveal();
    initLightbox();
    initLegal();
  });
})();

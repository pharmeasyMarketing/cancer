/* Cancer hub: Read more / Read less on the opening description.
   Clamped on every screen size (the GLP-1 home pattern). Without JS the full text shows. */
(function () {
  'use strict';
  var intro = document.getElementById('hero-intro');
  var btn = document.getElementById('hero-toggle');
  if (!intro || !btn) return;
  var label = btn.querySelector('span');

  function apply() {
    var open = btn.classList.contains('open');
    if (open) return;                              // reader expanded it; leave it
    intro.classList.remove('is-clamped');
    if (intro.scrollHeight <= 230) { btn.hidden = true; return; }   // short enough already
    btn.hidden = false;
    intro.classList.add('is-clamped');
  }

  btn.addEventListener('click', function () {
    var clamped = intro.classList.toggle('is-clamped');
    btn.classList.toggle('open', !clamped);
    btn.setAttribute('aria-expanded', String(!clamped));
    label.textContent = clamped ? 'Read more' : 'Read less';
  });

  apply();
  var t, w0 = window.innerWidth;     // width-only: the phone address bar fires height-only resizes while scrolling
  window.addEventListener('resize', function () { if (window.innerWidth === w0) return; w0 = window.innerWidth; clearTimeout(t); t = setTimeout(apply, 120); });
})();

/* Phone only (CSS does the hiding): long drug groups show 4 molecules, the reference
   list shows 5, each with a button to open the rest. A citation tap opens the list. */
(function () {
  'use strict';
  function btn(cls, text) {
    var b = document.createElement('button');
    b.type = 'button'; b.className = cls; b.textContent = text;
    b.setAttribute('aria-expanded', 'false');
    return b;
  }
  [].forEach.call(document.querySelectorAll('.dg-item'), function (item) {
    var n = parseInt(item.getAttribute('data-mols'), 10) || 0;
    if (n <= 4) return;
    var list = item.querySelector('.mol-list');
    item.classList.add('is-collapsed');
    var b = btn('dg-toggle', 'Show all ' + n + ' molecules');
    b.addEventListener('click', function () {
      var c = item.classList.toggle('is-collapsed');
      b.textContent = c ? 'Show all ' + n + ' molecules' : 'Show fewer';
      b.setAttribute('aria-expanded', String(!c));
    });
    list.appendChild(b);
  });

  var refs = document.getElementById('refs-list');
  if (!refs) return;
  var total = refs.children.length;
  if (total <= 5) return;
  refs.classList.add('is-collapsed');
  var rb = btn('refs-toggle', 'Show all ' + total + ' references');
  function open() { refs.classList.remove('is-collapsed'); rb.textContent = 'Show fewer references'; rb.setAttribute('aria-expanded', 'true'); }
  rb.addEventListener('click', function () {
    if (refs.classList.contains('is-collapsed')) open();
    else { refs.classList.add('is-collapsed'); rb.textContent = 'Show all ' + total + ' references'; rb.setAttribute('aria-expanded', 'false'); }
  });
  refs.parentNode.appendChild(rb);
  // a citation [n] always lands on its reference, collapsed or not
  document.addEventListener('click', function (e) {
    var a = e.target.closest && e.target.closest('a[href^="#ref-"]');
    if (a) open();
  }, true);
  if (/^#ref-/.test(location.hash)) open();
})();

/* Drug tables: two popups share one card.
   - "+N more molecules" (homepage drug table) lists the group's other molecules on PharmEasy, from
     assets/data/drug-more.json (built from the "Cancer Molecules list" sheet).
   - a molecule's "+N more" brand chip lists that molecule's other medicines on PharmEasy, from
     assets/data/mol-brands.json (build/fetch_mol_medicines.py, PharmEasy's molecule medicines API).
     The chip is a link to the molecule page, so without JS (or if the data fails) it still goes there.
   Neither list is part of the page HTML. */
(function () {
  'use strict';
  var groupBtns = document.querySelectorAll('.mol-more[data-group]');
  var brandChips = document.querySelectorAll('a.mol-brands[data-mol]');
  if (!groupBtns.length && !brandChips.length) return;
  var src = (document.querySelector('script[src*="assets/js/cancer.js"]') || {}).src || '';
  function dataUrl(f) { return src ? src.replace(/js\/cancer\.js.*$/, 'data/' + f) : 'assets/data/' + f; }
  var cache = {}, dlg, title, sub, list, lastBtn;

  function load(f) {
    if (!cache[f]) cache[f] = fetch(dataUrl(f), { credentials: 'same-origin' })
      .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
      .catch(function (e) { delete cache[f]; throw e; });
    return cache[f];
  }

  function build() {
    dlg = document.createElement('div');
    dlg.className = 'mm-overlay';
    dlg.hidden = true;
    dlg.innerHTML = '<div class="mm-dialog" role="dialog" aria-modal="true" aria-labelledby="mm-title">' +
      '<div class="mm-head"><h3 id="mm-title"></h3><button type="button" class="mm-close" aria-label="Close">' +
      '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M18 6 6 18M6 6l12 12"/></svg></button></div>' +
      '<p class="mm-sub"></p><ul class="mm-list"></ul></div>';
    document.body.appendChild(dlg);
    title = dlg.querySelector('#mm-title');
    sub = dlg.querySelector('.mm-sub');
    list = dlg.querySelector('.mm-list');
    dlg.addEventListener('click', function (e) { if (e.target === dlg || e.target.closest('.mm-close')) close(); });
    document.addEventListener('keydown', function (e) {
      if (dlg.hidden) return;
      if (e.key === 'Escape') { close(); return; }
      if (e.key !== 'Tab') return;                       // keep focus inside the popup
      var f = dlg.querySelectorAll('button, a[href]'), first = f[0], last = f[f.length - 1];
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
    });
  }

  function open(btn, heading, note, items, more) {
    if (!dlg) build();
    lastBtn = btn;
    title.textContent = heading;
    sub.textContent = note;
    list.innerHTML = '';
    items.forEach(function (m) {
      var li = document.createElement('li'), a = document.createElement('a');
      a.href = m.url; a.textContent = m.name;
      li.appendChild(a); list.appendChild(li);
    });
    if (more) {
      var li = document.createElement('li'), a = document.createElement('a');
      li.className = 'mm-all'; a.href = more.url; a.textContent = more.name;
      li.appendChild(a); list.appendChild(li);
    }
    dlg.hidden = false;
    document.documentElement.classList.add('mm-open');
    btn.setAttribute('aria-expanded', 'true');
    dlg.querySelector('.mm-close').focus();
  }

  function close() {
    dlg.hidden = true;
    document.documentElement.classList.remove('mm-open');
    if (lastBtn) { lastBtn.setAttribute('aria-expanded', 'false'); lastBtn.focus(); }
  }

  [].forEach.call(groupBtns, function (b) {
    b.setAttribute('aria-expanded', 'false');
    b.addEventListener('click', function () {
      b.setAttribute('aria-busy', 'true');
      load('drug-more.json').then(function (j) {
        var g = (j.groups || {})[b.getAttribute('data-group')];
        if (g && g.molecules.length) open(b, g.title,
          'More molecules in this group on PharmEasy. Your oncologist decides which medicine suits you.', g.molecules);
      }).catch(function () {}).then(function () { b.removeAttribute('aria-busy'); });
    });
  });

  [].forEach.call(brandChips, function (a) {
    a.setAttribute('aria-expanded', 'false');
    a.addEventListener('click', function (e) {
      if (e.metaKey || e.ctrlKey || e.shiftKey || e.button) return;   // new tab: follow the link
      e.preventDefault();
      var row = a.closest('.mol-row');
      var name = row ? row.querySelector('.mol-name').textContent.trim() : '';
      var skip = (a.getAttribute('data-skip') || '').split(',').filter(Boolean).map(Number);
      a.setAttribute('aria-busy', 'true');
      load('mol-brands.json').then(function (j) {
        var items = (j[a.getAttribute('data-mol')] || []).filter(function (m) { return skip.indexOf(m.p) === -1; })
          .map(function (m) { return { name: m.n, url: m.u }; });
        if (!items.length) { location.href = a.href; return; }
        open(a, name ? 'More ' + name + ' medicines' : 'More medicines',
          'Other medicines with ' + (name || 'this molecule') + ' on PharmEasy. Your oncologist decides which medicine suits you.',
          items, { name: 'About ' + (name || 'this molecule') + ' on PharmEasy', url: a.href });
      }).catch(function () { location.href = a.href; }).then(function () { a.removeAttribute('aria-busy'); });
    });
  });
})();

/* Cancer types A to Z: on mobile (CSS decides) a type's subpages fold behind its "N guides" toggle.
   The fold only switches on once this runs, so without JS every link stays visible. */
(function () {
  'use strict';
  var ctz = document.querySelector('.ctz');
  if (!ctz) return;
  ctz.classList.add('js-fold');
  [].forEach.call(ctz.querySelectorAll('.ctz-tog'), function (b) {
    b.addEventListener('click', function () {
      var item = b.closest('.ctz-item');
      var open = item.classList.toggle('open');
      b.setAttribute('aria-expanded', String(open));
    });
  });
})();

/* Preview only (GitHub Pages / localhost): links to hub pages that exist in this build open the
   built copy instead of pharmeasy.in, where they are not live yet. Production is untouched. */
(function () {
  'use strict';
  var h = location.hostname;
  if (!(/\.github\.io$/.test(h) || h === 'localhost' || h === '127.0.0.1')) return;
  var built = (document.body.getAttribute('data-built') || '').split(/\s+/).filter(Boolean);
  var src = (document.querySelector('script[src*="assets/js/cancer.js"]') || {}).src || '';
  if (!src) return;
  var base = src.replace(/assets\/js\/cancer\.js.*$/, '');
  [].forEach.call(document.querySelectorAll('a[href^="https://pharmeasy.in/cancer/"]'), function (a) {
    var p = a.getAttribute('href').replace('https://pharmeasy.in/cancer/', '').split('#')[0];
    if (p === '' || built.indexOf(p) !== -1) a.setAttribute('href', base + p + (a.hash || ''));
  });
})();

/* A table that is wider than the article column would hide its last columns behind a sideways
   scroll. Show it as row cards instead (.stack, see cancer.css). Re-checked on resize. */
(function () {
  'use strict';
  var wraps = [].slice.call(document.querySelectorAll('.rt-scroll'));
  if (!wraps.length) return;
  function fit() {
    wraps.forEach(function (s) {
      var t = s.querySelector('table.rtable');
      if (!t) return;
      t.classList.remove('stack');
      if (s.scrollWidth > s.clientWidth + 2) t.classList.add('stack');
    });
  }
  fit();
  var timer, fw = window.innerWidth;
  window.addEventListener('resize', function () { if (window.innerWidth === fw) return; fw = window.innerWidth; clearTimeout(timer); timer = setTimeout(fit, 150); });
  window.addEventListener('load', fit);
})();

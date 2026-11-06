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
  var t;
  window.addEventListener('resize', function () { clearTimeout(t); t = setTimeout(apply, 120); });
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

/* Drug table: "+N more molecules" opens a popup listing the group's other molecules on
   PharmEasy. The list is client-rendered from assets/data/drug-more.json (built from the
   "Cancer Molecules list" sheet), so it is not part of the page HTML. */
(function () {
  'use strict';
  var buttons = document.querySelectorAll('.mol-more[data-group]');
  if (!buttons.length) return;
  var src = (document.querySelector('script[src*="assets/js/cancer.js"]') || {}).src || '';
  var url = src ? src.replace(/js\/cancer\.js.*$/, 'data/drug-more.json') : 'assets/data/drug-more.json';
  var data = null, loading = null, dlg, title, list, lastBtn;

  function load() {
    if (data) return Promise.resolve(data);
    if (!loading) loading = fetch(url, { credentials: 'same-origin' })
      .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then(function (j) { data = j.groups || {}; return data; })
      .catch(function (e) { loading = null; throw e; });
    return loading;
  }

  function build() {
    dlg = document.createElement('div');
    dlg.className = 'mm-overlay';
    dlg.hidden = true;
    dlg.innerHTML = '<div class="mm-dialog" role="dialog" aria-modal="true" aria-labelledby="mm-title">' +
      '<div class="mm-head"><h3 id="mm-title"></h3><button type="button" class="mm-close" aria-label="Close">' +
      '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M18 6 6 18M6 6l12 12"/></svg></button></div>' +
      '<p class="mm-sub">More molecules in this group on PharmEasy. Your oncologist decides which medicine suits you.</p>' +
      '<ul class="mm-list"></ul></div>';
    document.body.appendChild(dlg);
    title = dlg.querySelector('#mm-title');
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

  function open(btn, group) {
    if (!dlg) build();
    lastBtn = btn;
    title.textContent = group.title;
    list.innerHTML = '';
    group.molecules.forEach(function (m) {
      var li = document.createElement('li'), a = document.createElement('a');
      a.href = m.url; a.textContent = m.name;
      li.appendChild(a); list.appendChild(li);
    });
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

  [].forEach.call(buttons, function (b) {
    b.setAttribute('aria-expanded', 'false');
    b.addEventListener('click', function () {
      b.setAttribute('aria-busy', 'true');
      load().then(function (groups) {
        var g = groups[b.getAttribute('data-group')];
        if (g && g.molecules.length) open(b, g);
      }).catch(function () {}).then(function () { b.removeAttribute('aria-busy'); });
    });
  });
})();

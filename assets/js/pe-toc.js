/* ============================================================
   Table of contents behaviour.

   Desktop: the rail stays pinned while the article is on screen,
   the link for the section you are reading is highlighted, and the
   rail scrolls itself so that link stays visible. Once the FAQs
   have scrolled past, the rail scrolls the rest of its cards into
   view instead of leaving them below the fold.

   Mobile: the in-page contents card is replaced by a sticky strip
   of quick-link chips, the same pattern the PharmEasy home page
   uses under its search bar. The active chip scrolls itself into
   view as you read.

   Runs after every dc-runtime render.
   ============================================================ */
(function (global) {
  'use strict';

  var MOBILE = 560;           // the breakpoint the design stacks the rail at

  // Chips need a label that fits a pill. Full headings stay untouched in the
  // desktop rail and in the page itself; only the carousel is abbreviated.
  var SHORT = {
    // cancer hub
    'What is cancer?': 'What is cancer',
    'How does cancer start?': 'How it starts',
    'Benign vs malignant tumour': 'Benign vs malignant',
    'How are cancers classified?': 'Classification',
    'How does cancer spread?': 'How it spreads',
    'The India picture': 'India picture',
    'Common symptoms of cancer': 'Symptoms',
    'How is cancer diagnosed?': 'Diagnosis',
    'Staging, grading and why they differ': 'Staging and grading',
    'How is cancer treated?': 'Treatment',
    'What to check for insurance in India': 'Insurance',
    'Screening and prevention': 'Screening',
    'When to see a doctor?': 'See a doctor',
    'Latest on cancer in India': 'Latest updates',
    'Frequently Asked Questions': 'FAQs',
    // hub home
    'GLP-1 based medicines available in India': 'Medicines in India',
    'How GLP-1 based medicines work': 'How they work',
    'Injectable vs oral options': 'Injectable vs oral',
    'What GLP-1-based therapy costs in India': 'Cost in India',
    'Are these medicines right for you?': 'Right for you?',
    'Safety and the rules in India': 'Safety and rules',
    'Latest GLP-1 updates in India': 'Latest updates',
    'Frequently asked questions': 'FAQs',
    // brand pages
    'How Mounjaro works': 'How it works',
    'How Wegovy works': 'How it works',
    'What it is approved for': 'Approved uses',
    'Strengths': 'Strengths',
    'Dosage and titration': 'Dosage',
    'Who should not take it': 'Who should avoid',
    'How to get it legally': 'How to get it',
    'Storing Mounjaro': 'Storage',
    'Storing Wegovy': 'Storage',
    'Mounjaro vs alternatives': 'Alternatives',
    'Wegovy vs alternatives': 'Alternatives',
    // price page
    'Why it got cheaper in 2026': 'Why it got cheaper',
    'Generic semaglutide options': 'Generic options',
    'Does insurance cover it?': 'Insurance',
    'How to buy with a prescription': 'How to buy',
    // compare
    'Comparing GLP-1 medicines': 'How to compare',
    'Which is right for you?': 'Right for you?',
    'How they work differently': 'How they differ',
    'What the trials show': 'Trials',
    'Cost comparison in India': 'Cost in India',
    'When might each be considered?': 'When each fits',
    // guide
    'Why these medicines upset the stomach': 'Why it happens',
    'Common effects and what helps': 'Common effects',
    'Effects that are never normal': 'Never normal',
    'Reporting a side effect': 'Reporting',
    'Questions people ask': 'Questions',
  };

  function chipLabel(text) {
    var full = String(text || '').trim().replace(/^\d+\.\s*/, '');
    // the news heading carries a date the design fixes in place; drop the
    // parenthetical for the chip only
    var bare = full.replace(/\s*\([^)]*\)\s*$/, '').trim();
    return SHORT[full] || SHORT[bare] || bare || full;
  }

  function vw() { return document.documentElement.clientWidth || window.innerWidth || 0; }
  function isMobile() { var w = vw(); return w > 0 && w <= MOBILE; }

  // the site header, once pe-shell has swapped it in for the placeholder
  function siteHeader() {
    return document.querySelector('body > header') ||
      document.querySelector('[data-pe-header] header, [data-pe-header] > *');
  }

  // how far a sticky header (plus the chip strip that rides under it) covers
  function headerHeight() {
    var h = siteHeader();
    if (!h) return 0;
    var cs = getComputedStyle(h);
    if (cs.position !== 'sticky' && cs.position !== 'fixed') return 0;
    return Math.round(h.getBoundingClientRect().height);
  }

  function headerOffset() {
    var base = headerHeight() + 12;
    var strip = document.getElementById('dc-toc-strip');
    if (strip && isMobile()) base += strip.getBoundingClientRect().height;
    return base;
  }

  // the "On this page" card, whatever wrapper the template uses
  function findTocCard() {
    var root = document.getElementById('dc-root');
    if (!root) return null;
    var nodes = root.querySelectorAll('div, span, h2, h3');
    for (var i = 0; i < nodes.length; i++) {
      var n = nodes[i];
      if (n.children.length === 0 && /^on this page$/i.test((n.textContent || '').trim())) {
        return n.parentElement;
      }
    }
    return null;
  }

  function cleanup() {
    var strip = document.getElementById('dc-toc-strip');
    if (strip) strip.parentNode.removeChild(strip);
    if (global.__dcTocScroll) {
      window.removeEventListener('scroll', global.__dcTocScroll);
      window.removeEventListener('resize', global.__dcTocScroll);
      global.__dcTocScroll = null;
    }
  }

  // one FAQ thread open at a time
  function singleOpenFaqs() {
    var all = [].slice.call(document.querySelectorAll('#dc-root details.faq'));
    all.forEach(function (d) {
      if (d.__dcBound) return;
      d.__dcBound = true;
      d.addEventListener('toggle', function () {
        if (!d.open) return;
        all.forEach(function (o) { if (o !== d && o.open) o.open = false; });
      });
    });
  }

  // On the phone the hero intro can be long, so it is clamped with a
  // Read more / Read less toggle, the same as the GLP-1 home page. On
  // desktop the full intro is always shown.
  function heroReadMore() {
    var lead = document.querySelector('#dc-root .hero-lead');
    if (!lead) return;
    var host = lead.parentNode;
    var prev = host.querySelector('.hero-more');
    if (prev) prev.parentNode.removeChild(prev);
    lead.classList.remove('is-clamped');

    if (!isMobile()) return;

    lead.classList.add('is-clamped');
    if (lead.scrollHeight <= lead.clientHeight + 4) {   // short enough already
      lead.classList.remove('is-clamped');
      return;
    }
    var btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'hero-more';
    btn.setAttribute('aria-expanded', 'false');
    btn.innerHTML = '<span>Read more</span><svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="m6 9 6 6 6-6"/></svg>';
    host.insertBefore(btn, lead.nextSibling);
    btn.addEventListener('click', function () {
      var clamped = lead.classList.toggle('is-clamped');   // true = now clamped
      btn.querySelector('span').textContent = clamped ? 'Read more' : 'Read less';
      btn.setAttribute('aria-expanded', String(!clamped));
      btn.classList.toggle('open', !clamped);
    });
  }

  function init() {
    cleanup();
    singleOpenFaqs();
    heroReadMore();
    if (!window.__dcHeroResize) {
      window.__dcHeroResize = function () { heroReadMore(); };
      window.addEventListener('resize', window.__dcHeroResize);
    }

    var card = findTocCard();
    if (!card) return;
    card.classList.add('dc-toc-source');

    var links = [].slice.call(card.querySelectorAll('a[href^="#"]'))
      .filter(function (a) { return a.getAttribute('href').length > 1; });
    if (!links.length) return;

    var targets = [];
    links.forEach(function (a) {
      a.classList.add('dc-toc-link');
      var t = document.getElementById(a.getAttribute('href').slice(1));
      if (t) targets.push({ link: a, el: t });
    });
    if (!targets.length) return;

    /* ---------- mobile: sticky quick-link chips ---------- */
    var strip = document.createElement('nav');
    strip.id = 'dc-toc-strip';
    strip.setAttribute('aria-label', 'On this page');
    var track = document.createElement('div');
    track.className = 'dc-toc-track';
    var chips = targets.map(function (t) {
      var a = document.createElement('a');
      a.href = t.link.getAttribute('href');
      a.className = 'dc-toc-chip';
      a.textContent = chipLabel(t.link.textContent);
      track.appendChild(a);
      return a;
    });
    strip.appendChild(track);

    var main = document.getElementById('main') || document.body;
    main.insertBefore(strip, main.firstChild);

    // the strip rides directly under the sticky header rather than on top of
    // it, and anchors must clear both
    function place() {
      strip.style.top = headerHeight() + 'px';
      var off = headerOffset();
      targets.forEach(function (t) { t.el.style.scrollMarginTop = off + 'px'; });
    }
    place();

    // it stays out of the way until the reader actually reaches the first
    // section; before that the hero is the page
    function reveal() {
      var first = targets[0].el.getBoundingClientRect().top;
      strip.classList.toggle('is-on', first <= headerHeight() + 8);
    }
    reveal();

    /* ---------- rail: pin, follow, then release ---------- */
    var rail = card.closest('.toc');
    if (!rail) {
      var p = card.parentElement;
      while (p && p !== document.body) {
        if (getComputedStyle(p).position === 'sticky') { rail = p; break; }
        p = p.parentElement;
      }
    }

    // the FAQ block is where the article ends for the rail's purposes
    var faq = document.getElementById('faqs') || document.getElementById('faq') ||
      (function () {
        for (var i = targets.length - 1; i >= 0; i--) {
          if (/faq/i.test(targets[i].el.id)) return targets[i].el;
        }
        return null;
      })();

    var railTimer = null;
    function easeRailTo(top) {
      var from = rail.scrollTop;
      if (Math.abs(from - top) < 2) return;
      if (railTimer) clearInterval(railTimer);
      var t0 = Date.now(), dur = 360;
      railTimer = setInterval(function () {
        var k = Math.min(1, (Date.now() - t0) / dur);
        rail.scrollTop = from + (top - from) * (1 - Math.pow(1 - k, 3));
        if (k >= 1) { clearInterval(railTimer); railTimer = null; }
      }, 16);
    }

    var lastActive = -1;
    function onScroll() {
      // a heading counts as "the one you are reading" once it is within a
      // band below the top of the viewport, not only after it has left it
      var line = (window.pageYOffset || document.documentElement.scrollTop) + headerOffset() + 72;

      var idx = 0;
      for (var i = 0; i < targets.length; i++) {
        var top = targets[i].el.getBoundingClientRect().top + window.pageYOffset;
        if (top - 4 <= line) idx = i; else break;
      }
      // at the very bottom of the page, the last entry wins
      if (window.innerHeight + window.pageYOffset >= document.body.scrollHeight - 4) idx = targets.length - 1;

      if (idx !== lastActive) {
        lastActive = idx;
        targets.forEach(function (t, i) { t.link.classList.toggle('is-active', i === idx); });
        chips.forEach(function (c, i) { c.classList.toggle('is-active', i === idx); });
        if (isMobile()) {
          var c = chips[idx];
          var want = c.offsetLeft - track.clientWidth / 2 + c.offsetWidth / 2;
          track.scrollLeft = Math.max(0, want);
        }
      }

      if (!rail || isMobile()) return;

      var overflow = rail.scrollHeight - rail.clientHeight;
      if (overflow <= 0) return;

      var faqDone = faq && (faq.getBoundingClientRect().bottom < headerOffset());
      if (faqDone) {
        // FAQs are behind us: bring the rest of the rail's cards into view
        easeRailTo(overflow);
      } else {
        // still reading: keep the active link comfortably in the rail
        var a = targets[idx].link;
        var aTop = a.offsetTop - rail.offsetTop;
        var want2 = rail.scrollTop;
        if (aTop < rail.scrollTop + 24) want2 = Math.max(0, aTop - 24);
        else if (aTop > rail.scrollTop + rail.clientHeight - 60) want2 = Math.min(overflow, aTop - rail.clientHeight + 60);
        if (want2 !== rail.scrollTop) easeRailTo(want2);
      }
    }

    // a plain timer rather than requestAnimationFrame: rAF is suspended while
    // the tab is in the background, which would leave the highlight stale
    var ticking = false;
    global.__dcTocScroll = function () {
      if (ticking) return;
      ticking = true;
      setTimeout(function () { ticking = false; place(); reveal(); onScroll(); }, 16);
    };
    window.addEventListener('scroll', global.__dcTocScroll, { passive: true });
    window.addEventListener('resize', global.__dcTocScroll);
    onScroll();
  }

  var prev = global.__dcAfterRender;
  global.__dcAfterRender = function () {
    if (prev) prev();
    init();
  };
  // Run once on load for every page. Interactive pages also re-run init via
  // __dcAfterRender (dc-runtime replaces #dc-root on each render); static pages
  // (SSR, no dc-runtime) rely solely on this, so it must fire on its own.
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})(window);

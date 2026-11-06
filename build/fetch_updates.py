#!/usr/bin/env python3
"""Collect candidate items for the "Latest on cancer in India" section.

Nothing collected here reaches the page on its own. Every candidate lands in
updates_queue.json with status "pending"; an editor approves or rejects it with
review_updates.py, and only approved items (copied to updates.json) are rendered
by build.py.

Headlines are kept verbatim from the source. Nothing is summarised or rewritten.

Sources
  feeds     WHO news (the site's own OData API: the news RSS is a frozen legacy feed whose
            83 items are 2003-2020 stories with re-stamped pubDates), IARC RSS (site feed +
            pressrelease + news-events post types),
            PIB press releases (English RSS + today's all-releases page)
  monitors  ICMR-NINE homepage (formerly ICMR-NCDIR; ncdirindia.org now points there),
            GLOBOCAN India fact sheet PDF (the GCO page itself is a JS app shell)

Run:  python3 fetch_updates.py            fetch, filter, append new candidates
      python3 fetch_updates.py --dry-run  print what would be queued, write nothing
"""
import argparse, datetime as dt, email.utils, hashlib, html, json, os, re, ssl, sys, time
import urllib.error, urllib.request
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
QUEUE = os.path.join(HERE, 'updates_queue.json')
APPROVED = os.path.join(HERE, 'updates.json')
STATE = os.path.join(HERE, 'updates_state.json')

LOOKBACK_DAYS = 120          # feed items older than this are ignored
UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/130 Safari/537.36')
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))

WHO_API = ('https://www.who.int/api/news/newsitems?sf_culture=en'
           '&$orderby=PublicationDateAndTime%20desc&$top=100&$skip={skip}'   # $top above 100 is a 400
           '&$select=Title,ItemDefaultUrl,PublicationDateAndTime')
FEEDS = [
    # (source label, rss url)
    # the site-wide feed only carries 5 stale posts; the real content is in these post types
    ('IARC', 'https://www.iarc.who.int/feed/?post_type=pressrelease'),
    ('IARC', 'https://www.iarc.who.int/feed/?post_type=news-events'),
    ('IARC', 'https://www.iarc.who.int/feed/'),
]
# PIB: there is no Ministry of Health feed. The English press-release feed works once the
# region param is present (without &reg= it 302s to the Hindi feed) but holds only the
# latest ~20 releases across all ministries, so today's all-releases page is read too.
PIB_RSS = 'https://www.pib.gov.in/RssMain.aspx?ModId=6&Lang=1&Regid=3&reg=3'
PIB_ALLREL = 'https://www.pib.gov.in/allRel.aspx?reg=3&lang=1'
PIB_RELEASE = 'https://pib.gov.in/PressReleasePage.aspx?PRID=%s'
NINE_HOME = 'https://icmrnine.org/'
GCO_INDIA_PAGE = 'https://gco.iarc.who.int/today/en/fact-sheets-populations/356/india'
GCO_INDIA_PDF = 'https://gco.iarc.who.int/media/globocan/factsheets/populations/356-india-fact-sheet.pdf'

# ---------------------------------------------------------------- relevance rules
# A candidate needs a STRONG term, or a WEAK term together with a SITE term
# ("screening" alone also matches TB or diabetes screening).
STRONG = [r'cancers?', r'oncolog\w*', r'tumou?rs?', r'carcinoma\w*', r'carcinogen\w*', r'malignan\w*',
          r'leuka?emia\w*', r'lymphoma\w*', r'melanoma\w*', r'myeloma\w*', r'sarcoma\w*', r'glioma\w*',
          r'HPV', r'human papillomavirus', r'mammogra\w*', r'pap smears?', r'chemotherap\w*',
          r'radiotherap\w*', r'immunotherap\w*', r'metasta\w*', r'GLOBOCAN', r'cancer registr\w*']
WEAK = [r'screening', r'biops\w*', r'early detection', r'tobacco', r'areca', r'gutka', r'betel']
SITE = [r'breast', r'cervi\w*', r'oral', r'mouth', r'lung', r'colorectal', r'colon', r'prostate',
        r'liver', r'stomach', r'gastric', r'oesophag\w*', r'esophag\w*', r'ovar\w*', r'thyroid', r'blood']
INDIA = [r'India', r'Indian', r'Bharat', r'ICMR', r'NCDIR', r'NINE', r'MoHFW', r'Ayushman', r'PM-?JAY',
         r'NP-?NCD', r'AIIMS', r'Tata Memorial', r'CGHS', r'Delhi', r'Mumbai', r'Kolkata', r'Chennai',
         r'Bengaluru', r'Bangalore', r'Hyderabad', r'Kerala', r'Tamil Nadu', r'Karnataka', r'Maharashtra',
         r'Gujarat', r'Punjab', r'Assam', r'Mizoram', r'Meghalaya', r'Bihar', r'Uttar Pradesh', r'Rajasthan',
         r'West Bengal', r'Odisha', r'Andhra Pradesh', r'Telangana', r'Madhya Pradesh', r'Jharkhand']
REGION = [r'South-East Asia', r'South Asia', r'SEARO', r'low- and middle-income', r'LMICs?',
          r'low-resource']


def _rx(terms):
    return re.compile(r'\b(%s)\b' % '|'.join(terms), re.I)


RX_STRONG, RX_WEAK, RX_SITE, RX_INDIA, RX_REGION = map(_rx, (STRONG, WEAK, SITE, INDIA, REGION))
RX_INDIA_CS = re.compile(r'\b(%s)\b' % '|'.join(INDIA))   # case-sensitive: "nine" is not ICMR-NINE


def hits(rx, text):
    return sorted({m.group(1).lower() for m in rx.finditer(text or '')})


def score(title, desc, india_default=0):
    """-> (is_relevant, cancer_score, india_score, matched_terms)."""
    t_strong, d_strong = hits(RX_STRONG, title), hits(RX_STRONG, desc)
    t_weak, d_weak = hits(RX_WEAK, title), hits(RX_WEAK, desc)
    t_site, d_site = hits(RX_SITE, title), hits(RX_SITE, desc)
    relevant = bool(t_strong or d_strong or ((t_weak or d_weak) and (t_site or d_site)))
    cancer = 3 * len(t_strong) + len(d_strong) + len(t_weak) + (1 if (t_weak or d_weak) and (t_site or d_site) else 0)
    t_in = sorted({m.group(1) for m in RX_INDIA_CS.finditer(title or '')})
    d_in = sorted({m.group(1) for m in RX_INDIA_CS.finditer(desc or '')})
    t_reg, d_reg = hits(RX_REGION, title), hits(RX_REGION, desc)
    india = india_default + 3 * len(t_in) + len(d_in) + (1 if (t_reg or d_reg) else 0)
    terms = {'cancer': sorted(set(t_strong + d_strong + t_weak + d_weak)), 'india': sorted(set(t_in + d_in + t_reg + d_reg))}
    return relevant, cancer, india, terms


# ---------------------------------------------------------------- http
_CTX_UNVERIFIED = ssl._create_unverified_context()


def get(url, head=False, tries=3):
    """GET (or HEAD) with a browser UA. Falls back to an unverified SSL context when the local
    CA bundle cannot validate the host (the laptop's python.org build needs this for some gov hosts)."""
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept-Language': 'en'},
                                 method='HEAD' if head else 'GET')
    ctx = None
    for i in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=40, context=ctx) as r:
                return r.status, dict(r.headers), (b'' if head else r.read()), r.geturl()
        except urllib.error.URLError as e:
            if isinstance(e.reason, ssl.SSLError) and ctx is None:
                ctx = _CTX_UNVERIFIED
                continue
            if isinstance(e, urllib.error.HTTPError) and e.code < 500:
                raise
            if i == tries - 1:
                raise
            time.sleep(2 * (i + 1))


def text_of(s):
    s = re.sub(r'<[^>]+>', ' ', s or '')
    return re.sub(r'\s+', ' ', html.unescape(s)).strip()


# ---------------------------------------------------------------- dates
def iso_from_rfc822(s):
    try:
        return email.utils.parsedate_to_datetime(s.replace(' Z', ' +0000')).astimezone(IST).date().isoformat()
    except Exception:
        return None


def today():
    return dt.datetime.now(IST).date().isoformat()


def now_iso():
    return dt.datetime.now(IST).replace(microsecond=0).isoformat()


def item_id(url):
    return hashlib.sha1(url.encode()).hexdigest()[:8]


def norm_title(t):
    return re.sub(r'[^a-z0-9]+', ' ', (t or '').lower()).strip()


def make(source, title, url, date, desc='', india_default=0, **extra):
    rel, c, i, terms = score(title, desc, india_default)
    if not rel:
        return None
    d = dict(id=item_id(url), status='pending', kind='article', title=title, source=source, date=date, url=url,
             cancer_score=c, india_score=i, terms=terms, fetched_at=now_iso())
    d.update(extra)
    return d


# ---------------------------------------------------------------- sources
def fetch_feed(source, url, log):
    _, _, body, _ = get(url)
    root = ET.fromstring(body.lstrip(b'\xef\xbb\xbf'))
    items = root.findall('.//item')
    out, cutoff = [], (dt.date.today() - dt.timedelta(days=LOOKBACK_DAYS)).isoformat()
    for it in items:
        title = text_of(it.findtext('title'))
        link = (it.findtext('link') or '').strip()
        if not title or not link:
            continue
        date = iso_from_rfc822(it.findtext('pubDate') or '')
        if not date or date < cutoff:
            continue
        c = make(source, title, link, date, text_of(it.findtext('description')), via=url)
        if c:
            out.append(c)
    log.append('%-5s %3d items, %d cancer-relevant in last %dd  (%s)' % (source, len(items), len(out), LOOKBACK_DAYS, url))
    return out


def fetch_who(log):
    out, cutoff = [], (dt.date.today() - dt.timedelta(days=LOOKBACK_DAYS)).isoformat()
    items = []
    for skip in range(0, 1000, 100):  # newest first; page until past the lookback window
        page = json.loads(get(WHO_API.format(skip=skip))[2])['value']
        items += page
        if not page or (page[-1].get('PublicationDateAndTime') or '')[:10] < cutoff:
            break
    for it in items:
        date = (it.get('PublicationDateAndTime') or '')[:10]
        if not it.get('Title') or not it.get('ItemDefaultUrl') or date < cutoff:
            continue
        c = make('WHO', text_of(it['Title']), 'https://www.who.int/news/item' + it['ItemDefaultUrl'], date, via='WHO news API')
        if c:
            out.append(c)
    log.append('WHO   %d latest news items, %d cancer-relevant in last %dd  (who.int/api/news)' % (len(items), len(out), LOOKBACK_DAYS))
    return out


def pib_release(prid):
    """-> (ministry, iso_date, full_title) read from the release page."""
    _, _, body, _ = get(PIB_RELEASE % prid)
    s = body.decode('utf-8', 'replace')
    mm = re.search(r'MinistryNameSub[Hh]ead[^>]*>([^<]*)', s)
    dm = re.search(r'(\d{1,2}) (JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC) (\d{4})', s)
    tm = re.search(r'og:title" content="([^"]*)"', s)
    date = dt.datetime.strptime(' '.join(dm.groups()), '%d %b %Y').date().isoformat() if dm else None
    return (text_of(mm.group(1)) if mm else ''), date, (html.unescape(tm.group(1)).strip() if tm else '')


def fetch_pib(log):
    seen = {}
    _, _, body, _ = get(PIB_RSS)
    root = ET.fromstring(body.lstrip(b'\xef\xbb\xbf'))
    for it in root.findall('.//item'):
        m = re.search(r'PRID=(\d+)', it.findtext('link') or '')
        if m:
            seen[m.group(1)] = text_of(it.findtext('title'))
    n_rss = len(seen)
    _, _, body, _ = get(PIB_ALLREL)
    for m in re.finditer(r"<a title='([^']*)' href='/PressReleaseDetail\.aspx\?PRID=(\d+)'", body.decode('utf-8', 'replace')):
        seen.setdefault(m.group(2), html.unescape(m.group(1)).strip())
    out = []
    for prid, title in seen.items():
        if not score(title, '')[0]:
            continue  # only cancer-relevant titles cost a page fetch
        ministry, date, full = pib_release(prid)
        if full.startswith(title.rstrip(' .')) or not title:
            title = full or title
        src = 'PIB' if not ministry else (ministry if ministry.startswith('PIB') else 'PIB, ' + ministry)
        c = make(src, title, PIB_RELEASE % prid, date or today(),
                 india_default=5, ministry=ministry, via='PIB')
        if c:
            out.append(c)
    log.append('PIB   %d releases (rss %d + today\'s list), %d cancer-relevant' % (len(seen), n_rss, len(out)))
    return out


def nine_sections(s):
    """Pull the parts of icmrnine.org that announce new things: the marquee, Featured
    Publications and the Important Link box. -> (section_text_for_hash, [(title, url)])."""
    parts, links = [], []
    m = re.search(r'id="marqueeText"(.*?)</div>', s, re.S)
    if m:
        parts.append(text_of(m.group(1)))
    m = re.search(r'Featured Publications(.*?)featuredPublicationsCarousel"\s*data-slide', s, re.S) or \
        re.search(r'Featured Publications(.*?)</ol>', s, re.S)
    fp = m.group(1) if m else ''
    for a in re.finditer(r'<li>\s*<p>\s*<b>\s*<a href="([^"]+)"[^>]*>(.*?)</a>', fp, re.S):
        links.append((text_of(a.group(2)), a.group(1)))
    m = re.search(r'Important Link(.*?)</div>\s*</div>', s, re.S)
    imp = m.group(1) if m else ''
    imp_links = [(text_of(a.group(2)), a.group(1)) for a in re.finditer(r'<a [^>]*href="([^"]+)"[^>]*>(.*?)</a>', imp, re.S)]
    parts += ['%s %s' % l for l in links + imp_links]
    return '\n'.join(parts), links, imp_links


def absolute(base, href):
    return href if href.startswith('http') else base.rstrip('/') + '/' + href.lstrip('/')


def monitor_nine(state, log):
    _, _, body, final = get(NINE_HOME)
    s = body.decode('utf-8', 'replace')
    text, pubs, imp = nine_sections(s)
    h = hashlib.sha256(text.encode()).hexdigest()
    st = state.setdefault('icmr_nine', {})
    first, changed = 'hash' not in st, st.get('hash') != h
    seen = set(st.get('seen_links', []))
    out = []
    # Featured publications carry real titles: queue the cancer-relevant ones verbatim. Keyed on
    # title + link, because the site has given several titles the same (wrong) link before.
    shared = {}
    for _, href in pubs:
        shared[href] = shared.get(href, 0) + 1
    for title, href in pubs:
        url = absolute(NINE_HOME, href)
        key = '%s|%s' % (url, title)
        if key in seen:
            continue
        c = make('ICMR-NINE', title, url, today(), india_default=5, date_source='first seen on icmrnine.org', via=NINE_HOME)
        if c:
            c['id'] = item_id(key)
            if shared[href] > 1:
                c['warning'] = ('icmrnine.org links %d featured publications to this same URL; open it and confirm '
                                'it is this paper before approving (use --url to correct it)' % shared[href])
            out.append(c)
    # The Important Link box only has generic labels ("ICMR - NINE Press Release"); a new target
    # file there becomes a page-change alert that the editor titles by hand.
    new_imp = [(t, absolute(NINE_HOME, u)) for t, u in imp if absolute(NINE_HOME, u) not in seen]
    if new_imp and not first:
        out.append(page_change('ICMR-NINE', NINE_HOME, 'New file(s) in the "Important Link" box on icmrnine.org',
                               [{'label': t, 'url': u} for t, u in new_imp]))
    st.update(hash=h, checked_at=now_iso(), seen_links=sorted(
        seen | {'%s|%s' % (absolute(NINE_HOME, u), t) for t, u in pubs} | {absolute(NINE_HOME, u) for _, u in imp}))
    if changed and not first:
        st['changed_at'] = now_iso()
    log.append('NINE  homepage %s, %d featured publications, %d queued' %
               ('baseline recorded' if first else ('CHANGED' if changed else 'unchanged'), len(pubs), len(out)))
    return out


def page_change(source, url, label, changes, date=None):
    key = '%s#%s' % (url, hashlib.sha1(json.dumps(changes, sort_keys=True).encode()).hexdigest()[:10])
    return dict(id=item_id(key), status='pending', kind='page_change', title='', label=label, source=source,
                date=date or today(), url=url, changes=changes, cancer_score=0, india_score=5,
                terms={}, fetched_at=now_iso())


def monitor_globocan(state, log):
    """The GCO fact-sheet page is a JS app shell (its HTML never changes with the data), so the
    published PDF behind it is watched: ETag + Last-Modified + SHA-256 of the bytes."""
    _, hdr, body, _ = get(GCO_INDIA_PDF)
    hdr = {k.lower(): v for k, v in hdr.items()}
    h = hashlib.sha256(body).hexdigest()
    st = state.setdefault('globocan_india', {})
    first, changed = 'hash' not in st, st.get('hash') != h
    lm = hdr.get('last-modified', '')
    lm_iso = iso_from_rfc822(lm) if lm else None
    out = []
    recent = lm_iso and lm_iso >= (dt.date.today() - dt.timedelta(days=LOOKBACK_DAYS)).isoformat()
    if (changed and not first) or (first and recent):
        out.append(page_change('IARC Global Cancer Observatory', GCO_INDIA_PAGE,
                               'GLOBOCAN India fact sheet PDF %s (Last-Modified %s)' % ('changed' if not first else 'recently updated', lm or 'n/a'),
                               [{'label': 'India fact sheet PDF', 'url': GCO_INDIA_PDF, 'etag': hdr.get('etag', ''),
                                 'last_modified': lm, 'sha256': h, 'bytes': len(body)}], date=lm_iso))
    st.update(hash=h, etag=hdr.get('etag', ''), last_modified=lm, bytes=len(body), checked_at=now_iso())
    log.append('GCO   India fact sheet PDF %s, Last-Modified %s, %d queued' %
               ('baseline recorded' if first else ('CHANGED' if changed else 'unchanged'), lm or 'n/a', len(out)))
    return out


# ---------------------------------------------------------------- queue io
def load(path, default):
    if os.path.exists(path):
        with open(path, encoding='utf8') as f:
            return json.load(f)
    return default


def save(path, data):
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write('\n')
    os.replace(tmp, path)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--dry-run', action='store_true', help='print candidates, write nothing')
    args = ap.parse_args()

    queue = load(QUEUE, {'items': []})
    state = load(STATE, {})
    known_ids = {i['id'] for i in queue['items']}
    known_titles = {norm_title(i['title']) for i in queue['items'] if i.get('title')}

    log, found, errors = [], [], []
    jobs = [(u, lambda s=s, u=u: fetch_feed(s, u, log)) for s, u in FEEDS]
    jobs += [('WHO', lambda: fetch_who(log)), ('PIB', lambda: fetch_pib(log)), ('ICMR-NINE', lambda: monitor_nine(state, log)),
             ('GLOBOCAN', lambda: monitor_globocan(state, log))]
    for name, job in jobs:
        try:
            found += job()
        except Exception as e:  # one dead source must not stop the others
            errors.append('%s: %r' % (name, e))

    new = []
    for c in sorted(found, key=lambda c: (c['india_score'], c['date']), reverse=True):
        nt = norm_title(c['title'])
        if c['id'] in known_ids or (nt and nt in known_titles):
            continue  # already queued (IARC posts the same story as news + press release)
        known_ids.add(c['id'])
        if nt:
            known_titles.add(nt)
        new.append(c)

    print('\n'.join(log))
    for e in errors:
        print('ERROR', e, file=sys.stderr)
    print('\n%d new candidate(s)%s' % (len(new), ' (dry run)' if args.dry_run else ''))
    for c in new:
        print('  [%s] %s  %-34s india=%d cancer=%d  %s' % (c['id'], c['date'], c['source'][:34], c['india_score'],
                                                         c['cancer_score'], c['title'] or c['label']))
        if c.get('warning'):
            print('             WARNING: ' + c['warning'])
    if not args.dry_run:
        queue['items'] += new
        queue['updated_at'] = now_iso()
        save(QUEUE, queue)
        save(STATE, state)
    return 1 if errors and not found else 0


if __name__ == '__main__':
    sys.exit(main())

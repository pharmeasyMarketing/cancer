#!/usr/bin/env python3
"""Crawl every link on the built cancer hub pages and record which ones are dead.

Collects links from the homepage, every inner page in pages.json, the drug-table popup data
(assets/data/drug-more.json) and the shared header/footer (assets/js/pe-shell.js), checks each URL
once and writes build/link_status.json. build.py and pages.py then remove dead links at build time.

Dead means the server answered 404 or 410, nothing else. A 403, 429, 5xx, a bot challenge or a
timeout is recorded as "unverified" and the link stays: it may be a block, not a missing page.

pharmeasy.in is paced at ~40 requests a minute (its bot challenge trips near 60) with retries on
its 405 "Human Verification" response. /cancer/ links are checked against the CyberPanel origin
(72.60.200.28) because CloudFront does not route /cancer to it yet; once it does, they are checked
like any other pharmeasy.in URL.

Medicine and molecule links (pharmeasy.in/online-medicine-order/..., /molecules/...) always point at the
URL the PharmEasy page itself declares: its <link rel="canonical">. PharmEasy leaves the canonical out on
pages it sets to NOINDEX; for those the checker records the page's own slug URL (same product or molecule
id, taken from the page data) as "self_url", so a short numeric link like /online-medicine-order/11353
still becomes /online-medicine-order/exeget-25mg-strip-of-10-tablets-11353. The builders link whichever
of the two was found, once the target itself answers 200.

Run:  python3 check_links.py            check URLs not checked in the last 7 days
      python3 check_links.py --daily    as above, plus every medicine/molecule link and its canonical
                                        target, whatever their age (the daily GitHub job runs this)
      python3 check_links.py --all      recheck everything

A recheck that only fails to get through (bot challenge, timeout, 5xx) keeps the last good result, so a
bad crawl day never reverts a link to its short URL. 404/410 still replaces it.
"""
import collections, concurrent.futures as cf, datetime as dt, html, json, os, re, ssl, subprocess, sys, threading, time
import urllib.error, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
OUT = os.path.join(HERE, 'link_status.json')
ORIGIN_IP = '72.60.200.28'
UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36'
MAX_AGE_DAYS = 7
DEAD = {404, 410}
CTX = ssl._create_unverified_context()
PRODUCT = re.compile(r'^https://(?:www\.)?pharmeasy\.in/(online-medicine-order|molecules)/([^/?#]+)')


def is_product(u):
    return bool(PRODUCT.match(u))


def self_url_of(u, page_html):
    """For a medicine/molecule page with no canonical: the page's own slug URL (same section, same id)."""
    m = PRODUCT.match(u)
    idm = re.search(r'(\d+)$', m.group(2)) if m else None
    if not idm:
        return ''
    sec, pid = m.group(1), idm.group(1)
    t = page_html.replace('\\/', '/')
    found = re.search(r'pharmeasy\.in/%s/([a-z0-9][a-z0-9-]*-%s)(?=["\'?#/\\<\s])' % (sec, pid), t)
    if not found:
        found = re.search(r'"slug":"([a-z0-9][a-z0-9-]*-%s)"' % pid, t)
    if not found:
        return ''
    out = 'https://pharmeasy.in/%s/%s' % (sec, found.group(1))
    return '' if out == u else out


def collect():
    """Every link as the builders wrote it, before dead-link removal and canonical swaps (all_links.json,
    written by build.py/pages.py), plus the shared header/footer. Falls back to scanning the pages."""
    al = os.path.join(HERE, 'all_links.json')
    if os.path.exists(al):
        urls = collections.defaultdict(set)
        for page, lst in json.load(open(al, encoding='utf8')).items():
            for u in lst:
                urls[u].add(page)
        shell = open(os.path.join(ROOT, 'assets', 'js', 'pe-shell.js'), encoding='utf8').read()
        for u in re.findall(r'href=\\?[\'"](https?://[^\'"\\]+)', shell):
            urls[html.unescape(u).split('#')[0]].add('assets/js/pe-shell.js')
        return urls
    return collect_from_pages()


def collect_from_pages():
    pages = ['index.html'] + [p['path'] + 'index.html' for p in json.load(open(os.path.join(HERE, 'pages.json')))['pages']]
    urls = collections.defaultdict(set)
    for p in pages:
        f = os.path.join(ROOT, p)
        if not os.path.exists(f):
            continue
        for u in re.findall(r'<a\b[^>]*\bhref="(https?://[^"]+)"', open(f, encoding='utf8').read()):
            urls[html.unescape(u).split('#')[0]].add(p)
    for g in json.load(open(os.path.join(ROOT, 'assets', 'data', 'drug-more.json')))['groups'].values():
        for m in g['molecules']:
            urls[m['url']].add('assets/data/drug-more.json')
    shell = open(os.path.join(ROOT, 'assets', 'js', 'pe-shell.js'), encoding='utf8').read()
    for u in re.findall(r'href=\\?[\'"](https?://[^\'"\\]+)', shell):
        urls[html.unescape(u).split('#')[0]].add('assets/js/pe-shell.js')
    return urls


def host(u):
    return re.match(r'https?://([^/]+)', u).group(1).lower()


class Pacer:
    """Minimum gap between requests to one host."""
    def __init__(self):
        self.last, self.lock = {}, threading.Lock()

    def wait(self, h, gap):
        with self.lock:
            t = max(time.time(), self.last.get(h, 0) + gap)
            self.last[h] = t
        time.sleep(max(0, t - time.time()))


PACE = Pacer()


def canonical_of(page_html, base):
    """<link rel="canonical" href="..."> from a page head, made absolute. '' if none."""
    from urllib.parse import urljoin
    for m in re.finditer(r'<link\b[^>]*>', page_html, re.I):
        tag = m.group(0)
        if re.search(r'rel=["\']?canonical["\'\s>]', tag, re.I):
            h = re.search(r'href=["\']([^"\']+)["\']', tag, re.I)
            if h:
                return urljoin(base, html.unescape(h.group(1).strip()))
    return ''


def fetch(u):
    """-> (status, final_url, canonical_or_note[, '\tNOINDEX'][, '\tSELF ' + self_url])."""
    h = host(u)
    if re.match(r'https?://(www\.)?pharmeasy\.in/cancer(/|$)', u):
        # CyberPanel origin, asked directly with the public host name
        r = subprocess.run(['curl', '-sk', '-o', '/dev/null', '-w', '%{http_code}', '--max-time', '25',
                            '--resolve', 'pharmeasy.in:443:' + ORIGIN_IP, u], capture_output=True, text=True)
        return int(r.stdout or 0), u, ''
    gap = 1.5 if h.endswith('pharmeasy.in') else 1.0
    for attempt in range(4):
        PACE.wait(h, gap)
        req = urllib.request.Request(u, headers={'User-Agent': UA, 'Accept': 'text/html,*/*', 'Accept-Language': 'en'})
        try:
            with urllib.request.urlopen(req, timeout=30, context=CTX) as r:
                canon = ''
                if 'html' in (r.headers.get('Content-Type') or ''):
                    head = b''
                    while len(head) < 600000 and b'</head>' not in head.lower():
                        chunk = r.read(65536)
                        if not chunk:
                            break
                        head += chunk
                    txt = head.decode('utf8', 'replace')
                    canon = canonical_of(txt, r.geturl())
                    rb = re.search(r'<meta\s+name=["\']robots["\']\s+content=["\']([^"\']*)', txt, re.I)
                    noindex = bool(rb and 'noindex' in rb.group(1).lower())
                    selfu = ''
                    if not canon and is_product(u):
                        # no canonical (PharmEasy NOINDEX pages): read the page data for its own slug URL
                        body = head + r.read(4000000)
                        selfu = self_url_of(u, body.decode('utf8', 'replace'))
                    if noindex:
                        canon += '\tNOINDEX'
                    if selfu:
                        canon += '\tSELF ' + selfu
                else:
                    r.read(2048)
                return r.status, r.geturl(), canon
        except urllib.error.HTTPError as e:
            if e.code == 405 and h.endswith('pharmeasy.in'):      # bot challenge burst: back off and retry
                time.sleep(20 * (attempt + 1))
                continue
            if e.code in (429, 503) and attempt < 3:
                time.sleep(10 * (attempt + 1))
                continue
            return e.code, u, ''
        except Exception as e:  # timeouts, TLS, DNS
            if attempt < 2:
                time.sleep(5)
                continue
            return 0, u, 'error: ' + type(e).__name__ + ': ' + str(e)[:80]
    return 405, u, 'error: bot challenge persisted'


def main():
    recheck_all = '--all' in sys.argv
    daily = '--daily' in sys.argv
    urls = collect()
    old = json.load(open(OUT)) if os.path.exists(OUT) else {}
    cutoff = (dt.datetime.now() - dt.timedelta(days=MAX_AGE_DAYS)).isoformat()
    todo = [u for u in urls if recheck_all or (daily and is_product(u)) or u not in old or old[u].get('checked', '') < cutoff]
    print('%d links on the pages, %d to check' % (len(urls), len(todo)))
    res = {u: v for u, v in old.items() if u in urls}
    old.setdefault('_canonical_targets', {})
    done = [0]

    def one(u):
        st, final, extra = fetch(u)
        note = extra if extra.startswith('error:') else ''
        parts = ('' if note else extra).split('\t')
        canon = parts[0]
        robots = 'NOINDEX' in parts[1:]
        selfu = next((x[5:] for x in parts[1:] if x.startswith('SELF ')), '')
        verdict = 'dead' if st in DEAD else ('ok' if 200 <= st < 400 else 'unverified')
        now = dt.datetime.now().replace(microsecond=0).isoformat()
        prev = old.get(u)
        if verdict == 'unverified' and isinstance(prev, dict) and prev.get('verdict') == 'ok':
            # could not get through this time: keep the last good result (and its canonical)
            rec = dict(prev)
            rec['last_failed'] = {'status': st, 'at': now}
            rec['found_on'] = sorted(urls[u])
            done[0] += 1
            return u, rec
        rec = {'status': st, 'verdict': verdict, 'checked': now, 'found_on': sorted(urls[u])}
        if final != u:
            rec['final_url'] = final
        if note:
            rec['note'] = note
        if canon:
            rec['canonical'] = canon
        if selfu:
            rec['self_url'] = selfu
        if robots:
            rec['robots'] = 'noindex'
        done[0] += 1
        if done[0] % 50 == 0:
            print('  %d/%d' % (done[0], len(todo)), flush=True)
        return u, rec

    # one worker per host keeps the per-host pacing simple; many hosts run in parallel
    by_host = collections.defaultdict(list)
    for u in todo:
        by_host[host(u)].append(u)
    with cf.ThreadPoolExecutor(max_workers=16) as ex:
        futs = [ex.submit(lambda us: [one(u) for u in us], us) for us in by_host.values()]
        for f in cf.as_completed(futs):
            for u, rec in f.result():
                res[u] = rec
    # second pass: a canonical we would switch a link to must itself work
    def target(u, v):
        return v.get('canonical') or v.get('self_url') or ''
    every = {target(u, v) for u, v in res.items() if not u.startswith('_') and target(u, v) and target(u, v) != u}
    known = set(old.get('_canonical_targets', {}))
    # --daily rechecks every medicine/molecule target so a canonical that stops working is dropped next day
    fresh = {target(u, v) for u, v in res.items() if not u.startswith('_') and daily and is_product(u)} - {''}
    targets = sorted((every - set(res) - known) | (fresh & every) - set(res))
    canon_status = dict(old.get('_canonical_targets', {})) if not recheck_all else {}
    if targets:
        print('checking %d canonical targets' % len(targets))
        by_h = collections.defaultdict(list)
        for t in targets:
            by_h[host(t)].append(t)
        with cf.ThreadPoolExecutor(max_workers=16) as ex:
            for f in cf.as_completed([ex.submit(lambda ts: [(t, fetch(t)[0]) for t in ts], ts) for ts in by_h.values()]):
                for t, st in f.result():
                    st = st if isinstance(st, int) else 0
                    was = canon_status.get(t)
                    if st not in DEAD and not 200 <= st < 400 and isinstance(was, int) and 200 <= was < 400:
                        continue          # blocked this time: keep the last good status
                    canon_status[t] = st
    for u in res:
        res[u]['found_on'] = sorted(urls[u])
    res['_canonical_targets'] = canon_status
    json.dump(dict(sorted(res.items())), open(OUT, 'w'), indent=1, ensure_ascii=False)
    c = collections.Counter(v['verdict'] for k, v in res.items() if not k.startswith('_'))
    print('ok %d, dead %d, unverified %d  ->  build/link_status.json' % (c['ok'], c['dead'], c['unverified']))
    for u, v in sorted(res.items()):
        if u.startswith('_'):
            continue
        if v['verdict'] != 'ok':
            print('  %-10s %3s %s' % (v['verdict'], v['status'], u))


if __name__ == '__main__':
    main()

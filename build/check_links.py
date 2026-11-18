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

Run:  python3 check_links.py            check URLs not checked in the last 7 days
      python3 check_links.py --all      recheck everything
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


def collect():
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


def fetch(u):
    """-> (status, final_url, note)."""
    h = host(u)
    if re.match(r'https?://(www\.)?pharmeasy\.in/cancer(/|$)', u):
        # CyberPanel origin, asked directly with the public host name
        r = subprocess.run(['curl', '-sk', '-o', '/dev/null', '-w', '%{http_code}', '--max-time', '25',
                            '--resolve', 'pharmeasy.in:443:' + ORIGIN_IP, u], capture_output=True, text=True)
        return int(r.stdout or 0), u, 'checked at the CyberPanel origin'
    gap = 1.5 if h.endswith('pharmeasy.in') else 1.0
    for attempt in range(4):
        PACE.wait(h, gap)
        req = urllib.request.Request(u, headers={'User-Agent': UA, 'Accept': 'text/html,*/*', 'Accept-Language': 'en'})
        try:
            with urllib.request.urlopen(req, timeout=30, context=CTX) as r:
                r.read(2048)
                return r.status, r.geturl(), ''
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
            return 0, u, type(e).__name__ + ': ' + str(e)[:80]
    return 405, u, 'bot challenge persisted'


def main():
    recheck_all = '--all' in sys.argv
    urls = collect()
    old = json.load(open(OUT)) if os.path.exists(OUT) else {}
    cutoff = (dt.datetime.now() - dt.timedelta(days=MAX_AGE_DAYS)).isoformat()
    todo = [u for u in urls if recheck_all or u not in old or old[u].get('checked', '') < cutoff]
    print('%d links on the pages, %d to check' % (len(urls), len(todo)))
    res = {u: v for u, v in old.items() if u in urls}
    done = [0]

    def one(u):
        st, final, note = fetch(u)
        verdict = 'dead' if st in DEAD else ('ok' if 200 <= st < 400 else 'unverified')
        rec = {'status': st, 'verdict': verdict, 'checked': dt.datetime.now().replace(microsecond=0).isoformat(),
               'found_on': sorted(urls[u])}
        if final != u:
            rec['final_url'] = final
        if note:
            rec['note'] = note
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
    for u in res:
        res[u]['found_on'] = sorted(urls[u])
    json.dump(dict(sorted(res.items())), open(OUT, 'w'), indent=1, ensure_ascii=False)
    c = collections.Counter(v['verdict'] for v in res.values())
    print('ok %d, dead %d, unverified %d  ->  build/link_status.json' % (c['ok'], c['dead'], c['unverified']))
    for u, v in sorted(res.items()):
        if v['verdict'] != 'ok':
            print('  %-10s %3s %s' % (v['verdict'], v['status'], u))


if __name__ == '__main__':
    main()

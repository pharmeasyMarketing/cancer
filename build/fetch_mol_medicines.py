#!/usr/bin/env python3
"""Fetch the medicines PharmEasy lists for each molecule behind a "+N more" brand chip.

The docs end each molecule's brand chips with "+N more", linked to the molecule page. On the hub that chip
opens a card listing those medicines (assets/js/cancer.js), so the reader does not have to leave the page.
The list comes from the API PharmEasy's own molecule page uses for its medicine list:

    GET https://pharmeasy.in/api/moleculeDetails/fetchMoleculeMedicines/<molecule id>?page=<n>

10 products a page, an empty page ends the list. Only the name and the product URL are kept
(https://pharmeasy.in/online-medicine-order/<slug>, the slug the molecule page itself links); nothing
about price or stock is shown. Available products come first, in PharmEasy's order.

Writes assets/data/mol-brands.json:  {"<molecule id>": [{"n": name, "u": url, "p": product id}, ...]}
A molecule that fails to fetch keeps its previous list. Paced at ~40 requests a minute.

Run:  python3 fetch_mol_medicines.py
"""
import glob, json, os, re, ssl, sys, time, urllib.error, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', 'assets', 'data', 'mol-brands.json')
API = 'https://pharmeasy.in/api/moleculeDetails/fetchMoleculeMedicines/%s?page=%d'
UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36'
CTX = ssl._create_unverified_context()
GAP = 1.5
MAX_PAGES = 30
MORE = re.compile(r'\\?\+\d+ more\]\((https://pharmeasy\.in/molecules/[^)\s]*?(\d+))\)')
_last = [0.0]


def molecules():
    """Molecule ids behind a "+N more" chip in the homepage doc and the inner-page docs."""
    ids = set()
    for f in [os.path.join(HERE, 'source.md')] + glob.glob(os.path.join(HERE, 'pages', '*.md')):
        ids |= {m.group(2) for m in MORE.finditer(open(f, encoding='utf8').read())}
    return sorted(ids, key=int)


def get(url):
    for attempt in range(4):
        time.sleep(max(0, _last[0] + GAP - time.time()))
        _last[0] = time.time()
        req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': 'application/json'})
        try:
            with urllib.request.urlopen(req, timeout=30, context=CTX) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code in (405, 429, 503) and attempt < 3:     # bot challenge / rate limit: back off
                time.sleep(20 * (attempt + 1))
                continue
            raise
        except Exception:
            if attempt < 3:
                time.sleep(5)
                continue
            raise


SMALL = {'of', 'for', 'and', 'in', 'with', 'per'}
UNIT = re.compile(r'(?i)\b(\d+(?:\.\d+)?)(\s?)(mg|ml|mcg|gm|g|iu|kg)\b')


def nice(name):
    """'PLATIN 50MG VIAL OF 50ML SOLUTION FOR INFUSION' -> 'Platin 50mg Vial of 50ml Solution for Infusion'."""
    words = name.strip().split()
    out = [w.lower() if i and w.lower() in SMALL else w[:1].upper() + w[1:].lower() for i, w in enumerate(words)]
    return UNIT.sub(lambda m: m.group(1) + m.group(2) + m.group(3).lower(), ' '.join(out))


def fetch(mid):
    items, seen = [], set()
    for page in range(1, MAX_PAGES + 1):
        prods = (get(API % (mid, page)).get('data') or {}).get('products') or []
        if not prods:
            break
        for p in prods:
            pid, slug = p.get('productId'), p.get('slug')
            if not slug or pid in seen:
                continue
            seen.add(pid)
            avail = bool((p.get('productAvailabilityFlags') or {}).get('isAvailable'))
            items.append((not avail, len(items), {'n': nice(p.get('name') or slug), 'u': 'https://pharmeasy.in/online-medicine-order/' + slug, 'p': pid}))
    return [x[2] for x in sorted(items, key=lambda x: (x[0], x[1]))]


def main():
    old = json.load(open(OUT, encoding='utf8')) if os.path.exists(OUT) else {}
    ids = molecules()
    print('%d molecules behind a "+N more" chip' % len(ids))
    out, failed = {}, []
    for i, mid in enumerate(ids, 1):
        try:
            out[mid] = fetch(mid)
        except Exception as e:
            failed.append(mid)
            if mid in old:
                out[mid] = old[mid]
            print('  %s failed (%s), kept previous list' % (mid, e))
        if i % 20 == 0:
            print('  %d/%d' % (i, len(ids)), flush=True)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(out, open(OUT, 'w', encoding='utf8'), ensure_ascii=False, separators=(',', ':'))
    print('%d medicines for %d molecules -> assets/data/mol-brands.json (%d failed)'
          % (sum(len(v) for v in out.values()), len(out), len(failed)))
    if len(failed) > len(ids) // 2:
        sys.exit('more than half the molecules failed')


if __name__ == '__main__':
    main()

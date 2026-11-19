#!/usr/bin/env python3
"""Build the cancer hub's inner pages from their editorial docs (build/pages/*.md).

One generic renderer for every doc: hero (H1, reviewer byline, intro, consult card), a body made
from the doc's ## sections (paragraphs, lists, tables, the "Medicines on PharmEasy" molecule/brand
table, images), FAQs with FAQPage schema, numbered references, the explore band and the same
shell, noindex, nofollow and /cancer/ URL-plan rules as the homepage (build.py).

Doc text is kept as written. Mechanical changes only, and each is reported:
  * links to /cancer/ pages that are not in cancer_urls.txt keep their words but lose the link
  * em/en dashes become a colon, comma or hyphen (house style: no dashes in output)
  * the "Latest on ..." placeholder module (sample rows, no data) is left out
Run:  python3 pages.py            (GitHub Pages copy, noindex)
      python3 pages.py --production
"""
import base64, html, json, os, re, sys
from collections import OrderedDict, Counter

import build as B
from lib import inline, unesc, clean_url, ref_html

HERE = B.HERE
ROOT = os.path.join(HERE, '..')
SRC_DIR = os.path.join(HERE, 'pages')
CX = B.CX

# doc file -> URL path under /cancer/
ABOUT = {p['path']: p.get('about', []) for p in json.load(open(os.path.join(HERE, 'pages.json'), encoding='utf8'))['pages']}
PAGES = [(p['doc'], p['path']) for p in json.load(open(os.path.join(HERE, 'pages.json'), encoding='utf8'))['pages']]

ALLOWED = {l.strip() for l in open(B.URLS_FILE, encoding='utf8') if l.startswith('/cancer/')}

# page names for breadcrumbs and related links, from the homepage's explore band + A to Z data
NAMES = {'': 'Cancer'}
for title, _d, _ic, path, subs in B.EXPLORE:
    NAMES[path] = title
    for t, p in subs:
        NAMES.setdefault(p, t)
for name, path, subs in B.CANCER_TYPES:
    NAMES[path] = name
    for t, p in subs:
        NAMES[p] = t
NAMES.update({'symptoms/is-it-cancer/': 'Tumour or cancer?', 'prevention/hpv/': 'HPV and cancer',
              'treatment/chemotherapy/': 'Chemotherapy'})

# reviewer photos by editorial-policy slug (some docs omit the image line)
REVIEWER_IMG = {
    'dr-sarthak-moharir-195': 'https://pharmeasy.in/blog/wp-content/uploads/2026/10/Sarthak-Moharir.webp',
    'dr-swetha-dama-194': 'https://pharmeasy.in/blog/wp-content/uploads/2026/10/dr-swetha.webp',
    'dr-suvarna-kulkarni-196': 'https://pharmeasy.in/blog/wp-content/uploads/2026/10/Dr_Suvarna_Kulkarni.webp',
    '-dr-ayush-shashikant-dubey-190': B.REVIEWER_IMG,
}
REVIEWER_NAME = {'-dr-ayush-shashikant-dubey-190': B.REVIEWER}   # the doc says "Dr Ayush Dubey"; use the profile name

# embedded doc images that are prototype screenshots, not content (left out, noted for the editors)
SKIP_IMAGES = {'types/cervical-cancer/': {'image1': 'screenshot of a prototype widget ("Treatment options this library records", '
                                                    '"covered on 45 pages"); the table below it already links each treatment'}}

REPORT = OrderedDict()   # page -> list of notes for the editors


def note(page, msg):
    REPORT.setdefault(page, []).append(msg)


def esc(s):
    return html.escape(s, quote=True)


# ---------------------------------------------------------------- text clean-up
ZW = re.compile('[​‌‍﻿￼]')
LINK_MD = re.compile(r'\[([^\]]*)\]\((https?://[^)\s]+)\)')


def prep(text, page):
    """Raw doc text -> cleaned markdown (off-plan /cancer/ links unlinked, dashes normalised)."""
    text = ZW.sub('', text).replace(' ', ' ')
    text = re.sub(r'(?m)^\s*[*\-]\s+(#{2,4}\s)', r'\1', text)
    # "(https://...-\(hpv\)-...)": encode the escaped brackets so the link parses
    text = re.sub(r'\]\((https?://(?:\\.|[^)\s\\])+)\)',
                  lambda m: '](' + m.group(1).replace('\\(', '%28').replace('\\)', '%29') + ')', text)   # "* ### **Question**" -> "### **Question**"

    def unlink(m):
        url = clean_url(m.group(2))
        mm = re.match(r'https?://(?:www\.)?pharmeasy\.in(/cancer/[^?#]*)', url)
        if mm:
            path = mm.group(1) if mm.group(1).endswith('/') else mm.group(1) + '/'
            if path not in ALLOWED:
                note(page, 'link removed (page not in the URL plan): "%s" -> %s' % (unesc(m.group(1)).strip(), path))
                return m.group(1)
        return m.group(0)
    text = LINK_MD.sub(unlink, text)
    n = len(re.findall('[–—]', text))
    if n:
        note(page, '%d em/en dash(es) replaced (colon between phrases, otherwise comma or hyphen)' % n)
    text = re.sub(r'\s+—\s+', ': ', text)
    text = text.replace('—', ', ').replace('–', '-')
    return tidy(text, page)


# Visible-text clean-up found in the 18 Nov 2026 desktop + mobile review.
TYPOS = [('imgaing', 'imaging'), ('modality of choce', 'modality of choice'), ('CLosed', 'Closed'),
         ('precanceruous', 'precancerous'), ('pregant', 'pregnant'), ('duaorubicin', 'daunorubicin'),
         ('Ou can find', 'You can find'), ('can effect the total', 'can affect the total'),
         ('Factors that can effect', 'Factors that can affect'), ('child nis 14', 'child is 14'),
         ('Section 5, ide effects', 'Section 5, side effects'), ('Pharmeasy website', 'PharmEasy website'),
         ('lymphnodes', 'lymph nodes')]
META_SENTENCES = [  # editor / prototype notes that are not meant for readers
    r'[^.\n|]*\bprototype\b[^.\n|]*\.[ \t]*',
    r'\*\*Prices are read live from the product catalogue\.\*\*[ \t]*',
    r'There are no rupee figures here\.[ \t]*',
    r'This section does not give prices in rupees\.[ \t]*',
]


def tidy(text, page):
    for a, b in TYPOS:
        if a in text:
            text = text.replace(a, b)
            note(page, 'typo fixed: "%s" -> "%s"' % (a, b))
    for pat in META_SENTENCES:
        for m in re.findall(pat, text):
            note(page, 'editor note removed from the page: "%s"' % m.strip())
        text = re.sub(pat, '', text)
    # "[.16](url)", "[)9](url)", "[38.](url)", "[,63](url)": punctuation caught inside a citation link
    text = re.sub(r'\[([^\w\s\]\[]*)(\d{1,3})([^\w\s\]\[]*)\]\((https?://[^)\s]+)\)',
                  lambda m: m.group(0) if not (m.group(1) or m.group(3))
                  else '%s[%s](%s)%s' % (m.group(1), m.group(2), m.group(4), m.group(3)), text)
    # "[medicines grouped by class](url)es": a word split by the link
    text = re.sub(r'\[([^\]]*[A-Za-z][^\]]*)\]\((https?://[^)\s]+)\)([a-z]{1,3})\b', r'[\1\3](\2)', text)
    # "(CHE).42 A study": a citation typed as plain digits. Body only, never the reference list.
    parts = re.split(r'(?m)(?=^#+\s*\**References)', text, maxsplit=1)
    parts[0] = re.sub(r'(?<=[a-z)])\.(\d{1,2})(?=[\s|]|$)', lambda m: '.\x01%s\x02' % m.group(1), parts[0])
    text = ''.join(parts)
    # stray punctuation left by edits: "continuous. . In", "cancer..", "status,  .", "stage/,"
    text = re.sub(r'(?<![.\d])\.[ \t]*\.(?!\.)', '.', text)
    text = re.sub(r',[ \t]*\.', '.', text)
    text = re.sub(r'(?<=[a-z])/,(?= )', ',', text)
    # "Insurance in India- what to check" (a dash that lost its space); keep "low- and middle-income"
    text = re.sub(r'(?<=[a-z])- (?!(?:and|or|to)\b)(?=[a-z])', ': ', text)
    text = re.sub(r'(?<=[A-Za-z])- (?=\d)', ' ', text)            # "Cancer Antigen- 15-3"
    parts = re.split(r'(?m)(?=^#+\s*\**References)', text, maxsplit=1)   # "Imaging test - what each test" (was an en dash)
    parts[0] = re.sub(r'(?<=[a-z]) - (?=[a-z])', ': ', parts[0])
    text = ''.join(parts)
    text = re.sub(r'(?<=\w) +:(?=\s)', ':', text)                  # "Tests & tumour markers : what"
    return text


def fill(s):
    s = s.replace('{MONTH\\_YEAR}', B.CURRENT_MONTH_YEAR).replace('{MONTH_YEAR}', B.CURRENT_MONTH_YEAR)
    return (s.replace('{{CURRENT\\_MONTH\\_YEAR}}', B.CURRENT_MONTH_YEAR).replace('{{CURRENT_MONTH_YEAR}}', B.CURRENT_MONTH_YEAR)
             .replace('{{PUBLISHED\\_DATE}}', B.PUBLISHED_DATE).replace('{{LAST\\_UPDATED}}', B.LAST_UPDATED))


def il(s):
    return inline(fill(s))


def plain_heading(s):
    s = re.sub(r'^#+\s*', '', s.strip())
    s = s.replace('▾', '').replace('**', '')
    s = re.sub(r'^H1\s*-\s*', '', s.strip())
    return unesc(s).strip().rstrip(':').strip()


def slug(s):
    return re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')[:60]


# ---------------------------------------------------------------- block rendering
def is_table(l):
    return l.lstrip().startswith('|')


LIST_RE = re.compile(r'^(\s*)((?:>\s*)*)[*\-]\s+(.*)$')


def render_list(items):
    """items: [(level, text)] -> <ul> with one level of nesting."""
    h, sub = '<ul class="pg-list">', False
    for i, (lvl, t) in enumerate(items):
        if lvl == 0:
            if sub:
                h += '</ul>'
                sub = False
            if i:
                h += '</li>'
            h += '<li>' + il(t)
        else:
            if i == 0:
                h += '<li>'
            if not sub:
                h += '<ul>'
                sub = True
            h += '<li>%s</li>' % il(t)
    h += ('</ul>' if sub else '') + '</li></ul>'
    return '    ' + h + '\n'


def split_cells(l):
    return [c.strip() for c in re.split(r'(?<!\\)\|', l.strip())[1:-1]]


def cell_html(c):
    # the docs flatten in-cell bullet lists into "item  item  item": break them back onto lines
    # ...including a bold sub-label ("**Taxanes:** ...  **Vinca alkaloids:** ...")
    parts = re.split(r'\s{2,}(?=[A-Z\[]|\*\*)', c.strip())
    parts = [p for p in parts if p.strip()]
    if len(parts) == 1 and re.fullmatch(r'[\s:;,.\-]*', parts[0]):
        return ''          # a cell holding only ":" is an unfilled placeholder
    return '<br>'.join(il(p) for p in parts)


def render_table(rows, page):
    rows = [r for r in rows if not all(re.fullmatch(r':?-+:?', x) for x in r)]
    hdr, body = rows[0], rows[1:]
    hdr_txt = [plain_heading(h) for h in hdr]
    if [h.lower() for h in hdr_txt[:2]] == ['molecule', 'brands on pharmeasy']:
        return render_medicines(body)
    width = len(hdr)
    body = [(r + [''] * width)[:width] for r in body]
    # a column whose every cell is an unfilled CMS field ({{X}}) has nothing to show: drop it
    empty = [j for j in range(width) if body and all(re.fullmatch(r'\s*\{\{[^}]*\}\}\s*', r[j]) for r in body)]
    # ...and so does one that says the same CMS placeholder on every row ("Brand-specific" prices)
    empty += [j for j in range(width) if j not in empty and len(body) > 1
              and len({unesc(r[j]).strip().lower() for r in body}) == 1
              and re.fullmatch(r'(?i)\s*brand[- ]specific\s*', unesc(body[0][j]))]
    if empty:
        note(page, 'dropped table column "%s": every cell is an unfilled CMS field (%s)'
             % (', '.join(hdr_txt[j] for j in empty), ', '.join(sorted({unesc(r[j]).strip() for r in body for j in empty}))))
        keep = [j for j in range(width) if j not in empty]
        hdr_txt, body, width = [hdr_txt[j] for j in keep], [[r[j] for j in keep] for r in body], len(keep)
    cells = [[cell_html(c) for c in r] for r in body]
    return B.rtable(hdr_txt, cells, ['k'] + [''] * (width - 1), extra='two' if width == 2 else '')


def render_medicines(body):
    """The docs' "Medicines on PharmEasy" table: group label rows, then molecule rows with brand links.
    Rendered with the homepage drug-table styles (molecule name + brand chips, mobile key)."""
    groups, cur = [], None
    for r in body:
        r = (r + ['', ''])[:2]
        mol, brands = r
        if not brands.strip() and not LINK_MD.search(mol):
            cur = (plain_heading(mol), [])
            groups.append(cur)
            continue
        m = LINK_MD.search(mol)
        name = unesc(re.sub(r'\*', '', m.group(1) if m else mol)).strip()
        murl = clean_url(m.group(2)) if m else ''
        chips = []
        for bm in LINK_MD.finditer(brands):
            t = unesc(bm.group(1)).strip()
            chips.append('<a class="brand%s" href="%s">%s</a>' % (' more' if t.startswith('+') else '', esc(clean_url(bm.group(2))), esc(t)))
        if cur is None:
            cur = ('', [])
            groups.append(cur)
        nm = esc(name).replace('+', '+<wbr>').replace('/', '/<wbr>')   # "Capecitabine+Cyclophosphamide" may wrap
        nm = '<a href="%s">%s</a>' % (esc(murl), nm) if murl else nm
        cur[1].append('<div class="mol-row"><div class="mol-name">%s</div><div class="brands">%s</div></div>'
                      % (nm, ''.join(chips) or '<span class="brand none">no brands listed</span>'))
    out = []
    for label, rows in groups:
        out.append('<div class="med-group">%s<div class="mol-list">%s%s</div></div>'
                   % ('<div class="med-label">%s</div>' % esc(label) if label else '', B.MOL_KEY, ''.join(rows)))
    return '    <div class="rt-wrap med-table">%s</div>\n' % ''.join(out)


def render_blocks(lines, page, images):
    """A run of body lines -> html. Handles h3, tables, lists, images, paragraphs."""
    out, i, n = [], 0, len(lines)
    while i < n:
        l = lines[i]
        s = l.strip()
        if not s:
            i += 1
            continue
        if s.startswith('### ') or s.startswith('#### '):
            t = plain_heading(s)
            if t:
                out.append('    <h3 class="h3" style="margin-top:24px">%s</h3>\n' % il(t))
            i += 1
            continue
        if is_table(s):
            rows = []
            while i < n and is_table(lines[i]):
                rows.append(split_cells(lines[i]))
                i += 1
            out.append(render_table(rows, page))
            continue
        if LIST_RE.match(l):
            items = []
            while i < n and (LIST_RE.match(lines[i]) or not lines[i].strip()):
                m = LIST_RE.match(lines[i])
                if m:
                    lvl = 1 if (len(m.group(1)) >= 2 or m.group(2)) else 0
                    if m.group(3).strip():
                        items.append((lvl, m.group(3)))
                i += 1
                # stop a list at a blank line followed by non-list content
                if i < n and not lines[i].strip():
                    j = i
                    while j < n and not lines[j].strip():
                        j += 1
                    if j >= n or not LIST_RE.match(lines[j]):
                        break
            if items:
                out.append(render_list(items))
            continue
        m = re.match(r'^!\[[^\]]*\]\[(\w+)\]', s)
        if m:
            src = images.get(m.group(1), '')
            if src:
                out.append('    <figure class="pg-fig"><img src="%s" alt="" loading="lazy"></figure>\n' % src)
            elif src is None:
                pass
            else:
                note(page, 'image placeholder %s has no data; left out' % m.group(1))
            i += 1
            continue
        if re.match(r'^\*\*Related reading:?\*\*', s):
            out.append('    <p class="lead-p rel-reading">%s</p>\n' % il(s))
            i += 1
            continue
        out.append('    <p class="lead-p">%s</p>\n' % il(s))
        i += 1
    return ''.join(out)


# ---------------------------------------------------------------- doc parsing
def parse(fname, path):
    raw = open(os.path.join(SRC_DIR, fname), encoding='utf8').read()
    page = path
    # embedded images: [image1]: <data:image/png;base64,...>
    images = {}
    img_dir = os.path.join(ROOT, 'assets', 'img')
    for m in re.finditer(r'^\[(\w+)\]:\s*<data:image/(\w+);base64,([A-Za-z0-9+/=\s]+)>', raw, re.M):
        why = SKIP_IMAGES.get(path, {}).get(m.group(1))
        if why:
            note(page, 'left out image %s: %s' % (m.group(1), why))
            images[m.group(1)] = None
            continue
        os.makedirs(img_dir, exist_ok=True)
        fn = '%s-%s.%s' % (slug(path.strip('/').replace('/', '-')), m.group(1), m.group(2))
        with open(os.path.join(img_dir, fn), 'wb') as f:
            f.write(base64.b64decode(re.sub(r'\s', '', m.group(3))))
        images[m.group(1)] = 'IMGPREFIX/' + fn
    raw = re.sub(r'^\[\w+\]:\s*<data:image[^\n]*$', '', raw, flags=re.M)
    lines = prep(raw, page).split('\n')

    # H1 = first non-empty line
    k = 0
    while not lines[k].strip():
        k += 1
    h1 = plain_heading(lines[k])
    k += 1

    # header: byline/reviewer/published/your-path lines until the first prose paragraph
    head_txt, path_line = [], None
    while k < len(lines):
        s = lines[k].strip()
        if not s:
            k += 1
            continue
        if re.search(r'Written by|reviewer|Reviewer|editorial-policy|\.webp|Published \{\{|^\\?\[?https?\\?:', s):
            head_txt.append(s)
            k += 1
            continue
        if s.startswith('Your path'):
            path_line = s
            k += 1
            continue
        break
    head_blob = ' '.join(head_txt)
    rlink = re.search(r'\((https://pharmeasy\.in/legal/editorial-policy/([^)\s]+))\)', head_blob)
    rslug = rlink.group(2) if rlink else ''
    rname = re.search(r'reviewer\\?_name\s*:?\s*([^\]\n]*?)\s*(?:reviewer|Reviewer|\\\]|$)', head_blob)
    reviewer = REVIEWER_NAME.get(rslug) or (rname.group(1).strip(' :') if rname else 'PharmEasy Medical Team')
    rimg = re.search(r'\((https://[^)\s]+\.(?:webp|png|jpe?g))\)', head_blob)
    reviewer_img = REVIEWER_IMG.get(rslug) or (rimg.group(1) if rimg else '')
    if not rlink:
        note(page, 'no reviewer link found in the doc header')

    # intro = everything before the first "## "
    intro = []
    while k < len(lines) and not lines[k].startswith('## '):
        if lines[k].strip():
            intro.append(lines[k].strip())
        k += 1

    # sections
    sections, cur = [], None
    for l in lines[k:]:
        if l.startswith('## '):
            cur = [plain_heading(l), []]
            sections.append(cur)
        elif cur is not None:
            cur[1].append(l)
    return dict(h1=h1, reviewer=reviewer, reviewer_url=rlink.group(1) if rlink else '', reviewer_img=reviewer_img,
                path_line=path_line, intro=intro, sections=sections, images=images)


def strip_latest_module(lines, page):
    """Drop the "Latest on ..." sample-row module (no data source yet)."""
    out, skipping = [], False
    for l in lines:
        s = l.strip()
        if re.match(r'^Latest on\b', s):
            skipping = True
            note(page, 'left out the "Latest on ..." placeholder module (sample rows only)')
            continue
        if skipping:
            if s.startswith('The dates and prices on this page are CMS fields') :
                skipping = False
            elif s.startswith('Related pages') or s.startswith('## '):
                skipping = False
                out.append(l)
            continue
        out.append(l)
    return out


def split_related(lines):
    """A plain "Related pages" line starts the related-links box (it is not a ## heading in most docs)."""
    for i, l in enumerate(lines):
        if l.strip().strip('*').strip().rstrip(':') == 'Related pages':   # plain or **bold**
            return lines[:i], lines[i + 1:]
    return lines, None


def parse_faqs(lines):
    qs, cur = [], None
    for l in lines:
        s = l.strip()
        if not s:
            continue
        is_q = (s.startswith('###') or '▾' in s or re.fullmatch(r'\*\*[^*]+\?\*\*', s.replace(' ', ' ')))
        if is_q and plain_heading(s):
            cur = [plain_heading(s), []]
            qs.append(cur)
        elif cur is not None:
            cur[1].append(s)
    return [(q, a) for q, a in qs if a]


def parse_refs(lines):
    refs = {}
    for l in lines:
        m = re.match(r'^\s*(\d+)\\?\.\s+(.*\S)\s*$', l)
        if m:
            t = m.group(2)
            # the trailing link must read [url](url): some docs use a bare domain as the text or add a full stop after it
            lm = re.search(r'\[([^\]]*)\]\((https?://[^)\s]+)\)\s*\.?\s*$', t)
            if lm:
                t = t[:lm.start()] + '[%s](%s)' % (lm.group(2), lm.group(2))
            refs[int(m.group(1))] = t
    return refs


# ---------------------------------------------------------------- page pieces
def related_links(path):
    """Parent hub, this page's children and its siblings, from the URL plan."""
    me = '/cancer/' + path
    parent = me.rsplit('/', 2)[0] + '/'
    kids = sorted(u for u in ALLOWED if u.startswith(me) and u != me and u[len(me):].count('/') == 1)
    sibs = sorted(u for u in ALLOWED if u.startswith(parent) and u not in (me, parent) and u[len(parent):].count('/') == 1)
    out = []
    if parent != '/cancer/':
        out.append(parent)
    out += kids + [s for s in sibs if s not in kids]
    if parent == '/cancer/':
        out = kids + [u for u in ('/cancer/types/', '/cancer/symptoms/', '/cancer/tests/', '/cancer/screening/', '/cancer/treatment/',
                                  '/cancer/prevention/') if u != me and u not in kids]
    have = {'/cancer/' + p for p in B.existing_pages()}
    out = [u for u in out if u in have]          # only pages that exist
    for u in sorted(have - {'/cancer/', me}, key=lambda x: (x.count('/'), x)):
        if len(out) >= 4:
            break
        if u not in out:
            out.append(u)                          # top up with other built hub pages
    res = []
    for u in out[:8]:
        p = u[len('/cancer/'):]
        res.append((NAMES.get(p) or p.strip('/').split('/')[-1].replace('-', ' ').capitalize(), 'https://pharmeasy.in' + u))
    return res


def crumbs(path, h1):
    parts = path.strip('/').split('/')
    items = [('Home', 'https://pharmeasy.in/'), ('Cancer', CX)]
    for d in range(1, len(parts)):
        p = '/'.join(parts[:d]) + '/'
        if '/cancer/' + p in ALLOWED:
            items.append((NAMES.get(p, parts[d - 1].capitalize()), CX + p))
    items.append((NAMES.get(path) or h1, None))
    return items


def crumb_html(items):
    chev = ('<svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M10 8 L14 12 L10 16" '
            'stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"></path></svg>')
    lis = ''.join(('<li><a href="%s">%s</a>%s</li>' % (u, esc(t), chev)) if u else '<li><span aria-current="page">%s</span></li>' % esc(t)
                  for t, u in items)
    return '<nav class="glp-crumb" aria-label="Breadcrumb"><ol>%s</ol></nav>' % lis


def hero(doc, path):
    stetho = B.svg(B.IC['steth'], 17)
    img = ('<img src="%s" alt="%s" width="42" height="42" loading="lazy" style="width:42px;height:42px;min-width:42px;max-width:none;'
           'border-radius:999px;object-fit:cover;border:1px solid #B8DEDB;flex-shrink:0;display:block">' % (doc['reviewer_img'], esc(doc['reviewer']))) if doc['reviewer_img'] else ''
    who = ('<a href="%s" style="color:#00736C;font-weight:700">%s</a>' % (doc['reviewer_url'], esc(doc['reviewer']))) if doc['reviewer_url'] else esc(doc['reviewer'])
    intro = ''.join('      <p style="font-size:18px;line-height:30px;color:#3D4A48;margin:0 0 16px">%s</p>\n' % il(p) for p in doc['intro'])
    ypath = ''   # the docs' "Your path" line is recognised (kept out of the intro) but not shown (decision 18 Nov 2026)
    return f'''
  <div style="background:linear-gradient(180deg,#EDF6F5 0%,#F8FBFB 100%);border-bottom:1px solid #DCE6E5">

  {crumb_html(crumbs(path, doc['h1']))}

  <div class="sec" style="max-width:1120px;margin:0 auto;padding:20px 20px 36px;text-align:left">
    <h1 style="font-size:40px;line-height:48px;font-weight:800;letter-spacing:-0.03em;margin:0 0 16px;color:#0F2E2C;text-wrap:pretty">{esc(doc['h1'])}</h1>

    <div style="display:flex;align-items:center;gap:12px;font-size:12px;line-height:19px;color:#5C7370;padding-bottom:18px;border-bottom:1px solid #DCE6E5;margin-bottom:22px">
      {img}
      <div class="byline" style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;row-gap:4px">
        <span><strong style="color:#25282B;font-weight:700">Medically reviewed by</strong> {who}</span>
        <span style="color:#C9D0D8">·</span>
        <span><strong style="color:#25282B;font-weight:700">Written by</strong> <a href="https://pharmeasy.in/legal/editorial-policy" style="color:#00736C;font-weight:700">PharmEasy Medical Team</a></span>
        <span style="color:#C9D0D8">·</span>
        <span>Updated on {B.LAST_UPDATED}</span>
      </div>
    </div>
{ypath}
    <div class="hero-intro" id="hero-intro">
{intro}    </div>
    <button type="button" class="hero-toggle" id="hero-toggle" aria-expanded="false" aria-controls="hero-intro" hidden><span>Read more</span>{B.svg(B.IC['chev'], 16)}</button>

    <div style="background:#fff;border:1px solid #DCE6E5;border-radius:12px;padding:20px;display:flex;gap:14px;align-items:flex-start;box-shadow:0 2px 10px rgba(15,46,44,0.05)">
      <div style="width:30px;height:30px;border-radius:8px;background:#008880;color:#fff;display:flex;align-items:center;justify-content:center;flex-shrink:0">{stetho}</div>
      <div>
        <p style="font-size:14px;line-height:22px;color:#25282B;margin:0 0 14px"><strong style="font-weight:800">Have a question about your situation?</strong> An online doctor consultation can help you understand what applies to you and how urgently you may need further evaluation.</p>
        <div style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:12px">
          <a class="cx-btn-primary" href="{B.ODC}">Consult a doctor</a>
        </div>
        <p style="font-size:12px;line-height:19px;color:#8E97A3;margin:0">This information is meant for educational purposes and does not replace advice from your doctor. All oncology medicines are prescription-only.</p>
      </div>
    </div>
  </div>

  </div>
'''


def rail(toc, rel, has_faq, has_refs):
    items = list(toc) + ([('toc-faq', 'Frequently Asked Questions')] if has_faq else []) + ([('references', 'References')] if has_refs else [])
    links = ''.join('<a href="#%s" style="font-size:14px;line-height:20px;color:#5C636D">%s</a>' % (i, esc(t)) for i, t in items)
    r = ''.join('<a class="rel-a" href="%s" style="line-height:20px">%s</a>' % (u, esc(t)) for t, u in rel)
    return (
        '      <div class="toc" style="order:1;flex:0 1 250px;min-width:230px;position:sticky;top:16px;max-height:calc(100vh - 32px);overflow-y:auto;display:flex;flex-direction:column;gap:14px">\n'
        '        <div class="pad toc-nav" style="background:#fff;border:1px solid #E6E9ED;border-radius:12px;padding:18px">\n'
        '          <div style="font-size:11px;font-weight:800;letter-spacing:0.06em;text-transform:uppercase;color:#8E97A3;margin-bottom:12px">On this page</div>\n'
        '          <div style="display:flex;flex-direction:column;gap:10px">%s</div>\n        </div>\n'
        '        <div class="pad" style="background:#F2F9F8;border:1px solid #B8DEDB;border-radius:12px;padding:18px">\n'
        '          <div style="display:flex;gap:10px;align-items:center;margin-bottom:8px"><span style="width:32px;height:32px;border-radius:10px;background:#fff;border:1px solid #B8DEDB;color:#008880;display:flex;align-items:center;justify-content:center;flex-shrink:0">%s</span>'
        '<div style="font-size:15px;font-weight:800;color:#004D48">Consult a doctor</div></div>\n'
        '          <p style="font-size:13px;line-height:20px;color:#5C636D;margin:0 0 12px">Unsure whether a symptom or a test result needs attention? A doctor can help you understand how urgently it needs to be checked.</p>\n'
        '          <a href="%s" style="display:block;text-align:center;background:#008880;color:#fff;font-weight:700;font-size:13px;padding:11px 16px;border-radius:12px">Consult a doctor</a>\n        </div>\n'
        '        <div class="pad" style="background:#fff;border:1px solid #E6E9ED;border-radius:12px;padding:18px">\n'
        '          <div style="font-size:11px;font-weight:800;letter-spacing:0.06em;text-transform:uppercase;color:#8E97A3;margin-bottom:12px">Related pages</div>\n'
        '          <div style="display:flex;flex-direction:column;gap:10px">%s</div>\n        </div>\n'
        '      </div>\n' % (links, B.svg(B.IC['steth'], 17), B.ODC, r))


def faq_html(faqs):
    items = []
    for i, (q, a) in enumerate(faqs):
        ans = ''.join('<p style="font-size:15px;line-height:26px;color:#5C636D;margin:0 0 8px">%s</p>' % il(x) for x in a)
        items.append('      <details class="faq"%s style="background:#fff;border:1px solid #E6E9ED;border-radius:12px;overflow:hidden;box-shadow:0 1px 3px rgba(15,46,44,0.06),0 4px 14px rgba(15,46,44,0.05)">\n'
                     '        <summary style="padding:20px 24px;display:flex;justify-content:space-between;gap:16px;align-items:center">'
                     '<h3 style="margin:0;font-size:17px;line-height:25px;font-weight:800;color:#25282B;text-wrap:pretty">%s</h3>'
                     '<span class="chev" style="color:#8E97A3;flex-shrink:0;display:flex">%s</span></summary>\n'
                     '        <div style="padding:0 24px 12px">%s</div>\n      </details>' % (' open' if i == 0 else '', esc(q), B.svg(B.IC['chev'], 18), ans))
    return ('\n  <div class="asec" style="padding:36px 0 0">\n'
            '    <h2 id="toc-faq" style="font-size:24px;line-height:32px;font-weight:800;margin:0 0 16px;color:#1C1F22;scroll-margin-top:20px">Frequently Asked Questions</h2>\n'
            '    <div style="display:flex;flex-direction:column;gap:12px">\n%s\n    </div>\n  </div>\n' % '\n'.join(items))


def refs_html(refs):
    rows = []
    for k in sorted(refs):
        t, _ = ref_html(refs[k])
        rows.append('        <div style="display:flex;gap:10px;font-size:13px;line-height:21px;color:#5C636D"><span id="ref-%d" style="font-weight:800;color:#8E97A3;flex-shrink:0;scroll-margin-top:20px">%d.</span><span>%s</span></div>' % (k, k, t))
    return ('\n  <div class="asec" style="padding:36px 0 0">\n    <div id="references">\n'
            '      <h2 style="font-size:24px;line-height:32px;font-weight:800;margin:0 0 14px;color:#1C1F22;scroll-margin-top:20px">References</h2>\n'
            '      <div class="pad refs" id="refs-list" style="background:#fff;border:1px solid #E6E9ED;border-radius:12px;padding:22px;display:flex;flex-direction:column;gap:10px">\n%s\n      </div>\n    </div>\n  </div>\n' % '\n'.join(rows))


def related_box(lines):
    # an item whose page is not live yet lost its link in prep(): a related-pages list only lists pages you can open
    have = B.existing_pages()

    def live(l):
        for m in LINK_MD.finditer(l):
            mm = re.match(r'https?://(?:www\.)?pharmeasy\.in/cancer/([^?#]*)', clean_url(m.group(2)))
            if not mm or (mm.group(1) if mm.group(1).endswith('/') or not mm.group(1) else mm.group(1) + '/') in have:
                return True
        return False
    dropped = [l for l in lines if LIST_RE.match(l) and not live(l)]
    for l in dropped:
        note('related pages', 'related item left out, its page is not built yet: %s' % re.sub(r'\s+', ' ', l.strip())[:90])
    lines = [l for l in lines if l not in dropped]
    body = render_blocks(lines, '', {})
    if not re.search(r'<a ', body):
        return ''
    return ('\n  <div class="asec" style="padding:28px 0 0">\n    <div class="pad related-box">\n'
            '      <div class="cx-eyebrow" style="margin-bottom:8px">Related pages</div>\n%s    </div>\n  </div>\n' % body)


def head(doc, path, faqs, desc, title, prefix):
    canon = CX + path
    org = json.load(open(os.path.join(HERE, 'org-schema.json'), encoding='utf8'))
    graph = list(org['@graph'])
    rev = {'@type': 'Person', 'name': doc['reviewer']}
    if doc['reviewer_url']:
        rev['url'] = doc['reviewer_url']
    if doc['reviewer_img']:
        rev['image'] = doc['reviewer_img']
    graph.append({'@type': 'MedicalWebPage', '@id': canon + '#webpage', 'url': canon, 'name': doc['h1'], 'description': desc, 'inLanguage': 'en-IN',
                  'isPartOf': {'@id': 'https://pharmeasy.in/#Website'}, 'breadcrumb': {'@id': canon + '#breadcrumb'},
                  'publisher': {'@id': 'https://pharmeasy.in/#Organization'},
                  'author': {'@type': 'Organization', 'name': 'PharmEasy Medical Team', 'url': 'https://pharmeasy.in/legal/editorial-policy'},
                  'dateModified': B.LAST_UPDATED_ISO, 'reviewedBy': rev, **B.medical_page_props(ABOUT.get(path, []))})
    cr = crumbs(path, doc['h1'])
    graph.append({'@type': 'BreadcrumbList', '@id': canon + '#breadcrumb', 'itemListElement': [
        {'@type': 'ListItem', 'position': i + 1, 'name': t, 'item': u or canon} for i, (t, u) in enumerate(cr)]})
    if faqs:
        graph.append({'@type': 'FAQPage', '@id': canon + '#faq', 'mainEntity': [
            {'@type': 'Question', 'name': q, 'acceptedAnswer': {'@type': 'Answer', 'text': ' '.join(B.strip_tags(il(x)) for x in a)}} for q, a in faqs]})
    ld = json.dumps({'@context': 'https://schema.org', '@graph': graph}, ensure_ascii=False, separators=(',', ':'))
    css = ''.join('<link rel="stylesheet" href="%sassets/css/%s.css">\n' % (prefix, c) for c in ('tokens', 'pe', 'page', 'cancer'))
    return f'''<!DOCTYPE html>
<html lang="en-IN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" href="https://pharmeasy.in/favicon.ico" sizes="any">
<link rel="apple-touch-icon" href="https://pharmeasy.in/favicon.ico">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
{B.ROBOTS}<link rel="canonical" href="{canon}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{canon}">
<meta property="og:type" content="article">
<meta property="og:site_name" content="PharmEasy">
<script type="application/ld+json">{ld}</script>
<link rel="preconnect" href="https://assets.pharmeasy.in" crossorigin>
{css}</head>'''


def meta_desc(doc):
    txt = B.strip_tags(il(doc['intro'][0])) if doc['intro'] else doc['h1']
    if len(txt) <= 158:
        return txt
    cut = txt[:158]
    end = max(cut.rfind('. '), cut.rfind('? '))
    return cut[:end + 1] if end > 80 else cut[:cut.rfind(' ')].rstrip(',;:') + '.'


# ---------------------------------------------------------------- build
SEC_STOP = set('the a an of and in to is it its what how for on with or your you this that are be does do when which '
               'why explains mentions discusses describes'.split())


def _toks(s):
    return {w for w in re.findall(r'[a-z]+', html.unescape(s).lower()) if w not in SEC_STOP and len(w) > 2}


def link_sections(page, toc, path):
    """The "Which applies to you?" tables point at "Section 5, when to see a doctor", but the page does not
    number its sections. Link each pointer to the heading it names (an h2 or one of its h3 sub-headings),
    with that heading's own wording as the link text. Words decide first; the number is the fallback, read
    against the doc's own outline (its offset is learned from pointers whose words clearly match one h2)."""
    if not toc:
        return page
    h2 = [(sid, t, _toks(t)) for sid, t in toc]
    # give the h3 sub-headings ids so a pointer can land on them
    h3, used = [], set(s for s, _ in toc)
    def h3_id(m):
        text = html.unescape(re.sub(r'<[^>]+>', '', m.group(2))).strip()
        sid = 'sub-' + slug(re.sub(r'^\d+\.\s*', '', text))
        while sid in used:
            sid += '-2'
        used.add(sid)
        h3.append((sid, re.sub(r'^\d+\.\s*', '', text), _toks(text)))
        return '<h3 class="h3" id="%s"%s>%s</h3>' % (sid, m.group(1) or '', m.group(2))
    page = re.sub(r'<h3 class="h3"( [^>]*)?>(.*?)</h3>', h3_id, page)
    cell = re.compile(r'(<td[^>]*>)\s*Section (\d+)\s*[,:]?\s*([^<]*)(</td>)')
    see = re.compile(r'\(see section (\d+)\)', re.I)

    def by_words(rest, cands):
        want = _toks(rest)
        # rank: shared words, all pointer words found, then an h2 before an h3 on a tie
        sc = sorted(((len(want & tt), len(want - tt) == 0, sid.startswith('toc-'), i)
                     for i, (sid, _, tt) in enumerate(cands)), reverse=True)
        if not sc or sc[0][0] == 0 or (len(sc) > 1 and sc[0][:3] == sc[1][:3]):
            return None
        best = sc[0]
        return best[3] if (best[0] >= 2 or best[1]) else None

    offs = Counter()
    for m in cell.finditer(page):
        i = by_words(m.group(3), h2)
        if i is not None:
            offs[int(m.group(2)) - 1 - i] += 1
    off = offs.most_common(1)[0][0] if offs else 0

    def target(n, rest=''):
        if rest:
            i = by_words(rest, h2 + h3)
            if i is not None:
                return (h2 + h3)[i]
        i = n - 1 - off
        return h2[i] if 0 <= i < len(h2) else None

    def cell_sub(m):
        t = target(int(m.group(2)), m.group(3))
        if not t:
            note(path, 'section pointer left as text, no matching section: "Section %s %s"' % (m.group(2), m.group(3)))
            return m.group(0)
        return '%s<a href="#%s">%s</a>%s' % (m.group(1), t[0], esc(t[1]), m.group(4))

    def see_sub(m):
        t = target(int(m.group(1)))
        return '(see <a href="#%s">%s</a>)' % (t[0], esc(t[1])) if t else m.group(0)

    n = len(cell.findall(page)) + len(see.findall(page))
    if n:
        note(path, '%d "Section N" pointer(s) linked to the heading they name (number offset %d)' % (n, off))
    return see.sub(see_sub, cell.sub(cell_sub, page))


def build_page(fname, path, built):
    doc = parse(fname, path)
    depth = path.count('/')
    prefix = '../' * depth
    toc, body, faqs, refs, related = [], [], [], {}, None
    for title, lines in doc['sections']:
        low = title.lower()
        lines = strip_latest_module(lines, path)
        lines, rel = split_related(lines)
        if rel is not None:
            related = (related or []) + rel
        if low.startswith('frequently asked'):
            faqs = parse_faqs(lines)
            continue
        if low.startswith('references'):
            refs = parse_refs(lines)
            continue
        if low.startswith('related pages'):
            related = (related or []) + lines
            continue
        title = re.sub(r'^\d+\.\s+', '', title)       # "5. Blood tests and tumour markers": the only numbered h2
        sid = 'toc-' + slug(title)
        toc.append((sid, title))
        body.append(B.sec(sid, title, render_blocks(lines, path, doc['images'])))
    if related:
        body.append(related_box(related))
    desc = meta_desc(doc)
    title = '%s | PharmEasy' % doc['h1']
    page = (head(doc, path, faqs, desc, title, prefix)
            + '\n<body data-built="%s">\n<a class="skip" href="#main">Skip to content</a>\n<div data-pe-header></div>\n<main id="main"><div id="dc-root">\n' % ' '.join(built)
            + '<div style="background:#F5F7F8;font-family:var(--glp-font,Inter,Mulish,sans-serif);color:#25282B;padding-bottom:48px;container-type:inline-size">\n'
            + hero(doc, path) + '\n  <div class="sec" style="max-width:1120px;margin:0 auto;padding:24px 20px 0">\n    <div style="display:flex;flex-wrap:wrap;gap:24px;align-items:flex-start">\n\n'
            + rail(toc, related_links(path), bool(faqs), bool(refs))
            + '\n      <div class="art" style="order:2;flex:1 1 560px;min-width:0">\n' + ''.join(body) + B.explore_band()
            + (faq_html(faqs) if faqs else '') + (refs_html(refs) if refs else '')
            + '\n      </div>\n    </div>\n  </div>\n' + B.disclaimer()
            + '\n</div>\n</div></main>\n<div data-pe-footer></div>\n'
            + ''.join('<script src="%sassets/js/%s.js" defer></script>\n' % (prefix, j) for j in ('pe-shell', 'pe-toc', 'cancer'))
            + '</body>\n</html>\n')
    page = page.replace('IMGPREFIX/', prefix + 'assets/img/')
    page = link_sections(page, toc, path)
    page = B.remove_dead_links(page, '/cancer/' + path)
    page = B.nofollow_external(page)
    used = set(re.findall(r'href="https://pharmeasy\.in(/cancer/[^"#?]*)', page))
    bad = sorted(used - ALLOWED)
    assert not bad, '%s links to /cancer/ pages outside cancer_urls.txt: %s' % (path, bad)
    assert not re.search('[–—]', page), (path, [m.start() for m in re.finditer('[–—]', page)][:5])
    # citations that point at a missing reference
    cited = {int(x) for x in re.findall(r'href="#ref-(\d+)"', page)}
    missing = sorted(cited - set(refs))
    if missing:
        note(path, 'cited but not in the reference list: %s' % missing)
    out = os.path.join(ROOT, path, 'index.html')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, 'w', encoding='utf8').write(B.bust(page))
    return out, len(toc), len(faqs), len(refs)


def write_sitemap():
    """sitemap.xml for the hub: the homepage plus every page that exists (the same set the explore band
    links). Production URLs on pharmeasy.in; deployed to /cancer/sitemap.xml."""
    paths = sorted(B.existing_pages(), key=lambda p: (p.count('/'), p))
    lastmod = B.LAST_UPDATED_ISO[:10]
    rows = ''.join('  <url><loc>%s%s</loc><lastmod>%s</lastmod></url>\n' % (CX, p, lastmod) for p in paths)
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n%s</urlset>\n' % rows
    open(os.path.join(ROOT, 'sitemap.xml'), 'w', encoding='utf8').write(xml)
    return len(paths)


def main():
    built = [p for _, p in PAGES]
    for fname, path in PAGES:
        out, ns, nf, nr = build_page(fname, path, built)
        print('wrote /cancer/%-26s sections %2d  faqs %d  refs %d' % (path, ns, nf, nr))
    print('robots: %s' % ('indexable (production build)' if B.INDEXABLE else 'NOINDEX (production build, --noindex)' if B.PRODUCTION else 'NOINDEX (GitHub Pages copy)'))
    print('sitemap.xml: %d urls' % write_sitemap())
    B.write_removed_report()
    with open(os.path.join(HERE, 'pages_report.md'), 'w', encoding='utf8') as f:
        f.write('# Editorial notes from the page build\n\nMechanical changes the build made, and things for the editors to fix in the docs.\n')
        for page, notes in REPORT.items():
            f.write('\n## /cancer/%s\n\n' % page)
            seen = []
            for n in notes:
                if n not in seen:
                    seen.append(n)
                    f.write('- %s\n' % n)
    print('editor notes: build/pages_report.md (%d notes)' % sum(len(set(v)) for v in REPORT.values()))


if __name__ == '__main__':
    main()

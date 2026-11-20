"""Present the editorial tables as components that suit their data, without touching the words.

Every table the builds emit (build.rtable) is re-laid out here from its own <th>/<td> HTML:
  * "If this is you / What happens next / Where to read more"  -> situation cards
  * a one-row, many-column table (an "at a glance" table)      -> fact tiles
  * the GLOBOCAN India numbers                                 -> stat cards with a male/female split
  * everything else                                            -> one card per row; short values become
                                                                  pills, Yes/No becomes a badge, limitations
                                                                  become a caution note, "when to call/check"
                                                                  becomes an alert
Cell HTML is reused verbatim (citations, links, <br> line breaks), headers become the field labels, and
empty cells are left out instead of leaving a blank gap. The medicines tables (.med-table, .dg) are not
touched: they already have their own layout.
"""
import re

TABLE_RE = re.compile(
    r'    <div class="rt-wrap"><div class="rt-scroll"><table class="rtable([^"]*)">(?:<colgroup>.*?</colgroup>)?'
    r'<thead><tr>(.*?)</tr></thead><tbody>(.*?)</tbody></table></div>((?:<div class="rt-foot">.*?</div>)?)</div>\n',
    re.S)
TH_RE = re.compile(r'<th[^>]*>(.*?)</th>', re.S)
TR_RE = re.compile(r'<tr>(.*?)</tr>', re.S)
TD_RE = re.compile(r'<td[^>]*>(.*?)</td>', re.S)

ICON = {
    'warn': '<svg viewBox="0 0 24 24" width="15" height="15" aria-hidden="true"><path fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" d="M12 9v4m0 4h.01M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/></svg>',
    'alert': '<svg viewBox="0 0 24 24" width="15" height="15" aria-hidden="true"><path fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" d="M12 8v4m0 4h.01M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0z"/></svg>',
    'tip': '<svg viewBox="0 0 24 24" width="15" height="15" aria-hidden="true"><path fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" d="M9 18h6m-5 3h4M12 3a6 6 0 0 0-3.5 10.9c.6.4 1 1.1 1 1.8V16h5v-.3c0-.7.4-1.4 1-1.8A6 6 0 0 0 12 3z"/></svg>',
    'do': '<svg viewBox="0 0 24 24" width="15" height="15" aria-hidden="true"><path fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" d="m5 12 5 5L20 7"/></svg>',
    'info': '<svg viewBox="0 0 24 24" width="15" height="15" aria-hidden="true"><path fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" d="M12 16v-4m0-4h.01M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0z"/></svg>',
    'arrow': '<svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true"><path fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" d="M5 12h14m-6-6 6 6-6 6"/></svg>',
    'chev': '<svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><path fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" d="m6 9 6 6 6-6"/></svg>',
    'q': '<svg viewBox="0 0 24 24" width="15" height="15" aria-hidden="true"><path fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" d="M9.1 9a3 3 0 0 1 5.8 1c0 2-3 3-3 3m.1 4h.01M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0z"/></svg>',
}


def text(h):
    return re.sub(r'\s+', ' ', re.sub(r'<sup class="cite">.*?</sup>', '', re.sub(r'<(?!sup|/sup)[^>]+>', '', h))).strip()


def is_empty(h):
    return not re.sub(r'<[^>]+>|&nbsp;|\s', '', h)


def kind(label):
    """What a column is, from its header."""
    l = text(label).lower()
    if re.search(r'limitation', l):
        return 'warn'
    if re.search(r'other causes', l):
        return 'info'
    if re.search(r'when to call|when should it be checked|when to see', l):
        return 'alert'
    if re.search(r'kitchen note', l):
        return 'tip'
    if re.search(r'^what to do$|^what helps$|^what to change$', l):
        return 'do'
    if re.search(r'can you change it|does it spread|is it cancerous', l):
        return 'badge'
    return ''


def badge(v, label):
    """Colour by meaning: a "Yes" to "can you change it?" is good news, a "Yes" to "does it spread?" is not."""
    t, l = text(v).lower(), text(label).lower()
    good_if_yes = 'change' in l
    if t.startswith('yes') or t == 'cancerous':
        return 'good' if good_if_yes else 'bad'
    if t in ('no', 'not cancerous'):
        return 'muted' if good_if_yes else 'good'
    return 'mid'


def short(v):
    t = text(v)
    return bool(t) and len(t) <= 42 and '<br>' not in v and '<a ' not in v


# ---------------------------------------------------------------- components

def situations(hdr, rows):
    cards = []
    for r in rows:
        who, nxt, more = (r + ['', '', ''])[:3]
        b = ['<div class="pv-sit">',
             '<div class="pv-sit-who"><span class="pv-lbl">%s</span><p>%s</p></div>' % (hdr[0], who)]
        if not is_empty(nxt):
            b.append('<div class="pv-sit-next"><span class="pv-lbl">%s</span><p>%s</p></div>' % (hdr[1], nxt))
        if len(hdr) > 2 and not is_empty(more):
            b.append('<div class="pv-sit-more"><span class="pv-lbl">%s</span><span class="pv-more-v">%s%s</span></div>'
                     % (hdr[2], ICON['arrow'], more))
        b.append('</div>')
        cards.append(''.join(b))
    return '<div class="pv pv-sits">%s</div>' % ''.join(cards)


def facts(hdr, row):
    tiles = ''.join('<div class="pv-fact"><span class="pv-fact-q">%s%s</span><p>%s</p></div>' % (ICON['q'], h, v)
                    for h, v in zip(hdr, row) if not is_empty(v))
    return '<div class="pv pv-facts">%s</div>' % tiles


def num(v):
    t = text(v).replace(',', '')
    m = re.fullmatch(r'(\d+(?:\.\d+)?)(%?)', t)
    return (float(m.group(1)), m.group(2)) if m else None


def stats(hdr, rows):
    cards = []
    for r in rows:
        label, m, f, both = (r + [''] * 4)[:4]
        nm, nf = num(m), num(f)
        bar = ''
        if nm and nf and not nm[1] and not nf[1]:          # counts: show the male/female split
            pm = round(100 * nm[0] / (nm[0] + nf[0]))
            bar = ('<div class="pv-split" role="img" aria-label="%s: %s, %s: %s">'
                   '<span class="pv-split-m" style="width:%d%%"></span><span class="pv-split-f" style="width:%d%%"></span></div>'
                   % (hdr[1], text(m), hdr[2], text(f), pm, 100 - pm))
        cards.append('<div class="pv-stat%s"><span class="pv-stat-k">%s</span>'
                     '<span class="pv-stat-v"><span class="pv-lbl">%s</span>%s</span>%s'
                     '<div class="pv-stat-mf"><span><i class="dot m"></i>%s <b>%s</b></span><span><i class="dot f"></i>%s <b>%s</b></span></div></div>'
                     % ('' if num(both) else ' txt', label, hdr[3], both, bar, hdr[1], m, hdr[2], f))
    return '<div class="pv pv-stats">%s</div>' % ''.join(cards)


LABEL_RE = re.compile(r'(?<!<br>)(?<!^)\s*(<(strong|b)>[^<]{1,60}:</\2>)')


def split_labels(v):
    """A field that lists two or more groups by bold label ("Anthracyclines: ... Alkylating agents: ...")
    starts each label on its own line, even where the doc ran the first one into the sentence."""
    if len(re.findall(r'<(strong|b)>[^<]{1,60}:</\1>', v)) < 2:
        return v
    return LABEL_RE.sub(lambda m: '<br>' + m.group(1), v)


def balance(body):
    """Three or more fields side by side leave the short ones next to a tall empty space when one field is
    much longer. Then the long field goes last and spans the full card width; the short ones stay in a row."""
    if len(body) < 3:
        return body
    # rough height: characters, plus a line's worth for every forced line break (one-per-line lists)
    lens = [len(text(f)) + 40 * f.count('<br') for f in body]
    i = max(range(len(body)), key=lambda k: lens[k])
    rest = sorted(lens[:i] + lens[i + 1:])
    if lens[i] < 160 or lens[i] < 2 * rest[len(rest) // 2]:
        return body
    wide = flow_lines(body[i].replace('<div class="pv-f">', '<div class="pv-f pv-wide">', 1))
    return body[:i] + body[i + 1:] + [wide]


def flow_lines(field, heads=()):
    """In a full-width field, a run of 3+ short line-broken items (a list of cancers, one per line) is laid
    out in columns instead of a tall single column. The words are not changed."""
    m = re.match(r'(.*?<div>)(.*)(</div></div>)$', field, re.S)
    if not m:
        return field
    segs = re.split(r'<br\s*/?>', m.group(2))
    out, run = [], []

    def flush():
        if len(run) >= 2:
            out.append('<span class="pv-lines">%s</span>' % ''.join('<span>%s</span>' % x.strip() for x in run))
        else:
            out.extend(run)
        run.clear()
    for k, seg in enumerate(segs):
        t = text(seg)
        heading = ('<b>' in seg or '<strong>' in seg or t.rstrip().endswith(':')    # "Vinblastine:" starts a new group
                   or t.strip().rstrip(':').lower() in heads)                       # "Oxaliplatin" (a molecule of this group)
        if k and 0 < len(t) <= 40 and not heading:
            run.append(seg)
        else:
            flush()
            out.append(seg)
    flush()
    joined = ''
    for part in out:          # <br> between plain segments; the column block breaks lines by itself
        if joined and not joined.endswith('</span>') and not part.startswith('<span class="pv-lines">'):
            joined += '<br>'
        joined += part
    return m.group(1) + joined + m.group(3)


def cards(hdr, rows):
    kinds = [kind(h) for h in hdr]
    # a column that is short on every row reads as a pill under the title
    pill = [j > 0 and kinds[j] == '' and all(short(r[j]) or is_empty(r[j]) for r in rows)
            and any(not is_empty(r[j]) for r in rows) for j in range(len(hdr))]
    out = []
    for i, r in enumerate(rows, 1):
        head, metas, body, notes = [], [], [], []
        for j, (h, v) in enumerate(zip(hdr, r)):
            if is_empty(v):
                continue
            v = split_labels(v)
            k = kinds[j]
            if j == 0:
                head.append('<div class="pv-title">%s</div>' % v)
            elif k == 'badge':
                metas.append('<span class="pv-badge %s"><span class="pv-badge-l">%s</span> %s</span>' % (badge(v, h), h, v))
            elif pill[j]:
                metas.append('<span class="pv-pill"><span class="pv-pill-l">%s</span> %s</span>' % (h, v))
            elif k in ('warn', 'info', 'alert', 'tip', 'do'):
                notes.append('<div class="pv-note %s"><span class="pv-note-l">%s%s</span><div>%s</div></div>' % (k, ICON[k], h, v))
            else:
                body.append('<div class="pv-f"><span class="pv-lbl">%s</span><div>%s</div></div>' % (h, v))
        body = balance(body)
        out.append('<div class="pv-card"><div class="pv-head"><span class="pv-n">%d</span><div>%s%s</div></div>%s%s</div>'
                   % (i, ''.join(head),
                      '<div class="pv-metas">%s</div>' % ''.join(metas) if metas else '',
                      ('<div class="pv-body%s">%s</div>' % (' pv-top-%d' % (len(body) - 1) if 'pv-wide' in body[-1] else '', ''.join(body))) if body else '',
                      '<div class="pv-notes">%s</div>' % ''.join(notes) if notes else ''))
    # few rows, or light rows: lay the cards side by side; heavy rows read better one per line
    weight = sum(len(text(v)) for r in rows for v in r) / max(1, len(rows))
    layout = 'pv-row' if len(rows) <= 3 else ('pv-grid' if weight < 260 else 'pv-list')
    return '<div class="pv pv-cards %s">%s</div>' % (layout, ''.join(out))


def is_medicine_groups(hdr):
    """The chemotherapy page's "Medicine group | Molecules used in India | How it is given | What it is used
    for | Brands on PharmEasy" table."""
    heads = [text(h).lower() for h in hdr]
    return heads and heads[0] == 'medicine group' and 'brands on pharmeasy' in heads and 'what it is used for' in heads


def accordion(hdr, rows):
    """One accordion per medicine group, every group in the same order: molecules and how it is given side by
    side, then what it is used for, then the brands (grouped by molecule, in columns). Closed, a group shows
    its name and a plain-text preview of its molecules. The first group starts open."""
    heads = [text(h).lower() for h in hdr]
    col = lambda name: heads.index(name) if name in heads else None
    i_mol, i_how, i_use, i_br = col('molecules used in india'), col('how it is given'), col('what it is used for'), col('brands on pharmeasy')
    used = {0, i_mol, i_how, i_use, i_br}
    other = [j for j in range(len(hdr)) if j not in used and any(not is_empty(r[j]) for r in rows)]   # e.g. a filled Price column

    def field(j, r, extra=''):
        if j is None or is_empty(r[j]):
            return ''
        return '<div class="pv-f%s"><span class="pv-lbl">%s</span><div>%s</div></div>' % (extra, hdr[j], split_labels(r[j]))
    out = []
    for n, r in enumerate(rows, 1):
        preview = text(re.sub(r'\s*<br\s*/?>\s*', ', ', r[i_mol])) if i_mol is not None else ''
        mols = {x.strip().lower() for x in re.split(r'[,;]|\band\b', preview) if x.strip()}
        top = field(i_mol, r) + field(i_how, r) + ''.join(field(j, r) for j in other)
        use = field(i_use, r, ' pv-wide')
        br = field(i_br, r, ' pv-wide')
        br = flow_lines(br, mols) if br else ''
        out.append('<details class="pv-acc"%s><summary><span class="pv-n">%d</span><span class="pv-acc-h"><span class="pv-title">%s</span>'
                   '<span class="pv-acc-sub" aria-hidden="true">%s</span></span><span class="pv-acc-chev" aria-hidden="true">%s</span></summary>'
                   '<div class="pv-acc-body"><div class="pv-acc-top">%s</div>%s%s</div></details>'
                   % (' open' if n == 1 else '', n, r[0], preview, ICON['chev'], top, use, br))
    return '<div class="pv pv-accs">%s</div>' % ''.join(out)


def one(m):
    cls, thead, tbody, foot = m.groups()
    hdr = [h.strip() for h in TH_RE.findall(thead)]
    rows = [[c.strip() for c in TD_RE.findall(tr)] for tr in TR_RE.findall(tbody)]
    rows = [(r + [''] * len(hdr))[:len(hdr)] for r in rows if r]
    if not rows:
        return m.group(0)
    h0 = text(hdr[0]).lower()
    if is_medicine_groups(hdr):
        body = accordion(hdr, rows)
    elif h0.startswith('if this') and len(hdr) in (2, 3):
        body = situations(hdr, rows)
    elif 'nums' in cls and len(hdr) == 4:
        body = stats(hdr, rows)
    elif len(rows) == 1 and len(hdr) >= 4:
        body = facts(hdr, rows[0])
    else:
        body = cards(hdr, rows)
    return '    <div class="pv-wrap">%s%s</div>\n' % (body, foot.replace('rt-foot', 'pv-foot') if foot else '')


MECH_ICON = {   # simple line icons for the chemotherapy "How it works" medicine types (by label keyword)
    'alkylat': '<path d="M7 3c0 6 10 6 10 12M17 3c0 3-2.5 4.5-5 6M7 21c0-3 2.5-4.5 5-6M8.5 6h7M8 18h8"/><path d="m14 10 3 2" stroke-dasharray="2 2"/>',
    'antimetab': '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><path d="M14 14h7v7h-7z" stroke-dasharray="2.5 2"/>',
    'microtub': '<circle cx="7" cy="12" r="4"/><circle cx="17" cy="12" r="4"/><path d="M11 12h2" stroke-dasharray="1.5 1.5"/>',
    'antibiot': '<rect x="3" y="8.5" width="18" height="7" rx="3.5" transform="rotate(-35 12 12)"/><path d="m9.2 15.9 5.6-7.8"/>',
    'misc': '<circle cx="6" cy="12" r="1.6"/><circle cx="12" cy="12" r="1.6"/><circle cx="18" cy="12" r="1.6"/><circle cx="12" cy="12" r="9"/>',
}
CELL_ICON = '<svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true"><g fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="3.2"/><path d="M12 3v2M12 19v2M3 12h2M19 12h2"/></g></svg>'


def mech_icon(label):
    l = text(label).lower()
    key = next((k for k in MECH_ICON if k in l), 'misc')
    return ('<span class="mech-ic" aria-hidden="true"><svg viewBox="0 0 24 24" width="22" height="22"><g fill="none" stroke="currentColor" '
            'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">%s</g></svg></span>' % MECH_ICON[key])


HOW_RE = re.compile(r'(<h2 id="toc-how-it-works"[^>]*>.*?</h2>.*?)<ul class="pg-list">(.*?)</ul>\s*<p class="lead-p">(.*?)</p>', re.S)
LI_RE = re.compile(r'<li><strong>([^<]{2,60}?):</strong>\s*(.*?)</li>', re.S)


def how_it_works(page):
    """Chemotherapy "How it works": the list of medicine types (every item a bold label + its sentence)
    becomes a grid of cards with an icon each, and the closing paragraph a highlighted note. Same words."""
    def fix(m):
        items = LI_RE.findall(m.group(2))
        if len(items) < 3 or len(items) != m.group(2).count('<li>'):
            return m.group(0)
        cards = ''.join('<div class="mech">%s<div><div class="mech-t">%s:</div><p>%s</p></div></div>' % (mech_icon(l), l, t) for l, t in items)
        return ('%s<div class="mech-grid">%s</div>\n    <div class="mech-note"><span class="mech-note-ic">%s</span><p>%s</p></div>'
                % (m.group(1), cards, CELL_ICON, m.group(3)))
    return HOW_RE.sub(fix, page, count=1)


ROUTE_ICON = {   # "How it is given" routes (by label keyword)
    'oral': '<rect x="3" y="8.5" width="18" height="7" rx="3.5" transform="rotate(-35 12 12)"/><path d="m9.2 15.9 5.6-7.8"/>',
    'injection': '<path d="m18 2 4 4M15 5l4 4M16.5 7.5 8 16l-3 1 1-3 8.5-8.5M10 9l2 2M7.5 11.5l2 2M5 17l-3 3"/>',
    'intravenous': '<path d="M8 2h8v9a4 4 0 0 1-8 0z"/><path d="M8 6h8M12 15v3a3 3 0 0 0 3 3h5"/>',
    'topical': '<path d="M7 3h10l-1 4H8z"/><path d="M8 7h8v11a3 3 0 0 1-3 3h-2a3 3 0 0 1-3-3z"/><path d="M10 12h4"/>',
    'intrathecal': '<rect x="9" y="2" width="6" height="4" rx="1.5"/><rect x="9" y="8" width="6" height="4" rx="1.5"/><rect x="9" y="14" width="6" height="4" rx="1.5"/><path d="M12 18v4M5 10h3M16 10h3"/>',
    'intraperitoneal': '<path d="M6 4c-2 4-2 12 1 16M18 4c2 4 2 12-1 16"/><path d="M9 9c1.5-1 4.5-1 6 0M9 13c1.5 1 4.5 1 6 0M10 17h4"/>',
    'intra-arterial': '<path d="M3 12c3-4 6-4 9 0s6 4 9 0"/><path d="M3 8c3-4 6-4 9 0M12 16c3 4 6 4 9 0" opacity=".5"/>',
}


def route_icon(label):
    l = text(label).lower()
    key = next((k for k in ROUTE_ICON if k in l), None)
    body = ROUTE_ICON[key] if key else MECH_ICON['misc']
    return ('<span class="mech-ic" aria-hidden="true"><svg viewBox="0 0 24 24" width="22" height="22"><g fill="none" stroke="currentColor" '
            'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">%s</g></svg></span>' % body)


GIVEN_RE = re.compile(r'(<h2 id="toc-how-it-is-given"[^>]*>.*?</h2>.*?)<ul class="pg-list">(.*?)</ul>\s*<p class="lead-p"><strong>([^<]+:)</strong>\s*(.*?)</p>', re.S)


def sentences(h):
    """Split html text into sentences at ". " + capital letter (citations stay with their sentence)."""
    out, i = [], 0
    for m in re.finditer(r'(?<=[.!?])(?:</sup>)?\s+(?=[A-Z])', h):
        out.append(h[i:m.start()] + (m.group(0).strip() if m.group(0).strip().startswith('</sup>') else ''))
        i = m.end()
    out.append(h[i:])
    return [x.strip() for x in out if x.strip()]


def how_it_is_given(page):
    """Chemotherapy "How it is given": the routes become icon cards, and the "What to expect during a
    chemotherapy session" paragraph a numbered timeline, one sentence per step. Same words, same order."""
    def fix(m):
        items = LI_RE.findall(m.group(2))
        if len(items) < 3 or len(items) != m.group(2).count('<li>'):
            return m.group(0)
        cards = ''.join('<div class="mech">%s<div><div class="mech-t">%s:</div><p>%s</p></div></div>' % (route_icon(l), l, t) for l, t in items)
        steps = sentences(m.group(4))
        tl = ''.join('<li><span class="tl-n">%d</span><p>%s</p></li>' % (k, st) for k, st in enumerate(steps, 1))
        return ('%s<div class="mech-grid routes">%s</div>\n    <div class="tl-box"><div class="tl-t">%s</div><ol class="tl">%s</ol></div>'
                % (m.group(1), cards, m.group(3), tl))
    return GIVEN_RE.sub(fix, page, count=1)


def present(page):
    return how_it_is_given(how_it_works(TABLE_RE.sub(one, page)))

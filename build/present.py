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
        # "... Used for: Head and neck cancers" then one item per line: the item after the colon is the
        # first of the list
        if len(run) >= 2 and out and not out[-1].startswith('<span class="pv-lines">'):
            t = re.match(r'^(.*:)\s*([^:<>]{1,40})\s*$', out[-1], re.S)
            if t and not t.group(2).strip().endswith(':'):
                out[-1] = t.group(1)
                run.insert(0, t.group(2).strip())
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


# first-column headings shown above each card title where the title alone does not say what it is (Sarthak, 20 Nov)
SHOW_FIRST_LABEL = {'cancer site', 'marker', 'type of biopsies', 'test', 'symptom', 'how the taste has shifted',
                    'cancer or situation', 'type of cancer/situation', 'subtype'}


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
                if text(h).lower() in SHOW_FIRST_LABEL:   # the title alone would not say what it is ("Cervix")
                    head.append('<span class="pv-lbl pv-kicker">%s</span>' % h)
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
    if heads and heads[0] == 'medicine group' and 'brands on pharmeasy' in heads and 'what it is used for' in heads:
        return True
    # treatment page "Medicine prices": the 9 drug groups (Sarthak, 20 Nov: accordion, first open)
    return (PAGE.get('url', '').endswith(('/cancer/treatment/', '/cancer/types/cervical-cancer/')) and heads and heads[0] == 'drug group'
            and 'molecules used in india' in heads and ('what it is used for' in heads or 'what is it used for' in heads))


def accordion(hdr, rows):
    """One accordion per medicine group, every group in the same order: molecules and how it is given side by
    side, then what it is used for, then the brands (grouped by molecule, in columns). Closed, a group shows
    its name and a plain-text preview of its molecules. The first group starts open."""
    heads = [text(h).lower() for h in hdr]
    col = lambda name: heads.index(name) if name in heads else None
    i_mol, i_how, i_br = col('molecules used in india'), col('how it is given'), col('brands on pharmeasy')
    i_use = col('what it is used for') if col('what it is used for') is not None else col('what is it used for')
    used = {0, i_mol, i_how, i_use, i_br}
    other = [j for j in range(len(hdr)) if j not in used and any(not is_empty(r[j]) for r in rows)]   # e.g. a filled Price column

    def field(j, r, extra=''):
        if j is None or is_empty(r[j]):
            return ''
        return '<div class="pv-f%s"><span class="pv-lbl">%s</span><div>%s</div></div>' % (extra, hdr[j], split_labels(r[j]))
    out = []
    for n, r in enumerate(rows, 1):
        preview = re.sub(r':\s*,', ':', text(re.sub(r'\s*<br\s*/?>\s*', ', ', r[i_mol]))) if i_mol is not None else ''
        mols = {x.strip().lower() for x in re.split(r'[,;]|\band\b', preview) if x.strip()}
        top = title_field(hdr[0], r[0]) + field(i_mol, r) + field(i_how, r) + ''.join(field(j, r) for j in other)
        use = field(i_use, r, ' pv-wide')
        use = flow_lines(use, mols) if use else ''
        br = field(i_br, r, ' pv-wide')
        br = flow_lines(br, mols) if br else ''
        out.append('<details class="pv-acc"%s><summary><span class="pv-n">%d</span><span class="pv-acc-h"><span class="pv-title">%s</span>'
                   '<span class="pv-acc-sub" aria-hidden="true">%s</span></span><span class="pv-acc-chev" aria-hidden="true">%s</span></summary>'
                   '<div class="pv-acc-body"><div class="pv-acc-top">%s</div>%s%s</div></details>'
                   % (' open' if n == 1 else '', n, plain_title(r[0]), preview, ICON['chev'], top, use, br))
    return '<div class="pv pv-accs">%s</div>' % ''.join(out)


def risks(hdr, rows):
    """Prevention "Risk factor | What the evidence shows | What it contributes | Can you change it? | What to do":
    one full-width row per factor (factor + changeability | evidence + contribution | what to do), the row edge
    coloured by whether it can be changed."""
    heads = [text(h).lower() for h in hdr]
    ci = heads.index('can you change it?')
    di = next((k for k, h in enumerate(heads) if h == 'what to do'), None)
    mid = [k for k in range(1, len(hdr)) if k not in (ci, di)]
    out = []
    for r in rows:
        tone = badge(r[ci], hdr[ci]) if not is_empty(r[ci]) else 'muted'
        left = ('<div class="rk-l"><span class="pv-lbl">%s</span><div class="rk-t">%s</div>%s</div>'
                % (hdr[0], r[0], '<span class="pv-badge %s"><span class="pv-badge-l">%s</span> %s</span>' % (tone, hdr[ci], r[ci]) if not is_empty(r[ci]) else ''))
        midh = ''.join('<div class="pv-f"><span class="pv-lbl">%s</span><div>%s</div></div>' % (hdr[k], r[k]) for k in mid if not is_empty(r[k]))
        do = ('<div class="rk-do"><span class="pv-note-l">%s%s</span><div>%s</div></div>' % (ICON['do'], hdr[di], r[di])) if di is not None and not is_empty(r[di]) else ''
        out.append('<div class="rk rk-%s">%s<div class="rk-m">%s</div>%s</div>' % (tone, left, midh, do))
    return '<div class="pv pv-risks">%s</div>' % ''.join(out)


def plain_title(h):
    """An accordion row title without links or citation markers (a link inside the clickable row is a nested
    control). The original, with its link/citations, goes inside the row as the first field."""
    return re.sub(r'<a\b[^>]*>(.*?)</a>', r'\1', re.sub(r'\s*<sup class="cite">.*?</sup>', '', h, flags=re.S), flags=re.S).strip()


def title_field(label, h):
    return '' if plain_title(h) == h.strip() else '<div class="pv-f pv-src"><span class="pv-lbl">%s</span><div>%s</div></div>' % (label, h)


def table_accordion(hdr, rows):
    """A long card set as an accordion: closed = number, the first-column label and the row name; open = the
    other columns as fields (limitations / other causes keep their note styling). First row open."""
    out = []
    for n, r in enumerate(rows, 1):
        fields, notes = [], []
        for j in range(1, len(hdr)):
            v = r[j]
            if is_empty(v):
                continue
            k = kind(hdr[j])
            if k in ('warn', 'info', 'alert', 'tip', 'do'):
                notes.append('<div class="pv-note %s"><span class="pv-note-l">%s%s</span><div>%s</div></div>' % (k, ICON[k], hdr[j], split_labels(v)))
            else:
                fields.append('<div class="pv-f"><span class="pv-lbl">%s</span><div>%s</div></div>' % (hdr[j], split_labels(v)))
        kicker = '' if text(hdr[0]).lower() in NO_KICKER else '<span class="pv-lbl pv-kicker">%s</span>' % hdr[0]
        fields.insert(0, title_field(hdr[0], r[0]))
        out.append('<details class="pv-acc tacc%s"%s><summary><span class="pv-n">%d</span>%s'
                   '<span class="pv-title">%s</span><span class="pv-acc-chev" aria-hidden="true">%s</span></summary>'
                   '<div class="pv-acc-body"><div class="pv-acc-top">%s</div>%s</div></details>'
                   % ('' if kicker else ' nokick', ' open' if n == 1 else '', n, kicker, plain_title(r[0]), ICON['chev'], ''.join(fields), '<div class="pv-notes">%s</div>' % ''.join(notes) if notes else ''))
    return '<div class="pv pv-accs">%s</div>' % ''.join(out)


NO_KICKER = {'subtype'}     # the section heading "Subtypes" already says it (Sarthak, 20 Nov)

ACCORDION_TABLES = {'/cancer/tests/': {'type of biopsies', 'test', 'marker'},                  # Sarthak, 20 Nov
                    '/cancer/types/cervical-cancer/': {'subtype', 'treatment', 'component'}}


def one(m):
    cls, thead, tbody, foot = m.groups()
    hdr = [h.strip() for h in TH_RE.findall(thead)]
    rows = [[c.strip() for c in TD_RE.findall(tr)] for tr in TR_RE.findall(tbody)]
    rows = [(r + [''] * len(hdr))[:len(hdr)] for r in rows if r]
    if not rows:
        return m.group(0)
    h0 = text(hdr[0]).lower()
    acc_pages = [v for k, v in ACCORDION_TABLES.items() if PAGE.get('url', '').endswith(k)]
    if is_medicine_groups(hdr):
        body = accordion(hdr, rows)
    elif acc_pages and text(hdr[0]).lower() in acc_pages[0]:
        body = table_accordion(hdr, rows)
    elif h0 == 'risk factor' and 'can you change it?' in [text(h).lower() for h in hdr]:
        body = risks(hdr, rows)
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


def _ic(paths):
    return ('<span class="mech-ic" aria-hidden="true"><svg viewBox="0 0 24 24" width="22" height="22"><g fill="none" stroke="currentColor" '
            'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">%s</g></svg></span>' % paths)


IC_LEAF = '<path d="M5 19c0-8 5-13 14-14-1 9-6 14-14 14z"/><path d="M5 19 13 11"/>'
IC_SLIDERS = '<path d="M4 7h10M18 7h2M4 17h4M12 17h8"/><circle cx="16" cy="7" r="2"/><circle cx="10" cy="17" r="2"/>'
IC_SHIELD = '<path d="M12 3 5 6v6c0 4 3 7 7 9 4-2 7-5 7-9V6z"/><path d="m9 12 2 2 4-4"/>'
IC_DNA = MECH_ICON['alkylat']
IC_PILL = ROUTE_ICON['oral']


def section_span(page, sid):
    a = page.find('id="%s"' % sid)
    if a < 0:
        return None
    b = page.find('<div class="asec"', a)
    return a, (b if b > 0 else len(page))


def _course(seg):
    ps = re.findall(r'\n    <p class="lead-p">(.*?)</p>', seg, re.S)
    if len(ps) != 3 or not all(k in ps[0] for k in ('two weeks', 'one-week break', '21 days')):
        return seg
    diagram = ('<div class="cyc" aria-hidden="true"><div class="cyc-bar"><span class="cyc-on">treatment for two weeks</span>'
               '<span class="cyc-off">a one-week break</span></div><div class="cyc-loop">%s repeated every 21 days</div></div>'
               % '<svg viewBox="0 0 24 24" width="15" height="15"><path fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" d="M20 12a8 8 0 1 1-2.3-5.7M20 4v4h-4"/></svg>')
    duo = ('<div class="duo"><div class="mech">%s<p>%s</p></div><div class="mech">%s<p>%s</p></div></div>'
           % (_ic(IC_LEAF), ps[1], _ic(IC_SLIDERS), ps[2]))
    seg = seg.replace('<p class="lead-p">%s</p>' % ps[0], '<p class="lead-p">%s</p>\n    %s' % (ps[0], diagram), 1)
    seg = seg.replace('<p class="lead-p">%s</p>' % ps[1], duo, 1).replace('\n    <p class="lead-p">%s</p>' % ps[2], '', 1)
    return seg


MED_LI = re.compile(r'<li>(<a href="[^"]+">[^<]+</a>):\s*(.*?)</li>', re.S)


def _medicines(seg):
    m = re.search(r'<ul class="pg-list">((?:<li><a href="[^"]+">[^<]+</a>:.*?</li>)+)</ul>', seg, re.S)
    if m and len(MED_LI.findall(m.group(1))) >= 3:
        cards = ''.join('<div class="medex"><div class="medex-t">%s:</div><p>%s</p></div>' % x for x in MED_LI.findall(m.group(1)))
        seg = seg.replace(m.group(0), '<div class="medex-grid">%s</div>' % cards, 1)
    seg = seg.replace('<p class="lead-p"><strong>A note of caution:</strong>', '<p class="note-warn"><strong>A note of caution:</strong>', 1)
    for lbl in ('The medicines used:', 'Medicine Prices and Prescription Requirements:'):
        seg = seg.replace('<p class="lead-p"><strong>%s</strong>' % lbl, '<p class="note-info"><strong>%s</strong>' % lbl, 1)
    return seg


def _changed(seg):
    m = re.search(r'\n    <p class="lead-p">(.*?)</p>', seg, re.S)
    if not m:
        return seg
    groups = []
    for st in sentences(m.group(1)):
        if groups and re.match(r'(This|These|It)\b', st):
            groups[-1] += ' ' + st
        else:
            groups.append(st)
    if len(groups) < 2:
        return seg
    def icon(g):
        l = g.lower()
        return _ic(IC_PILL if 'olanzapine' in l or 'sickness' in l else IC_SHIELD if 'white blood' in l or 'infection' in l else IC_DNA if 'gene' in l else MECH_ICON['misc'])
    cards = ''.join('<div class="mech">%s<p>%s</p></div>' % (icon(g), g) for g in groups)
    return seg.replace(m.group(0), '\n    <div class="news-grid">%s</div>' % cards, 1)


def _questions(seg):
    m = re.search(r'(</h2>\s*)<ul class="pg-list">((?:<li>[^<]*\?</li>)+)</ul>', seg)
    if not m:
        return seg
    qs = re.findall(r'<li>([^<]*\?)</li>', m.group(2))
    items = ''.join('<li><span class="q-n" aria-hidden="true">%d</span><span>%s</span></li>' % (k, q) for k, q in enumerate(qs, 1))
    return seg.replace(m.group(0), m.group(1) + '<ol class="qlist">%s</ol>' % items, 1)


def chemo_sections(page):
    """Chemotherapy page: the sections not yet laid out as components, same words."""
    for sid, fn in (('toc-what-a-course-looks-like', _course), ('toc-the-medicines-used', _medicines),
                    ('toc-what-has-changed-recently', _changed), ('toc-questions-to-ask-your-oncologist', _questions)):
        sp = section_span(page, sid)
        if sp:
            page = page[:sp[0]] + fn(page[sp[0]:sp[1]]) + page[sp[1]:]
    return page


IC = {
    'target': '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1.5"/>',
    'gauge': '<path d="M4 16a8 8 0 1 1 16 0"/><path d="m12 16 4-5"/><path d="M4 20h16"/>',
    'heart': '<path d="M12 20s-7-4.5-7-10a4 4 0 0 1 7-2.6A4 4 0 0 1 19 10c0 5.5-7 10-7 10z"/>',
    'person': '<circle cx="12" cy="8" r="3.5"/><path d="M5 20c0-3.9 3.1-7 7-7s7 3.1 7 7"/>',
    'scalpel': '<path d="M4 20 15 9l3 3-8 8z"/><path d="m15 9 4-5 1 1-2 6"/>',
    'pill': ROUTE_ICON['oral'],
    'ray': '<circle cx="12" cy="12" r="3"/><path d="M12 2v4M12 18v4M2 12h4M18 12h4M5 5l2.5 2.5M16.5 16.5 19 19M5 19l2.5-2.5M16.5 7.5 19 5"/>',
    'scope': '<path d="M6 18h8M3 22h18M14 22a7 7 0 1 0 0-14h-1M9 14h2M9 12a2 2 0 0 1-2-2V6h6v4a2 2 0 0 1-2 2zM12 6V3a1 1 0 0 0-1-1H9a1 1 0 0 0-1 1v3"/>',
    'scan': '<rect x="3" y="4" width="18" height="14" rx="2"/><path d="M8 20h8M7 13l3-3 2 2 4-4"/>',
    'shield': IC_SHIELD,
    'rupee': '<path d="M6 3h12M6 8h12M6 13h3M9 13c6.667 0 6.667-10 0-10M6 13l8.5 8"/>',
    'tag': '<path d="M3 12V4h8l10 10-8 8z"/><circle cx="7.5" cy="8.5" r="1.5"/>',
}
LABEL_LI = re.compile(r'<li>((?:<strong>[^<]+</strong>\s*)+):?\s*(.*?)</li>', re.S)


def label_cards(ul_inner, icon_for, cls='mech-grid'):
    """<li><strong>Label</strong>: text</li> items -> icon cards (None if the list is not all labelled)."""
    items = LABEL_LI.findall(ul_inner)
    if len(items) < 2 or len(items) != ul_inner.count('<li>'):
        return None
    out = []
    for lab, body in items:
        name = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', lab)).strip().rstrip(':')
        out.append('<div class="mech">%s<div><div class="mech-t">%s:</div><p>%s</p></div></div>' % (_ic(IC[icon_for(name)]), name, body.lstrip(': ').strip()))
    return '<div class="%s">%s</div>' % (cls, ''.join(out))


def _note(seg, starts, cls='note-info'):
    return re.sub(r'<p class="lead-p">(%s)' % re.escape(starts), r'<p class="%s">\1' % cls, seg, count=1)


def _stat(seg, starts, number):
    m = re.search(r'<p class="lead-p">(%s.*?)</p>' % re.escape(starts), seg, re.S)
    if not m or number not in m.group(1):
        return seg
    return seg.replace(m.group(0), '<div class="statp"><span class="statp-n" aria-hidden="true">%s</span><p>%s</p></div>' % (number, m.group(1)), 1)


def _t_cure(seg):
    m = re.search(r'<ul class="pg-list">(.*?)</ul>', seg, re.S)
    if m:
        cards = label_cards(m.group(1), lambda n: 'target' if 'curative' in n.lower() else 'gauge' if 'control' in n.lower() else 'heart', 'mech-grid goals')
        if cards:
            seg = seg.replace(m.group(0), cards, 1)
    return seg


def _t_plan(seg):
    m = re.search(r'<ul class="pg-list">(.*?)</ul>', seg, re.S)
    if m:
        role = lambda n: {'surgeon': 'scalpel', 'medical oncologist': 'pill', 'radiation oncologist': 'ray', 'pathologist': 'scope', 'radiologist': 'scan'}.get(n.lower(), 'person')
        cards = label_cards(m.group(1), role, 'mech-grid team')
        if cards:
            seg = seg.replace(m.group(0), cards, 1)
    seg = _note(seg, 'If you are receiving treatment at a smaller cancer centre')
    return _note(seg, 'Ask your doctor which tests')


def _t_types(seg):
    return _note(seg, 'Medicine prices may change over time')


def _t_support(seg):
    m = re.search(r'(<p class="lead-p">They were shown to be less likely.*?median survival of (\d+(?:\.\d+)?) months compared with (\d+(?:\.\d+)?) months in the other group\..*?</p>)', seg, re.S)
    if m:
        a, b = float(m.group(2)), float(m.group(3))
        bars = ('<div class="cmp" aria-hidden="true"><div class="cmp-row"><span class="cmp-l">early palliative care alongside standard cancer care</span>'
                '<span class="cmp-bar"><i style="width:%d%%"></i></span><b>%s months</b></div><div class="cmp-row"><span class="cmp-l">the other group</span>'
                '<span class="cmp-bar alt"><i style="width:%d%%"></i></span><b>%s months</b></div><div class="cmp-cap">median survival</div></div>'
                % (100, m.group(2), round(100 * b / a), m.group(3)))
        seg = seg.replace(m.group(1), m.group(1) + '\n    ' + bars, 1)
    seg = _stat(seg, 'According to WHO, only about 14%', '14%')
    return _note(seg, 'One more misunderstanding', 'note-key')


def _t_pay(seg):
    seg = _stat(seg, 'Cancer treatment is not just a medical concern', '75%')
    m = re.search(r'<ul class="pg-list">((?:<li>.*?</li>)+)</ul>', seg, re.S)
    if m:
        lis = re.findall(r'<li>(.*?)</li>', m.group(1), re.S)
        def icon(t):
            l = t.lower()
            return 'shield' if 'pm-jay' in l[:40] else 'rupee' if 'fund' in l[:80] else 'tag'
        if len(lis) >= 2:
            seg = seg.replace(m.group(0), '<div class="mech-grid relief">%s</div>' % ''.join('<div class="mech">%s<p>%s</p></div>' % (_ic(IC[icon(t)]), t) for t in lis), 1)
    return _note(seg, "Contact your treating team's medical social worker")


def _t_when(seg):
    for starts, cls in (('Seek immediate medical care', 'panel-urgent'), ('Consult your oncology team within days', 'panel-soon')):
        m = re.search(r'<p class="lead-p">(%s[^<]*)</p>\s*<ul class="pg-list">(.*?)</ul>' % re.escape(starts), seg, re.S)
        if m:
            seg = seg.replace(m.group(0), '<div class="%s"><p class="panel-t">%s</p><ul>%s</ul></div>' % (cls, m.group(1), m.group(2)), 1)
    return seg


def treatment_sections(page):
    """Treatment page: sections laid out as components, same words."""
    if 'id="toc-what-cure-actually-means-in-cancer-care"' not in page:
        return page
    for sid, fn in (('toc-what-cure-actually-means-in-cancer-care', _t_cure), ('toc-how-your-treatment-plan-is-decided', _t_plan),
                    ('toc-the-main-types-of-cancer-treatment', _t_types), ('toc-supportive-care-palliative-care-and-side-effects', _t_support),
                    ('toc-paying-for-cancer-treatment-in-india', _t_pay), ('toc-when-to-see-a-doctor', _t_when)):
        sp = section_span(page, sid)
        if sp:
            page = page[:sp[0]] + fn(page[sp[0]:sp[1]]) + page[sp[1]:]
    return page


IC.update({
    'protein': '<path d="M5 12a7 7 0 0 0 14 0z"/><path d="M3 12h18M9 8c0-2 1-3 3-3M13 7c0-1.5 1-2.5 2.5-2.5"/>',
    'energy': '<path d="M13 2 4 14h7l-1 8 9-12h-7z"/>',
    'scale': '<rect x="3" y="4" width="18" height="16" rx="3"/><path d="M8 10a4 4 0 0 1 8 0zM12 10l1.5-2"/>',
    'flask': '<path d="M9 3h6M10 3v6l-5 9a2 2 0 0 0 1.8 3h10.4a2 2 0 0 0 1.8-3l-5-9V3"/><path d="M7.5 15h9"/>',
    'glass': '<path d="M6 3h12l-1.5 17a1.5 1.5 0 0 1-1.5 1.4H9a1.5 1.5 0 0 1-1.5-1.4z"/><path d="M6.5 9h11"/>',
    'nocarb': '<circle cx="12" cy="12" r="9"/><path d="m5.6 5.6 12.8 12.8M9 9c1-2 5-2 6 0s-1 5-3 6"/>',
    'leaf': IC_LEAF,
    'herb': '<path d="M12 21V9M12 13c-4 0-6-3-6-7 4 0 6 3 6 7zM12 11c3 0 5-2 5-5-3 0-5 2-5 5z"/>',
})


def top_items(ul_inner):
    """Top-level <li> contents of a list, nested lists kept inside their item."""
    items, depth, start = [], 0, None
    for m in re.finditer(r'<(/?)(li|ul)\b[^>]*>', ul_inner):
        close, tag = m.group(1), m.group(2)
        if tag == 'ul':
            depth += -1 if close else 1
        elif depth == 0:
            if not close:
                start = m.end()
            elif start is not None:
                items.append(ul_inner[start:m.start()])
                start = None
    return items


def first_ul(seg, after=None):
    """(full match span, inner) of the first top-level <ul class="pg-list"> in seg (optionally after a phrase)."""
    a = seg.find('<ul class="pg-list">', seg.find(after) if after else 0)
    if a < 0:
        return None
    depth, i = 0, a
    for m in re.finditer(r'<(/?)ul\b[^>]*>', seg[a:]):
        depth += -1 if m.group(1) else 1
        if depth == 0:
            e = a + m.end()
            return (a, e), seg[a + len('<ul class="pg-list">'):e - len('</ul>')]
    return None


def labelled_cards(seg, after, icon_for, cls='mech-grid', card='mech'):
    """A list whose every item opens with a bold label -> icon cards (nested sub-lists stay in the card)."""
    hit = first_ul(seg, after)
    if not hit:
        return seg
    (a, e), inner = hit
    items = top_items(inner)
    cards = []
    for it in items:
        m = re.match(r'\s*((?:<strong>[^<]+</strong>\s*)+)(.*)$', it, re.S)
        if not m:
            return seg
        name = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', m.group(1))).strip()
        body = m.group(2).strip()
        if body.startswith(':') and not name.endswith(':'):
            name, body = name + ':', body[1:].strip()
        body_html = body if body.startswith('<') and not body.startswith('<a') and not body.startswith('<sup') else '<p>%s</p>' % body
        body_html = re.sub(r'^<p>(.*?)(<ul class="pg-list">.*)</p>$', r'<p>\1</p>\2', body_html, flags=re.S)
        cards.append('<div class="%s">%s<div><div class="mech-t">%s</div>%s</div></div>' % (card, _ic(IC[icon_for(name)]), name, body_html))
    return seg[:a] + '<div class="%s">%s</div>' % (cls, ''.join(cards)) + seg[e:]


def _checks(seg, after):
    hit = first_ul(seg, after)
    if not hit:
        return seg
    (a, e), inner = hit
    return seg[:a] + '<ul class="pg-list checks">' + inner + '</ul>' + seg[e:]


def _h3_panel(seg, h3_start, cls):
    m = re.search(r'<h3 class="h3" id="([^"]+)"[^>]*>(%s[^<]*)</h3>\s*<ul class="pg-list">(.*?)</ul>' % re.escape(h3_start), seg, re.S)
    if not m:
        return seg
    return seg.replace(m.group(0), '<div class="%s"><h3 class="panel-t" id="%s">%s</h3><ul>%s</ul></div>' % (cls, m.group(1), m.group(2), m.group(3)), 1)


def _bars(seg, starts, a_label, b_label, cap):
    m = re.search(r'(<p class="lead-p">%s.*?at (\d+(?:\.\d+)?) months compared against (\d+(?:\.\d+)?) months.*?</p>)' % re.escape(starts), seg, re.S)
    if not m:
        return seg
    a, b = float(m.group(2)), float(m.group(3))
    bars = ('<div class="cmp" aria-hidden="true"><div class="cmp-row"><span class="cmp-l">%s</span><span class="cmp-bar"><i style="width:100%%"></i></span><b>%s months</b></div>'
            '<div class="cmp-row"><span class="cmp-l">%s</span><span class="cmp-bar alt"><i style="width:%d%%"></i></span><b>%s months</b></div><div class="cmp-cap">%s</div></div>'
            % (a_label, m.group(2), b_label, round(100 * b / a), m.group(3), cap))
    return seg.replace(m.group(1), m.group(1) + '\n    ' + bars, 1)


def _n_needs(seg):
    return labelled_cards(seg, None, lambda n: 'protein' if 'protein' in n.lower() else 'energy' if 'energy' in n.lower() else 'scale', 'mech-grid tips3')


def _n_eating(seg):
    seg = _checks(seg, 'Avoiding these in Indian cooking')
    seg = _note(seg, 'A dental checkup before treatment')
    seg = _note(seg, 'Call your doctor if mouth, lip or throat pain', 'note-warn')
    seg = _checks(seg, 'Now comes the dietary adjustment part')
    seg = _note(seg, 'If nausea begins even before you reach the hospital')
    seg = _checks(seg, 'Appetite loss without nausea')
    seg = re.sub(r'<p class="lead-p">(<strong>The medicines used:</strong>)', r'<p class="note-info">\1', seg, count=1)
    return _note(seg, 'Treatment options may change as new evidence')


def _n_safety(seg):
    seg = _checks(seg, 'Some practical rules for an Indian kitchen')
    return re.sub(r'<p class="lead-p">(<strong>Note:</strong>\s*A fever)', r'<p class="note-warn">\1', seg, count=1)


def _n_cachexia(seg):
    seg = _note(seg, 'Explaining this clearly is important', 'note-key')
    return _note(seg, 'Blood tests have a useful but limited role')


def _n_diets(seg):
    def icon(n):
        l = n.lower()
        return ('flask' if 'alkaline' in l else 'glass' if 'juic' in l else 'nocarb' if 'keto' in l or 'carbo' in l
                else 'leaf' if 'fruit' in l else 'herb' if 'herbal' in l else 'pill')
    seg = labelled_cards(seg, None, icon, 'mech-grid myths', 'mech myth')
    return re.sub(r'<p class="lead-p">(<strong>Important:</strong>)', r'<p class="note-warn">\1', seg, count=1)


def _n_when(seg):
    seg = _h3_panel(seg, 'Contact your team the same day', 'panel-urgent')
    seg = _h3_panel(seg, 'Arrange an appointment within a week or two', 'panel-soon')
    return _bars(seg, 'One study at a single institution', 'nutritional counselling was included in care', 'compared against', 'overall survival')


def nutrition_sections(page):
    if 'id="toc-what-the-body-actually-needs-during-treatment"' not in page:
        return page
    for sid, fn in (('toc-what-the-body-actually-needs-during-treatment', _n_needs), ('toc-eating-through-taste-change-mouth-sores-and-nausea', _n_eating),
                    ('toc-food-safety-when-white-cell-counts-are-low', _n_safety), ('toc-cachexia-when-eating-more-is-not-enough', _n_cachexia),
                    ('toc-anti-cancer-diets-alkaline-diets-and-what-they-cost', _n_diets), ('toc-when-to-see-a-doctor', _n_when)):
        sp = section_span(page, sid)
        if sp:
            page = page[:sp[0]] + fn(page[sp[0]:sp[1]]) + page[sp[1]:]
    return page


IC['virus'] = ('<circle cx="12" cy="12" r="5"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M4.9 19.1 7 17M17 7l2.1-2.1"/>'
               '<circle cx="12" cy="12" r="1" fill="currentColor"/>')


def _cmp_pct(seg, starts, rx, la, lb):
    """Comparison bar for two percentages found in a paragraph (labels are the doc's own phrases)."""
    m = re.search(r'(<p class="lead-p">%s.*?</p>)' % re.escape(starts), seg, re.S)
    n = m and re.search(rx, m.group(1))
    if not n:
        return seg
    a, b = float(n.group(1)), float(n.group(2))
    hi = max(a, b)
    bars = ('<div class="cmp" aria-hidden="true"><div class="cmp-row"><span class="cmp-l">%s</span><span class="cmp-bar"><i style="width:%d%%"></i></span><b>%s%%</b></div>'
            '<div class="cmp-row"><span class="cmp-l">%s</span><span class="cmp-bar alt"><i style="width:%d%%"></i></span><b>%s%%</b></div></div>'
            % (la, round(100 * a / hi), n.group(1), lb, round(100 * b / hi), n.group(2)))
    return seg.replace(m.group(1), m.group(1) + '\n    ' + bars, 1)


def _p_tobacco(seg):
    m = re.search(r'<p class="lead-p">(Tobacco use in India takes.*?)</p>', seg, re.S)
    n = m and re.search(r'([\d.]+)% of Indian adults use tobacco, with ([\d.]+)% using smokeless tobacco and ([\d.]+)% smoking', m.group(1))
    if n:
        tiles = ('<div class="stat3" aria-hidden="true"><div><b>%s%%</b><span>of Indian adults use tobacco</span></div>'
                 '<div><b>%s%%</b><span>using smokeless tobacco</span></div><div><b>%s%%</b><span>smoking</span></div></div>' % n.groups())
        seg = seg.replace(m.group(0), m.group(0) + '\n    ' + tiles, 1)
    return seg     # quit-advice comparison bar removed (Sarthak, 20 Nov)


def _p_infections(seg):
    hit = first_ul(seg, 'Several viruses and one bacterium')
    if not hit:
        return seg
    (a, e), inner = hit
    items = top_items(inner)
    if len(items) < 3 or not all(it.lstrip().startswith(('<strong>', '<a href')) for it in items):
        return seg
    # HPV: the vaccination programme starts its own paragraph (Sarthak, 20 Nov)
    body = lambda it: re.sub(r'(\.(?:<sup class="cite">.*?</sup>)?\.?)\s+(India launched a nationwide)', r'\1</p><p>\2', it.strip(), count=1)
    cards = ''.join('<div class="mech">%s<div>%s</div></div>' % (_ic(IC['virus']), '<p>%s</p>' % body(it)) for it in items)
    return seg[:a] + '<div class="mech-grid infx">%s</div>' % cards + seg[e:]


def _p_plan(seg):
    hit = first_ul(seg, 'Prioritise changes by how much they help')
    if not hit:
        return seg
    (a, e), inner = hit
    items = top_items(inner)
    lis = ''.join('<li><span class="tl-n" aria-hidden="true">%d</span><p>%s</p></li>' % (k, it.strip()) for k, it in enumerate(items, 1))
    return seg[:a] + '<ol class="tl prio">%s</ol>' % lis + seg[e:]


def _p_when(seg):
    for starts, cls in (('Seek care within days if you notice', 'panel-urgent'), ('Contact a doctor within a few weeks', 'panel-soon')):
        m = re.search(r'<p class="lead-p">((?:<strong>)?%s.*?)</p>\s*<ul class="pg-list">(.*?)</ul>' % re.escape(starts), seg, re.S)
        if m:
            head = re.sub(r'</?strong>', '', m.group(1))          # the panel title is bold already
            seg = seg.replace(m.group(0), '<div class="%s"><p class="panel-t">%s</p><ul>%s</ul></div>' % (cls, head, m.group(2)), 1)
    return re.sub(r'<p class="lead-p">(<strong>Note:</strong>\s*The information on this page)', r'<p class="note-info">\1', seg, count=1)


def prevention_sections(page):
    if 'id="toc-tobacco-the-single-largest-modifiable-cause-in-india"' not in page:
        return page
    for sid, fn in (('toc-tobacco-the-single-largest-modifiable-cause-in-india', _p_tobacco), ('toc-infections-alcohol-weight-and-diet', _p_infections),
                    ('toc-sorting-real-risks-from-rumours', _p_plan), ('toc-when-to-see-a-doctor', _p_when)):
        sp = section_span(page, sid)
        if sp:
            page = page[:sp[0]] + fn(page[sp[0]:sp[1]]) + page[sp[1]:]
    return page


IC['clock'] = '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>'
IC['syringe'] = ROUTE_ICON['injection']


def _replace_ul(seg, after, render):
    hit = first_ul(seg, after)
    if not hit:
        return seg
    (a, e), inner = hit
    out = render(top_items(inner))
    return seg if out is None else seg[:a] + out + seg[e:]


def _h_types(items):
    if len(items) != 2:
        return None
    tone = lambda it: 'lo' if text(it).lower().startswith('low-risk') else 'hi'
    return '<div class="hpvt">%s</div>' % ''.join('<div class="hpvt-%s"><p>%s</p></div>' % (tone(it), it.strip()) for it in items)


def _h_schedule(items):
    rows = ''.join('<li>%s<span>%s</span></li>' % (_ic(IC['syringe']), re.sub(r'(\([^()]*doses?[^()]*\))', r'<b class="dose">\1</b>', it.strip())) for it in items)
    return '<ul class="sched">%s</ul>' % rows


def _h_india(items):
    def icon(it):
        l = text(it).lower()
        return ('clock' if '2008' in l else 'person' if 'girls only' in l or 'targets 14' in l else 'shield' if 'no evidence' in l
                else 'scope' if 'np-ncd' in l or 'screening is offered' in l else 'target')
    return '<div class="mech-grid infx">%s</div>' % ''.join('<div class="mech">%s<p>%s</p></div>' % (_ic(IC[icon(it)]), it.strip()) for it in items)


def _h_measures(items):
    out = []
    for it in items:
        lab = text(re.split(r'<ul>', it)[0]).lower()
        if 'contact the doctor promptly' in lab or 'arrange an appointment' in lab:
            head, _, rest = it.partition('<ul>')
            cls = 'panel-urgent' if 'contact' in lab else 'panel-soon'
            out.append('<div class="%s"><p class="panel-t">%s</p><ul>%s</div>' % (cls, head.strip(), rest))
        else:
            m = re.match(r'\s*<strong>([^<]+?):?</strong>:?\s*(.*)$', it, re.S)
            if not m:
                return None
            icon = 'scope' if 'screening' in m.group(1).lower() else 'syringe'
            out.append('<div class="mech">%s<div><div class="mech-t">%s:</div><p>%s</p></div></div>' % (_ic(IC[icon]), m.group(1), m.group(2).strip()))
    cards = ''.join(x for x in out if x.startswith('<div class="mech"'))
    panels = ''.join(x for x in out if not x.startswith('<div class="mech"'))
    return '<div class="mech-grid tips3">%s</div>%s' % (cards, panels)


def _h_myths(items):
    out = []
    for it in items:
        m = re.match(r'\s*<strong>([^<]+?)</strong>\s*(.*)$', it, re.S)
        if not m:
            return None
        out.append('<div class="mech myth">%s<div><div class="mech-t">%s</div><p>%s</p></div></div>' % (_ic(IC['nocarb']), m.group(1), m.group(2).strip()))
    return '<div class="mech-grid myths">%s</div>' % ''.join(out)


def hpv_sections(page):
    if '/cancer/prevention/hpv/' not in PAGE.get('url', ''):
        return page
    def evidence(seg):
        return _replace_ul(seg, 'HPV types are classified as low-risk or high-risk', _h_types)
    def risk(seg):
        seg = _replace_ul(seg, 'According to the World Health Organization (WHO), vaccine recommendations', _h_schedule)
        return _stat(seg, 'An Indian multicentre study found that a single dose', '95.4%')
    def india(seg):
        m = re.search(r'sets three targets: (\d+)% of girls fully vaccinated by age 15, (\d+)% of women screened with a high-performance test by ages 35 and 45, and (\d+)% of women with cervical disease receiving treatment', seg)
        seg = _replace_ul(seg, 'Some important points include', _h_india)
        if m:
            tiles = ('<div class="stat3" aria-hidden="true"><div><b>%s%%</b><span>of girls fully vaccinated by age 15</span></div>'
                     '<div><b>%s%%</b><span>of women screened with a high-performance test by ages 35 and 45</span></div>'
                     '<div><b>%s%%</b><span>of women with cervical disease receiving treatment</span></div></div>' % m.groups())
            i = seg.find('<div class="mech-grid infx">')
            j = seg.find('\n', i)
            seg = seg[:j] + '\n    ' + tiles + seg[j:] if i >= 0 and j > 0 else seg
        return seg
    def measures(seg):
        return _replace_ul(seg, 'Here’s what you can do to protect', _h_measures)
    def myths(seg):
        return _replace_ul(seg, 'Several myths about HPV', _h_myths)
    for sid, fn in (('toc-what-the-evidence-shows', evidence), ('toc-how-it-changes-risk', risk), ('toc-the-india-picture', india),
                    ('toc-measures-to-protect-and-prevent', measures), ('toc-what-the-evidence-does-not-support', myths)):
        sp = section_span(page, sid)
        if sp:
            page = page[:sp[0]] + fn(page[sp[0]:sp[1]]) + page[sp[1]:]
    return page


# ---------------------------------------------------------------- semantics
# The components above are laid out with <div>s. Search engines read a page's structure from its tags, so a
# last pass gives them back what the doc had: a card set that came from a list is a <ul> of <li> cards, and a
# card's title is a heading one level below the section it sits in (h3 under an h2, h4 under an h3).

LIST_SETS = (('mech-grid', 'mech'), ('medex-grid', 'medex'), ('pv pv-cards', 'pv-card'), ('pv pv-risks', 'rk'),
             ('hpvt', 'hpvt-'), ('pv pv-sits', 'pv-sit'), ('pv pv-facts', 'pv-fact'), ('pv pv-stats', 'pv-stat'))
TITLE_CLASSES = ('mech-t', 'medex-t', 'pv-title', 'rk-t', 'panel-t', 'tl-t', 'dg-name', 'med-label')
TAG_RE = re.compile(r'<(/?)div\b[^>]*>')


def _match_div(h, start):
    """Index just past the </div> that closes the <div> opening at start."""
    depth = 0
    for m in TAG_RE.finditer(h, start):
        depth += -1 if m.group(1) else 1
        if depth == 0:
            return m.end()
    return -1


def _listify(h):
    out, i = [], 0
    pat = re.compile(r'<div class="(%s)(?: [^"]*)?">' % '|'.join(re.escape(c) for c, _ in LIST_SETS))
    while True:
        m = pat.search(h, i)
        if not m:
            out.append(h[i:])
            return ''.join(out)
        end = _match_div(h, m.start())
        if end < 0:
            out.append(h[i:])
            return ''.join(out)
        child = dict(LIST_SETS)[m.group(1)]
        inner = h[m.end():end - len('</div>')]
        kids, j, ok = [], 0, True
        while j < len(inner):
            cm = re.match(r'<div class="%s[^"]*"[^>]*>' % re.escape(child), inner[j:])
            if not cm:
                ok = False
                break
            ce = _match_div(inner, j)
            body = inner[j + cm.end():ce - len('</div>')]
            kids.append('<li' + cm.group(0)[4:] + _listify(body) + '</li>')
            j = ce
        if ok and kids:
            out.append(h[i:m.start()] + '<ul' + m.group(0)[4:] + ''.join(kids) + '</ul>')
        else:
            out.append(h[i:m.end()])
            end = m.end()
        i = end


def _titles(h):
    """Card titles -> h3/h4, one level below the closest section heading (h2 or a doc h3) above them."""
    tag_re = re.compile(r'<(h2|h3)\b(?![^>]*class="(?:%s)")|<(div|span|p) class="(%s)"' % ('|'.join(TITLE_CLASSES), '|'.join(TITLE_CLASSES)))
    out, i, level = [], 0, 2
    for m in tag_re.finditer(h):
        if m.group(1):
            level = int(m.group(1)[1])
            continue
        if m.start() < i:
            continue
        tag, cls = m.group(2), m.group(3)
        close = h.find('</%s>' % tag, m.end())
        if tag == 'div':            # titles hold no nested divs
            close = h.find('</div>', m.end())
        hx = 'h%d' % min(level + 1, 4)
        out.append(h[i:m.start()] + '<%s class="%s"' % (hx, cls) + h[m.end():close] + '</%s>' % hx)
        i = close + len('</%s>' % tag)
    out.append(h[i:])
    return ''.join(out)


def semantic(page):
    a = page.find('<div class="art"')
    if a < 0:
        return page
    b = page.find('id="references"', a)
    b = len(page) if b < 0 else b
    art = page[a:b]
    # accordion summary: the group name is the heading, the molecule preview stays beside it
    art = re.sub(r'<span class="pv-acc-h">(<span class="pv-title">.*?</span>)(<span class="pv-acc-sub"[^>]*>.*?</span>)</span>', r'\1\2', art, flags=re.S)
    art = _titles(_listify(art))
    return page[:a] + art + page[b:]


IC.update({
    'lump': '<circle cx="12" cy="12" r="8"/><circle cx="14" cy="10" r="3"/>',
    'mouth': '<path d="M4 12c2-3 5-4 8-4s6 1 8 4c-2 3-5 4-8 4s-6-1-8-4z"/><path d="M4 12h16"/>',
    'lungs': '<path d="M12 4v8M12 12c-1 0-2 1-3 2l-3 3c-1 1-3 0-3-2V11c0-3 2-5 4-5 1 0 2 1 2 2M12 12c1 0 2 1 3 2l3 3c1 1 3 0 3-2V11c0-3-2-5-4-5-1 0-2 1-2 2"/>',
    'gut': '<path d="M7 4c-2 2-2 5 0 6h8c2 0 3 2 2 4s-3 2-5 2H9c-2 0-3 2-2 3s3 1 4 1"/>',
    'throat': '<path d="M9 3v6c0 2-2 3-2 6v6M15 3v6c0 2 2 3 2 6v6"/><path d="M10 13h4"/>',
    'flame': '<path d="M12 3c1 4 6 6 6 11a6 6 0 0 1-12 0c0-3 2-4 3-6 0 2 1 3 2 3 0-3-1-5 1-8z"/>',
    'drop': '<path d="M12 3s6 7 6 11a6 6 0 0 1-12 0c0-4 6-11 6-11z"/>',
    'skin': '<rect x="4" y="4" width="16" height="16" rx="4"/><circle cx="10" cy="10" r="1.5"/><circle cx="15" cy="14" r="2"/>',
    'battery': '<rect x="3" y="8" width="16" height="8" rx="2"/><path d="M21 11v2M6 11v2"/>',
    'thermo': '<path d="M14 14.8V5a2 2 0 0 0-4 0v9.8a4 4 0 1 0 4 0z"/><path d="M12 9v7"/>',
    'wind': '<path d="M3 9h11a3 3 0 1 0-3-3M3 15h15a3 3 0 1 1-3 3M3 12h7"/>',
    'female': '<circle cx="12" cy="9" r="5"/><path d="M12 14v7M9 18h6"/>',
    'male': '<circle cx="10" cy="14" r="5"/><path d="M14 10l6-6M15 4h5v5"/>',
    'child': '<circle cx="12" cy="6" r="3"/><path d="M8 21v-6l-2-3 3-2h6l3 2-2 3v6"/>',
    'pin': '<path d="M12 21s7-6 7-11a7 7 0 0 0-14 0c0 5 7 11 7 11z"/><circle cx="12" cy="10" r="2.5"/>',
    'approx': '<circle cx="9" cy="12" r="5.5"/><circle cx="15" cy="12" r="5.5" stroke-dasharray="2.4 2"/>',   # a lookalike
    'flag': '<path d="M5 21V4M5 4h11l-2 4 2 4H5"/>',
})


def _sym_icon(n):
    l = n.lower()
    for k, ic in (('lump', 'lump'), ('mouth', 'mouth'), ('cough', 'lungs'), ('bowel', 'gut'), ('swallow', 'throat'), ('heartburn', 'flame'),
                  ('bleeding', 'drop'), ('weight', 'scale'), ('skin', 'skin'), ('fatigue', 'battery'), ('fever', 'thermo'), ('breath', 'wind'),
                  ('women', 'female'), ('men', 'male'), ('children', 'child'), ('site', 'pin')):
        if k in l:
            return ic
    return 'target'


def _plain_cards(items, icon, cls):
    ic = _ic(IC[icon]) if icon else ''
    return '<div class="mech-grid %s">%s</div>' % (cls, ''.join('<div class="mech">%s<p>%s</p></div>' % (ic, it.strip()) for it in items))


def labelled_accordion(seg, after, icon_for, cls):
    """A list whose every item opens with a bold label -> one accordion row per item (icon + label as the
    row heading, the rest inside). First row open."""
    hit = first_ul(seg, after)
    if not hit:
        return seg
    (a, e), inner = hit
    rows = []
    for n, it in enumerate(top_items(inner)):
        m = re.match(r'\s*((?:<strong>[^<]+</strong>\s*)+)(.*)$', it, re.S)
        if not m:
            return seg
        name = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', m.group(1))).strip()
        body = m.group(2).strip()
        if body.startswith(':') and not name.endswith(':'):
            name, body = name + ':', body[1:].strip()
        rows.append('<details class="pv-acc %s"%s><summary>%s<span class="pv-title">%s</span><span class="pv-acc-chev" aria-hidden="true">%s</span></summary>'
                    '<div class="pv-acc-body"><p>%s</p></div></details>' % (cls, ' open' if n == 0 else '', _ic(IC[icon_for(name)]), name, ICON['chev'], body))
    return seg[:a] + '<div class="pv pv-accs">%s</div>' % ''.join(rows) + seg[e:]


LAB_LI = re.compile(r'\s*<strong>(.*?)</strong>\s*(.*)$', re.S)


def _lab(it):
    """(title html, title text, body) of an item that opens with a bold label (links inside the label kept)."""
    # "[**C-Reactive Protein Test (CRP)**](link)**:**" -> one bold label holding the link
    it = re.sub(r'^\s*<a ([^>]*)><strong>(.*?)</strong></a>\s*<strong>:</strong>', r'<strong><a \1>\2</a>:</strong>', it, flags=re.S)
    m = LAB_LI.match(it)
    if not m:
        return None
    title, body = m.group(1).strip(), m.group(2).strip()
    c = re.match(r'(<sup class="cite">.*?</sup>)\s*:\s*', body, re.S)     # "**Immunohistochemistry**[46]:"
    if c:
        title, body = title + c.group(1) + ':', body[c.end():]
    if body.startswith(':') and not re.sub(r'<[^>]+>', '', title).rstrip().endswith(':'):
        title, body = title + ':', body[1:].strip()
    return title, re.sub(r'<[^>]+>', '', title), body


def tests_sections(page):
    if not PAGE.get('url', '').endswith('/cancer/tests/'):
        return page
    def biopsy(seg):
        return re.sub(r'<p class="lead-p">(<strong>Note:</strong>\s*Biopsies may cause)', r'<p class="note-info">\1', seg, count=1)
    def blood(seg):
        def nonmarkers(items):
            out = []
            for it in items:
                lab = _lab(it)
                if not lab:
                    return None
                icon = 'drop' if 'blood' in lab[1].lower() or 'crp' in lab[1].lower() or 'ana' in lab[1].lower() else 'flask'
                out.append('<div class="mech">%s<div><div class="mech-t">%s</div><p>%s</p></div></div>' % (_ic(IC[icon]), lab[0], lab[2]))
            return '<div class="mech-grid infx">%s</div>' % ''.join(out)
        seg = _replace_ul(seg, 'Blood tests that are not tumour markers', nonmarkers)
        def markers(items):
            rows, merged = [], []
            for it in items:                     # an unlabelled item continues the one above it (AFP in testicular cancer)
                lab = _lab(it)
                if lab:
                    merged.append([lab[0], [lab[2]]])
                elif merged:
                    merged[-1][1].append(it.strip())
                else:
                    return None
            for n, (title, bodies) in enumerate(merged):
                lab = (title, None, '</p><p>'.join(bodies))
                # plain bold titles, not headings: the marker cards above already head these markers (Sarthak, 20 Nov)
                rows.append('<details class="pv-acc sym"%s><summary>%s<strong class="pv-title nohead">%s</strong><span class="pv-acc-chev" aria-hidden="true">%s</span></summary>'
                            '<div class="pv-acc-body"><p>%s</p></div></details>' % (' open' if n == 0 else '', _ic(IC['flask']), lab[0], ICON['chev'], lab[2]))
            return '<div class="pv pv-accs">%s</div>' % ''.join(rows)
        return _replace_ul(seg, 'how doctors use different tumour markers', markers)
    def report(seg):
        def parts(items):
            out = []
            for it in items:
                lab = _lab(it)
                if not lab:
                    return None
                out.append('<div class="medex"><div class="medex-t">%s</div><p>%s</p></div>' % (lab[0], lab[2]))
            return '<div class="medex-grid rpt">%s</div>' % ''.join(out)
        return _replace_ul(seg, 'The main details in a report may include', parts)
    def when(seg):
        def panels(items):
            out = []
            for it in items:
                lab = _lab(it)
                if not lab:
                    return None
                l = lab[1].lower()
                cls = 'panel-urgent' if 'same day' in l else 'panel-soon' if 'soon' in l else 'note-panel'
                out.append('<div class="%s"><p class="panel-t">%s</p><p>%s</p></div>' % (cls, lab[0], lab[2]))
            return ''.join(out)                  # the doc's order
        return _replace_ul(seg, 'Consult a doctor if you notice any of the following', panels)
    for sid, fn in (('toc-biopsy-what-it-is-and-how-it-is-done', biopsy), ('toc-blood-tests-and-tumour-markers', blood),
                    ('toc-what-a-pathology-report-actually-says', report), ('toc-when-to-see-a-doctor', when)):
        sp = section_span(page, sid)
        if sp:
            page = page[:sp[0]] + fn(page[sp[0]:sp[1]]) + page[sp[1]:]
    return page


def _wrap_p(seg, starts, cls, icon=None):
    """A paragraph beginning with a phrase -> a styled block (same paragraph inside)."""
    m = re.search(r'<p class="lead-p">(%s.*?)</p>' % re.escape(starts), seg, re.S)
    if not m:
        return seg
    if icon:
        return seg.replace(m.group(0), '<div class="mech %s">%s<p>%s</p></div>' % (cls, _ic(IC[icon]), m.group(1)), 1)
    return seg.replace(m.group(0), '<div class="%s"><p>%s</p></div>' % (cls, m.group(1)), 1)


def cervical_sections(page):
    if not PAGE.get('url', '').endswith('/cancer/types/cervical-cancer/'):
        return page
    def symptoms(seg):
        hit = first_ul(seg, 'When symptoms do appear')
        if hit:
            (a, e), inner = hit
            seg = seg[:a] + '<div class="panel-soon"><ul class="cols2">%s</ul></div>' % inner + seg[e:]
        return seg
    def diagnosis(seg):
        icon = lambda n: 'scan' if 'imag' in n.lower() else 'scope'
        seg = labelled_accordion(seg, 'may be done to reach a diagnosis', icon, 'sym')     # accordions (Sarthak, 20 Nov)
        return labelled_accordion(seg, 'the extent of its spread', icon, 'sym')
    def stages(seg):
        hit = first_ul(seg, 'FIGO 2018 system')
        if not hit:
            return seg
        (a, e), inner = hit
        out = []
        for it in top_items(inner):
            lab = _lab(it)
            if not lab:
                return seg
            n = re.search(r'Stage\s+([IV]+)', lab[1])
            lvl = {'I': 1, 'II': 2, 'III': 3, 'IV': 4}.get(n.group(1), 1) if n else 1
            out.append('<div class="medex stg stg-%d"><span class="stg-b" aria-hidden="true">%s</span><div><div class="medex-t">%s</div><p>%s</p></div></div>'
                       % (lvl, n.group(1) if n else '', lab[0], lab[2]))
        return seg[:a] + '<div class="medex-grid stages">%s</div>' % ''.join(out) + seg[e:]
    def treatment(seg):
        return _replace_ul(seg, 'treatment at each stage includes the following',
                           lambda items: '<ol class="tl prio">%s</ol>' % ''.join('<li><span class="tl-n" aria-hidden="true">%d</span><p>%s</p></li>' % (k, it.strip()) for k, it in enumerate(items, 1)))
    def prevention(seg):
        seg = _wrap_p(seg, '<strong>Vaccination.</strong>', 'prev-card', 'syringe')
        seg = _wrap_p(seg, '<strong>Screening.</strong>', 'prev-card', 'scope')
        seg = re.sub(r'(<div class="mech prev-card">.*?</div>)\s*(<div class="mech prev-card">.*?</div>)', r'<div class="mech-grid prev2">\1\2</div>', seg, count=1, flags=re.S)
        return _note(seg, "General women's health panels are also available")
    def applies(seg):
        seg = _wrap_p(seg, 'Seek care within days if you have any of the following types of bleeding', 'panel-soon')
        return _note(seg, 'Go to an emergency department for heavy bleeding', 'note-warn')
    def related(seg):
        seg = _note(seg, '<strong>Disclaimer:</strong>')
        seg = _note(seg, '<strong>Tip:</strong>')
        icon = lambda n: {'day-care cover:': 'clock', 'waiting periods:': 'clock'}.get(n.lower(), 'shield')
        return labelled_cards(seg, 'Four things that often people are unaware of', icon, 'mech-grid infx')
    for sid, fn in (('toc-symptoms', symptoms), ('toc-diagnosis-of-precancer-and-cancer', diagnosis), ('toc-stages', stages), ('toc-treatment', treatment),
                    ('toc-prevention-and-screening', prevention), ('toc-which-applies-to-you', applies), ('toc-related-cancers', related)):
        sp = section_span(page, sid)
        if sp:
            page = page[:sp[0]] + fn(page[sp[0]:sp[1]]) + page[sp[1]:]
    return page


def symptoms_sections(page):
    if '/cancer/symptoms/' not in PAGE.get('url', ''):
        return page
    def warrant(seg):
        return labelled_accordion(seg, None, _sym_icon, 'sym')     # accordion (Sarthak, 20 Nov)
    def mimic(seg):
        return _replace_ul(seg, 'Other such examples include', lambda it: _plain_cards(it, None, 'mimic'))
    def redflag(seg):
        return _replace_ul(seg, 'Some common red-flag symptoms include', lambda it: _plain_cards(it, 'flag', 'redflags'))
    def sexsite(seg):
        for after in ('Some changes to watch out for', 'Check our guide for more details'):
            seg = labelled_cards(seg, after, _sym_icon, 'mech-grid groups')
        seg = re.sub(r'(<div class="mech-grid groups">.*?)(?=\n    <p)', lambda m: m.group(1).replace('<ul>', '<ul class="pg-list checks">'), seg, flags=re.S)
        return _stat(seg, '<strong>Note:</strong> Only 0.9%', '0.9%')
    def when(seg):
        hit = first_ul(seg, 'Contact your doctor if you notice')
        if hit:
            (a, e), inner = hit
            seg = seg[:a] + '<div class="panel-soon"><ul>%s</ul></div>' % inner + seg[e:]
        return re.sub(r'<p class="lead-p">(<strong>Note:</strong>\s*See your doctor immediately)', r'<p class="note-warn">\1', seg, count=1)
    for sid, fn in (('toc-the-symptoms-that-genuinely-warrant-assessment', warrant), ('toc-health-conditions-that-can-mimic-cancer-symptoms', mimic),
                    ('toc-red-flag-combinations', redflag), ('toc-variations-by-sex-and-site', sexsite), ('toc-when-to-see-a-doctor', when)):
        sp = section_span(page, sid)
        if sp:
            page = page[:sp[0]] + fn(page[sp[0]:sp[1]]) + page[sp[1]:]
    return page


PAGE = {}


def present(page):
    m = re.search(r'<link rel="canonical" href="([^"]+)"', page)
    PAGE['url'] = m.group(1) if m else ''
    return semantic(cervical_sections(tests_sections(symptoms_sections(hpv_sections(prevention_sections(nutrition_sections(treatment_sections(chemo_sections(how_it_is_given(how_it_works(TABLE_RE.sub(one, page))))))))))))

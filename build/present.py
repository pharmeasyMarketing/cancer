"""Present SOME editorial tables as components that suit their data, without touching the words.

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
        out.append('<div class="pv-card"><div class="pv-head"><span class="pv-n">%d</span><div>%s%s</div></div>%s%s</div>'
                   % (i, ''.join(head),
                      '<div class="pv-metas">%s</div>' % ''.join(metas) if metas else '',
                      '<div class="pv-body">%s</div>' % ''.join(body) if body else '',
                      '<div class="pv-notes">%s</div>' % ''.join(notes) if notes else ''))
    # few rows, or light rows: lay the cards side by side; heavy rows read better one per line
    weight = sum(len(text(v)) for r in rows for v in r) / max(1, len(rows))
    layout = 'pv-row' if len(rows) <= 3 else ('pv-grid' if weight < 260 else 'pv-list')
    return '<div class="pv pv-cards %s">%s</div>' % (layout, ''.join(out))


def one(m):
    cls, thead, tbody, foot = m.groups()
    hdr = [h.strip() for h in TH_RE.findall(thead)]
    rows = [[c.strip() for c in TD_RE.findall(tr)] for tr in TR_RE.findall(tbody)]
    rows = [(r + [''] * len(hdr))[:len(hdr)] for r in rows if r]
    if not rows:
        return m.group(0)
    h0 = text(hdr[0]).lower()
    heads = ' | '.join(text(h).lower() for h in hdr)
    # the mix Sarthak chose (19 Nov 2026): cards only where a grid reads badly; real comparisons stay tables
    if not (h0.startswith('if this') or 'nums' in cls or len(rows) == 1
            or 'when to call' in heads or 'can you change it' in heads or 'is it cancerous' in heads):
        return m.group(0)
    if h0.startswith('if this') and len(hdr) in (2, 3):
        body = situations(hdr, rows)
    elif 'nums' in cls and len(hdr) == 4:
        body = stats(hdr, rows)
    elif len(rows) == 1 and len(hdr) >= 4:
        body = facts(hdr, rows[0])
    else:
        body = cards(hdr, rows)
    return '    <div class="pv-wrap">%s%s</div>\n' % (body, foot.replace('rt-foot', 'pv-foot') if foot else '')


def present(page):
    return TABLE_RE.sub(one, page)

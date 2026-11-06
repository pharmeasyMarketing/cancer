#!/usr/bin/env python3
"""Build the cancer hub homepage (cancer/index.html).

Content is read from source.md (the editorial doc) via lib.py so prose, tables, links and
citations stay faithful; the page shell, tokens and components mirror the GLP-1 hub.
Run:  python3 build.py
"""
import re, json, html, os, sys
from lib import *

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', 'index.html')

# ---- CMS fields (the doc's {{...}} placeholders) ----
PUBLISHED_DATE = '6 November 2026'
LAST_UPDATED = '6 November 2026'
CURRENT_MONTH_YEAR = 'November 2026'
LAST_UPDATED_ISO = '2026-11-06T09:00:00+05:30'
CANON = 'https://pharmeasy.in/cancer/'
# The committed index.html is what GitHub Pages serves (pharmeasymarketing.github.io/cancer/),
# and that copy must stay out of search. Only a pharmeasy.in deploy builds with --production.
PRODUCTION = '--production' in sys.argv
ROBOTS = '' if PRODUCTION else '<meta name="robots" content="noindex, nofollow">\n'

REVIEWER = 'Dr. Ayush Shashikant Dubey'
REVIEWER_URL = 'https://pharmeasy.in/legal/editorial-policy/-dr-ayush-shashikant-dubey-190'
REVIEWER_IMG = 'https://seo-cdn.pharmeasy.in/production/218efe56-c2ff-4c94-88ae-a769771b01ec.webp'

ODC = 'https://pharmeasy.in/online-doctor-consultation/'


def fill(s):
    return (s.replace('{{CURRENT_MONTH_YEAR}}', CURRENT_MONTH_YEAR)
             .replace('{{PUBLISHED_DATE}}', PUBLISHED_DATE)
             .replace('{{LAST_UPDATED}}', LAST_UPDATED))


def T(n):
    """Inline html of a whole source line."""
    return fill(inline(line(n)))


def esc(s):
    return html.escape(s, quote=True)


# ---------------------------------------------------------------- icons (lucide-style, 24px grid)
def svg(paths, size=18):
    return ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" '
            'stroke-linejoin="round" style="width:%dpx;height:%dpx;display:block;flex-shrink:0" aria-hidden="true">%s</svg>' % (size, size, paths))


IC = {
    'search': '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>',
    'flask': '<path d="M10 2v7.527a2 2 0 0 1-.211.896L4.72 20.55a1 1 0 0 0 .9 1.45h12.76a1 1 0 0 0 .9-1.45l-5.069-10.127A2 2 0 0 1 14 9.527V2"/><path d="M8.5 2h7"/><path d="M7 16h10"/>',
    'clip': '<rect width="8" height="4" x="8" y="2" rx="1"/><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><path d="m9 14 2 2 4-4"/>',
    'pill': '<path d="m10.5 20.5 10-10a4.95 4.95 0 1 0-7-7l-10 10a4.95 4.95 0 1 0 7 7Z"/><path d="m8.5 8.5 7 7"/>',
    'leaf': '<path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.48 19 2c1 2 2 4.18 2 8 0 5.5-4.78 10-10 10Z"/><path d="M2 21c0-3 1.85-5.36 5.08-6C9.5 14.52 12 13 13 12"/>',
    'wallet': '<path d="M19 7V4a1 1 0 0 0-1-1H5a2 2 0 0 0 0 4h15a1 1 0 0 1 1 1v4h-3a2 2 0 0 0 0 4h3a1 1 0 0 0 1-1v-2a1 1 0 0 0-1-1"/><path d="M3 5v14a2 2 0 0 0 2 2h15a1 1 0 0 0 1-1v-4"/>',
    'heart': '<path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z"/>',
    'pin': '<path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z"/><circle cx="12" cy="10" r="3"/>',
    'shield': '<path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/><path d="m9 12 2 2 4-4"/>',
    'scale': '<path d="m16 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1Z"/><path d="m2 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1Z"/><path d="M7 21h10"/><path d="M12 3v18"/><path d="M3 7h2c2 0 5-1 7-2 2 1 5 2 7 2h2"/>',
    'steth': '<path d="M11 2v2"/><path d="M5 2v2"/><path d="M5 3H4a2 2 0 0 0-2 2v4a6 6 0 0 0 12 0V5a2 2 0 0 0-2-2h-1"/><path d="M8 15a6 6 0 0 0 12 0v-3"/><circle cx="20" cy="10" r="2"/>',
    'arrow': '<path d="M5 12h14"/><path d="m12 5 7 7-7 7"/>',
    'chev': '<path d="m6 9 6 6 6-6"/>',
    'check': '<path d="M20 6 9 17l-5-5"/>',
    'grid': '<rect width="7" height="7" x="3" y="3" rx="1"/><rect width="7" height="7" x="14" y="3" rx="1"/><rect width="7" height="7" x="14" y="14" rx="1"/><rect width="7" height="7" x="3" y="14" rx="1"/>',
}
ARROW_BIG = svg(IC['arrow'], 26)


# ---------------------------------------------------------------- layout helpers
def sec(id_, h2, body, eyebrow=None, mb=8):
    eb = '<div class="cx-eyebrow">%s</div>' % esc(eyebrow) if eyebrow else ''
    hid = ' id="%s"' % id_ if id_ else ''
    return ('\n  <div class="asec" style="padding:36px 0 0">\n    %s<h2%s style="font-size:24px;line-height:32px;'
            'font-weight:800;margin:0 0 %dpx;color:#1C1F22;scroll-margin-top:20px">%s</h2>\n%s\n  </div>\n' % (eb, hid, mb, esc(h2), body))


def P(n_or_html, cls='lead-p', raw=False):
    h = n_or_html if raw else T(n_or_html)
    return '    <p class="%s">%s</p>\n' % (cls, h)


def H3(text):
    return '    <h3 class="h3" style="margin-top:24px">%s</h3>\n' % esc(text)


def note_box(html_):
    return '    <div class="note-box" style="margin:16px 0"><p>%s</p></div>\n' % html_


def numbered_tiles(items, minw=230):
    out = ['    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(%dpx,1fr));gap:12px;margin:0 0 18px">' % minw]
    for i, t in enumerate(items, 1):
        out.append('      <div class="cx-tile step-tile"><div class="num" style="width:26px;height:26px;border-radius:999px;background:#008880;color:#fff;font-size:12px;font-weight:800;'
                   'display:flex;align-items:center;justify-content:center;margin-bottom:10px">%d</div>'
                   '<p style="font-size:14px;line-height:21px;color:#5C636D">%s</p></div>' % (i, t))
    out.append('    </div>\n')
    return '\n'.join(out)


def bullet_text(n):
    return inline(re.sub(r'^\*\s+', '', line(n)))


def rtable(headers, rows, cls_cols=None, foot=None, widths=None, extra=''):
    """headers: list[str]; rows: list[list[html]]; cls_cols: per-column class (k, num, '')."""
    cls_cols = cls_cols or [''] * len(headers)
    th = ''.join('<th%s>%s</th>' % (' class="%s"' % c if c and c != 'k' else '', esc(h)) for h, c in zip(headers, cls_cols))
    trs = []
    for r in rows:
        tds = ''.join('<td%s data-label="%s">%s</td>' % (' class="%s"' % c if c else '', esc(h), v) for h, c, v in zip(headers, cls_cols, r))
        trs.append('<tr>%s</tr>' % tds)
    f = '<div class="rt-foot">%s</div>' % foot if foot else ''
    cg = '<colgroup>%s</colgroup>' % ''.join('<col style="width:%s">' % w for w in widths) if widths else ''
    return ('    <div class="rt-wrap"><div class="rt-scroll"><table class="rtable%s%s">%s<thead><tr>%s</tr></thead><tbody>%s</tbody></table></div>%s</div>\n'
            % (' fixed' if widths else '', (' ' + extra) if extra else '', cg, th, ''.join(trs), f))


def md_table(start, end, first_key=True, cls_cols=None, foot=None, extra=''):
    hdr, rows = table(start, end)
    hdr = [unesc(re.sub(r'\*', '', h)).strip() for h in hdr]
    rows = [[fill(inline(c)) for c in r] for r in rows]
    cc = cls_cols or (['k'] + [''] * (len(hdr) - 1) if first_key else None)
    return rtable(hdr, rows, cc, foot, extra=extra or ('two' if len(hdr) == 2 else ''))


# ---------------------------------------------------------------- illustrations
def ill_dna():
    damage = [('Tobacco, in every form', '27.1% of all cancers in India'),
              ('Chronic infection', 'HPV, hepatitis B and C, H. pylori'),
              ('Alcohol', 'Group 1 carcinogen, seven cancer sites'),
              ('UV light, occupation, air pollution', 'Excess body weight, and simple ageing')]
    genes = [('Proto-oncogenes', 'Normally: drive cell division, under control', 'Damaged: drive it continuously'),
             ('Tumour suppressor genes', 'Normally: apply the brakes, repair DNA', 'Lost: the brakes fail'),
             ('DNA repair genes', 'Normally: keep the error rate low', 'Failed: every other fault accelerates')]
    does = ['Keeps dividing when it should stop', 'Ignores the signal to self-destruct', 'Recruits its own blood supply',
            'Evades the immune cells', 'Invades the tissue around it']
    c1 = ''.join('<div class="ill-card"><b>%s</b><span>%s</span></div>' % (esc(a), esc(b)) for a, b in damage)
    c2 = ''.join('<div class="ill-card"><b>%s</b><span>%s</span><span class="bad">%s</span></div>' % (esc(a), esc(b), esc(c)) for a, b, c in genes)
    c3 = ''.join('<div class="dna-do d%d">%s</div>' % (i, esc(t)) for i, t in enumerate(does, 1))
    return ('    <figure class="ill" style="margin:20px 0" aria-label="How damage to DNA leads to cancer: what damages the DNA, which genes fail, and what the cell does">\n'
            '      <div class="dna-grid">\n'
            '        <div class="dna-col"><div class="ill-eyebrow">What damages the DNA</div>%s</div>\n'
            '        <div class="ill-arrow dna-arrow">%s</div>\n'
            '        <div class="dna-col"><div class="ill-eyebrow">Which genes fail</div>%s</div>\n'
            '        <div class="ill-arrow dna-arrow">%s</div>\n'
            '        <div class="dna-col"><div class="ill-eyebrow">What the cell does</div>%s</div>\n'
            '      </div>\n'
            '      <div class="dna-time"><div class="dna-pt"><b>One mutation</b>is not enough</div>'
            '<div class="dna-pt mid"><b>Faults accumulate</b>usually over decades</div>'
            '<div class="dna-pt end"><b>Cancer</b>becomes dangerous</div></div>\n'
            '      <div class="ill-callout"><b>Why this matters</b><p>That long build-up is the reason prevention and early detection work at all: '
            'for most cancers there is a window of years before the disease becomes dangerous.</p></div>\n'
            '    </figure>\n' % (c1, ARROW_BIG, c2, ARROW_BIG, c3))


def dots(kind, n):
    return ''.join('<span class="cx-dot %s"></span>' % kind for _ in range(n))


def ill_tumours():
    benign = ('<div class="tm-cells"><div class="tm-row">%s</div><div class="tm-row" style="margin-left:14px">%s</div><div class="tm-row" style="margin-right:10px">%s</div></div>'
              % (dots('b', 2), dots('b', 3), dots('b', 1)))
    situ = ('<div class="tm-cells"><div class="tm-row">%s</div><div class="tm-row">%s</div><div class="tm-row">%s</div></div>'
            % (dots('i', 5), dots('i', 4), dots('i', 3)))
    mal = ('<div class="tm-cells"><div class="tm-row">%s</div><div class="tm-row">%s</div><div class="tm-row">%s</div></div>'
           % (dots('m', 4), dots('m', 4), dots('m', 3)))

    def panel(cls, title, cells, cap, extra_line='', extra_tissue='', tissue_txt='tissue below'):
        return ('<div class="tm"><div class="tm-title %s">%s</div><div class="tm-box">%s<div class="tm-line">%s</div>'
                '<div class="tm-label">basement membrane</div><div class="tm-tissue">%s%s</div></div><div class="tm-cap">%s</div></div>'
                % (cls, title, cells, extra_line, tissue_txt, extra_tissue, cap))
    p1 = panel('t-b', 'Benign', benign, 'Grows, stays put.<br>Does not invade.')
    p2 = panel('t-i', 'In situ', situ, 'Looks malignant, has not<br>crossed the membrane yet.')
    p3 = panel('t-m', 'Malignant', mal, 'Pushes through, and can<br>travel elsewhere.',
               extra_line='<span class="cx-dot m" style="left:42%"></span>',
               extra_tissue='<span class="cx-dot m" style="left:66%"></span>',
               tissue_txt='tissue below <span class="tm-vessel">vessel</span>')
    return ('    <figure class="ill" style="margin:20px 0" aria-label="Benign, in situ and malignant tissue compared: benign cells stay in place, in situ cells have not crossed the basement membrane, malignant cells push through it and can travel">'
            '<div class="tm-grid">%s%s%s</div></figure>\n' % (p1, p2, p3))


def ill_spread():
    routes = [('grows into', 'Direct extension', 'the tissue immediately next door'),
              ('carried to', 'Lymphatic spread', 'the nearest lymph nodes'),
              ('carried to', 'Bloodstream', 'distant organs')]
    cells = []
    for i, (lbl, t, s) in enumerate(routes, 1):
        cells.append('<div class="sp-c c%d"><i class="v"></i><i class="h"></i><span class="lbl">%s</span></div>' % (i, lbl))
        cells.append('<div class="sp-r sp-r%d"><div class="ill-card"><span class="sp-via">%s</span><b>%s</b><span>%s</span></div></div>' % (i, lbl, t, s))
    return ('    <figure class="ill" style="margin:20px 0" aria-label="How cancer spreads from a primary tumour: direct extension, lymphatic spread or the bloodstream, most often to the lungs, liver, bone and brain">'
            '<div class="sp"><div class="sp-primary">Primary tumour</div>%s<div class="sp-a" aria-hidden="true">%s</div>'
            '<div class="sp-dest"><b>Commonest destinations</b><div class="big">lungs · liver · bone · brain</div>'
            '<span>A deposit in a distant organ is called a metastasis.</span></div></div></figure>\n' % (''.join(cells), svg(IC['arrow'], 26)))


# values read off the charts in the source doc (each series sums to ~100%)
BOTH = [('Breast', 15.18), ('Lip, oral cavity', 13.17), ('Trachea, bronchus and lung', 7.21), ('Colorectum', 5.35), ('Cervix uteri', 5.08),
        ('Stomach', 4.39), ('Oesophagus', 3.69), ('Leukaemia', 3.17), ('Ovary', 2.92), ('Liver and intrahepatic bile ducts', 2.69),
        ('Non-Hodgkin lymphoma', 2.69), ('Prostate', 2.56), ('Hypopharynx', 2.27), ('Larynx', 2.25), ('Thyroid', 2.13),
        ('Others (brain, bladder, oropharynx, etc.)', 25.25)]
MALES = [('Lip, oral cavity', 20.42), ('Trachea, bronchus and lung', 10.11), ('Colorectum', 6.21), ('Stomach', 5.82), ('Prostate', 5.12),
         ('Oesophagus', 4.64), ('Larynx', 3.94), ('Leukaemia', 3.8), ('Liver and intrahepatic bile ducts', 3.77), ('Hypopharynx', 3.57),
         ('Non-Hodgkin lymphoma', 3.23), ('Bladder', 2.6), ('Oropharynx', 2.37), ('Brain, central nervous system', 2.27), ('Pancreas', 1.56),
         ('Others (kidney, skin, thyroid, etc.)', 20.57)]
FEMALES = [('Breast', 30.39), ('Cervix uteri', 10.17), ('Lip, oral cavity', 5.91), ('Ovary', 5.84), ('Colorectum', 4.49),
           ('Trachea, bronchus and lung', 4.31), ('Corpus uteri', 3.63), ('Thyroid', 3.13), ('Stomach', 2.95), ('Oesophagus', 2.71),
           ('Gallbladder', 2.67), ('Leukaemia', 2.54), ('Non-Hodgkin lymphoma', 2.14), ('Liver and intrahepatic bile ducts', 1.61),
           ('Brain, central nervous system', 1.54), ('Others (pancreas, hypopharynx, kidney, etc.)', 15.94)]


def chart_rows(data):
    rows = []
    for i, (l, v) in enumerate(data):
        rows.append((l, v, 'other' if l.startswith('Others') else ('top' if i == 0 else '')))
    return rows


def fmt(v):
    return ('%.2f' % v).rstrip('0').rstrip('.')


def bar_chart2(title, data, axis_max):
    tick_pct = 5 / axis_max * 100
    out = ['    <figure class="chart" style="--tick:%.4f%%" aria-label="%s: share of new cancer cases in India, 2024, by cancer type">' % (tick_pct, esc(title)),
           '      <div class="chart-h"><b>%s</b><span>Share of new cancer cases, India 2024</span></div>' % esc(title)]
    for label, v, kind in chart_rows(data):
        w = v / axis_max * 100
        out.append('      <div class="bar-row"><div class="bar-label">%s</div><div class="bar-track"><div class="bar %s" style="width:%.2f%%"></div>'
                   '<span class="bar-val" style="left:%.2f%%">%s</span></div></div>' % (esc(label), kind, w, w, fmt(v)))
    ticks = ''.join('<i style="left:%.3f%%">%d</i>' % (t / axis_max * 100, t) for t in range(0, axis_max + 1, 5))
    out.append('      <div class="axis"><div></div><div class="axis-ticks">%s</div></div>' % ticks)
    out.append('      <div class="axis-title">Percentage (%)</div>')
    out.append('    </figure>\n')
    return '\n'.join(out)


# ---------------------------------------------------------------- drug table
def parse_drugs():
    hdr, rows = table(187, 200)

    def mols(c):
        return [(m.group(1), clean_url(m.group(2))) for m in re.finditer(r'\[\*\*(.+?)\*\*\]\((https?://[^)\s]+)\)', c)]

    def groups(c):
        parts = re.split(r'\)\s{2,}(?=\[)', c.strip())
        out = []
        for p in parts:
            if not p.endswith(')'):
                p += ')'
            out.append([(unesc(m.group(1)), clean_url(m.group(2))) for m in LINK_RE.finditer(p)])
        return out
    res = []
    for r in rows:
        ms, gs = mols(r[1]), groups(r[4])
        assert len(ms) - len(gs) in (0, 1), (r[0], len(ms), len(gs))
        res.append(dict(group=re.sub(r'\*', '', r[0]).strip(), mols=ms, groups=gs, route=inline(r[2]), use=fill(inline(r[3]))))
    return res


SHEET_CSV = os.path.join(HERE, 'molecules_sheet.csv')          # snapshot of the "Cancer Molecules list" Google Sheet
GROUP_MAP = os.path.join(HERE, 'molecule_groups.json')         # which drug-table row each sheet molecule belongs to
MORE_JSON = os.path.join(HERE, '..', 'assets', 'data', 'drug-more.json')   # loaded by cancer.js when "+N more" is clicked


def mol_id(url):
    m = re.search(r'-?(\d+)/?$', url)
    return m.group(1) if m else url


def mol_display(name):
    """'MESNA+IFOSFAMIDE' -> 'Mesna + Ifosfamide' (the table's Title Case)."""
    name = re.sub(r'\s*\+\s*', ' + ', name.strip())
    return re.sub(r"(^|[ /])([a-z])", lambda m: m.group(1) + m.group(2).upper(), name.lower())


def more_molecules(drugs):
    """Per drug group, the sheet molecules not already shown in that row. Every sheet row must be
    placed in a group or explicitly excluded in molecule_groups.json, so new sheet rows fail the build."""
    import csv
    with open(SHEET_CSV, encoding='utf8') as f:
        sheet = {r['molecule_name'].strip(): r for r in csv.DictReader(f)}
    with open(GROUP_MAP, encoding='utf8') as f:
        gm = json.load(f)
    placed = [n for names in gm['groups'].values() for n in names]
    excluded = [n for names in gm['excluded'].values() for n in names]
    every = placed + excluded
    dupes = sorted({n for n in every if every.count(n) > 1})
    assert not dupes, 'listed twice in molecule_groups.json: %s' % dupes
    unknown = sorted(set(every) - set(sheet))
    assert not unknown, 'molecule_groups.json names not in the sheet: %s' % unknown
    unplaced = sorted(set(sheet) - set(every))
    assert not unplaced, 'sheet molecules with no group (add to molecule_groups.json): %s' % unplaced
    names = [d['group'] for d in drugs]
    assert set(gm['groups']) <= set(names), 'unknown groups: %s' % sorted(set(gm['groups']) - set(names))
    out = {}
    for d in drugs:
        shown = {mol_id(u) for _, u in d['mols']}
        out[d['group']] = [{'name': mol_display(n), 'url': sheet[n]['urls'].strip()}
                           for n in gm['groups'].get(d['group'], []) if sheet[n]['molecule_id'].strip() not in shown]
    return out


def slug(s):
    return re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')


# Mobile only (CSS): the desktop column header is hidden there, so each group's list gets its own key.
MOL_KEY = ('<div class="mol-key" aria-hidden="true"><span class="k-mol">Molecule</span>'
           '<span class="k-brand">Brands on PharmEasy</span></div>')


def drug_table():
    items = []
    drugs = parse_drugs()
    more = more_molecules(drugs)
    os.makedirs(os.path.dirname(MORE_JSON), exist_ok=True)
    with open(MORE_JSON, 'w', encoding='utf8') as f:
        json.dump({'groups': {slug(g): {'title': g, 'molecules': m} for g, m in more.items() if m}}, f, ensure_ascii=False, indent=1)
        f.write('\n')
    for d in drugs:
        lines = []
        for i, (mn, mu) in enumerate(d['mols']):
            g = d['groups'][i] if i < len(d['groups']) else []
            chips = []
            for name, url in g:
                cls = 'brand more' if name.startswith('+') else 'brand'
                chips.append('<a class="%s" href="%s">%s</a>' % (cls, esc(url), esc(name)))
            if not chips:
                chips = ['<span class="brand none">no brands listed</span>']
            lines.append('<div class="mol-row"><div class="mol-name"><a href="%s">%s</a></div><div class="brands">%s</div></div>' % (esc(mu), esc(mn), ''.join(chips)))
        n_more = len(more[d['group']])
        if n_more:
            # the list itself is client-rendered by cancer.js from assets/data/drug-more.json
            lines.append('<div class="mol-more-row"><button type="button" class="brand more mol-more" data-group="%s" aria-haspopup="dialog">'
                         '+%d more %s</button></div>' % (slug(d['group']), n_more, 'molecule' if n_more == 1 else 'molecules'))
        items.append('<div class="dg-item" data-mols="%d"><div class="dg-side">' % len(d['mols']) + '<div class="dg-name">%s</div><span class="route-pill">%s</span>'
                     '<p class="dg-use"><b>Used for:</b> %s</p></div><div class="mol-list">%s%s</div></div>' % (esc(d['group']), d['route'], d['use'], MOL_KEY, ''.join(lines)))
    return ('    <div class="rt-wrap dg"><div class="dg-head"><span>Drug group, how it is given and what it is used for</span><span>Molecules and brands on PharmEasy</span></div>%s</div>\n' % ''.join(items))


# ---------------------------------------------------------------- page sections
UPDATES = os.path.join(HERE, 'updates.json')
UPDATES_MAX = 5
MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']


def approved_updates():
    """Newest UPDATES_MAX approved items from updates.json, or [] (-> sample fallback)."""
    if not os.path.exists(UPDATES):
        return []
    with open(UPDATES, encoding='utf8') as f:
        items = json.load(f).get('items', [])
    items = [i for i in items if i.get('status') == 'approved' and i.get('title') and i.get('url')
             and re.fullmatch(r'\d{4}-\d{2}-\d{2}', i.get('date', ''))]
    return sorted(items, key=lambda i: i['date'], reverse=True)[:UPDATES_MAX]


def pill_date(iso):
    y, m, d = map(int, iso.split('-'))
    return '%d %s %d' % (d, MONTHS[m - 1][:3], y)


def month_year(iso):
    y, m, _ = map(int, iso.split('-'))
    return '%s %d' % (MONTHS[m - 1], y)


def build_sections():
    S = []
    toc = []

    def add(id_, title, body, **kw):
        toc.append((id_, title))
        S.append(sec(id_, title, body, **kw))

    # ---- What is cancer?
    b = P(15) + P(17)
    b += numbered_tiles([bullet_text(n) for n in range(19, 25)], 250)
    b += P(26)
    add('toc-what', 'What is cancer?', b, mb=14)

    # ---- How does cancer start?
    b = P(30) + P(32)
    gene_titles = ['Proto-oncogenes', 'Tumour suppressor genes', 'DNA repair genes']
    cards = ''.join('<div class="cx-tile"><div style="font-size:16px;font-weight:800;color:#1C1F22;margin-bottom:6px">%s</div>'
                    '<p style="font-size:14px;line-height:22px;color:#5C636D">%s</p></div>' % (t, bullet_text(n)) for t, n in zip(gene_titles, (34, 35, 36)))
    b += '    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px;margin:0 0 18px">%s</div>\n' % cards
    b += P(38)
    b += ill_dna()
    add('toc-start', 'How does cancer start?', b)

    # ---- Benign vs malignant tumour
    b = P(44) + ill_tumours()
    b += md_table(50, 54, cls_cols=['k', '', '', '', ''])
    b += '    <p class="lead-p" style="margin-top:16px">%s</p>\n' % T(56)
    add('toc-benign', 'Benign vs malignant tumour', b)

    # ---- How are cancers classified?
    b = P(60)
    b += H3('Classification by primary site') + P(64)
    b += H3('Classification by histological type') + P(68)
    b += md_table(70, 78, cls_cols=['k', '', ''])
    b += H3('Classification by molecular profile') + P(84)
    rows = []
    for n in range(86, 91):
        m = re.match(r'^\*\s+\*\*(.+?):\*\*\s*(.*)$', line(n))
        rows.append('<div class="pill-row"><span class="cx-pill">%s</span><p>%s</p></div>' % (esc(unesc(m.group(1))), inline(m.group(2))))
    b += '    <div class="pill-list">%s</div>\n' % ''.join(rows)
    add('toc-classify', 'How are cancers classified?', b)

    # ---- How does cancer spread?
    b = P(94)
    spread_titles = ['Direct spread', 'Through the blood', 'Through the lymphatic system']
    cards = []
    for n in (96, 97, 98):
        m = re.match(r'^\*\s+\*\*(.+?):\*\*\s*(.*)$', line(n))
        cards.append('<div class="cx-card" style="border-left:3px solid #008880;padding:18px"><div style="font-size:15px;font-weight:800;color:#1C1F22;margin-bottom:6px">%s</div>'
                     '<p style="font-size:14px;line-height:22px;color:#5C636D">%s</p></div>' % (esc(unesc(m.group(1))), inline(m.group(2))))
    b += '    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px;margin:0 0 14px">%s</div>\n' % ''.join(cards)
    b += note_box(T(100))
    b += ill_spread()
    add('toc-spread', 'How does cancer spread?', b)

    # ---- The India picture
    b = P(106)
    b += ('    <div class="stats">'
          '<div class="stat hot"><b>1.56 million</b><span>new cancer cases in India, 2024</span></div>'
          '<div class="stat"><b>902,000</b><span>cancer deaths in 2024</span></div>'
          '<div class="stat"><b>3.32 million</b><span>people living with a diagnosis made in the previous five years</span></div>'
          '<div class="stat"><b>11.2%</b><span>lifetime risk of developing cancer before age 75</span></div>'
          '</div>\n')
    hdr, rows = table(108, 116)
    hdr = [unesc(h) for h in hdr]
    rows = [[inline(c) for c in r] for r in rows]
    b += rtable(hdr, rows, ['k', 'num', 'num', 'num'], extra='nums', foot='Source: GLOBOCAN 2024 estimates for India, IARC Global Cancer Observatory.<sup class="cite">[<a href="#ref-4">4</a>]</sup>')
    b += '    <p class="lead-p" style="margin-top:16px">%s</p>\n' % T(120)
    b += bar_chart2('Both sexes', BOTH, 30)
    b += P(124)
    b += bar_chart2('Males', MALES, 25)
    b += P(128)
    b += bar_chart2('Females', FEMALES, 35)
    add('toc-india', 'The India picture', b)

    # ---- Common symptoms
    b = P(134) + P(136) + note_box(T(138)) + '    <p class="lead-p">%s</p>\n' % T(140)
    add('toc-symptoms', 'Common symptoms of cancer', b)

    # ---- How is cancer diagnosed?
    b = P(144)
    b += ('    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:14px;margin:0 0 16px">'
          '<div class="cx-card" style="border-left:3px solid #008880;padding:18px"><div style="font-size:15px;font-weight:800;color:#1C1F22;margin-bottom:6px">Screening tests</div>'
          '<p style="font-size:14px;line-height:22px;color:#5C636D">%s</p></div>'
          '<div class="cx-card" style="border-left:3px solid #008880;padding:18px"><div style="font-size:15px;font-weight:800;color:#1C1F22;margin-bottom:6px">Diagnostic tests</div>'
          '<p style="font-size:14px;line-height:22px;color:#5C636D">%s</p></div></div>\n' % (T(146), T(148)))
    b += ('    <div class="note-box" style="display:flex;gap:12px;align-items:center;flex-wrap:wrap">'
          '<span style="width:32px;height:32px;border-radius:10px;background:#fff;border:1px solid #B8DEDB;color:#008880;display:flex;align-items:center;justify-content:center;flex-shrink:0">%s</span>'
          '<p style="flex:1 1 260px">%s</p></div>\n' % (svg(IC['flask'], 17), T(150)))
    add('toc-diagnosis', 'How is cancer diagnosed?', b)

    # ---- Staging and grading
    b = P(154)
    lead_tnm = re.sub(r'^\*\s+', '', line(156))
    b += '    <p class="lead-p">%s</p>\n' % inline(lead_tnm)
    tnm = []
    for letter, n in (('T', 157), ('N', 158), ('M', 159)):
        tnm.append('<div class="cx-tile step-tile"><b class="l num">%s</b><p style="font-size:14px;line-height:22px;color:#5C636D">%s</p></div>' % (letter, bullet_text(n)))
    b += '    <div class="tnm">%s</div>\n' % ''.join(tnm)
    b += ('    <div class="cx-card card-pad" style="padding:22px;margin:0 0 18px"><div class="cx-eyebrow">Stages are typically numbered 0 to IV</div>'
          '<div class="stage"><div class="s0">0</div><div class="s1">I</div><div class="s2">II</div><div class="s3">III</div><div class="s4">IV</div></div>'
          '<div class="stage-notes"><p><b>Stages I to III:</b> %s</p><p><b>Stage IV:</b> %s</p></div></div>\n'
          % (bullet_text(161).replace('Stages I to III refer to ', '').rstrip('.') + '.', bullet_text(162).replace('Stage IV indicates that ', '').rstrip('.') + '.'))
    # grade paragraph (cite sits at the end of the source paragraph)
    b += P(164)
    b += ('    <div class="cx-card card-pad" style="padding:22px;margin:0 0 4px"><div class="cx-eyebrow">Grade 1 to Grade 4</div>'
          '<div class="grade"><div class="g1">Grade 1</div><div class="g2">Grade 2</div><div class="g3">Grade 3</div><div class="g4">Grade 4</div></div>'
          '<div class="grade-ends"><span>Least aggressive (well differentiated)</span><span>Most aggressive (poorly differentiated)</span></div></div>\n')
    add('toc-staging', 'Staging, grading and why they differ', b)

    # ---- How is cancer treated?
    b = P(168)
    b += md_table(170, 179, cls_cols=['k', ''])
    b += '    <p class="lead-p" style="margin-top:16px">%s</p>\n' % T(183)
    b += P(185)
    b += drug_table()
    b += '    <p class="lead-p" style="margin-top:16px">%s</p>\n' % T(204)
    b += P(206)
    add('toc-treatment', 'How is cancer treated?', b)

    # ---- Insurance
    b = P(210) + md_table(212, 220, cls_cols=['k', ''])
    b += '    <p class="lead-p" style="margin-top:16px">%s</p>\n' % T(224)
    t226 = T(226).replace('Verified as of %s.' % CURRENT_MONTH_YEAR, '')
    b += '    <p class="lead-p" style="margin-bottom:10px">%s</p>\n' % t226.strip()
    b += '    <p style="margin:0 0 16px"><span class="verified">%s Verified as of %s</span></p>\n' % (svg(IC['check'], 14), CURRENT_MONTH_YEAR)
    b += ('    <div class="note-box" style="display:flex;gap:12px;align-items:center;flex-wrap:wrap"><span style="width:32px;height:32px;border-radius:10px;background:#fff;border:1px solid #B8DEDB;color:#008880;display:flex;align-items:center;justify-content:center;flex-shrink:0">%s</span>'
          '<p style="flex:1 1 260px">%s</p></div>\n' % (svg(IC['wallet'], 17), T(228)))
    add('toc-insurance', 'What to check for insurance in India', b)

    # ---- Screening and prevention
    b = P(232)
    b += ('    <div class="stats" style="grid-template-columns:repeat(auto-fit,minmax(240px,1fr))">'
          '<div class="stat hot"><b>0.9%</b><span>of women aged 30 to 49 had undergone breast cancer screening<sup class="cite">[<a href="#ref-39">39</a>]</sup></span></div>'
          '<div class="stat hot"><b>1.9%</b><span>of women aged 30 to 49 had undergone cervical cancer screening<sup class="cite">[<a href="#ref-39">39</a>]</sup></span></div>'
          '<div class="stat"><b>38%</b><span>of cancers can currently be prevented, according to the WHO<sup class="cite">[<a href="#ref-1">1</a>]</sup></span></div>'
          '</div>\n')
    b += P(234)
    b += ('    <div class="screen">'
          '<div class="cx-tile"><div class="k">Oral cancer</div><b>Oral visual examination (OVE)</b><span>Once every five years, ages 30 to 65.</span></div>'
          '<div class="cx-tile"><div class="k">Cervical cancer</div><b>Visual inspection with acetic acid (VIA)</b><span>Once every five years, ages 30 to 65.</span></div>'
          '<div class="cx-tile"><div class="k">Breast cancer</div><b>Clinical breast examination (CBE)</b><span>Once every five years, ages 30 to 65.</span></div>'
          '</div>\n')
    b += P(236) + P(238)
    b += ('    <div class="note-box" style="display:flex;justify-content:space-between;align-items:center;gap:16px;flex-wrap:wrap">'
          '<div style="flex:1 1 340px"><p>%s</p></div>'
          '<a class="cx-btn-primary" href="https://pharmeasy.in/diagnostics/packages/cancer-screening-male-1420">Screening for men</a>'
          '<a class="cx-btn-ghost" href="https://pharmeasy.in/diagnostics/packages/cancer-screening-female-1418">Screening for women</a></div>\n' % T(240))
    b += '    <p class="lead-p" style="margin-top:16px">%s</p>\n' % T(242)
    b += P(244)
    add('toc-screening', 'Screening and prevention', b)

    # ---- When to see a doctor?
    b = P(248)
    b += ('    <div style="margin-top:14px;background:#FCE9E8;border:1px solid #F4C4C0;border-left:3px solid #E5453A;border-radius:12px;padding:20px">'
          '<div style="font-size:16px;font-weight:800;color:#A6231A;margin-bottom:6px">Seek urgent medical attention.</div>'
          '<p style="font-size:14px;line-height:22px;color:#25282B;margin:0">%s</p></div>\n' % T(250))
    b += ('    <div class="note-box" style="margin-top:14px;display:flex;justify-content:space-between;align-items:center;gap:16px;flex-wrap:wrap">'
          '<div style="flex:1 1 340px"><p>%s</p></div><a class="cx-btn-primary" href="%s">Consult a doctor</a></div>\n' % (T(252), ODC))
    add('toc-doctor', 'When to see a doctor?', b)

    # ---- Latest on cancer in India
    # Editor-approved items from updates.json (fetch_updates.py -> review_updates.py approve).
    # The source.md sample rows are only a fallback for when nothing has been approved yet.
    approved = approved_updates()
    if approved:
        rows = ''.join('<div class="pill-row"><span class="cx-pill">%s</span><p><strong style="color:#25282B">%s</strong>'
                       '<span class="src">Source: <a href="%s" target="_blank" rel="noopener">%s</a></span></p></div>'
                       % (pill_date(u['date']), esc(u['title']), esc(u['url']), esc(u['source'])) for u in approved)
        updated = month_year(approved[0]['date'])
    else:
        feed = []
        for n in (256, 257, 258):
            m = re.match(r'^\*\s+SAMPLE\s+\*\*(.+?)\*\*.*?Source:\s*\[(.+?)\]\((https?://[^)\s]+)\)', line(n))
            title = unesc(m.group(1)).replace('Placeholder — ', 'Placeholder: ').replace('—', ':')
            inst = re.search(r'\{\{PUBLISHED\\_DATE\}\}\s*\xb7\s*([A-Za-z\-]+?)Source', line(n))
            feed.append((title, inst.group(1) if inst else '', unesc(m.group(2)), clean_url(m.group(3))))
        rows = ''.join('<div class="pill-row"><span class="cx-pill grey">Sample</span><p><strong style="color:#25282B">%s</strong>'
                       '<span class="src">%s, %s · Source: <a href="%s">%s</a></span></p></div>' % (esc(t), PUBLISHED_DATE, esc(i), esc(u), esc(s)) for t, i, s, u in feed)
        updated = CURRENT_MONTH_YEAR
    b = '    <p class="lead-p">Updated %s.</p>\n' % updated
    b += '    <div class="pill-list">%s</div>\n' % rows
    srcs = [('ICMR-NCDIR National Cancer Registry Programme', 'https://ncdirindia.org/'), ('IARC Global Cancer Observatory', 'https://gco.iarc.who.int/today/'),
            ('GCO data tables', 'https://gco.iarc.who.int/today/en/dataviz/tables'), ('WHO cancer fact sheet', 'https://www.who.int/news-room/fact-sheets/detail/cancer'),
            ('data.gov.in cancer datasets', 'https://data.gov.in/keywords/Cancer')]
    b += '    <div class="srcs">%s</div>\n' % ''.join('<a href="%s">%s</a>' % (u, esc(t)) for t, u in srcs)
    add('toc-updates', 'Latest on cancer in India', b)

    return S, toc


CX = 'https://pharmeasy.in/cancer/'

# Explore band: each card links its hub page plus that hub's most useful child pages; the A to Z
# directory under it links every cancer type and subtype, so every page in cancer_urls.txt is one
# click from the homepage. Anchor text names the page (no bare "Symptoms" or "Read more").
EXPLORE = [
    ('Cancer types', 'Guides to 21 cancers and their subtypes.', 'grid', 'types/',
     [('Lung cancer', 'types/lung-cancer/'), ('Blood cancer', 'types/blood-cancer/'),
      ('Colorectal cancer', 'types/colorectal-cancer/'), ('Prostate cancer', 'types/prostate-cancer/')]),
    ('Symptoms and early signs', 'Common symptoms and when to get them checked.', 'search', 'symptoms/',
     [('Tumour or cancer?', 'symptoms/is-it-cancer/'), ('Breast cancer symptoms', 'types/breast-cancer/symptoms/'),
      ('Brain cancer symptoms', 'types/brain-cancer/symptoms/')]),
    ('Tests and tumour markers', 'Markers, imaging and biopsy explained.', 'flask', 'tests/',
     [('Breast cancer diagnosis', 'types/breast-cancer/diagnosis/'), ('Cervical cancer diagnosis', 'types/cervical-cancer/diagnosis/'),
      ('Prostate cancer diagnosis', 'types/prostate-cancer/diagnosis/')]),
    ('Cancer screening', 'Who should be screened, and for what. India screens for these three:', 'clip', 'screening/',
     [('Breast cancer', 'types/breast-cancer/'), ('Oral cancer', 'types/head-and-neck-cancer/oral-cancer/'),
      ('Cervical cancer', 'types/cervical-cancer/')]),
    ('Cancer treatment', 'How each treatment works and what to expect.', 'pill', 'treatment/',
     [('Surgery', 'treatment/surgery/'), ('Chemotherapy', 'treatment/chemotherapy/'), ('Radiation therapy', 'treatment/radiation-therapy/'),
      ('Immunotherapy', 'treatment/immunotherapy/'), ('Targeted therapy', 'treatment/targeted-therapy/'), ('Hormone therapy', 'treatment/hormone-therapy/')]),
    ('Cancer prevention', 'Steps that lower your risk.', 'shield', 'prevention/',
     [('Tobacco and cancer', 'prevention/tobacco/'), ('HPV and the vaccine', 'prevention/hpv/'),
      ('Lifestyle changes', 'prevention/lifestyle/'), ('Cancer myths', 'prevention/myths/')]),
    ('Nutrition during treatment', 'What to eat during and after treatment.', 'leaf', 'nutrition/', []),
    ('Cost and support', 'Insurance, schemes and financial support.', 'wallet', 'cost-and-support/', []),
    ('Living with cancer', 'Follow-up, late effects and fertility.', 'heart', 'living-with/', []),
    ('Cancer in India', 'Burden, screening gaps and schemes.', 'pin', 'india/', []),
]

# A to Z: (type, path, [(subpage anchor, path)])
CANCER_TYPES = [
    ('Anal cancer', 'types/anal-cancer/', []),
    ('Bladder cancer', 'types/bladder-cancer/', []),
    ('Blood cancer', 'types/blood-cancer/', [('Leukaemia', 'types/blood-cancer/leukaemia/'), ('Lymphoma', 'types/blood-cancer/lymphoma/'),
                                             ('Multiple myeloma', 'types/blood-cancer/multiple-myeloma/')]),
    ('Bone cancer', 'types/bone-cancer/', []),
    ('Brain cancer', 'types/brain-cancer/', [('Brain cancer symptoms', 'types/brain-cancer/symptoms/')]),
    ('Breast cancer', 'types/breast-cancer/', [('Breast cancer symptoms', 'types/breast-cancer/symptoms/'),
                                               ('Breast cancer stages and types', 'types/breast-cancer/stages-and-types/'),
                                               ('Breast cancer diagnosis', 'types/breast-cancer/diagnosis/'),
                                               ('Breast cancer treatment', 'types/breast-cancer/treatment/')]),
    ('Cervical cancer', 'types/cervical-cancer/', [('Cervical cancer diagnosis', 'types/cervical-cancer/diagnosis/')]),
    ('Colorectal cancer', 'types/colorectal-cancer/', [('Colon cancer', 'types/colorectal-cancer/colon-cancer/'),
                                                       ('Rectal cancer', 'types/colorectal-cancer/rectal-cancer/')]),
    ('Head and neck cancer', 'types/head-and-neck-cancer/', [('Oral cancer', 'types/head-and-neck-cancer/oral-cancer/'),
                                                             ('Tongue cancer', 'types/head-and-neck-cancer/oral-cancer/tongue-cancer/'),
                                                             ('Throat cancer', 'types/head-and-neck-cancer/throat-cancer/')]),
    ('Kidney cancer', 'types/kidney-cancer/', []),
    ('Liver cancer', 'types/liver-cancer/', []),
    ('Lung cancer', 'types/lung-cancer/', []),
    ('Oesophageal cancer', 'types/oesophageal-cancer/', []),
    ('Ovarian cancer', 'types/ovarian-cancer/', []),
    ('Prostate cancer', 'types/prostate-cancer/', [('Prostate cancer diagnosis', 'types/prostate-cancer/diagnosis/')]),
    ('Skin cancer', 'types/skin-cancer/', [('Melanoma', 'types/skin-cancer/melanoma/'),
                                           ('Non-melanoma skin cancer', 'types/skin-cancer/non-melanoma-skin-cancer/')]),
    ('Stomach cancer', 'types/stomach-cancer/', []),
    ('Testicular cancer', 'types/testicular-cancer/', []),
    ('Thyroid cancer', 'types/thyroid-cancer/', []),
    ('Uterine cancer', 'types/uterine-cancer/', []),
    ('Vaginal and vulvar cancer', 'types/vaginal-and-vulvar-cancer/', []),
]


def explore_band():
    cards = []
    for title, desc, ic, path, subs in EXPLORE:
        sub = ('<div class="ex-subs">%s</div>' % ''.join('<a href="%s%s">%s</a>' % (CX, p, esc(t)) for t, p in subs)) if subs else ''
        cards.append('<div class="ex-card"><span class="ex-ic">%s</span><div class="ex-body"><a class="ex-title" href="%s%s">%s</a>'
                     '<span class="ex-desc">%s</span>%s</div></div>' % (svg(IC[ic], 18), CX, path, esc(title), esc(desc), sub))
    # grouped by first letter; a type with subpages gets a toggle on mobile (cancer.js), everything
    # stays in the HTML and is visible without JS
    letters = {}
    for name, path, subs in CANCER_TYPES:
        letters.setdefault(name[0].upper(), []).append((name, path, subs))
    groups = []
    for letter in sorted(letters):
        rows = []
        for name, path, subs in letters[letter]:
            if subs:
                sid = 'ctz-' + slug(name)
                n_guides = '%d guide%s' % (len(subs), '' if len(subs) == 1 else 's')
                rows.append('<li class="ctz-item has-subs"><div class="ctz-row"><a class="ctz-type" href="%s%s">%s</a>'
                            '<button type="button" class="ctz-tog" aria-expanded="false" aria-controls="%s" aria-label="%s on %s">'
                            '<span>%s</span>%s</button></div><div class="ctz-subs" id="%s">%s</div></li>'
                            % (CX, path, esc(name), sid, n_guides, esc(name), n_guides, svg(IC['chev'], 16), sid,
                               ''.join('<a href="%s%s">%s</a>' % (CX, p, esc(t)) for t, p in subs)))
            else:
                rows.append('<li class="ctz-item"><div class="ctz-row"><a class="ctz-type" href="%s%s">%s%s</a></div></li>'
                            % (CX, path, esc(name), '<span class="ctz-go" aria-hidden="true">%s</span>' % svg(IC['arrow'], 16)))
        groups.append('<div class="ctz-group"><div class="ctz-letter" aria-hidden="true">%s</div><ul class="ctz-list">%s</ul></div>' % (letter, ''.join(rows)))
    types = groups
    return ('\n  <div class="asec" style="padding:36px 0 0">\n'
            '    <div class="pad explore" style="background:#F2F9F8;border:1px solid #B8DEDB;border-radius:12px;padding:20px;margin-bottom:20px">\n'
            '      <div class="cx-eyebrow" style="margin-bottom:4px">Explore cancer care</div>\n'
            '      <p style="font-size:14px;line-height:22px;color:#5C636D;margin:0 0 14px">Each guide goes deeper on one part of this page. They are for information and do not replace your oncologist.</p>\n'
            '      <div class="ex-grid">%s</div>\n'
            '      <div class="ctz">\n        <div class="ctz-head"><a href="%stypes/">Cancer types A to Z</a><span>21 cancers</span></div>\n'
            '        <div class="ctz-groups">%s</div>\n      </div>\n    </div>\n  </div>\n' % (''.join(cards), CX, ''.join(types)))


def faq_and_refs():
    faqs = []
    n = 266
    while n < 294:
        if line(n).startswith('### '):
            q = re.sub(r'^###\s*▾\s*', '', line(n)).strip()
            a_line = n + 2
            faqs.append((unesc(q), a_line))
            n += 4
        else:
            n += 1
    items = []
    for i, (q, a) in enumerate(faqs):
        ans = inline(line(a))
        items.append('      <details class="faq"%s style="background:#fff;border:1px solid #E6E9ED;border-radius:12px;overflow:hidden;box-shadow:0 1px 3px rgba(15,46,44,0.06),0 4px 14px rgba(15,46,44,0.05)">\n'
                     '        <summary style="padding:20px 24px;display:flex;justify-content:space-between;gap:16px;align-items:center">'
                     '<h3 style="margin:0;font-size:17px;line-height:25px;font-weight:800;color:#25282B;text-wrap:pretty">%s</h3>'
                     '<span class="chev" style="color:#8E97A3;flex-shrink:0;display:flex">%s</span></summary>\n'
                     '        <div style="padding:0 24px 20px"><p style="font-size:15px;line-height:26px;color:#5C636D;margin:0">%s</p></div>\n      </details>'
                     % (' open' if i == 0 else '', esc(q), svg(IC['chev'], 18), ans))
    faq = ('\n  <div class="asec" style="padding:36px 0 0">\n'
           '    <h2 id="toc-faq" style="font-size:24px;line-height:32px;font-weight:800;margin:0 0 16px;color:#1C1F22;scroll-margin-top:20px">Frequently Asked Questions</h2>\n'
           '    <div style="display:flex;flex-direction:column;gap:12px">\n%s\n    </div>\n  </div>\n' % '\n'.join(items))

    refs = references()
    rows = []
    for k in sorted(refs):
        t, url = ref_html(refs[k])
        rows.append('        <div style="display:flex;gap:10px;font-size:13px;line-height:21px;color:#5C636D"><span id="ref-%d" style="font-weight:800;color:#8E97A3;flex-shrink:0;scroll-margin-top:20px">%d.</span><span>%s</span></div>' % (k, k, t))
    ref = ('\n  <div class="asec" style="padding:36px 0 0">\n    <div id="references">\n'
           '      <h2 style="font-size:24px;line-height:32px;font-weight:800;margin:0 0 14px;color:#1C1F22;scroll-margin-top:20px">References</h2>\n'
           '      <div class="pad refs" id="refs-list" style="background:#fff;border:1px solid #E6E9ED;border-radius:12px;padding:22px;display:flex;flex-direction:column;gap:10px">\n%s\n      </div>\n    </div>\n  </div>\n' % '\n'.join(rows))
    return faq, ref, faqs


def disclaimer():
    return ('\n  <div class="sec" style="max-width:1120px;margin:0 auto;padding:24px 20px 0">\n'
            '    <div style="background:#fff;border:1px solid #E6E9ED;border-radius:12px;padding:20px;display:flex;flex-direction:column;gap:10px">\n'
            '      <div style="font-size:11px;font-weight:800;letter-spacing:0.06em;text-transform:uppercase;color:#8E97A3;margin-bottom:8px">Disclaimer</div>\n'
            '      <p style="font-size:12px;line-height:19px;color:#8E97A3;margin:0">The information provided on this page is intended solely to educate and inform users about cancer, how it is diagnosed and treated, and other relevant considerations. The purpose of this content is to help users make informed decisions and have meaningful discussions with their healthcare professional. PharmEasy does not intend to promote or recommend any specific medicine, brand or treatment.</p>\n'
            '      <p style="font-size:12px;line-height:19px;color:#8E97A3;margin:0">The information provided is for general informational and educational purposes only and does not constitute medical advice, diagnosis, or treatment, and should not be considered a substitute for consultation with a qualified doctor or other healthcare professional. All oncology medicines mentioned are prescription-only and must be used under an oncologist\'s supervision. Before starting, stopping, or changing any medication or treatment, please consult your doctor or qualified healthcare professional.</p>\n'
            '    </div>\n  </div>\n')


# ---------------------------------------------------------------- hero + TOC + head
def hero():
    stetho = svg(IC['steth'], 17)
    return f'''
  <div style="background:linear-gradient(180deg,#EDF6F5 0%,#F8FBFB 100%);border-bottom:1px solid #DCE6E5">

  <nav class="glp-crumb" aria-label="Breadcrumb"><ol><li><a href="https://pharmeasy.in/">Home</a><svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M10 8 L14 12 L10 16" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"></path></svg></li><li><span aria-current="page">Cancer</span></li></ol></nav>

  <div class="sec" style="max-width:1120px;margin:0 auto;padding:20px 20px 36px;text-align:left">
    <h1 style="font-size:44px;line-height:52px;font-weight:800;letter-spacing:-0.03em;margin:0 0 16px;color:#0F2E2C;text-wrap:pretty">Cancer</h1>

    <div style="display:flex;align-items:center;gap:12px;font-size:12px;line-height:19px;color:#5C7370;padding-bottom:18px;border-bottom:1px solid #DCE6E5;margin-bottom:22px">
      <img src="{REVIEWER_IMG}" alt="{esc(REVIEWER)}" width="42" height="42" loading="lazy" style="width:42px;height:42px;min-width:42px;max-width:none;border-radius:999px;object-fit:cover;border:1px solid #B8DEDB;flex-shrink:0;display:block">
      <div class="byline" style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;row-gap:4px">
        <span><strong style="color:#25282B;font-weight:700">Medically reviewed by</strong> <a href="{REVIEWER_URL}" style="color:#00736C;font-weight:700">{esc(REVIEWER)}</a></span>
        <span style="color:#C9D0D8">·</span>
        <span><strong style="color:#25282B;font-weight:700">Written by</strong> <a href="https://pharmeasy.in/legal/editorial-policy" style="color:#00736C;font-weight:700">PharmEasy Medical Team</a></span>
        <span style="color:#C9D0D8">·</span>
        <span>Published {PUBLISHED_DATE}</span>
        <span style="color:#C9D0D8">·</span>
        <span>Updated on {LAST_UPDATED}</span>
      </div>
    </div>

    <div class="hero-intro" id="hero-intro">
      <p style="font-size:18px;line-height:30px;color:#3D4A48;margin:0 0 16px">{T(7)}</p>
      <p style="font-size:18px;line-height:30px;color:#3D4A48;margin:0 0 16px">{T(9)}</p>
      <p style="font-size:18px;line-height:30px;color:#3D4A48;margin:0 0 14px">{T(11)}</p>
    </div>
    <button type="button" class="hero-toggle" id="hero-toggle" aria-expanded="false" aria-controls="hero-intro" hidden><span>Read more</span>{svg(IC['chev'], 16)}</button>

    <div style="background:#fff;border:1px solid #DCE6E5;border-radius:12px;padding:20px;display:flex;gap:14px;align-items:flex-start;box-shadow:0 2px 10px rgba(15,46,44,0.05)">
      <div style="width:30px;height:30px;border-radius:8px;background:#008880;color:#fff;display:flex;align-items:center;justify-content:center;flex-shrink:0">{stetho}</div>
      <div>
        <p style="font-size:14px;line-height:22px;color:#25282B;margin:0 0 14px"><strong style="font-weight:800">Worried about a symptom or a test result?</strong> A lump, a shadow on a scan or a raised blood test value does not automatically mean cancer. If you are unsure whether it needs to be checked, an online doctor consultation can help you understand how urgently you may need further evaluation.</p>
        <div style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:12px">
          <a class="cx-btn-primary" href="{ODC}">Consult a doctor</a>
          <a class="cx-btn-ghost" href="#toc-screening">Screening and prevention</a>
        </div>
        <p style="font-size:12px;line-height:19px;color:#8E97A3;margin:0">This information is meant for educational purposes and does not replace advice from your doctor. All oncology medicines are prescription-only.</p>
      </div>
    </div>
  </div>

  </div>
'''


def rail(toc):
    items = list(toc) + [('toc-faq', 'Frequently Asked Questions'), ('references', 'References')]
    links = ''.join('<a href="#%s" style="font-size:14px;line-height:20px;color:#5C636D">%s</a>' % (i, esc(t)) for i, t in items)
    rel = [('Cancer types', 'https://pharmeasy.in/cancer/types/'), ('Cancer symptoms and early signs', 'https://pharmeasy.in/cancer/symptoms/'), ('Cancer tests and tumour markers', 'https://pharmeasy.in/cancer/tests/'),
           ('Cancer screening', 'https://pharmeasy.in/cancer/screening/'), ('Cancer treatment', 'https://pharmeasy.in/cancer/treatment/'),
           ('Cancer in India', 'https://pharmeasy.in/cancer/india/'), ('Tumour versus cancer', 'https://pharmeasy.in/cancer/symptoms/is-it-cancer/'),
           ('Medicines by drug class', 'https://pharmeasy.in/molecules-by-class/')]
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
        '          <a href="%s" style="display:block;text-align:center;background:#008880;color:#fff;font-weight:700;font-size:13px;padding:11px 16px;border-radius:12px;margin-bottom:10px">Consult a doctor</a>\n'
        '          <a href="#toc-screening" style="font-size:13px;font-weight:700;color:#00736C">Or read about screening and prevention</a>\n        </div>\n'
        '        <div class="pad" style="background:#fff;border:1px solid #E6E9ED;border-radius:12px;padding:18px">\n'
        '          <div style="font-size:11px;font-weight:800;letter-spacing:0.06em;text-transform:uppercase;color:#8E97A3;margin-bottom:12px">Related pages</div>\n'
        '          <div style="display:flex;flex-direction:column;gap:10px">%s</div>\n        </div>\n'
        '      </div>\n' % (links, svg(IC['steth'], 17), ODC, r))


def strip_tags(s):
    s = re.sub(r'<sup class="cite">.*?</sup>', '', s)
    s = re.sub(r'<[^>]+>', '', s)
    return html.unescape(re.sub(r'\s+', ' ', s)).strip()


def head(faqs, desc, title):
    org = json.load(open(os.path.join(HERE, 'org-schema.json'), encoding='utf8'))
    graph = list(org['@graph'])
    graph.append({'@type': 'MedicalWebPage', '@id': CANON + '#webpage', 'url': CANON, 'name': 'Cancer', 'description': desc, 'inLanguage': 'en-IN',
                  'isPartOf': {'@id': 'https://pharmeasy.in/#Website'}, 'breadcrumb': {'@id': CANON + '#breadcrumb'},
                  'publisher': {'@id': 'https://pharmeasy.in/#Organization'},
                  'author': {'@type': 'Organization', 'name': 'PharmEasy Medical Team', 'url': 'https://pharmeasy.in/legal/editorial-policy'},
                  'dateModified': LAST_UPDATED_ISO,
                  'reviewedBy': {'@type': 'Person', 'name': REVIEWER, 'url': REVIEWER_URL, 'image': REVIEWER_IMG}})
    graph.append({'@type': 'BreadcrumbList', '@id': CANON + '#breadcrumb', 'itemListElement': [
        {'@type': 'ListItem', 'position': 1, 'name': 'Home', 'item': 'https://pharmeasy.in/'},
        {'@type': 'ListItem', 'position': 2, 'name': 'Cancer', 'item': CANON}]})
    graph.append({'@type': 'FAQPage', '@id': CANON + '#faq', 'mainEntity': [
        {'@type': 'Question', 'name': q, 'acceptedAnswer': {'@type': 'Answer', 'text': strip_tags(inline(line(a)))}} for q, a in faqs]})
    ld = json.dumps({'@context': 'https://schema.org', '@graph': graph}, ensure_ascii=False, separators=(',', ':'))
    return f'''<!DOCTYPE html>
<html lang="en-IN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" href="https://pharmeasy.in/favicon.ico" sizes="any">
<link rel="apple-touch-icon" href="https://pharmeasy.in/favicon.ico">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
{ROBOTS}<link rel="canonical" href="{CANON}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{CANON}">
<meta property="og:type" content="article">
<meta property="og:site_name" content="PharmEasy">
<script type="application/ld+json">{ld}</script>
<link rel="preconnect" href="https://assets.pharmeasy.in" crossorigin>
<link rel="stylesheet" href="assets/css/tokens.css">
<link rel="stylesheet" href="assets/css/pe.css">
<link rel="stylesheet" href="assets/css/page.css">
<link rel="stylesheet" href="assets/css/cancer.css">
</head>'''


EXTERNAL_A = re.compile(r'<a\b[^>]*\bhref="(?:https?:)?//(?!(?:www\.)?pharmeasy\.in[/"])[^"]*"[^>]*>')


def nofollow_external(page):
    """Every link off pharmeasy.in gets rel="nofollow" (merged with any rel already there)."""
    def fix(m):
        tag = m.group(0)
        rel = re.search(r'\brel="([^"]*)"', tag)
        tokens = rel.group(1).split() if rel else []
        tokens += [t for t in ('nofollow',) if t not in tokens]
        if rel:
            return tag[:rel.start()] + 'rel="%s"' % ' '.join(tokens) + tag[rel.end():]
        return tag[:-1] + ' rel="%s">' % ' '.join(tokens)
    return EXTERNAL_A.sub(fix, page)


URLS_FILE = os.path.join(HERE, 'cancer_urls.txt')


def check_cancer_links(page):
    """Only the planned /cancer/ pages may be linked (cancer_urls.txt). Fails the build otherwise."""
    allowed = {l.strip() for l in open(URLS_FILE, encoding='utf8') if l.startswith('/cancer/')}
    used = set(re.findall(r'href="https://pharmeasy\.in(/cancer/[^"#?]*)', page))
    bad = sorted(used - allowed)
    assert not bad, 'links to /cancer/ pages that are not in cancer_urls.txt: %s' % bad
    missing = sorted(allowed - used - {'/cancer/'})
    print('cancer links: %d of %d planned pages linked%s' % (len(used & allowed), len(allowed),
          ('; not linked: ' + ', '.join(missing)) if missing else ''))


def built_pages():
    """Inner pages present in this build (for the preview-only link rewrite in cancer.js)."""
    root = os.path.join(HERE, '..')
    out = []
    for d, _, files in os.walk(root):
        rel = os.path.relpath(d, root).replace(os.sep, '/')
        if 'index.html' in files and rel != '.' and not rel.startswith(('build', 'assets', '.git')):
            out.append(rel + '/')
    return sorted(out)


def main():
    sections, toc = build_sections()
    faq, ref, faqs = faq_and_refs()
    title = 'Cancer: Symptoms, Diagnosis, Treatment and Care in India | PharmEasy'
    desc = ('Understand what cancer is, how it starts and spreads, how it is diagnosed and treated, the India numbers, insurance and screening. '
            'Medically reviewed by Dr. Ayush Shashikant Dubey.')
    body = ''.join(sections)
    # the explore band sits before the FAQ, like the GLP-1 tools band
    page = (head(faqs, desc, title) + '\n<body data-built="%s">\n<a class="skip" href="#main">Skip to content</a>' % ' '.join(built_pages()) + '\n<div data-pe-header></div>\n<main id="main"><div id="dc-root">\n'
            '<div style="background:#F5F7F8;font-family:var(--glp-font,Inter,Mulish,sans-serif);color:#25282B;padding-bottom:48px;container-type:inline-size">\n'
            + hero() + '\n  <div class="sec" style="max-width:1120px;margin:0 auto;padding:24px 20px 0">\n    <div style="display:flex;flex-wrap:wrap;gap:24px;align-items:flex-start">\n\n' + rail(toc)
            + '\n      <div class="art" style="order:2;flex:1 1 560px;min-width:0">\n' + body + explore_band() + faq + ref + '\n      </div>\n    </div>\n  </div>\n' + disclaimer() +
            '\n</div>\n</div></main>\n<div data-pe-footer></div>\n'
            '<script src="assets/js/pe-shell.js" defer></script>\n<script src="assets/js/pe-toc.js" defer></script>\n<script src="assets/js/cancer.js" defer></script>\n</body>\n</html>\n')
    page = nofollow_external(page)
    check_cancer_links(page)
    # the house rule: no em or en dashes in any output
    assert '—' not in page and '–' not in page, [m.start() for m in re.finditer('[—–]', page)][:5]
    open(OUT, 'w', encoding='utf8').write(page)
    print('wrote', os.path.abspath(OUT), len(page), 'bytes; sections', len(toc), 'faqs', len(faqs))
    print('robots: indexable (production build)' if PRODUCTION else
          'robots: NOINDEX (GitHub Pages copy; build with --production for pharmeasy.in)')


if __name__ == '__main__':
    main()

"""Source parsing + inline markdown helpers for the cancer hub build."""
import re, html

SRC = open(__file__.rsplit('/', 1)[0] + '/source.md', encoding='utf8').read().split('\n')


def line(n):
    """1-indexed source line (line numbers match the original download, minus nothing:
    image data lines were only removed from the tail, so 1..386 are unchanged)."""
    return SRC[n - 1]


def clean_url(u):
    u = u.replace('%20', '').replace('\\', '').strip()
    return u


def unesc(s):
    s = s.replace('\\_', '_').replace('\\[', '[').replace('\\]', ']').replace('\\+', '+')
    s = s.replace('\\.', '.').replace('\\&', '&').replace('\\-', '-').replace('\\(', '(').replace('\\)', ')')
    s = s.replace('\\*', '*').replace('\\|', '|').replace('\\<', '<').replace('\\>', '>').replace('\\\\', '\\')
    return s


CITE_RE = re.compile(r'\[(\d+)\]\((https?://[^)\s]+)\)')
LINK_RE = re.compile(r'\[([^\]]+)\]\((https?://[^)\s]+)\)')

CITES_SEEN = []  # (num, url) for the audit


def inline(s, links=True):
    """Source markdown inline -> HTML. Citations [N](url) become superscript [N] anchors
    to #ref-N; adjacent citations merge into one superscript group."""
    s = s.strip()
    # citations first -> placeholder token so the generic link pass skips them
    def cite_sub(m):
        CITES_SEEN.append((int(m.group(1)), clean_url(m.group(2))))
        return '\x01%s\x02' % m.group(1)
    s = CITE_RE.sub(cite_sub, s)
    # merge "\x01a\x02,\x01b\x02" (optionally spaced) into one group
    s = re.sub(r'(\x01\d+\x02)(\s*,\s*\x01\d+\x02)+', lambda m: m.group(0), s)
    def group(m):
        nums = re.findall(r'\x01(\d+)\x02', m.group(0))
        inner = ', '.join('[<a href="#ref-%s">%s</a>]' % (n, n) for n in nums)
        return '<sup class="cite">%s</sup>' % inner
    s = re.sub(r'(?:\x01\d+\x02)(?:\s*,\s*\x01\d+\x02)*', group, s)
    # generic links
    def link_sub(m):
        txt, url = m.group(1), clean_url(m.group(2))
        if not links:
            return txt
        return '<a href="%s">%s</a>' % (html.escape(url, quote=True), txt)
    s = LINK_RE.sub(link_sub, s)
    s = unesc(s)
    s = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', s)
    s = re.sub(r'(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])', r'<em>\1</em>', s)
    s = s.replace('&amp;', '&').replace('&', '&amp;')
    s = re.sub(r'\s+', ' ', s).strip()
    # no em / en dashes anywhere on this laptop's output
    s = s.replace('—', ', ').replace('–', '-')
    return s


def table(start, end):
    """Parse a markdown pipe table spanning source lines start..end (inclusive).
    Returns (header_cells, rows) with raw cell strings."""
    rows = []
    for n in range(start, end + 1):
        l = line(n).strip()
        if not l.startswith('|'):
            continue
        cells = [c.strip() for c in re.split(r'(?<!\\)\|', l)[1:-1]]
        if all(re.fullmatch(r':?-+:?', c) for c in cells):
            continue
        rows.append(cells)
    return rows[0], rows[1:]


def references():
    refs = {}
    for l in SRC:
        m = re.match(r'^(\d+)\\\.\s+(.*\S)\s*$', l)
        if m:
            refs[int(m.group(1))] = m.group(2)
    return refs


def ref_html(text):
    """A reference line -> html with the trailing url linked, italics kept."""
    t = text
    # take the markdown link at the end and keep its visible text
    m = re.search(r'\[(https?[^\]]+)\]\((https?://[^)\s]+)\)\s*$', t)
    url = None
    if m:
        url = clean_url(m.group(2))
        t = t[:m.start()].rstrip()
    t = unesc(t)
    t = re.sub(r'\*(.+?)\*', r'<em>\1</em>', t)
    t = t.replace('&', '&amp;').replace('<em>', '\x03').replace('</em>', '\x04')
    t = t.replace('\x03', '<em>').replace('\x04', '</em>')
    t = t.replace('—', ', ').replace('–', '-')
    t = re.sub(r'\s+', ' ', t).strip()
    if url:
        t = t + ' Available from: <a href="%s" style="overflow-wrap:anywhere">%s</a>' % (html.escape(url, quote=True), html.escape(url))
    return t, url


if __name__ == '__main__':
    r = references()
    print(len(r), sorted(r)[:3], sorted(r)[-3:])
    print(ref_html(r[3])[0]); print(ref_html(r[45])[0])
    print(inline(line(9))[:700])

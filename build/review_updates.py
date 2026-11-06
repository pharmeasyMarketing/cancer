#!/usr/bin/env python3
"""Editor approval step for the "Latest on cancer in India" section.

  python3 review_updates.py list                 pending candidates, most India-relevant first
  python3 review_updates.py list --all           every queued item with its status
  python3 review_updates.py show ID              one item in full (terms, warnings, page changes)
  python3 review_updates.py approve ID [ID ...]  publish to updates.json (rendered on next build)
        --title "..."   required for page-change alerts (they have no source headline);
                        on an article it replaces the verbatim headline, so use only to fix a typo
        --date YYYY-MM-DD   override the date shown in the pill
        --url URL           correct a wrong source link
        --by NAME           who approved it (default: your login name)
  python3 review_updates.py reject ID [ID ...]   drop from the queue (never re-queued)
  python3 review_updates.py withdraw ID          take an approved item off the page again

Approval is the only way an item reaches the page. Re-run build.py after approving.
"""
import argparse, getpass, re, sys, textwrap
from fetch_updates import QUEUE, APPROVED, load, save, now_iso


def find(queue, ids):
    by_id = {i['id']: i for i in queue['items']}
    missing = [x for x in ids if x not in by_id]
    if missing:
        sys.exit('unknown id(s): %s  (run: python3 review_updates.py list --all)' % ', '.join(missing))
    return [by_id[x] for x in ids]


def row(i):
    head = i['title'] or '(page change, needs --title) %s' % i.get('label', '')
    flag = '  !' if i.get('warning') else ''
    return '[%s] %-9s %s  india=%-2d %-30s%s\n      %s\n      %s' % (
        i['id'], i['status'], i['date'], i['india_score'], i['source'][:30], flag, head, i['url'])


def cmd_list(q, a):
    items = q['items'] if a.all else [i for i in q['items'] if i['status'] == 'pending']
    items = sorted(items, key=lambda i: (i['india_score'], i['date']), reverse=True)
    for i in items:
        print(row(i))
    print('\n%d item(s). %d pending, %d approved, %d rejected.' % (
        len(items), *(sum(1 for i in q['items'] if i['status'] == s) for s in ('pending', 'approved', 'rejected'))))


def cmd_show(q, a):
    for i in find(q, a.ids):
        print(row(i))
        for k in ('warning', 'label', 'date_source', 'ministry', 'terms', 'changes', 'via', 'fetched_at',
                  'approved_by', 'approved_at', 'rejected_at', 'withdrawn_at'):
            if i.get(k):
                print('      %s: %s' % (k, i[k]))


def published(approved):
    return {i['id']: i for i in approved['items']}


def cmd_approve(q, a):
    if len(a.ids) > 1 and (a.title or a.date or a.url):
        sys.exit('--title/--date/--url apply to one item at a time')
    approved = load(APPROVED, {'items': []})
    live = published(approved)
    for i in find(q, a.ids):
        if i['kind'] == 'page_change' and not a.title:
            sys.exit('[%s] is a page-change alert with no source headline. Open %s, then approve with '
                     '--title "the headline as the editor wants it shown".' % (i['id'], i['url']))
        if a.date and not re.fullmatch(r'\d{4}-\d{2}-\d{2}', a.date):
            sys.exit('--date must be YYYY-MM-DD')
        title = a.title or i['title']
        if re.search('[\u2013\u2014]', title):
            sys.exit('title contains an em/en dash; house style is commas, colons or parentheses. '
                     'Pass --title with the dash replaced.')
        if i.get('warning') and not a.url:
            print('note [%s]: %s' % (i['id'], i['warning']))
        entry = {'id': i['id'], 'status': 'approved', 'title': title, 'source': i['source'],
                 'date': a.date or i['date'], 'url': a.url or i['url'], 'kind': i['kind'],
                 'approved_by': a.by, 'approved_at': now_iso()}
        if title != i['title']:
            entry['source_title'] = i['title']  # keep the original headline on record
        live[i['id']] = entry
        i.update(status='approved', approved_by=a.by, approved_at=entry['approved_at'])
        print('approved [%s] %s' % (i['id'], title))
    approved['items'] = sorted(live.values(), key=lambda e: e['date'], reverse=True)
    approved['updated_at'] = now_iso()
    save(APPROVED, approved)
    save(QUEUE, q)
    print('-> updates.json now has %d approved item(s). Rebuild: python3 build.py' % len(approved['items']))


def cmd_reject(q, a):
    for i in find(q, a.ids):
        if i['status'] == 'approved':
            sys.exit('[%s] is live; use withdraw first' % i['id'])
        i.update(status='rejected', rejected_at=now_iso())
        print('rejected [%s] %s' % (i['id'], i['title'] or i.get('label')))
    save(QUEUE, q)


def cmd_withdraw(q, a):
    approved = load(APPROVED, {'items': []})
    live = published(approved)
    for i in find(q, a.ids):
        live.pop(i['id'], None)
        i.update(status='rejected', withdrawn_at=now_iso())
        print('withdrawn [%s] %s' % (i['id'], i['title'] or i.get('label')))
    approved['items'] = sorted(live.values(), key=lambda e: e['date'], reverse=True)
    approved['updated_at'] = now_iso()
    save(APPROVED, approved)
    save(QUEUE, q)
    print('-> rebuild to take it off the page: python3 build.py')


def main():
    ap = argparse.ArgumentParser(description=textwrap.dedent(__doc__), formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('list'); p.add_argument('--all', action='store_true'); p.set_defaults(fn=cmd_list)
    p = sub.add_parser('show'); p.add_argument('ids', nargs='+'); p.set_defaults(fn=cmd_show)
    p = sub.add_parser('approve'); p.add_argument('ids', nargs='+'); p.set_defaults(fn=cmd_approve)
    p.add_argument('--title'); p.add_argument('--date'); p.add_argument('--url'); p.add_argument('--by', default=getpass.getuser())
    p = sub.add_parser('reject'); p.add_argument('ids', nargs='+'); p.set_defaults(fn=cmd_reject)
    p = sub.add_parser('withdraw'); p.add_argument('ids', nargs='+'); p.set_defaults(fn=cmd_withdraw)
    a = ap.parse_args()
    q = load(QUEUE, {'items': []})
    a.fn(q, a)


if __name__ == '__main__':
    main()

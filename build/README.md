# Cancer hub build

`python3 build.py` regenerates `../index.html` from `source.md` (the doctor-reviewed editorial doc).

## Drug table: "+N more molecules" popups

Each drug-group row ends with a "+N more molecules" chip. Clicking it opens a popup listing that
group's other molecules on PharmEasy, each linked to its molecule page. The list is rendered client
side by `assets/js/cancer.js` from `assets/data/drug-more.json`, so the molecule links are not in
the page HTML.

- `molecules_sheet.csv` is a snapshot of the "Cancer Molecules list" Google Sheet
  (molecule_name, molecule_id, urls).
- `molecule_groups.json` says which row each sheet molecule belongs to, plus an `excluded` list
  (not a cancer medicine, or a cancer medicine with no matching row).
- `build.py` writes `drug-more.json`, leaving out molecules already shown in that row (matched by
  molecule id). The build **fails** if a sheet molecule is neither grouped nor excluded, so a new
  sheet row always needs a decision.

To refresh: re-export the sheet as CSV over `molecules_sheet.csv`, place any new molecules in
`molecule_groups.json`, run `python3 build.py`.

## "Latest on cancer in India": semi-automated updates

Collection is automatic. Publishing is not: nothing reaches the page until an editor approves it.
Headlines are kept exactly as the source wrote them. Nothing is summarised or rewritten by AI.

### Daily flow

```
fetch_updates.py   ->  updates_queue.json (status "pending")
review_updates.py  ->  approve / reject by id
                       approved items are copied to updates.json (status "approved")
build.py           ->  renders the newest 5 approved items; "Updated <Month Year>" comes
                       from the newest approved item's date
```

1. **Fetch** (nightly in CI, or by hand): `python3 fetch_updates.py`
   (`--dry-run` prints what it would queue and writes nothing). Re-running is safe: an item
   is queued once, ever, by id and by normalised headline.
2. **Review**: `python3 review_updates.py list` shows pending items, most India-relevant first.
   Open the link, check it with the medical reviewer if needed, then
   - `python3 review_updates.py approve 85faa86c b8dd83b9`
   - `python3 review_updates.py reject 640a3949 404c86a4`
   - `python3 review_updates.py show ID` for the matched terms, warnings and page-change details
3. **Build**: `python3 build.py`, then deploy as usual.
4. **Take something down**: `python3 review_updates.py withdraw ID`, then rebuild.

If `updates.json` is missing or has no approved items, the section falls back to the three
"Sample" placeholder rows from `source.md` (byte-identical to the original build).

### Approval rules built into the CLI

- **Page-change alerts** (ICMR-NINE, GLOBOCAN) have no source headline, so they can only be
  approved with `--title "..."` written by the editor.
- **Dashes**: the page may not contain em or en dashes (build.py asserts this). A headline that
  contains one is refused; approve it with `--title` and the dash replaced. The original headline
  is kept in `updates.json` as `source_title`.
- `--date YYYY-MM-DD` overrides the pill date; `--url` corrects a bad source link;
  `--by NAME` records the approver (default: your login).
- Items flagged `!` in `list` carry a warning to read before approving (see ICMR-NINE below).

### Sources (checked 6 Nov 2026)

| Source | How it is read | Notes |
|---|---|---|
| WHO news | `who.int/api/news/newsitems` (the site's own OData API, newest first, paged 100 at a time) | The suggested RSS (`rss-feeds/news-english.xml`) is a frozen legacy feed: all 83 items are 2003 to 2020 stories whose pubDate gets re-stamped, so it is not used. |
| IARC | RSS: `feed/?post_type=pressrelease`, `feed/?post_type=news-events`, plus `feed/` | The site-wide `feed/` only holds 5 stale posts (some with blank titles); the real content is in the two post-type feeds. The same story often appears in both; it is queued once. |
| PIB | English press-release RSS `RssMain.aspx?ModId=6&Lang=1&Regid=3&reg=3` + today's `allRel.aspx` list | The original URL 302s to the **Hindi** feed only because `&reg=` was missing. There is **no Ministry of Health feed** (PIB offers only all-ministry feeds; mohfw.gov.in has no RSS). The RSS keeps only the latest ~20 releases across all ministries, so today's all-releases page is read too. Each cancer-matching release page is opened to read the ministry and date, which go into the source label (e.g. "PIB, Ministry of Health and Family Welfare"). |
| ICMR-NINE | Page monitor on `icmrnine.org` (marquee, Featured Publications, Important Link box), SHA-256 of those sections | **ICMR-NCDIR is now ICMR-NINE**; ncdirindia.org only shows a redirect notice. Featured publications are queued with their titles verbatim. On 6 Nov 2026 the site linked three of the four featured titles to the same unrelated stroke paper, so items whose link is shared get a warning; fix with `--url` before approving. A new file in the Important Link box becomes a page-change alert. |
| GLOBOCAN India | Page monitor on the fact-sheet **PDF** (`media/globocan/factsheets/populations/356-india-fact-sheet.pdf`): ETag, Last-Modified, SHA-256 | The fact-sheet page is a JS app shell whose HTML never changes with the data, so hashing it would only detect app redeploys. First run records a baseline and raises an alert only if the PDF changed within the lookback window (it was last modified 21 Oct 2026). |

The baseline hashes and seen links live in `updates_state.json`.

### Relevance rules

- **Cancer filter** (title + description, whole words, case-insensitive): an item needs a strong term
  (cancer, oncology, tumour/tumor, carcinoma, carcinogen, malignant, leukaemia, lymphoma, melanoma,
  myeloma, sarcoma, glioma, HPV, human papillomavirus, mammography, Pap smear, chemotherapy,
  radiotherapy, immunotherapy, metastasis, GLOBOCAN, cancer registry), or a weak term (screening,
  biopsy, early detection, tobacco, areca, gutka, betel) together with a body site (breast, cervix,
  oral, lung, colorectal, prostate and so on). "Screening" alone also matches TB or diabetes screening.
- **India score**: India terms in the title count 3, in the description 1 (India, ICMR, NCDIR/NINE,
  MoHFW, Ayushman, PM-JAY, AIIMS, Tata Memorial, major states and cities); South-East Asia / LMIC /
  low-resource wording adds 1; PIB, ICMR-NINE and GLOBOCAN India items start at 5. The score only
  orders the review list. It never publishes or drops anything.
- Feed items older than 120 days (`LOOKBACK_DAYS`) are ignored.

### Nightly GitHub Actions (when this hub gets a repo like GLP-1)

Run only the fetch step in CI and commit the queue back. The editor approves locally (or via
the Sheet option below), and the approval commit goes through the normal build and deploy.
Because `build.py` only ever reads `updates.json`, adding `python3 build/build.py` to the nightly
job would also be safe: it cannot publish a pending item.

```yaml
# .github/workflows/cancer-updates.yml
name: "Cancer hub: fetch update candidates"
on:
  schedule:
    - cron: "0 1 * * *"      # 06:30 IST daily
  workflow_dispatch:
permissions:
  contents: write
jobs:
  fetch:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - name: Fetch candidates (standard library only)
        run: python3 build/fetch_updates.py | tee fetch.log
      - name: Commit queue + monitor state
        run: |
          set -euo pipefail
          git config user.name  "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add build/updates_queue.json build/updates_state.json
          git diff --staged --quiet && { echo "no new candidates"; exit 0; }
          git commit -m "updates: new candidates $(date -u +%Y-%m-%d) [skip ci]"
          git push
      # Optional: open an issue listing new candidates so the editor gets a notification
      # (gh issue create --title "Cancer hub: new update candidates" --body-file fetch.log).
```

`fetch_updates.py` exits 1 only when every source failed, so a single flaky host does not fail the job.
Errors for individual sources are printed to stderr and show in the Actions log.

### Easier for a non-technical editor: a Google Sheet

If the editor would rather not use a terminal, the queue can live in a Google Sheet instead:
the nightly job appends new candidates as rows (id, date, source, India score, headline, link,
an empty **Decision** column with an approve/reject dropdown, and an optional **Editor title**
column). The build step reads the Sheet's approved rows (published-to-web CSV or a service-account
read) and writes `updates.json` before running `build.py`. The CLI stays as the fallback. This needs
a service account with edit access to the Sheet stored as a repo secret.

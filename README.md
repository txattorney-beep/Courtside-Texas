# Courtside Texas

A mobile-first public reference for Texas litigation, by Eric A. Hudson.

Website: https://courtsidetexas.com

## What is included

- All 519 Texas state district courts and all 17 state appellate courts in the current official OCA directory, plus the four federal districts and Fifth Circuit.
- Court- and county-specific links, judge names, official docket portals, and applicable administrative judicial-region rules.
- Local rules, standing orders and related documents from the official repository, with extracted text or OCR and explicit retrieval status.
- Official federal and Texas civil practice rule collections.
- All 17 Texas Administrative Code titles and 136 current agency/part entries. Full TAC text is searched at the official Secretary of State portal.
- Device-local favorite courts, import/export, and a downloadable self-contained HTML directory.
- Search-engine-readable court pages, sitemap, robots policy, canonical URLs and structured metadata.

## Hosting and publication

GitHub stores the source, data snapshots, and generated `site/` output. A small Cloudflare Worker in `cloudflare/worker.js` serves that public output at courtsidetexas.com. It uses the fixed public repository origin, streams files, caches for two minutes, and requires no GitHub or visitor credentials. The `www` hostname redirects to the canonical apex domain.

Source edits under `public/` trigger the publishing workflow. `scripts/build.py` generates the court pages and sitemap. The workflow validates before replacing `site/` and committing. No Node dependency installation is required.

## Weekly refresh

`.github/workflows/weekly-refresh.yml` runs Mondays at 12:00 UTC (6 a.m. Central Standard Time / 7 a.m. Central Daylight Time), and supports manual dispatch. It retrieves OCA court exports and local-rule associations, current rule documents, and the official TAC title/agency directory. Poppler extracts PDF text; Tesseract OCR handles image-only PDFs. Previous text is retained and labeled stale on retrieval failure. Source snapshots are published only after completeness and schema checks pass. A failed workflow leaves the prior site available, and GitHub's Actions log records the failure.

GitHub scheduled workflows can be delayed or disabled after prolonged repository inactivity. Weekly snapshot commits normally keep this repository active. Review Actions notifications and the public source-check date if an update is late.

Run locally (Python 3, Node for syntax checks, Poppler and Tesseract required):

```sh
python3 scripts/refresh.py
python3 scripts/build.py
python3 scripts/validate.py
```

`public/data/catalog.json.gz` contains document metadata and court entries. `text-*.json.gz` files contain extracted public-rule text. The browser decompresses these for local searching. The complete index is downloaded only when rule text is requested.

## Coverage and limitations

Official documents control. Rule-document metadata and retrieval status are shown separately from the document's effective date. OCA's repository does not establish that every court-specific practice or judge-specific order has been captured. Nine new district courts currently have no website listed in CARD, so their links lead to the official directory. Docket buttons open official portals; they do not bypass accounts, fees, access restrictions, or sealed records. re:SearchTX civil coverage varies; named criminal district courts use county criminal-record access instead.

The directory is an independent reference, not legal advice or an official court publication. No copyright is asserted over public-domain government rules. Original branding and editorial site content © Eric A. Hudson. External links do not imply endorsement.

## Search engines

The generated sitemap lists individual court pages and reference indexes. IndexNow notifications are submitted through `scripts/submit_indexnow.py` after refresh; acceptance does not guarantee indexing. Google Search Console ownership verification and sitemap submission may require Eric's Google account. There is no ranking or indexing guarantee.

## Legal news desk

`/news/` is a headline-first aggregator with three desktop columns and a single phone column. Original article links, publisher names and publication dates accompany every item. The daily workflow refreshes public Texas Tribune, State Bar, and Fifth Circuit RSS feeds at 13:00 UTC. Legal-topic filtering applies to general news feeds; opinions are labeled published or unpublished. Links older than 30 days expire; failed feeds retain prior links with their dates. Curated entries in `public/data/news-seed.json` provide reviewed lead stories and supplemental sources. No full articles are copied. The court/rules workflow remains weekly.

The biography in `public/biography.html` matches the Religious Liberty Watch biography retrieved November 15, 2026. The builder uses this single source for the static About page and application biography.


Business Court coverage includes the five operational divisions (1, 3, 4, 8 and 11), with official division pages, counties, judges, re:SearchTX docket access, current statewide rules and division procedures. The directory source is `data/business-court-sources.json`; `scripts/ingest/business.py` refreshes rule links and text during publication and weekly updates. Failed retrievals retain prior text with a status label. `scripts/business_catalog.py` merges this coverage into every generated catalog, court page and portable download.

Builds fingerprint CSS and JavaScript filenames and version the offline cache. Legal News is a normal link in the sidebar, top bar and static reference pages. Returning open tabs check the application release and reload when it changes.

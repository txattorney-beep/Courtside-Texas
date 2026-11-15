"""Refresh the Business Court's official rules and retain prior text on failure."""
import concurrent.futures
import datetime
import hashlib
import html
import json
import pathlib
import re
import subprocess
import tempfile
import urllib.parse
import urllib.request

from federal import Links

ROOT = pathlib.Path(__file__).resolve().parents[2]
SNAPSHOT = ROOT / 'public/data/business.json'
UA = 'CourtsideTexas/1.0 (+https://courtsidetexas.com; public court directory)'


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': UA}), timeout=30) as response:
        return response.read(30_000_000)


def run(fetch=True):
    source = json.loads((ROOT / 'data/business-court-sources.json').read_text())
    prior = json.loads(SNAPSHOT.read_text()) if SNAPSHOT.exists() else {'documents': []}
    old = {d['id']: d for d in prior['documents']}
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    courts = []
    documents = []
    for division in source['divisions']:
        number = division['number']
        court_id = f'tx-business-{number}'
        locations = []
        for location in division['locations']:
            address = location.get('address', '')
            city = next((c for c in division['cities'] if c in address), division['cities'][0])
            locations.append({'city': city, 'address': address, 'url': division['url']})
        courts.append({
            'id': court_id, 'name': division['name'],
            'shortName': f'Texas Business Court Division {number}',
            'aliases': ['Business courts', f'Division {number}A', f'Division {number}B'],
            'division': number, 'level': 'Business Court', 'jurisdiction': 'Texas',
            'cities': division['cities'], 'counties': division['counties'],
            'judge': '; '.join(division['judges']), 'url': division['url'], 'urlStatus': 'official',
            'locations': locations, 'sourceUrl': source['divisionSourceUrl'],
            'checkedAt': source['verifiedDate'], 'sourceNote': source['statusNote'],
            'docket': source['docket'], 'docketAlternatives': [],
            'localRulesUrls': [source['rulesPage'], division['url']],
            'practiceUrl': division['url'], 'ruleDocumentIds': [],
        })
        for index, procedure in enumerate(division['procedures']):
            documents.append({**procedure, 'id': f'business-{number}-procedure-{index+1}',
                              'sourcePage': division['url'], 'courtIds': [court_id],
                              'documentType': 'Court Procedures'})
    court_ids = [c['id'] for c in courts]
    for index, rule in enumerate(source['statewideRules']):
        documents.append({**rule, 'id': ['business-local-rules', 'business-admin-rules'][index],
                          'sourcePage': source['rulesPage'], 'courtIds': court_ids,
                          'documentType': 'Local Rules'})
    pages = {}
    if fetch:
        def page(url):
            try:
                parser = Links()
                parser.feed(get(url).decode(errors='replace'))
                return url, parser.links
            except Exception:
                return url, []
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            pages = dict(pool.map(page, sorted({d['sourcePage'] for d in documents})))

    def refresh(document):
        document = dict(document)
        url = document.pop('url')
        original_url = url
        # Titles, unlike filenames and revision dates, identify a current compilation.
        title_key = re.sub(r'\s*\(rev.*', '', document['title'], flags=re.I).lower()
        for href, label in pages.get(document['sourcePage'], []):
            label = html.unescape(label).replace('\u2019', "'").strip()
            normalized = re.sub(r'\s*\(rev.*', '', label, flags=re.I).lower()
            shared_match = (document['id'] == 'business-local-rules' and
                            re.search(r'local rules of (the )?business court', normalized))
            if normalized == title_key or shared_match:
                candidate = urllib.parse.urljoin(document['sourcePage'], href)
                if candidate.lower().endswith('.pdf') and urllib.parse.urlsplit(candidate).hostname in {'www.txcourts.gov', 'txcourts.gov'}:
                    url = candidate
                    document['title'] = label
                    if url != original_url:
                        document.pop('effectiveDate', None)
                    break
        document.update(category='local', jurisdiction='Texas', courtGroup='Business Court',
                        sourceUrl=url, status='link-only', text='', checkedAt=now if fetch else source['verifiedDate'])
        if not document['title'].startswith('Local Rules'):
            document['title'] = 'Texas Business Court: ' + document['title']
        try:
            if not fetch:
                raise ValueError('Official source link; retrieval pending')
            payload = get(url)
            if not payload.startswith(b'%PDF'):
                raise ValueError('Official source did not return a PDF')
            with tempfile.TemporaryDirectory() as temporary:
                file = pathlib.Path(temporary) / 'rules.pdf'
                file.write_bytes(payload)
                result = subprocess.run(['pdftotext', '-layout', str(file), '-'], capture_output=True, check=True, timeout=45)
            text = result.stdout.decode(errors='replace').strip()
            if len(text) < 60:
                raise ValueError('No extractable text; open the official PDF')
            document.update(text=text, status='indexed', retrievedAt=now,
                            sha256=hashlib.sha256(payload).hexdigest())
        except Exception as error:
            previous = old.get(document['id'], {})
            if previous.get('text'):
                document.update(text=previous['text'], status='stale',
                                retrievedAt=previous.get('retrievedAt'),
                                textSourceUrl=previous.get('textSourceUrl', previous.get('sourceUrl')))
            document['note'] = 'Latest retrieval: ' + str(error)[:160]
        return document

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        documents = list(pool.map(refresh, documents))
    result = {'courts': courts, 'documents': documents, 'checkedAt': now,
              'directoryVerifiedAt': source['verifiedDate'], 'statusNote': source['statusNote']}
    SNAPSHOT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'businessDivisions': len(courts), 'businessDocuments': len(documents),
                      'searchable': sum(bool(d.get('text')) for d in documents)}))
    return result


if __name__ == '__main__':
    run()

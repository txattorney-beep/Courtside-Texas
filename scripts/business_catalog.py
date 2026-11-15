"""Include Business Court divisions in every build, including weekly refreshes."""
import gzip
import json
import re


def add_business_courts(root, dist, catalog):
    data = json.loads((root / 'public/data/business.json').read_text())
    courts = data['courts']
    county_names = {re.sub(r'\W', '', name).lower(): name
                    for court in catalog['courts'] for name in court['counties']}
    for court in courts:
        court['counties'] = [county_names.get(re.sub(r'\W', '', c).lower(), c) for c in court['counties']]
    ids = {c['id'] for c in courts}
    catalog['courts'] = [c for c in catalog['courts'] if c['id'] not in ids] + courts
    docs = data['documents']
    doc_ids = {d['id'] for d in docs}
    catalog['documents'] = [d for d in catalog['documents'] if d['id'] not in doc_ids]
    for document in catalog['documents']:
        if document.get('courtGroup') == 'Business Court':
            division = re.search(r'Division\s+(\d+)', document['title'], re.I)
            # Keep useful repository forms tied to their division; current procedures are above.
            if division and document.get('documentType') == 'Forms':
                document['courtIds'] = [f'tx-business-{int(division[1])}']
            if document['id'] == 'oca-3023':
                document['versionNote'] = 'Earlier July 2026 version. Current Business Court rules are linked from each division.'
    texts = [{'id': d['id'], 'text': d.pop('text')} for d in docs if d.get('text')]
    for document in docs:
        document.pop('text', None)
    catalog['documents'].extend(docs)
    shard = '/data/business-text.json.gz'
    (dist / shard.lstrip('/')).write_bytes(gzip.compress(json.dumps(texts).encode(), mtime=0))
    catalog['status']['textShards'] = [s for s in catalog['status']['textShards'] if s != shard] + [shard]
    catalog['status'].update(courts=len(catalog['courts']), documents=len(catalog['documents']),
                             businessDirectoryVerifiedAt=data['directoryVerifiedAt'])
    catalog['status']['indexedDocuments'] += len(texts)
    (dist / 'data/catalog.json.gz').write_bytes(gzip.compress(json.dumps(catalog).encode(), mtime=0))
    return catalog

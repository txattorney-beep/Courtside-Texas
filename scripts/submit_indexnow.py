"""Notify IndexNow participants of published URLs and record their response."""
import argparse
import datetime
import json
import os
import pathlib
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parents[1]
ORIGIN = 'https://courtsidetexas.com'
ENDPOINT = 'https://api.indexnow.org/indexnow'
HEADERS = {'User-Agent': 'CourtsideTexas/1.0 (+https://courtsidetexas.com)',
           'Content-Type': 'application/json; charset=utf-8'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--news-only', action='store_true')
    args = parser.parse_args()
    key = (ROOT / 'public/indexnow-key.txt').read_text().strip()
    key_url = ORIGIN + '/' + key + '.txt'
    with urllib.request.urlopen(urllib.request.Request(key_url, headers=HEADERS), timeout=30) as response:
        if response.read().decode().strip() != key:
            raise ValueError('Published IndexNow key does not match')
    # Submit only pages in the live sitemap, including on manual notification runs.
    with urllib.request.urlopen(urllib.request.Request(ORIGIN + '/sitemap.xml', headers=HEADERS), timeout=30) as response:
        sitemap = ET.fromstring(response.read())
    urls = [e.text for e in sitemap.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}loc')]
    if not urls or any(not url.startswith(ORIGIN + '/') for url in urls):
        raise ValueError('Invalid published sitemap')
    if args.news_only:
        urls = [url for url in urls if url == ORIGIN + '/news/']
    if not urls:
        raise ValueError('No published URLs to notify')
    payload = {'host': 'courtsidetexas.com', 'key': key, 'keyLocation': key_url, 'urlList': urls}
    for attempt in range(3):
        try:
            request = urllib.request.Request(ENDPOINT, data=json.dumps(payload).encode(), headers=HEADERS)
            with urllib.request.urlopen(request, timeout=30) as response:
                status = response.status
            if status not in (200, 202):
                raise ValueError(f'Unexpected IndexNow status: {status}')
            report = {'submittedAt': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                      'endpoint': ENDPOINT, 'httpStatus': status, 'urlCount': len(urls),
                      'status': 'accepted' if status == 200 else 'received; key validation pending',
                      'note': 'Submission receipt does not guarantee crawling, indexing, or ranking.'}
            output = ROOT / 'work/indexnow-submission.json'
            output.parent.mkdir(exist_ok=True)
            output.write_text(json.dumps(report, indent=2) + '\n')
            print(json.dumps(report))
            if os.environ.get('GITHUB_STEP_SUMMARY'):
                with open(os.environ['GITHUB_STEP_SUMMARY'], 'a') as summary:
                    summary.write(f"### Search-engine notification\n\nIndexNow HTTP {status}: {report['status']}. "
                                  f"Submitted {len(urls)} published URLs. {report['note']}\n")
            return
        except urllib.error.HTTPError as error:
            print('IndexNow response:', error.code, error.read().decode(errors='replace')[:1000])
            if error.code not in (403, 429, 500, 502, 503, 504) or attempt == 2:
                raise
            time.sleep(20)
        except (urllib.error.URLError, TimeoutError):
            if attempt == 2:
                raise
            time.sleep(20)


if __name__ == '__main__':
    main()

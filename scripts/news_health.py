"""DST-aware refresh gate and real public-edition verification."""
import datetime as dt
import html
import json
import os
from pathlib import Path
import sys
import time
import urllib.request
from zoneinfo import ZoneInfo
ROOT = Path(__file__).resolve().parents[1]
CENTRAL = ZoneInfo('America/Chicago')
def latest_window(now):
    local = now.astimezone(CENTRAL)
    windows = [local.replace(hour=h, minute=30, second=0, microsecond=0) for h in (7,16)]
    return max([w for w in windows if w <= local] or [windows[-1]-dt.timedelta(days=1)])
def refresh_due(snapshot, now):
    try:
        checked = dt.datetime.fromisoformat(snapshot['checkedAt'])
        return checked < latest_window(now) or checked > now+dt.timedelta(minutes=5)
    except (KeyError, ValueError, TypeError):
        return True

def verify(expected, live, page):
    if dt.datetime.fromisoformat(live['checkedAt']) < dt.datetime.fromisoformat(expected['checkedAt']):
        raise ValueError('Public news snapshot still predates the published edition')
    if not live.get('articles') or not any(s.get('success') for s in live.get('feedStatus', [])):
        raise ValueError('Public news edition has no usable source results')
    if not all(html.escape(a['title']) in page for a in live['articles']):
        raise ValueError('Public news page does not match the refreshed headline data')

if __name__ == '__main__':
    snapshot = json.loads((ROOT/'public/data/news.json').read_text())
    if sys.argv[1:] == ['gate']:
        due = os.environ.get('GITHUB_EVENT_NAME') != 'schedule' or refresh_due(snapshot, dt.datetime.now(dt.timezone.utc))
        with open(os.environ['GITHUB_OUTPUT'], 'a') as out:
            out.write(f"refresh={'true' if due else 'false'}\n")
        print('Refresh required' if due else 'Latest Central-time window already collected; verify public edition')
    else:
        for attempt in range(13):
            try:
                def get(path):
                    req=urllib.request.Request('https://courtsidetexas.com'+path,headers={'Cache-Control':'no-cache','User-Agent':'CourtsideTexas-publication-check'})
                    with urllib.request.urlopen(req, timeout=15) as response:
                        return response.read().decode()
                live=json.loads(get('/data/news.json'))
                verify(snapshot, live, get('/news/'))
                print('Verified LIVE news edition:', live['checkedAt'], len(live['articles']), 'headlines')
                break
            except Exception as error:
                if attempt == 12:
                    raise RuntimeError('Publication is not verified live; prior edition remains available') from error
                print(f'Waiting for live edition: {error}', flush=True)
                time.sleep(10)

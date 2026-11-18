"""Run after scripts/build.py; verify complete, distinct, linkable lists."""
import pathlib, re, json, gzip, unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
class CourtLists(unittest.TestCase):
 def test_complete_lists(self):
  courts=json.loads(gzip.decompress((ROOT/'dist/data/catalog.json.gz').read_bytes()))['courts']
  for level in ['State appellate','Federal appellate','Federal district','State district','Business Court']:
   with self.subTest(level=level):
    route='/court-lists/'+level.lower().replace(' ','-')+'/'
    page=(ROOT/'dist'/route.strip('/')/'index.html').read_text()
    actual=re.findall(r'<li><a href="/courts/([^/]+)/">',page)
    expected=[c['id'] for c in courts if c['level']==level]
    self.assertCountEqual(actual,expected)
    self.assertEqual(len(actual),len(set(actual)))
    self.assertIn('https://courtsidetexas.com'+route,(ROOT/'dist/sitemap.xml').read_text())
    for court_id in actual:self.assertTrue((ROOT/'dist/courts'/court_id/'index.html').exists())
 def test_footer_links(self):
  app=(ROOT/'public/app.js').read_text()
  self.assertIn('class="court-list-link" href="/court-lists/',app)
  self.assertIn('View full list →',app)
  css=(ROOT/'public/styles.css').read_text()
  self.assertRegex(css,r'\.court-list-link\{[^}]*font-size:20px')
  self.assertRegex(css,r'\.court-list-link\{[^}]*overflow-wrap:anywhere')
if __name__=='__main__':unittest.main()

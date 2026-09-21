"""Local, dependency-free release gates for the static public report."""
import hashlib
import json
from html.parser import HTMLParser
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls, self.ids = [], set()
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if 'id' in attrs:
            assert attrs['id'] not in self.ids, f"Duplicate id {attrs['id']}"
            self.ids.add(attrs['id'])
        for key in ['href', 'src', 'poster']:
            if attrs.get(key): self.urls.append(attrs[key])


def main():
    text = (ROOT/'index.html').read_text()
    parser = Links(); parser.feed(text)
    for url in parser.urls:
        p = urlsplit(url)
        if p.scheme or p.netloc: continue
        if p.path:
            assert (ROOT/unquote(p.path)).exists(), f"Missing local asset: {url}"
        elif p.fragment:
            assert p.fragment in parser.ids, f"Missing anchor: {url}"
    d = json.loads((ROOT/'assets/results.json').read_text())
    f = d['full_hawor_show3d']
    assert f['complete'] and f['processed'] == f['selected'] == len(f['clips']) == 12
    assert f['finite_complete'] == sum(c['status']=='complete' for c in f['clips']) == 10
    assert f['visualized'] == 10
    assert d['detector']['complete']
    assert d['show3d']['common_handframes'] == 9029
    assert d['egoexo']['common_handframes'] == 3916
    assert abs(f['summary']['raw_common']['camera_MPJPE_mm_TP'] - f['summary']['full_common']['camera_MPJPE_mm_TP']) < 1e-4
    for path in ROOT.rglob('*'):
        if path.suffix not in ['.html','.json','.css','.js','.md']: continue
        body = path.read_text()
        assert not re.search(r'/root/|/Users/|BEGIN (?:RSA |OPENSSH )?PRIVATE KEY|hf_[A-Za-z0-9]{24,}|gh[pousr]_[A-Za-z0-9]{20,}|\b182\.242\.', body), path
    before = hashlib.sha256((ROOT/'index.html').read_bytes()).hexdigest()
    subprocess.run([sys.executable,str(ROOT/'tools/build_report.py')],check=True)
    assert hashlib.sha256((ROOT/'index.html').read_bytes()).hexdigest() == before
    print(f'PASS: {len(parser.ids)} unique anchors; {len(parser.urls)} links; results / privacy / deterministic build')


if __name__ == '__main__':
    main()

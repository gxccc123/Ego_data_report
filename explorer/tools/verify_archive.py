"""Offline completeness/privacy checks, independent of browser rendering."""
from collections import Counter
from html.parser import HTMLParser
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
index=json.loads((ROOT/'data/index.json').read_text())
provenance=json.loads((ROOT/'data/provenance.json').read_text())
media=json.loads((ROOT/'data/media.json').read_text())
ids=[c['id'] for c in index['cases']]
assert len(ids)==len(set(ids))
assert len(ids)==index['totals']['cases']
attempts=timelines=media_entries=tested=0
for meta in index['cases']:
    c=json.loads((ROOT/'data/cases'/f'{meta["id"]}.json').read_text())
    assert c['id']==meta['id'] and c['family']==meta['family']
    assert len(c['attempts'])==len(set(a['run'] for a in c['attempts']))
    assert len(c['attempts'])==meta['attempts']
    if c['dataset']=='SHOW3D-test':assert not meta['has_reference'],'Test split must not be labelled as scored'
    attempts+=len(c['attempts']);tested+=meta['tested']
    for a in c['attempts']:
        if a.get('timeline'):
            timelines+=1
            for b in a['timeline']['bins']:
                assert 0<=b['start']<=b['end']<a['timeline']['frames']
                assert all(0<=v<=1 for v in b['presence'])
        if a.get('media'):
            media_entries+=1
            assert c['family'] in ['SHOW3D','EgoTactile','Open-AoE']
            m=media[a['media_key']]
            assert m['case']==c['id'] and m['run']==a['run']
            assert m['full_decode_verified'] and m['frames']>0 and m['fps']>0
            for key in ['video','poster']:assert (ROOT/m[key]).is_file(),m[key]
        for s in a['scores']:
            assert s['artifact'] in provenance['artifact_sha256'],s['artifact']
assert attempts==index['totals']['attempts']
assert timelines==index['totals']['timeline_attempts']
assert media_entries==index['totals']['video_entries']
assert tested==index['totals']['tested_cases']
assert len(set(m['video'] for m in media.values()))==index['totals']['unique_videos']
for path in ROOT.rglob('*'):
    if path.suffix not in ['.json','.html','.js','.css','.md','.txt']:continue
    if 'tools' in path.parts:continue
    text=path.read_text()
    for forbidden in ['/root/','/Users/','182.242.','BEGIN PRIVATE KEY','hf_','ghp_']:
        assert forbidden not in text,(path,forbidden)
    if path.suffix=='.json':json.loads(text,parse_constant=lambda c: (_ for _ in ()).throw(ValueError(c)))

class Links(HTMLParser):
    def handle_starttag(self,tag,attrs):
        for k,v in attrs:
            if k not in ['src','href'] or not v or v.startswith(('http:','https:','data:','#')):continue
            target=(ROOT/v.split('#')[0].split('?')[0]).resolve()
            assert target.exists(),v
Links().feed((ROOT/'index.html').read_text())
assert sum(p.stat().st_size for p in ROOT.rglob('*') if p.is_file())<900_000_000,'Leave Pages budget headroom'
print(json.dumps({'verified':True,**index['totals']},ensure_ascii=False,indent=2))

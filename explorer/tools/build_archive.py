"""Build small index + per-case JSON from the sanitized remote snapshot.

Optionally import exact allowlisted MP4s from a local transfer cache, decode
every frame, create a poster, and deduplicate byte-identical assets. This does
not run or change any model evaluation.
"""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import shutil

DEST = Path(__file__).resolve().parents[1]


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, allow_nan=False, separators=(',', ':'))+'\n')


def bad(attempt):
    return (attempt.get('status') in ['failed', 'error', 'input_failed'] or bool(attempt.get('error')) or
            attempt.get('validation_status') in ['failed', 'invalid'] or bool(attempt.get('validation_error')))


def import_video(item, cache):
    import cv2
    src = cache/item['path']
    if not src.is_file(): return None
    digest = hashlib.sha256(src.read_bytes()).hexdigest()
    target = DEST/'media'/f'{digest[:20]}.mp4'
    poster = target.with_suffix('.jpg')
    target.parent.mkdir(exist_ok=True)
    if not target.exists(): shutil.copy2(src, target)
    cap = cv2.VideoCapture(str(target))
    fps = cap.get(cv2.CAP_PROP_FPS)
    expected = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    n = 0; mid = None; width = height = 0
    while True:
        ok, frame = cap.read()
        if not ok: break
        height, width = frame.shape[:2]
        if n == expected//2: mid = frame.copy()
        n += 1
    cap.release()
    if n != expected or n == 0 or mid is None:
        raise ValueError(f'Incomplete decode {item["key"]}: {n}/{expected}')
    cv2.imwrite(str(poster), mid, [cv2.IMWRITE_JPEG_QUALITY, 85])
    return {k: item[k] for k in ['key', 'case', 'run', 'dataset']} | {
        'video': str(target.relative_to(DEST)), 'poster': str(poster.relative_to(DEST)),
        'sha256': digest, 'bytes': target.stat().st_size,
        'frames': n, 'fps': fps, 'width': width, 'height': height, 'full_decode_verified': True}


def main():
    p = argparse.ArgumentParser(); p.add_argument('snapshot', type=Path)
    p.add_argument('--cache', type=Path); args = p.parse_args()
    bundle = json.loads(args.snapshot.read_text()); d = bundle['public']; media = {}
    old = DEST/'data/media.json'
    if old.exists(): media = json.loads(old.read_text())
    if args.cache:
        todo = [t for t in bundle['transfer'] if t['key'] not in media]
        with ThreadPoolExecutor(max_workers=4) as pool:
            for i, rec in enumerate(pool.map(lambda t: import_video(t, args.cache), todo), 1):
                if rec: media[rec['key']] = rec
                if i % 30 == 0: print('Verified media', i, '/', len(todo), flush=True)
    write(old, media)
    items = []
    for c in d['cases']:
        for a in c['attempts']:
            if a.get('media_key') in media: a['media'] = media[a['media_key']]
            a['has_failure'] = bad(a)
        # Latest scalar-camera protocol first, then full reconstructions, then old runs.
        c['attempts'].sort(key=lambda a: ('scalar_20260921_v2' not in a['run'],
                                          'phase2_20260921_v2' not in a['run'], a['run']))
        visual = [a for a in c['attempts'] if a.get('media')]
        timeline = next((a['timeline'] for a in c['attempts'] if a.get('timeline')), None)
        write(DEST/'data/cases'/f'{c["id"]}.json', c)
        tested = any(a.get('status') in ['complete', 'completed', 'failed'] and a['method'] != 'Detector diagnostic' for a in c['attempts'])
        items.append({k: c[k] for k in ['id', 'dataset', 'family', 'activity', 'evidence_tier'] if k in c} | {
            'tested': tested,
            'attempts': len(c['attempts']), 'methods': sorted(set(a['method'] for a in c['attempts'])),
            'failures': sum(a['has_failure'] for a in c['attempts']),
            'prep_failures': sum(bool(p.get('error')) or p.get('status') == 'failed' for p in c['preparations']),
            'has_reference': any(s['protocol'] != 'no-GT-operational-diagnostics' and s.get('status') in ['scored', 'complete']
                                 for a in c['attempts'] for s in a['scores']),
            'videos': len(visual), 'poster': visual[0]['media']['poster'] if visual else None,
            'timeline': timeline,
            'preparations': len(c['preparations']), 'detector': bool(c.get('detector')),
        })
    # Separate prepared-only entries from actual evaluated items.
    datasets = []
    for name in sorted(set(c['family'] for c in items)):
        rows = [c for c in items if c['family'] == name]
        datasets.append({'name': name, 'cases': len(rows), 'tested': sum(c['tested'] for c in rows),
                         'videos': sum(c['videos'] for c in rows), 'failures': sum(c['failures'] > 0 or c['prep_failures'] > 0 for c in rows)})
    totals = {'datasets': len(datasets), 'cases': len(items), 'tested_cases': sum(c['tested'] for c in items),
              'attempts': sum(c['attempts'] for c in items), 'video_entries': sum(c['videos'] for c in items),
              'unique_videos': len(set(m['video'] for m in media.values())),
              'timeline_attempts': sum('timeline' in a for c in d['cases'] for a in c['attempts']),
              'failed_attempts': sum(c['failures'] for c in items),
              'no_run_cases': sum(not c['tested'] for c in items)}
    write(DEST/'data/index.json', {'snapshot_utc': d['snapshot_utc'], 'totals': totals, 'datasets': datasets, 'cases': items})
    write(DEST/'data/provenance.json', {k: d[k] for k in ['schema', 'scope', 'snapshot_utc', 'runs', 'manifests', 'artifact_sha256', 'scorer_checks'] if k in d})
    print(json.dumps(totals, ensure_ascii=False, indent=2))


if __name__ == '__main__': main()

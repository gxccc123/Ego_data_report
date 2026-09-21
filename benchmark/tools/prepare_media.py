"""Decode published previews end-to-end and select midpoint video posters.

Optional maintenance dependency: OpenCV. No model or dataset download occurs.
"""
import hashlib
import json
from pathlib import Path
import cv2

ROOT = Path(__file__).resolve().parents[1]
rows = []
for path in sorted((ROOT/'assets').glob('*.mp4')):
    cap = cv2.VideoCapture(str(path))
    fps = cap.get(cv2.CAP_PROP_FPS)
    count = 0; midpoint = None
    while True:
        ok, frame = cap.read()
        if not ok: break
        if count == 160: midpoint = frame.copy()
        count += 1
    cap.release()
    assert count == 321 and abs(fps-30) < .01, (path.name, count, fps)
    assert midpoint is not None
    assert cv2.imwrite(str(path.with_suffix('.jpg')), midpoint)
    rows.append(dict(file=path.name, frames=count, fps=fps, width=int(midpoint.shape[1]), height=int(midpoint.shape[0]),
                     bytes=path.stat().st_size, sha256=hashlib.sha256(path.read_bytes()).hexdigest(),poster_frame=160))
(ROOT/'assets/media-audit.json').write_text(json.dumps(rows,indent=2)+'\n')
print(f'PASS: {len(rows)} previews fully decoded; fixed midpoint posters saved')

"""Resume exact allowlisted research previews with bounded parallel rsync."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path, PurePosixPath
import subprocess


def main():
    p=argparse.ArgumentParser();p.add_argument('snapshot',type=Path);p.add_argument('host')
    p.add_argument('remote_root');p.add_argument('cache',type=Path);p.add_argument('--workers',type=int,default=4)
    a=p.parse_args();rows=json.loads(a.snapshot.read_text())['transfer'];pending=[]
    for row in rows:
        path=PurePosixPath(row['path'])
        if path.is_absolute() or '..' in path.parts or path.parts[0]!='runs' or path.suffix!='.mp4':
            raise ValueError('Invalid transfer path')
        target=a.cache/row['path']
        if not target.exists() or target.stat().st_size!=row['bytes']:pending.append(row['path'])
    a.cache.mkdir(parents=True,exist_ok=True)
    def transfer(i):
        paths=pending[i::a.workers]
        listing=a.cache.parent/f'transfer-{i}.txt';listing.write_text('\n'.join(paths)+'\n')
        if not paths:return
        subprocess.run(['rsync','-a',f'--files-from={listing}','-e','ssh -o ControlPath=none -o BatchMode=yes',
                         a.host+':'+a.remote_root.rstrip('/')+'/',str(a.cache)+'/'],check=True)
        print(f'Shard {i+1}: {len(paths)} files transferred',flush=True)
    print(f'{len(pending)} pending / {len(rows)} allowlisted files',flush=True)
    with ThreadPoolExecutor(max_workers=a.workers) as pool:list(pool.map(transfer,range(a.workers)))


if __name__=='__main__':main()

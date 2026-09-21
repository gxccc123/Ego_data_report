"""Read-only, explicit-whitelist exporter. Run on the benchmark host.

Prints {public, transfer}; transfer contains relative media paths and MUST stay
outside the published tree. No checkpoint, raw annotation or MANO assets copied.
"""
import argparse
import collections
import hashlib
import json
import math
from pathlib import Path
import re
import time


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def clean(value):
    if isinstance(value, dict):
        return {k: clean(v) for k, v in value.items()}
    if isinstance(value, list):
        return [clean(v) for v in value]
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def numeric(value):
    """Numeric metric trees only: never copy tracebacks or private paths."""
    if isinstance(value, dict):
        return {k: numeric(v) for k, v in value.items()
                if isinstance(v, (dict, int, float, bool)) or v is None}
    return clean(value)


def error_class(text):
    text = str(text).lower()
    for needles, label in [
        (['nonfinite', 'non-finite', 'nan'], 'non_finite_geometry'),
        (['context has already'], 'multiprocessing_context'),
        (['out of memory'], 'out_of_memory'),
        (['no such file', 'not found', 'filenotfound'], 'missing_file'),
        (['decode', 'ffmpeg', 'moov'], 'video_decode'),
        (['cuda'], 'cuda_error'), (['timeout'], 'timeout'),
        (['no hand', 'empty'], 'empty_hand_or_track'),
    ]:
        if any(n in text for n in needles):
            return label
    return 'other_error' if text and text != 'none' else None


def family(dataset):
    for prefix, name in [('SHOW3D', 'SHOW3D'), ('EgoTactile', 'EgoTactile'),
                         ('Ego-EXTRA', 'Ego-EXTRA'), ('HOT3D', 'HOT3D'),
                         ('Ego-Exo4D', 'Ego-Exo4D'), ('EgoDex', 'EgoDex'),
                         ('EgoProceL', 'EgoProceL'), ('Xperience', 'Xperience-10M')]:
        if dataset.startswith(prefix):
            return name
    return dataset


def method(tag):
    for prefix, name in [('ace_kfree', 'ACE · K-free'), ('ace_k', 'ACE · known-K'),
                         ('hawor_full', 'HaWoR · full'), ('hawor_camera', 'HaWoR · camera'),
                         ('ola_hand', 'OLA · hand'), ('mint', 'MINT')]:
        if tag.startswith(prefix):
            return name
    return 'Detector diagnostic'


def main():
    p = argparse.ArgumentParser(); p.add_argument('--root', type=Path, required=True)
    p.add_argument('--timelines', action='store_true'); args = p.parse_args(); root = args.root
    cases, runs, manifests, transfers = {}, {}, [], []
    artifacts = {}

    def read(path):
        try:
            obj = json.loads(path.read_text())
            artifacts[str(path.relative_to(root))] = sha(path)
            return obj
        except (OSError, ValueError):
            return {}

    def case(cid, dataset=None):
        if cid not in cases:
            guessed = {'show3d': 'SHOW3D', 'hot3d': 'HOT3D', 'egoexo': 'Ego-Exo4D',
                       'egotactile': 'EgoTactile', 'genegodata': 'JD-Gen-EgoData',
                       'openaoe': 'Open-AoE', 'egoextra': 'Ego-EXTRA',
                       'xperience': 'Xperience-10M'}.get(cid.split('-')[0], 'Unmapped')
            cases[cid] = {'id': cid, 'dataset': dataset or guessed, 'preparations': [], 'attempts': []}
        return cases[cid]

    for path in sorted(list((root/'suites').glob('*/manifest.json')) + list((root/'data').glob('*/manifest.json'))):
        d = read(path); tag = path.parent.name
        manifests.append({'id': tag, 'sha256': sha(path), 'entries': len(d.get('clips', []))})
        for row in d.get('clips', []):
            cid = row.get('id')
            if not cid: continue
            c = case(cid, row.get('dataset'))
            meta_keys = ['dataset', 'activity', 'scene_id', 'source_split', 'evidence_tier', 'split_status']
            for key in meta_keys:
                if row.get(key) is not None: c[key] = row[key]
            prep = {k: row[k] for k in ['status', 'frames', 'fps', 'size', 'input_sha256',
                    'intrinsics_status', 'gt_frame_alignment_gate'] if k in row}
            prep['suite'] = tag
            indices = row.get('source_frame_indices', [])
            if indices: prep['source_frame_range'] = [indices[0], indices[-1]]
            if row.get('error'): prep['error'] = error_class(row['error'])
            c['preparations'].append(clean(prep))

    folders = sorted(p for p in (root/'runs').iterdir() if p.is_dir())
    parent = {}
    statuses = {}
    for folder in folders:
        docs = [(p, read(p)) for p in sorted(folder.glob('worker_*.json'))]
        if (folder/'status.json').exists(): docs.append((folder/'status.json', read(folder/'status.json')))
        statuses[folder.name] = docs
        target = next((Path(d['input_run']).name for _, d in docs if isinstance(d, dict) and d.get('input_run')), None)
        if folder.name.endswith('_geometry'): target = target or folder.name[:-9]
        if '_mano_' in folder.name:
            target = target or folder.name.replace('_mano_', '_').replace('mint_hot3d_v1', 'mint_hot3d_public_v1')
        if target: parent[folder.name] = target

    # Each inference folder is a distinct attempt. Decoding attaches to its parent.
    index = {}
    def attempt(tag, cid):
        canonical = parent.get(tag, tag)
        key = (canonical, cid)
        if key not in index:
            obj = {'run': canonical, 'method': method(canonical), 'status': 'record_only', 'scores': []}
            index[key] = obj; case(cid)['attempts'].append(obj)
        return index[key]

    safe_run = ['repo_commit', 'checkpoint_sha256', 'config_sha256', 'script_sha256',
                'suite_sha256', 'torch', 'cuda', 'status', 'model_load_s', 'elapsed_s', 'evidence_tier']
    safe_record = ['status', 'frames', 'input_fps', 'input_sha256', 'video_sha256', 'warm_median_fps',
                   'decode_s', 'preprocess_inference_s', 'vae_encode_s', 'predict_s',
                   'total_s', 'total_decode_encode_predict_save_s', 'total_decode_predict_save_s', 'peak_allocated_gib',
                   'peak_reserved_gib', 'pnp_accept_fraction', 'camera_only', 'raw_hand_frames',
                   'track_side_frames', 'predict_side_frames']
    for folder in folders:
        tag = folder.name; docs = statuses[tag]
        run = {'id': tag, 'kind': 'decoder' if tag in parent else 'inference',
               'method': method(parent.get(tag, tag)), 'parent': parent.get(tag), 'record_count': 0}
        records = {}
        for path, d in docs:
            if not isinstance(d, dict): continue
            run.update({k: d[k] for k in safe_run if k in d})
            for row in d.get('clips', d.get('predictions', [])):
                cid = row.get('id') or ('hot3d-author-episode-%03d' % row['episode'] if 'episode' in row else None)
                if cid:
                    records[cid] = row
                    if 'episode' in row: case(cid, 'HOT3D-author-sample')
        for path in sorted(folder.glob('*/result.json')):
            d = read(path)
            if d.get('id'): records.setdefault(d['id'], {}).update(d)
        for cid, row in records.items():
            if row.get('dataset'): case(cid, row['dataset'])
            a = attempt(tag, cid)
            payload = {k: row[k] for k in safe_record if k in row}
            if 'episode' in row: payload['status'] = 'complete'
            for k in ['stage_times_s', 'timings', 'native_nonfinite']:
                if isinstance(row.get(k), dict): payload[k] = numeric(row[k])
            if row.get('error'): payload['error'] = error_class(row['error'])
            if tag in parent:
                a.setdefault('decoders', []).append({'run': tag, **payload})
            else:
                a.update(payload)
            if 'track_side_frames' in row or 'predict_side_frames' in row:
                a['scores'].append({'protocol': 'no-GT-operational-diagnostics',
                    'artifact': 'runs/'+tag+'/status.json', 'status': 'diagnostic_complete',
                    'metrics': {k: row[k] for k in ['track_side_frames', 'predict_side_frames'] if k in row}})
            if row.get('passes'):
                a['timing_passes'] = [{k: v for k, v in item.items() if isinstance(v, (int, float))}
                                       for item in row['passes']]
        run['record_count'] = len(records); runs[tag] = run

    scoring = {
        'show3d_reference_summary.json': 'SHOW3D-v2-reference',
        'sparse_reference_summary.json': 'EgoExo-sparse-reference',
        'official_metric_summary.json': 'EgoExo-official-metric-adapter',
        'hand_reference_summary.json': 'HOT3D-hand-reference',
        'broad_diagnostics.json': 'no-GT-operational-diagnostics',
        'camera_diagnostic.json': 'HOT3D-author-camera-diagnostic',
    }
    metric_keys = ['metrics', 'stats', 'counts', 'conditional', 'camera',
                   'MPJPE_mm', 'PA_MPJPE_mm', 'hand_frames', 'invalid_hands',
                   'predicted_present_handframes', 'possible_handframes', 'predicted_presence_pct',
                   'positive_joint_depth_pct', 'projected_joints_inside_image_pct',
                   'wrist_depth_m', 'camera_frame_wrist_speed_mps', 'presence_transitions',
                   'ATE_SE3_fixed_scale_mm', 'ATE_Sim3_rescaled_mm', 'RPE_SE3_translation_mm',
                   'RPE_rotation_deg', 'fitted_scale_diagnostic', 'gt_path_m', 'pred_path_m']
    for folder in folders:
        for filename, protocol in scoring.items():
            path = folder/filename
            if not path.exists(): continue
            d = read(path)
            for row in d.get('clips', d.get('episodes', [])):
                cid = row.get('id') or ('hot3d-author-episode-%03d' % row['episode'] if 'episode' in row else None)
                if not cid: continue
                a = attempt(folder.name, cid)
                score = {'protocol': protocol, 'artifact': str(path.relative_to(root)),
                         'status': row.get('status', 'scored')}
                score.update({k: numeric(row[k]) for k in metric_keys if k in row})
                a['scores'].append(score)
        if folder.name.startswith('hawor_full') and (folder/'analysis.json').exists():
            path = folder/'analysis.json'; d = read(path)
            for row in d.get('clips', []):
                if not row.get('id'): continue
                a = attempt(folder.name, row['id'])
                a['validation_status'] = row.get('status')
                for stage in ['raw', 'full']:
                    if stage+'_metrics' in row:
                        a['scores'].append({'protocol': 'full-pipeline-'+stage, 'artifact': str(path.relative_to(root)),
                                            'status': row.get('status'), 'metrics': numeric(row[stage+'_metrics']),
                                            'stats': numeric(row.get(stage+'_stats', {}))})
                a['full_validation'] = {k: numeric(row[k]) for k in ['native_nonfinite', 'world_geometry_finite',
                     'filled_handframes', 'observed_handframes', 'observed_both_frames'] if k in row}
                if row.get('error'): a['validation_error'] = error_class(row['error'])

    # Per-clip four-setting detector counts, never claim these are GT recall.
    detector_dir = root/'audit/detector_grid_phase2_20260921_v1'
    for path in sorted(detector_dir.glob('*.boxes.json')):
        cid = path.name[:-11]; d = read(path); out = {}
        for setting, rows in d.items():
            out[setting] = {'sampled_frames': len(rows), 'frames': []}
            for row in rows:
                if isinstance(row, dict):
                    entry = {k: numeric(v) for k, v in row.items()
                             if isinstance(v, (int, float, bool)) and not k.startswith('path')}
                    entry['box_count'] = len(row.get('classes', []))
                    entry['classes'] = row.get('classes', [])
                    entry['scores'] = clean(row.get('scores', []))
                    out[setting]['frames'].append(entry)
        case(cid)['detector'] = out

    # Retain every discovered paired wrist-proxy evaluation separately. Different
    # method sets imply different intersections; these are not interchangeable.
    for path in sorted((root/'audit').glob('*/paired_egodex_proxy.json')):
        d = read(path)
        for row in d.get('clips', []):
            cid = row['id']; c = case(cid)
            if row.get('task'): c['activity'] = row['task']
            for name, values in row.get('methods', {}).items():
                a = attempt(name+'_broad_20260921_v1', cid)
                a['scores'].append({'protocol': 'EgoDex-wrist-proxy-'+path.parent.name,
                    'artifact': str(path.relative_to(root)), 'status': 'scored',
                    'reference_handframes': row['reference_handframes'],
                    'common_handframes': row['common_handframes'], 'metrics': numeric(values)})

    # Public media: audited dataset-license allowlist; all completed previews,
    # including historical variants. Exact duplicates are deduplicated locally.
    for folder in folders:
        tag = folder.name
        for geom in sorted(folder.glob('*/geometry.npz')):
            cid = geom.parent.name; a = attempt(tag, cid); c = case(cid)
            if args.timelines:
                try:
                    import numpy as np
                    with np.load(geom, allow_pickle=False) as z:
                        present = z['predicted_present'].astype(bool)
                        joints = z['joints_cam']
                        depths = joints[:, :, 0, 2]
                    groups = np.array_split(np.arange(len(present)), min(48, len(present)))
                    a['timeline'] = {'frames': len(present), 'space': 'camera', 'bins': [
                        {'start': int(g[0]), 'end': int(g[-1]),
                         'presence': [round(float(present[g, h].mean()), 3) for h in range(2)],
                         'depth_m': [round(float(np.median(depths[g, h][present[g, h] & np.isfinite(depths[g, h])])), 3)
                          if np.any(present[g, h] & np.isfinite(depths[g, h])) else None for h in range(2)]}
                        for g in groups]}
                except Exception as exc:
                    a['timeline_status'] = error_class(str(exc)) or 'unavailable'
            video = geom.parent/'mesh_preview.mp4'
            complete = (geom.parent/'_MESH_VIS_COMPLETE').exists() and video.exists()
            a['local_visualization'] = complete or a.get('local_visualization', False)
            allowed = family(c['dataset']) in ['SHOW3D', 'EgoTactile', 'Open-AoE']
            if complete and allowed:
                media_id = hashlib.sha256(str(video.relative_to(root)).encode()).hexdigest()[:20]
                a['media_key'] = media_id
                transfers.append({'key': media_id, 'path': str(video.relative_to(root)),
                                  'bytes': video.stat().st_size, 'case': cid, 'run': parent.get(tag, tag),
                                  'dataset': family(c['dataset'])})

    for c in cases.values():
        c['family'] = family(c['dataset'])
        c['attempts'].sort(key=lambda a: a['run'])
        c['media_policy'] = 'licensed-research-preview' if c['family'] in ['SHOW3D', 'EgoTactile', 'Open-AoE'] else 'RGB-not-cleared-for-republication'
    data = {'schema': 1, 'snapshot_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            'scope': 'All discovered suite/data manifests and run folders under the scoped benchmark root; no live-job claim.',
            'cases': sorted(cases.values(), key=lambda c: (c['family'], c['id'])),
            'runs': list(runs.values()), 'manifests': manifests, 'artifact_sha256': artifacts}
    encoded = json.dumps(clean(data), ensure_ascii=False, allow_nan=False)
    for forbidden in ['/root/', '/Users/', 'BEGIN PRIVATE KEY', '182.242.']:
        assert forbidden not in encoded, forbidden
    print(json.dumps({'public': clean(data), 'transfer': transfers}, ensure_ascii=False, allow_nan=False))


if __name__ == '__main__': main()

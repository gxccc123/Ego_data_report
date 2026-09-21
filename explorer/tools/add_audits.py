"""Add frozen per-case paired audits without overwriting inference outcomes."""
import argparse
import hashlib
import json
from pathlib import Path


def main():
    p=argparse.ArgumentParser();p.add_argument('snapshot',type=Path);p.add_argument('audit_root',type=Path)
    a=p.parse_args();bundle=json.loads(a.snapshot.read_text());d=bundle['public']
    cases={c['id']:c for c in d['cases']}
    files=['expansion_20260921/show3d_original_paired.json',
           'expansion_20260921/show3d_scalar_paired.json',
           'expansion_20260921/egoexo_common_three.json']
    for rel in files:
        path=a.audit_root/rel; source='audit/'+rel
        if not path.exists():continue
        audit=json.loads(path.read_text());d['artifact_sha256'][source]=hashlib.sha256(path.read_bytes()).hexdigest()
        for row in audit.get('clips',[]):
            c=cases[row['id']]
            if row.get('task_name'):c['activity']=row['task_name']
            for tag,stats in row['stats'].items():
                if rel.endswith('egoexo_common_three.json'):tag+='_egoexo_unseen_v1'
                attempt=next((x for x in c['attempts'] if x['run']==tag),None)
                if not attempt:raise ValueError('Paired result has no matching attempt: '+tag)
                protocol='paired-common-TP-'+path.stem
                attempt['scores']=[s for s in attempt['scores'] if s['protocol']!=protocol]
                n=stats['tp_joints'];pa=stats['pa_joint_count'];w=stats['wrist_count']
                metrics={'common_camera_MPJPE_mm':stats['abs_error_sum_mm']/n if n else None,
                         'common_root_relative_MPJPE_mm':stats['root_relative_error_sum_mm']/n if n else None,
                         'common_PA_MPJPE_mm':stats['pa_error_sum_mm']/pa if pa else None,
                         'common_wrist_error_mm':stats['wrist_error_sum_mm']/w if w else None}
                attempt['scores'].append({'protocol':protocol,'artifact':source,'status':'scored' if n else 'no_common_TP',
                                          'stats':stats,'metrics':metrics})
    path=a.audit_root/'hawor_full_outcomes.json'
    if path.exists():
        source='audit/'+path.name;d['artifact_sha256'][source]=hashlib.sha256(path.read_bytes()).hexdigest()
        for row in json.loads(path.read_text())['clips']:
            attempt=next(x for x in cases[row['id']]['attempts'] if x['run']=='hawor_full_hot3d_v5')
            attempt['validation_status']=row['status']
            if row.get('error'):attempt['validation_error']='non_finite_geometry'
            attempt['full_validation']={k:row[k] for k in ['raw_both_hands_valid_frames','raw_geometry_finite',
                'native_post_infiller','post_infiller_valid_hand_frames'] if k in row}
            attempt['full_validation_artifact']=source
    # Publish scorer sanity checks as checks, never count them as model cases.
    path=a.audit_root/'hand_metric_gates.json'
    if path.exists():
        check=json.loads(path.read_text());d['scorer_checks']={k:check[k] for k in ['status','gates','self','translated_10cm','all_missing','note']}
        d['artifact_sha256']['audit/'+path.name]=hashlib.sha256(path.read_bytes()).hexdigest()
    a.snapshot.write_text(json.dumps(bundle,ensure_ascii=False,allow_nan=False))
    print('Paired audits and scorer checks attached; inference records unchanged.')


if __name__=='__main__':main()

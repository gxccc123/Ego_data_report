"""Build the static report from reviewed prose and sanitized measured results."""
import html
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def fmt(v):
    return f"{v:,.2f}" if isinstance(v, (float, int)) else str(v)


def table(caption, headers, rows):
    escape = lambda v: html.escape(fmt(v))
    return '<div class="table-wrap"><table><caption>' + html.escape(caption) + '</caption><thead><tr>' + ''.join('<th scope="col">'+html.escape(h)+'</th>' for h in headers) + '</tr></thead><tbody>' + ''.join('<tr>'+''.join('<td>'+escape(v)+'</td>' for v in row)+'</tr>' for row in rows) + '</tbody></table></div>'


def metric_rows(data):
    rows = []
    for key, v in data["summary"].items():
        name = next(n for prefix, n in [("ace_kfree", "ACE · K-free"), ("ace_k", "ACE · K-given"), ("hawor", "HaWoR · hand"), ("ola", "OLA · hand"), ("mint", "MINT")] if key.startswith(prefix))
        a = data["original_all_reference"][key]
        coverage = a.get("coverage_on_reference_pct", a.get("hand_recall_pct"))
        pck = a.get("absolute_PCK_50mm_all_reference_pct", a.get("absolute_PCK_50mm_allGT_pct"))
        rows.append([name, coverage, v["camera_MPJPE_mm_TP"], v["root_relative_MPJPE_mm_TP"], v["PA_MPJPE_mm_TP"], pck])
    return rows


def main():
    d = json.loads((ROOT / 'assets/results.json').read_text())
    f = d['full_hawor_show3d']
    assert f['complete'] and f['processed'] == 12
    headers = ["方法", "全参考输出覆盖 % ↑", "共同集 Camera mm ↓", "共同集 RR mm ↓", "共同集 PA mm ↓", "全参考 PCK50 % ↑"]
    fragments = {
        'timestamp': datetime.fromisoformat(d['snapshot_utc'].replace('Z', '+00:00')).astimezone(timezone(timedelta(hours=8))).strftime('%Y-%m-%d %H:%M:%S（UTC+8）'),
        'show_table': table('表 3 · SHOW3D：共同输出集误差 + 各方法全参考覆盖 / PCK', headers, metric_rows(d['show3d'])),
        'ego_table': table('表 4 · Ego-Exo4D：三个高覆盖分支的共同输出集', headers, metric_rows(d['egoexo'])),
        'full_finite': str(f['finite_complete']), 'full_failed': str(12-f['finite_complete']), 'full_visualized': str(f['visualized']),
    }
    rows = []
    for dataset, settings in d['detector']['aggregate'].items():
        for key, v in settings.items():
            rows.append([dataset, key.replace('size','').replace('_conf',' / '), str(v['sampled_frames']), str(v['predicted_slots']), f"{v['covered_reference_slots']} / {v['reference_slots']}", 100*v['covered_reference_slots']/v['reference_slots']])
    fragments['detector_table'] = table('表 5 · 检测器参数敏感性：帧 × 左右手槽位，不是空间框匹配 recall', ['数据域','尺寸 / 置信门槛','采样帧','预测槽位','覆盖参考槽位','槽位覆盖 % ↑'], rows)
    rows = []
    for k, v in f['summary'].items():
        rows.append([k, v['hand_recall_pct'], v['camera_MPJPE_mm_TP'], v['root_relative_MPJPE_mm_TP'], v['PA_MPJPE_mm_TP'], v['absolute_PCK_50mm_allGT_pct']])
    fragments['full_table'] = table('表 6 · 12 段完整 HaWoR：世界输出变回相机系后的参考一致性', ['阶段 / 集合','全参考覆盖 % ↑','Camera mm ↓','RR mm ↓','PA mm ↓','全参考 PCK50 % ↑'], rows)
    rows = [[c['id'].replace('show3d-',''), '有效完成' if c['status']=='complete' else '非有限数值', str(c['observed_handframes']), str(c['observed_both_frames']), str(c.get('filled_handframes','—'))] for c in f['clips']]
    fragments['full_cases'] = table('表 7 · 固定 12 个案例逐项审计（观察 / 补全数含无参考帧）', ['片段 ID','状态','观察手帧','同时观察双手帧','补全手帧'], rows)
    rows = []
    for key, v in d['egodex_wrist_proxy']['timing'].items():
        rows.append([key, str(v['clips']), v['median_clip_s'], v['peak_allocated_gib_max'], '含逐片段重复加载；非等价计时' if key in ['hawor_camera','ola_hand'] else '常驻模型；解码 / 推理 / 保存'])
    fragments['timing_table'] = table('表 8 · 单 H100 的测量成本；不是等配置速度榜', ['分支','片段数','中位耗时 s / 片段','峰值分配 GiB','计时范围'], rows)
    rows = [[k,v['own_coverage_on_reference_pct'],v['common_wrist_proxy_mm']] for k,v in d['egodex_wrist_proxy']['summary'].items()]
    fragments['proxy_table'] = table('附表 · EgoDex：ARKit 腕部代理，不是 21 关节独立真值', ['方法','全参考输出覆盖 %','共同集腕部代理误差 mm'],rows)
    rows = []
    for dataset, obj in [('SHOW3D',d['show3d']), ('Ego-Exo4D',d['egoexo'])]:
        for comparison, metrics in obj['subject_bootstrap']['differences'].items():
            if comparison.startswith('ola_'): continue
            label = 'ACE K-free − MINT' if comparison.startswith('ace_kfree') else 'ACE K-given − MINT' if comparison.startswith('ace_k_') else 'HaWoR hand − MINT'
            for metric,v in metrics.items():
                if metric not in ['camera_MPJPE_mm','root_relative_MPJPE_mm','PA_MPJPE_mm']: continue
                rows.append([dataset,label,metric.replace('_MPJPE_mm',''),v['difference'],f"[{v['ci95'][0]:.2f}, {v['ci95'][1]:.2f}]"])
    fragments['ci_table'] = table('附表 · 配对差值与受试者 bootstrap 95% 区间；负数意味着前者误差更低', ['数据域','比较','误差类型','差值 mm','95% 区间 mm'],rows)
    fragments['versions'] = table('附表 · 固定代码版本（实验时版本，不跟随 upstream 最新分支）', ['方法','版本'], list(d['method_commits'].items()))
    text = (ROOT / 'report.template.html').read_text()
    used = set(re.findall(r'\{\{([a-z_]+)\}\}', text))
    assert used == set(fragments), (used-set(fragments),set(fragments)-used)
    for k,v in fragments.items(): text = text.replace('{{'+k+'}}',v)
    assert '{{' not in text
    (ROOT / 'index.html').write_text(text)
    print('Built static benchmark/index.html from reviewed source and measured aggregates')


if __name__ == '__main__':
    main()

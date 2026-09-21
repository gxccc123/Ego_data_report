'use strict';
const $ = s => document.querySelector(s);
const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const number = (v, digits=2) => typeof v === 'number' && Number.isFinite(v) ? v.toLocaleString('en-US',{maximumFractionDigits:digits,minimumFractionDigits:digits}) : '未评分';
let archive, filtered = [], page = 0, selected = null, renderToken = 0;
const pageSize = 24;
const stateText = {complete:'推理完成',completed:'完成',failed:'失败',input_failed:'输入失败',error:'错误',decoded:'已解码',prepared:'已准备',record_only:'仅诊断 / 后处理记录',skipped:'跳过',scored:'已评分',unavailable:'不可用',no_reference:'无参考',no_public_reference:'无公开参考',no_geometry:'无有效几何',no_common_TP:'无共同有效预测',diagnostic_complete:'诊断完成'};
const errText = {non_finite_geometry:'几何含 NaN / Inf',multiprocessing_context:'多进程上下文冲突',out_of_memory:'显存不足',missing_file:'缺少输入文件',video_decode:'视频解码失败',cuda_error:'CUDA 错误',timeout:'超时',empty_hand_or_track:'缺少手 / 轨迹',other_error:'其他错误（原始日志留在受控存储）'};
const evidence = {
  'SHOW3D':'使用 v2 单目追踪参考；不是独立动作捕捉真值。train / test 子集明确区分；部分 test 案例无参考评分。',
  'Ego-Exo4D':'稀疏手工标注。只在标注有效处评分；未知标签不等于没手。official-metric-adapter 与 presence-conditioned 协议分开保留。',
  'HOT3D':'公开训练子集与作者演示样例分开。训练重叠可能存在，不能作为严格未见数据结论。',
  'EgoDex':'若有手腕参考，仅作为 wrist proxy；不能替代手指 / MANO 的独立 3D 精度。',
  'EgoTactile':'裸手与手套的跨域压力测试；本轮未加载独立 3D 手部真值。',
  'Open-AoE':'手机第一视角压力测试。原算法生成的 MANO 不能直接当作独立真值。',
  'JD-Gen-EgoData':'去畸变 / pinhole 与恢复版本分别保留。本轮没有独立 3D GT；不等于已取得 EgoLive 完整集。',
  'Xperience-10M':'同一公开原视频采出的多个片段，不是多个独立 episode。VFR / 对齐门禁使手部参考评分禁用。'
};

function timelineSVG(t, compact=false) {
  if (!t?.bins?.length) return '';
  const W=800,H=compact?160:240,left=compact?30:62,right=18,plot=W-left-right, bins=t.bins;
  let parts=[`<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="左右手预测出现比例与相机手腕深度时间线">`];
  const colors=['#247d99','#c17636'];
  for(let h=0;h<2;h++) {
    const y=16+h*22;
    if(!compact) parts.push(`<text x="2" y="${y+12}" font-size="12" fill="#62716a">${h?'右手':'左手'}</text>`);
    bins.forEach((b,i)=>parts.push(`<rect x="${left+i*plot/bins.length}" y="${y}" width="${plot/bins.length+.2}" height="16" fill="${colors[h]}" opacity="${.10+.90*(b.presence[h]??0)}"><title>帧 ${b.start}–${b.end}，${h?'右':'左'}手预测出现 ${number(100*b.presence[h],0)}%</title></rect>`));
  }
  const values=bins.flatMap(b=>b.depth_m).filter(v=>v!==null && Number.isFinite(v));
  const max=values.length?Math.max(...values):1,min=values.length?Math.min(...values):0;
  const span=Math.max(max-min,.05),top=compact?77:94,bottom=H-24;
  [0,.5,1].forEach(f=>{let y=bottom-f*(bottom-top);parts.push(`<line x1="${left}" y1="${y}" x2="${W-right}" y2="${y}" stroke="#dae2db"/>`);if(!compact)parts.push(`<text x="0" y="${y+4}" font-size="11" fill="#62716a">${number(min+span*f)} m</text>`);});
  for(let h=0;h<2;h++){
    let path='', connected=false;
    bins.forEach((b,i)=>{let v=b.depth_m[h];if(v===null||!Number.isFinite(v)){connected=false;return;}let x=left+(i+.5)*plot/bins.length,y=bottom-(v-min)/span*(bottom-top);path+=`${connected?'L':'M'}${x.toFixed(1)},${y.toFixed(1)} `;connected=true;});
    parts.push(`<path d="${path}" fill="none" stroke="${colors[h]}" stroke-width="2.2"/>`);
  }
  if(!compact)parts.push(`<text x="${left}" y="${H-4}" font-size="11" fill="#62716a">输入帧 0</text><text text-anchor="end" x="${W-right}" y="${H-4}" font-size="11" fill="#62716a">${t.frames-1}</text>`);
  parts.push('</svg>');return parts.join('');
}
function detectorChart(detector){
  return `<div class="camera-plots">${Object.entries(detector).map(([setting,d])=>{
    const counts=d.frames.map(x=>x.box_count??0),max=Math.max(2,...counts),W=520,H=130,pad=20;
    const bars=counts.map((v,i)=>`<rect x="${pad+i*(W-2*pad)/counts.length}" y="${100-v/max*70}" width="${(W-2*pad)/counts.length-1}" height="${v/max*70}" fill="#52816c"><title>输入帧 ${d.frames[i].frame}：${v} 个框</title></rect>`).join('');
    return `<figure><figcaption>${esc(setting)} · ${d.sampled_frames} 采样帧 · ${counts.reduce((a,b)=>a+b,0)} 个框</figcaption><svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(setting)} 逐帧检测框计数"><line x1="20" y1="100" x2="500" y2="100" stroke="#bdc9c0"/>${bars}<text x="20" y="122" fill="#62716a" font-size="12">采样时间 →（非 GT 召回）</text><text x="20" y="20" fill="#62716a" font-size="12">最大 ${max} 框 / 帧</text></svg></figure>`;
  }).join('')}</div>`;
}

function buildOverview(){
  const t=archive.totals;
  $('#snapshot').textContent=`快照 ${archive.snapshot_utc.replace('T',' ').replace('Z',' UTC')} · ${t.no_run_cases} 条仅有准备记录 · 同 ID 的历史版本合并浏览`;
  $('#totals').innerHTML=[['数据集来源',t.datasets],['已测 / 全部案例',`${t.tested_cases} / ${t.cases}`],['方法 × 案例实验记录',t.attempts],['去重后公开视频',t.unique_videos],['时序诊断记录',t.timeline_attempts]].map(([l,n])=>`<div class="total"><strong>${n}</strong><span>${l}</span></div>`).join('');
  $('#datasets').innerHTML=archive.datasets.map(d=>`<button type="button" class="dataset-button" data-dataset="${esc(d.name)}" aria-pressed="false"><strong>${esc(d.name)}</strong><span>${d.tested} 已测 / ${d.cases} 案例 · ${d.videos} 视频记录</span></button>`).join('');
  for(const d of archive.datasets) $('#dataset').add(new Option(`${d.name} (${d.cases})`,d.name));
  const methods=[...new Set(archive.cases.flatMap(c=>c.methods))].sort();
  for(const m of methods) $('#method').add(new Option(m,m));
}

function applyFilters(resetPage=true){
  if(resetPage) page=0;
  const query=$('#query').value.trim().toLowerCase(),dataset=$('#dataset').value,method=$('#method').value,status=$('#status').value;
  filtered=archive.cases.filter(c=>{
    if(dataset && c.family!==dataset || method&&!c.methods.includes(method))return false;
    if(query&&!`${c.id} ${c.dataset} ${c.family} ${c.activity||''}`.toLowerCase().includes(query))return false;
    if(status==='video'&&!c.videos || status==='reference'&&!c.has_reference || status==='failure'&&!c.failures&&!c.prep_failures || status==='notrun'&&c.tested)return false;
    return true;
  });
  const sort=$('#sort').value;
  filtered.sort((a,b)=> (sort==='media'?b.videos-a.videos:sort==='runs'?b.attempts-a.attempts:0)||a.family.localeCompare(b.family)||a.id.localeCompare(b.id));
  if(selected&&!filtered.some(c=>c.id===selected))closeCase();
  document.querySelectorAll('[data-dataset]').forEach(b=>b.setAttribute('aria-pressed',b.dataset.dataset===dataset));
  $('#match-count').textContent=`匹配 ${filtered.length} / ${archive.cases.length} 条案例。卡片合并同 ID 的实验版本，详细记录与分母在案例内查看。`;
  renderCards(); updateURL();
}

function renderCards(){
  const rows=filtered.slice(page*pageSize,(page+1)*pageSize);
  $('#cases').innerHTML=rows.map(c=>`<article class="case"><a href="#case=${encodeURIComponent(c.id)}" data-case="${esc(c.id)}">
    <div class="case-visual">${c.poster?`<img src="${esc(c.poster)}" alt="${esc(c.id)} 的模型叠加预览" loading="lazy" decoding="async">`:c.timeline?timelineSVG(c.timeline,true):'<div class="placeholder">暂无可公开的 RGB 预览<br>点击查看数值、状态与实验记录</div>'}</div>
    <div class="case-info"><div class="kicker">${esc(c.dataset)}</div><h3>${esc(c.id)}</h3>
    ${c.activity?`<p>${esc(c.activity)}</p>`:''}<p>${c.attempts} 次实验 · ${c.methods.length} 个方法分支 · ${c.videos} 视频记录</p>
    ${c.videos?'<span class="badge">可播放</span>':'<span class="badge neutral">RGB 未公开</span>'}
    ${c.has_reference?'<span class="badge">有参考评分记录</span>':'<span class="badge neutral">不作精度排名</span>'}
    ${c.failures||c.prep_failures?'<span class="badge warn">含失败 / 历史问题</span>':''}
    ${!c.tested?'<span class="badge warn">尚未进入模型推理</span>':''}</div></a></article>`).join('')||'<p class="empty">没有匹配案例。请调整筛选，不会隐藏未完成或失败记录。</p>';
  $('#page-count').textContent=`${page+1} / ${Math.max(1,Math.ceil(filtered.length/pageSize))}`;
  $('#prev').disabled=page===0;$('#next').disabled=(page+1)*pageSize>=filtered.length;
}

function updateURL(){
  const params=new URLSearchParams();for(const k of ['dataset','method','status','query'])if($('#'+k).value)params.set(k,$('#'+k).value);
  if(page)params.set('page',page+1);
  history.replaceState(null,'',`${location.pathname}${params.size?'?'+params:''}${selected?'#case='+encodeURIComponent(selected):''}`);
}
function flatten(obj,prefix=''){
  const rows=[];for(const [k,v] of Object.entries(obj||{})){const name=prefix?prefix+'.'+k:k;if(v&&typeof v==='object'&&!Array.isArray(v))rows.push(...flatten(v,name));else if(v===null||typeof v==='number'||typeof v==='boolean')rows.push([name,v]);}return rows;
}
function metricTable(obj){return `<div class="table-wrap"><table class="metric-list"><thead><tr><th>原始字段 / 协议单位</th><th>值</th></tr></thead><tbody>${flatten(obj).map(([k,v])=>`<tr><td>${esc(k)}</td><td class="number">${typeof v==='boolean'?(v?'true':'false'):number(v,4)}</td></tr>`).join('')}</tbody></table></div>`;}
function mainScore(a){
  return a.scores.find(s=>s.protocol==='full-pipeline-full')||a.scores.find(s=>['SHOW3D-v2-reference','EgoExo-sparse-reference'].includes(s.protocol))||a.scores.find(s=>s.protocol==='HOT3D-hand-reference');
}
function summaryRow(a,i){
  const s=mainScore(a),m=s?.metrics||{},cov=m.coverage_on_reference_pct??m.hand_recall_pct;
  const failure=a.has_failure, state=failure?(errText[a.validation_error||a.error]||'存在失败 / 校验问题'):(stateText[a.status]||a.status);
  return `<tr><td><a href="#attempt-${i}" data-jump="attempt-${i}">${esc(a.method)}</a><div class="runid">${esc(a.run)}</div></td><td class="${failure?'bad':''}">${esc(state)}${a.validation_status?`<br><span class="small">数值校验：${esc(a.validation_status)}</span>`:''}</td><td class="number">${number(cov)}</td><td class="number">${number(m.camera_MPJPE_mm_TP)}</td><td class="number">${number(m.root_relative_MPJPE_mm_TP)}</td><td class="number">${number(m.PA_MPJPE_mm_TP)}</td><td>${a.media?'视频':a.timeline?'时间线':'记录'}${s?`<div class="small">${esc(s.protocol)}</div>`:''}</td></tr>`;
}
function pairedTables(c){
  const groups=new Map();
  for(const a of c.attempts)for(const s of a.scores){
    if(!s.protocol.startsWith('paired-common-TP-')&&!s.protocol.startsWith('EgoDex-wrist-proxy-'))continue;
    if(!groups.has(s.protocol))groups.set(s.protocol,[]);groups.get(s.protocol).push({a,s});
  }
  if(!groups.size)return '';
  return `<details class="attempt-detail"><summary>共同有效集合上的逐案例配对结果 · ${groups.size} 个协议</summary><p class="small">每个表只比较该次协议内固定的方法集合。不同表的交集不同，仍不可跨表混排。分母为零时不产生误差值。</p>${[...groups].map(([protocol,rows])=>{
    const wrist=protocol.startsWith('EgoDex');
    return `<h4>${esc(protocol)}</h4><div class="table-wrap"><table><thead><tr><th>方法</th><th>共同手帧</th>${wrist?'<th>Wrist proxy · mm</th>':'<th>Camera · mm</th><th>Root-rel. · mm</th><th>PA · mm</th>'}</tr></thead><tbody>${rows.map(({a,s})=>`<tr><td>${esc(a.method)}</td><td>${s.common_handframes??s.stats?.detected_gt_hand_frames??'—'}</td>${wrist?`<td>${number(s.metrics.common_error_mm_mean)}</td>`:`<td>${number(s.metrics.common_camera_MPJPE_mm)}</td><td>${number(s.metrics.common_root_relative_MPJPE_mm)}</td><td>${number(s.metrics.common_PA_MPJPE_mm)}</td>`}</tr>`).join('')}</tbody></table></div>`;
  }).join('')}</details>`;
}
function attemptDetail(a,i){
  const runtime={};for(const k of ['frames','input_fps','decode_s','preprocess_inference_s','vae_encode_s','predict_s','total_s','total_decode_encode_predict_save_s','total_decode_predict_save_s','peak_allocated_gib','peak_reserved_gib','warm_median_fps','stage_times_s','timings'])if(k in a)runtime[k]=a[k];
  return `<details class="attempt-detail" id="attempt-${i}" ${i===0&&!a.media?'open':''}><summary>${esc(a.method)} · ${esc(stateText[a.status]||a.status)}${a.has_failure?' · ⚠':''}<div class="runid">${esc(a.run)}</div></summary>
    ${a.error||a.validation_error?`<p class="note error">${esc(errText[a.validation_error||a.error]||'记录存在错误')}。保留该次尝试，不用后续成功覆盖历史。</p>`:''}
    ${a.timeline?`<h4>左右手预测出现 / 相机手腕深度</h4><div class="legend"><span>左手</span><span>右手</span></div><div class="timeline-wrap">${timelineSVG(a.timeline)}</div><p class="small">48 个等帧区间（短输入更少）；色块深浅为预测出现比例，折线为有效预测的手腕深度中位数。断线是无有效预测，不补零。</p>`:''}
    ${a.scores.length?a.scores.map(s=>`<h4>${esc(s.protocol)} · ${esc(stateText[s.status]||s.status)}</h4><p class="runid">来源 ${esc(s.artifact)}</p>${s.protocol==='no-GT-operational-diagnostics'?'<p class="metric-note">这些是几何 / 运行诊断，不是对真值的准确率。</p>':''}${metricTable(s)}`).join(''):'<p class="note">此尝试没有已归档的逐案例参考评分。输出 / 视频存在不代表已经验证精度。</p>'}
    ${Object.keys(runtime).length?'<h4>耗时、显存与执行范围</h4>'+metricTable(runtime):''}
    ${a.full_validation?'<h4>完整重建数值门禁</h4>'+metricTable(a.full_validation):''}
    <details><summary>完整脱敏记录（JSON）</summary><pre>${esc(JSON.stringify(a,null,2))}</pre></details></details>`;
}

async function openCase(id,scroll=true){
  const token=++renderToken;
  selected=id;updateURL();$('#detail').hidden=false;$('#detail').innerHTML='<p>正在加载逐方法记录…</p>';
  try{
    const response=await fetch(`data/cases/${encodeURIComponent(id)}.json`);if(!response.ok)throw new Error('该案例未归档');
    const c=await response.json();if(token!==renderToken)return;
    const visuals=c.attempts.filter(a=>a.media);
    $('#detail').innerHTML=`<div class="detail-top"><div><p class="eyebrow">${esc(c.dataset)} / CASE RECORD</p><h2>${esc(c.activity||c.id)}</h2>${c.activity?`<p class="runid">${esc(c.id)}</p>`:''}</div><button id="close-case" type="button">关闭详情 ×</button></div>
      <div class="detail-meta"><span class="badge">${c.attempts.length} 次实验</span><span class="badge neutral">${c.preparations.length} 个准备版本</span><a class="small" href="data/cases/${encodeURIComponent(c.id)}.json" download>下载本案例 JSON</a><button id="copy-case" type="button">复制案例链接</button></div>
      <p class="note">${esc(evidence[c.family]||'跨数据集运行与输出诊断。没有独立有效参考的指标不可评分。')} ${c.source_split?'来源 split：'+esc(c.source_split)+'。':''}</p>
      ${visuals.length?`<h3>大尺寸可视化 · ${visuals.length} 条方法 / 版本记录</h3><p class="small">选择同一输入协议进行对照。原始相机与 scalar 重采样、不同帧窗不能自动视为严格配对；完整 HaWoR 与 camera-only 的阶段也不同。播放器支持全屏。</p><div class="viewer-controls"><label>左侧 / 主结果<select id="video-a">${visuals.map((a,i)=>`<option value="${i}">${esc(a.method+' — '+a.run)}</option>`).join('')}</select></label><label>右侧对照（可选）<select id="video-b"><option value="">不显示对照，保留最大画面</option>${visuals.map((a,i)=>`<option value="${i}">${esc(a.method+' — '+a.run)}</option>`).join('')}</select></label></div><div class="viewers" id="viewers"></div><div class="video-actions"><button id="sync" type="button">从头同步播放</button><button id="pause" type="button">全部暂停</button></div>`:`<p class="note">本案例不公开 RGB 视频：${c.media_policy==='RGB-not-cleared-for-republication'?'该来源的再次发布许可尚未完成核对，原视频与已有叠加仍保留在受控存储。':'暂无完成且通过媒体校验的对应渲染。'} 数值、时间线和失败记录在下面完整保留。</p>`}
      <h3>所有方法与历史实验</h3><p class="metric-note">下面的 mm 误差只在各方法自己的 TP 上计算，不是共同有效帧排名。详细原字段、HOT3D 专用指标及分母在每次实验的展开项中。未匹配到该通用字段显示“未评分”，不表示没有其他协议结果。</p><div class="table-wrap"><table class="attempts-table"><thead><tr><th>方法 / 实验版本</th><th>执行与校验</th><th>参考覆盖 %</th><th>Camera mm</th><th>Root-rel. mm</th><th>PA mm</th><th>证据</th></tr></thead><tbody>${c.attempts.map(summaryRow).join('')}</tbody></table></div>
      ${pairedTables(c)}${c.attempts.map(attemptDetail).join('')}
      ${c.detector?`<details class="attempt-detail"><summary>检测器四组参数诊断（逐采样帧）</summary><p class="small">检测框数量 / 置信度不是对真值的检测召回。参数和帧索引保留于下列记录。</p>${detectorChart(c.detector)}<details><summary>采样帧数据</summary><pre>${esc(JSON.stringify(c.detector,null,2))}</pre></details></details>`:''}
      <details class="attempt-detail"><summary>输入准备、帧窗、内参与历史版本</summary><div class="table-wrap"><table class="prep-table"><thead><tr><th>Suite</th><th>状态</th><th>帧 / FPS</th><th>源帧范围</th><th>内参状态</th></tr></thead><tbody>${c.preparations.map(p=>`<tr><td><code>${esc(p.suite)}</code></td><td>${esc(stateText[p.status]||p.status)}${p.error?'<br>'+esc(errText[p.error]):''}</td><td>${p.frames??'—'} / ${p.fps?number(p.fps):'—'}</td><td>${p.source_frame_range?.join('–')||'—'}</td><td>${esc(typeof p.intrinsics_status==='string'?p.intrinsics_status:JSON.stringify(p.intrinsics_status)||'见协议')}</td></tr>`).join('')}</tbody></table></div></details>`;
    $('#close-case').onclick=closeCase;$('#copy-case').onclick=async()=>{try{await navigator.clipboard.writeText(location.href);$('#copy-case').textContent='链接已复制';}catch{$('#copy-case').textContent='请复制地址栏链接';}};
    if(visuals.length){
      const renderVideos=()=>{
        $('#viewers').querySelectorAll('video').forEach(v=>v.pause());
        const indices=[$('#video-a').value,$('#video-b').value].filter(v=>v!=='');
        $('#viewers').classList.toggle('compare',indices.length===2);
        $('#viewers').innerHTML=indices.map(i=>{const a=visuals[+i],m=a.media;return `<figure><video controls playsinline preload="metadata" poster="${esc(m.poster)}" src="${esc(m.video)}" aria-label="${esc(a.method)} 预测视频"></video><figcaption>${esc(a.method)} · ${m.frames} 帧 / ${number(m.fps)} FPS · ${esc(a.run)}<br>${esc(c.family)} 数据源；仅研究预览，<a href="ATTRIBUTION.md">署名与许可</a>。</figcaption></figure>`;}).join('');
      };
      $('#video-a').onchange=renderVideos;$('#video-b').onchange=renderVideos;renderVideos();
      $('#sync').onclick=()=>{$('#viewers').querySelectorAll('video').forEach(v=>{v.currentTime=0;v.play().catch(()=>{});});};
      $('#pause').onclick=()=>$('#viewers').querySelectorAll('video').forEach(v=>v.pause());
    }
    if(scroll)$('#detail').scrollIntoView({behavior:'smooth',block:'start'});
  }catch(e){$('#detail').innerHTML=`<p class="error">加载失败：${esc(e.message)}</p><button id="close-case">关闭</button>`;$('#close-case').onclick=closeCase;}
}
function closeCase(){renderToken++;$('#detail').querySelectorAll('video').forEach(v=>v.pause());$('#detail').hidden=true;selected=null;updateURL();}

async function init(){
  try{
    const res=await fetch('data/index.json');if(!res.ok)throw new Error('无法加载结果索引');archive=await res.json();buildOverview();
    const params=new URLSearchParams(location.search);for(const k of ['dataset','method','status','query'])if(params.has(k))$('#'+k).value=params.get(k);
    page=Math.max(0,Number(params.get('page')||1)-1);const initialCase=new URLSearchParams(location.hash.slice(1)).get('case');
    applyFilters(false);if(page>=Math.ceil(filtered.length/pageSize)){page=0;renderCards();}
    if(initialCase)openCase(initialCase);
    $('#filters').onsubmit=e=>e.preventDefault();
    for(const k of ['query','dataset','method','status','sort'])$('#'+k).addEventListener(k==='query'?'input':'change',()=>applyFilters());
    $('#reset').onclick=()=>{for(const k of ['query','dataset','method','status'])$('#'+k).value='';$('#sort').value='media';applyFilters();};
    $('#prev').onclick=()=>{page--;renderCards();updateURL();$('#browse').scrollIntoView();};
    $('#next').onclick=()=>{page++;renderCards();updateURL();$('#browse').scrollIntoView();};
    document.addEventListener('click',e=>{
      const b=e.target.closest('[data-dataset]');if(b){$('#dataset').value=b.dataset.dataset;applyFilters();$('#browse').scrollIntoView();}
      const link=e.target.closest('[data-case]');if(link){e.preventDefault();openCase(link.dataset.case);}
      const jump=e.target.closest('[data-jump]');if(jump){e.preventDefault();const target=document.getElementById(jump.dataset.jump);target.open=true;target.scrollIntoView({block:'start'});}
    });
    window.addEventListener('hashchange',()=>{const id=new URLSearchParams(location.hash.slice(1)).get('case');if(id&&id!==selected)openCase(id);});
    const prov=await (await fetch('data/provenance.json')).json();
    $('#run-list').innerHTML=`<table><thead><tr><th>目录 / 版本</th><th>类型</th><th>记录数</th><th>状态</th></tr></thead><tbody>${prov.runs.map(r=>`<tr><td><code>${esc(r.id)}</code>${r.parent?'<div class="small">归属 '+esc(r.parent)+'</div>':''}</td><td>${r.kind==='decoder'?'几何解码':'推理 / 诊断'}</td><td>${r.record_count}</td><td>${esc(r.status||'仅目录')}</td></tr>`).join('')}</tbody></table>${prov.scorer_checks?`<h3>计分器自检（非模型样本）</h3><p>GT 自评分、整体平移 10 cm 和全部漏检的响应。Jitter 是运动曲率，即使完美 GT 也可能非零。</p><pre>${esc(JSON.stringify(prov.scorer_checks,null,2))}</pre>`:''}`;
  }catch(e){$('#snapshot').textContent='加载失败：'+e.message;$('#snapshot').classList.add('error');}
}
init();

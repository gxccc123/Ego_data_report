# 全量实验浏览器 / Experiment explorer

独立入口：<https://gxccc123.github.io/Ego_data_report/explorer/>。
结论和共同协议的汇总比较仍在 [benchmark](../benchmark/)。

本页面归档本项目已经保存的测试记录，不是一次新跑的推理，也不是生产标注
backlog 的完成情况。不同数据集的训练重叠未普遍排除，不宣称“全部未见数据”。

## 包含什么

- 所有已发现的 suite / data manifest 案例，包括准备失败的输入。
- 每个案例的各方法、内参协议、camera-only / full 阶段及历史重跑。
- 每次实验的状态、可用的逐片指标、分母、耗时和显存；缺失值保持 null。
- Ego-Exo4D、SHOW3D、HOT3D 的已归档参考评分；EgoDex wrist proxy 与
  common-TP 配对统计另列，不伪装成 21 关节真值。
- 无参考场景的输出率、深度、边界内投影比例等运行诊断。
- 对应输入帧上的左右手输出比例与相机手腕深度时间线；按最多 48 个等帧
  区间汇总，不是参考召回率，不是世界轨迹。
- 四组参数的检测器逐采样帧计数，以及预测 / 跟踪诊断历史。
- SHOW3D、EgoTactile、Open-AoE 的全部已完成、允许研究展示的既有渲染。
  每个视频保留准确的方法版本，内容相同的视频仅存一份。

“案例”按实验中使用的 clip ID 去重，不等于独立人物、独立原视频或独立任务。
同一个 ID 的准备版本和重跑保留在详情中。特别是 Xperience 的六个窗口来自
同一个公开原视频。目录中的 decoder 是后处理，不另算模型推理。
“实验记录”计数包括失败、输入失败和 detector 诊断，不等于成功输出数。

## 页面操作

1. 点击数据集目录，或通过 ID、活动、子集名称搜索。
2. 可按方法、存在失败、具有参考评分或有公开视频筛选。分页浏览覆盖全部案例。
3. 打开案例，在大播放器中切换方法 / 版本；右侧选择另一结果可以并排对照。
4. 点击某个方法进入其详细指标、分母和时序图。每个案例都有可复制的独立链接。
5. JSON 下载保留精确数值与哈希，表格只做显示精度截断。

视频浏览的同步是从零开始同时播放，浏览器解码可能漂移；它不是帧级测评工具。
不同准备版本、长度和内参的结果不可因为放在同一案例下而当作严格配对。

## 公开数据与素材边界

本仓库不包含输入全集、MANO 文件、模型权重、访问凭证或服务器绝对路径。
没有再次发布许可核对的 RGB / mesh 叠加保留在受控存储，但案例条目、指标和
失败不隐藏。详见 [素材署名](ATTRIBUTION.md)。
这里的素材限研究展示；原数据、模型、MANO 的许可分别适用，页面不授予新的
商业再利用权利。官方仓库代码开源不自动等于数据集允许再次公开。

## 文件组织

```text
explorer/
  index.html, explorer.css, explorer.js   # 无构建依赖的静态页面
  data/index.json                       # 全部案例索引与统计
  data/cases/<clip-id>.json              # 逐案例全部实验记录
  data/provenance.json                   # manifest、run 目录与日志 SHA-256
  data/media.json                        # 每条渲染的 SHA-256 / 帧数 / FPS
  media/<content-hash>.mp4, .jpg          # 去重后的视频与中帧海报
  tools/                                # 白名单导出、媒体核验与页面检查
```

## 复现归档（不重跑模型）

1. 将 `tools/collect_archive.py` 的代码通过 SSH stdin 送到已有 benchmark
   环境，用该环境的 Python 执行 `--root <BENCHMARK_ROOT> --timelines`。
   它只读，不启动 GPU 任务。stdout JSON 的 `public` 是脱敏数据；
   `transfer` 是传输计划，**不得直接发布整个 stdout 文件**。
2. 在本地将结果保存到 gitignored 的 `output/explorer/archive.json`。
   可用 `tools/add_audits.py <snapshot> <local-audit-root>` 附加冻结的
   common-TP 配对审核和计分器自检；不会改写推理状态。
3. `python3 explorer/tools/fetch_media.py <snapshot> <ssh-alias>
   <remote-benchmark-root> <cache> --workers 4` 仅传输白名单 MP4。
4. 在含 OpenCV 的 Python 环境运行
   `python explorer/tools/build_archive.py <snapshot> --cache <cache>`。
   每段视频逐帧解码检查、生成海报、按 SHA-256 去重，再生成逐案例 JSON。
5. `python3 explorer/tools/verify_archive.py` 做覆盖、完整性、隐私及本地链接
   检查；用普通静态 HTTP server 预览，并以 Playwright 核对筛选、深链接、
   播放器、失败记录、桌面和手机布局。最后再提交到 GitHub Pages。

部署后的确切规模从 `data/index.json` 自动生成，不在本 README 手写实时数字。
来源文件哈希用于审计，不代表受限原始文件也可公开下载。

## 指标解释

带 TP 的误差在该方法自己的有效预测交集上计算。配对结果的 `common_*`
使用指定方法集合的共同有效帧；换一组方法，交集也会变。归档保留各自协议名。
全参考 PCK / recall 保留漏检分母。null 表示不可评分，不是零误差。
HOT3D 的 Jitter 单位为 mm/frame²（预测轨迹二阶差分），不是 GT 加速度误差；
完美 GT 自评分也可以有非零 Jitter。SHOW3D 的随动 rig 坐标不能直接当固定世界
真值计算 ATE。无参考场景的输出率和时间线仅用于诊断。

# Ego 手部重建：跨数据集测评与采集方案

[在线阅读完整汇报](https://gxccc123.github.io/Ego_data_report/benchmark/) · [返回原管线报告](https://gxccc123.github.io/Ego_data_report/)

2026-09-20—21 的固定研究快照。正文为中文，不需要 JavaScript 也能读取所有表格；手机、桌面与浏览器打印均可使用。

## 汇报内容

1. MINT、ACE K-free / K-given、HaWoR hand、OLA hand 的方法和测试边界。
2. 275 段既有数据、166 段公开扩展样例，以及 Ego-Exo4D / SHOW3D 参考子集。
3. 共同输出集误差、全参考覆盖 / PCK、受试者 bootstrap 区间。
4. 113 段检测参数诊断与固定 12 人完整 HaWoR 审计。
5. 可视案例、失败保留、工程成本、数据交付契约与采集建议。

这不是官方全量排行榜复现、完全未见训练数据的保证、独立 MoCap 验收或下游机器人性能结论。具体参考类型和分母在各表旁注明。

## 本地预览与重建

在仓库根目录：

```bash
python3 benchmark/tools/build_report.py
python3 -m http.server 8848 --bind 127.0.0.1
```

打开 `http://127.0.0.1:8848/benchmark/`。无需 npm 或前端打包。

- `report.template.html`：人工审阅的正文与表格占位。
- `assets/results.json`：白名单公开聚合结果、原始精度、区间、固定版本和证据文件哈希。
- `tools/build_report.py`：纯 Python 标准库构建静态 `index.html`。
- `tools/export_results.py`：有原始审计产物的维护者可从外部目录导出白名单；拒绝未完成的第二轮结果。
- `tools/verify_report.py`：静态链接、结果完整性、隐私字段和构建确定性检查。
- `tools/prepare_media.py`：可选 OpenCV 维护工具，完整解码 321 帧预览并生成固定中点 poster 与媒体哈希清单。
- `report.css` / `report.js`：响应式布局、目录、同步播放和打印。
- `ASSET_ATTRIBUTION.md`：SHOW3D 展示素材来源与变换说明。

表格中的数值由 JSON 生成；正文解释为人工撰写。更新结果后必须重新检查正文中的样本量、数字和推论，构建器不会自动重写结论。

## 公开边界

本目录不包括模型权重、MANO 文件、原始标注数组、私有生产源码、受限原始视频、服务器地址、登录信息或绝对本地路径。

SHOW3D 的有限衍生展示按其 CC BY-NC 4.0 许可署名用于非商业研究。其他数据来源只公开聚合统计和说明，不重新分发 RGB。报告素材不替代上游数据 / 模型 / MANO 的许可。

公开聚合结果可以核查表格及部分计数，但不足以独立重跑模型推理；重跑仍需要取得对应数据访问权限、模型和完整实验适配器。

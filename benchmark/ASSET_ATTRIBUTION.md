# 展示素材来源与修改说明

本目录的第三方视频帧来源于 **SHOW3D: Capturing Scenes of 3D Hands and Objects in the Wild**，Patrick Rim、Kevin Harris、Braden Copple、Shangchen Han、Xu Xie、Ivan Shugurov、Sizhe An、He Wen、Alex Wong、Tomas Hodan、Kun He，CVPR 2026。

- [官方数据页](https://huggingface.co/datasets/facebook/show3d-dataset)
- 数据版本：`d37fdf3d5b6b7111e94d90d02a3cee28da9b1a5e`
- 许可：[Creative Commons Attribution-NonCommercial 4.0 International](https://creativecommons.org/licenses/by-nc/4.0/)
- 本页仅用于非商业研究说明。上游发布已对脸部做模糊处理；我们没有还原模糊区域。
- 修改后的展示不代表原作者认可模型、推理结果或本报告。

## 素材对照

| 公开文件 | 数据来源（headset0） | 源帧范围 / 选择规则 | 修改 |
|---|---|---|---|
| `show3d-detector-a.jpg` | `ASC023/mug_pouring-liquid-out_1709` | 截取源帧 532–1172、每 2 帧取 1，展示中点；固定 ID 顺序第 1 例 | 尺寸统一、4 参数预测框、类别颜色与文字拼接 |
| `show3d-detector-b.jpg` | `SHE109/cansoup_cleaning-the-outside_de0a` | 源帧 818–1458、每 2 帧取 1，展示中点；固定 ID 顺序第 2 例 | 同上；该 test 来源无可评分手部参考 |
| `full-a-raw.mp4` / `.jpg` | `YYE125/cantomatosauce_cleaning-the-outside_804c` | 源帧 866–1506，每 2 帧取 1；12 人固定哈希选样的第一例 | 标量相机重采样；原图与相机系手部预测并排；MANO 网格 / 21 点叠加 |
| `full-a-final.mp4` / `.jpg` | 同上 | 与 raw 相同的 321 帧 / 30 FPS | 完整 HaWoR 结果变回相机系后叠加；包含 infiller 输出 |
| `full-b-raw.mp4` / `.jpg` | `XYA827/none_rock-paper-scissors_c0d5` | 源帧 1207–1847，每 2 帧取 1；从成功可视化中事后选出的高误差诊断案例 | 同上 |
| `full-b-final.mp4` / `.jpg` | 同上 | 与 raw 相同的 321 帧 / 30 FPS | 同上 |
| `case-a-mint.mp4` / `.jpg` | 与 `full-a` 相同 | 同一标量相机输入 | MINT 相机系预测，按其解码投影参数展示 |
| `case-a-ace-free.mp4` / `.jpg` | 与 `full-a` 相同 | 同一标量相机输入 | ACE K-free 相机系预测与预测投影参数 |
| `case-a-ace-k.mp4` / `.jpg` | 与 `full-a` 相同 | 同一标量相机输入 | ACE K-given 相机系预测与给定投影参数 |

视频均为原图 / 预测并排，不叠加真值。青色左手、橙色右手；颜色代表预测身份。网页两个方法视图可以同步开始播放，但浏览器播放不构成逐帧同步精度证明。评分依据原始数组的 frame ID，而非播放器时间。

网页视频 poster 统一抽取展示视频第 160 帧，不用多帧缩略图压缩细节。`assets/media-audit.json` 记录每段视频完整解码帧数、FPS、尺寸和 SHA-256。

两段 raw 展示复用先前相同输入的 HaWoR hand 结果；与本次 full 任务内部 `camera_raw` 逐元素回查：关节最大差 **0.0 m**、有效性掩码相同、源 frame ID 相同。不是用不同视频冒充前后对比。

## 原视频 SHA-256

- mug：`05b73758c1a9b418fbcbb3461a0a94e91421c70989f2c90147317f933f14ec49`
- soup can：`9d47bc19fa0ef0fb4f7e1ae6d678cada5cd23cfd1e86173942a9b72901218861`
- tomato sauce can：`94c0fb979743d3bf4923a17715faa9de83d9098cde736a6d7d7ede0b129a9bd7`
- rock-paper-scissors：`21af47634d3ca9601fb4bee959e5210d4fb9a3305d024878a357393937c88b17`

原视频不在仓库内。获取与使用上游数据仍需遵守对应许可。第三方模型权重、MANO 资产和源码的许可独立生效，不能从本报告推导出额外授权。

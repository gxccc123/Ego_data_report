# Research preview attribution

This page is a non-commercial research comparison. Source datasets and model
authors do not endorse this report. The page is not a replacement download for
the source datasets. No MANO model files, checkpoint weights, or raw reference
annotations are redistributed.

## SHOW3D

- Source: [facebook/show3d-dataset](https://huggingface.co/datasets/facebook/show3d-dataset).
- Authors: Patrick Rim, Kevin Harris, Braden Copple, Shangchen Han, Xu Xie,
  Ivan Shugurov, Sizhe An, He Wen, Alex Wong, Tomas Hodan, Kun He.
- License: [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/).
- Modifications: temporal sampling, resizing / camera resampling per protocol,
  side-by-side model prediction overlay, captions and extracted preview posters.
  Source de-identification is retained. Each case retains its public scene ID,
  split and sampled frame range. The v2 reference in these tests is not claimed
  to be independent gold-standard motion capture.

## EgoTactile

- Source: [HustleHard/EgoTactile](https://huggingface.co/datasets/HustleHard/EgoTactile).
- Authors: Yuan Zeng, Yujia Shi, Tiao Tan, Xingting Li, Yaqi Qin, Zongqing Lu,
  Wenming Yang, Jing-Hao Xue, Qingmin Liao.
- [Paper](https://arxiv.org/abs/2606.09243).
- License: [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/).
- Modifications: short sampled video windows, resizing, prediction overlay,
  captions and preview posters. Bare-hand and gloved-hand subsets are distinct.
  Tactile and demographic metadata are not republished. These tests do not use
  an independently validated 3D hand ground truth.

## Open-AoE / OpenAoE-2000h

- Copyright (c) Ant Group / inclusionAI.
- Source: [inclusionAI/OpenAoE-2000h](https://huggingface.co/datasets/inclusionAI/OpenAoE-2000h).
- Paper: [Open-AoE: An Open Egocentric Manipulation Dataset and Toolchain for
  Embodied Learning](https://arxiv.org/abs/2607.14183).
- Dataset license: [included verbatim](licenses/OpenAoE.txt), from
  [the source repository](https://huggingface.co/datasets/inclusionAI/OpenAoE-2000h/raw/main/LICENSE).
- Modifications: sampled video windows, undistortion / pinhole preparation as
  recorded by each protocol, resizing, model prediction overlays and posters.
  The source algorithmic MANO labels are not independent evaluation ground truth.

## Model-derived overlays

Model branches are identified per video and run. MINT:
[wuji-technology/wuji-ego-mint](https://github.com/wuji-technology/wuji-ego-mint);
ACE: [ggxxii/ACE-Ego-Hand](https://github.com/ggxxii/ACE-Ego-Hand);
HaWoR: [project](https://hawor-project.github.io/).
OLA is our audited hand-pipeline wrapper, not a new independent learned model.
The [MANO license](https://mano.is.tue.mpg.de/license.html) and each upstream
model / dataset's terms remain applicable. The report grants no new commercial
rights to source material. Prediction overlays are scientific illustrations,
not a redistribution of the MANO model.

## Sources without RGB republication clearance

All discovered case records remain indexed, including failures. For datasets
outside the media allowlist, public artifacts are limited to experiment
metadata, scalar metrics, presence/depth diagnostics and provenance hashes.
Raw video and mesh overlays remain in the original controlled benchmark
storage. No access credentials or private filesystem paths are published.

## Provenance

`data/media.json` maps every published clip and poster to a case, experiment
variant, SHA-256 digest, frame count, FPS and resolution. Byte-identical videos
are stored only once; the separate experiment records remain visible. A model
variant without an exact completed rendering is not assigned another variant's
video. `data/provenance.json` retains source artifact hashes.

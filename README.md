# Ego Hand Reconstruction · 技术报告

第一人称视频的 3D 手部轨迹重建技术报告：完整处理流程、方法边界、案例分析、历史实验结果、输出契约与质量控制。

## 在线阅读

GitHub Pages 配置完成后，访问：
https://gxccc123.github.io/Ego_data_report/

仓库仅包含静态报告与展示素材，不包含私有 pipeline 核心代码、模型权重、原始视频或私有仓库历史。正文中的实现模块名用于说明方法来源，并不代表代码已开源。运行示例需要另行取得私有实现及其依赖。

## 本地预览

在本目录执行：

```bash
python3 -m http.server 8848
```

打开 http://localhost:8848/ 。无需安装前端依赖或构建。

## GitHub Pages 发布

在仓库 **Settings → Pages** 中选择：

- Source: **Deploy from a branch**
- Branch: **main**
- Folder: **/(root)**
- 点击 **Save**

部署成功后，每次向 main 推送网页更新都会触发发布。`.nojekyll` 保持静态资源原样发布。

## 内容与证据边界

- `index.html`：中文技术报告，正文不依赖 JavaScript 即可阅读。
- `styles.css`、`app.js`：响应式布局、目录与图片放大交互。
- `assets/`：案例图、历史测量数据、生产结果快照与 NPZ 字段契约。
- 报告中的历史统计不是实时任务进度；演示案例不等同于完整数据集精度评测。
- 素材来源与相关方法引用见正文；本仓库不额外授予第三方数据或模型的使用权。

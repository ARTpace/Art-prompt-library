---
name: collect-web-prompts
description: 在独立提示词仓库中检索网站公开提示词、选择已有采集器、增量下载并保留来源，形成待分类数据。用于网站提示词采集和续传，不用于 Art Canvas 界面或运行时搜索功能。
---

# 网站提示词采集

从本 Skill 定位仓库根目录，先读 [维护入口](../../../docs/prompt-maintenance.md)，仅按任务需要读对应采集器文档，不整库读取历史正文。

## 选择入口

- CCPrompt：`tools/ccprompt_download.py`，详见 [下载说明](../../../docs/ccprompt-download.md)。SQLite 记录列表、详情和错误，支持断点续跑。
- OpenNana：`tools/opennana-import/import.py`，详见其 README；支持离线缓存和 dry-run。
- 腾讯元宝：`tools/yuanbao-export/browser-export.js`、`download.mjs`，参见其 README。浏览器采集器复用用户当前登录会话；不要把凭据、会话数据提交到仓库。
- PromptImageAtlas 等导出的 JSONL：`tools/prompt-library-import/import.py` 转成中间库，`tools/merge-pia-into-style-presets.py` 做历史格式合并；它们是导入器，不能声称具备网站采集能力。
- Fooocus 官方预设源：`tools/fooocus_importer.py`；默认工作文件为本仓库 `data/style-presets.json`，不接入主工具用户目录。

## 采集边界

用户给出新网站时先检查已有脚本、公开索引与实际返回字段，再决定是否增加窄范围采集器。依据稳定 ID 分页和续传，完整保存原始正文、负向正文、封面地址与原始来源信息。记录实际覆盖页数、详情成功数、失败数，不把列表缓存数当成完整提示词数。

默认只采集用户指定的公开图片提示词，不扩展到视频。遇到登录要求、访问拒绝或客人额度限制，记录阻碍并停止相关请求，不绕过限制。临时网络错误有限重试，保留成功缓存，不无限重启全库下载。

有正在运行的下载时先检查进程和输出目录，不启动重复任务。迁移下载位置前记录命令，安全停止并验证数据库，再从新位置恢复；仅迁移不要求重新采集已完成条目。

工作数据写入 `artifacts/<来源>/`；数据库、日志、原始下载及图片缓存不默认提交。代码测试使用固定样本／mock，不用真实批量采集作测试。

## 接入分类与发布

先形成可核对的原始数据或中间 JSON，不自动安装到 Art Canvas。需要分类时转用本仓库 `classify-style-packs` Skill；需要发布时按 `scripts/split_platforms.py`、`scripts/build_catalog.py` 的流程准备平台包。发布前核对 ID、完整字段和来源，保留规则／人工审核状态。用户未授权发布时交付可检查文件，不推送远端。

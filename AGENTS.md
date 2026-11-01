# 提示词资产维护

- 本仓库统一维护网站提示词检索与采集、下载、分类、去重／翻译脚本、分类规范、Skill 和平台资产包。Art Canvas 主工具仅消费发布的包，不复制维护脚本。
- 网站提示词采集或增量下载，使用 [.agents/skills/collect-web-prompts/SKILL.md](.agents/skills/collect-web-prompts/SKILL.md)。风格分类、整理和审核，使用 [.agents/skills/classify-style-packs/SKILL.md](.agents/skills/classify-style-packs/SKILL.md)。
- 分类字典唯一来源：`docs/style-pack-taxonomy-v1.md`；数据规范：`docs/style-pack-spec-v1.md`。不要另建同义分类字典。
- `packs/` 是发布数据；`tools/` 是采集和历史转换工具；`scripts/` 是平台拆分和清单发布工具；`data/`、`artifacts/` 是本地工作数据与缓存，默认不进 Git。不要提交账号凭据、浏览器会话、下载数据库、日志和备份。
- 保留条目 ID、完整正文、负向正文、图片来源及未知扩展字段。分类不确定时保留 pending，规则建议不能标成人工审核。去重删除与分类分开，未明确授权不删条目。
- 采集脚本默认只写本仓库工作数据，不直接修改 Art Canvas 安装包、用户库或增量层。历史导入脚本仅用于本地中间数据，参见 `docs/prompt-maintenance.md`。
- 数据发布时仅更新变化的平台包版本，运行 `python -X utf8 scripts/build_catalog.py` 后核对 ID、内容和计数；仓库推送授权以当前会话为准，不因读取本文件自动发布。
- 验证按改动范围执行：Python 对应测试文件、Node 对应 `.cjs` 测试；不要连接真实网站跑批量采集来测试代码。跨仓库迁移可运行本仓库独立维护测试，不能依赖旁边有 Art Canvas 源码或其依赖。

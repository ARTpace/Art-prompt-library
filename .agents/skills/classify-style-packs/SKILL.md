---
name: classify-style-packs
description: 仅按标题批量整理 Art Canvas 风格包，明确项归标准大类和子类，不明确项保留待分类；不使用提示词正文判断，保留完整资产并输出可核对的 JSON 和报告。不用于标签、画师或角色包。
---

# 风格包标题分类

## 分类依据

用户已明确要求：**只根据条目的标题（name）分类，不使用提示词正文、负向提示词、描述、原包分类或图片推断类别。** 正文只用于原样复制、完整性校验和内容摘要，不能把正文送给 AI 或通过相同正文复用分类。

- 开始前读取 [分类表](../../../docs/style-pack-taxonomy-v1.md) 和 [数据规范](../../../docs/style-pack-spec-v1.md)，使用现有父子 ID，不另建分类字典。
- 标题大类与子类均明确：归标准父子分类，`stage: title`、`resolution: resolved`、`status: suggested`。
- 标题只能确定大类：归该类 `<category>_pending`，`resolution: category_only`、`status: needs_review`。
- 标题为空、抽象或有跨大类冲突：归 `uncategorized/uncategorized_pending`，`resolution: unresolved`。不能为了覆盖率猜测。
- `pending` 代表未确定，`other` 代表已判断的其他形态；不能混用。来源平台不是内容分类。
- 规则明确不等于人工审核，未人工确认不得标 `reviewed`。

## 输入与范围

- 发布风格包在 `packs/<packId>/`；原始数据在本地 `data/style-packs-source/`；采集缓存和分类报告在 `artifacts/`，不提交。
- 对用户指定的全部风格包逐条处理，不能只处理界面第一页。默认生成独立目录，保留输入；不改工具安装数据或用户增量层。
- 只读盘点时输出建议；用户要求整理时生成 JSON 目录和报告。用户另有发布、替换或安装授权时，按已有授权在完成核对后执行，不反复询问。
- 仍在写入的下载数据库不作为稳定输入；可处理明确的完整快照，记录范围和数量，不声称整站全部完成。

## 执行

在本仓库根运行（可传多个包目录或 ZIP）：

```powershell
python -X utf8 .agents/skills/classify-style-packs/scripts/title_classify.py --input packs/platform-chatgpt --output artifacts/title-classification/标题分类批次 --title-only --write-files
```

脚本默认也是仅标题；命令显式写 `--title-only` 便于后续复现。不要使用 `--content-assisted`、正文规则或任何 AI 正文复核。历史正文函数仅保留兼容能力，不属于此 Skill 的工作流；只有用户以后明确改变分类依据时才能启用。

- `classified/<packId>/`：重组后的完整 JSON 与清单，不生成 ZIP。
- `assignments.jsonl`：每条记录的旧路径、新分类、标题证据、阶段、审核状态及校验摘要。
- `pending-titles.jsonl`：未解决项，仅含标题与定位，不导出正文队列。
- `summary.json`：明确到子类、大类待细分、全局待整理、冲突、空正文及生成目录统计；`content_enabled` 应为 false，`content_attempted` 应为 0。

输出目录不能在输入包内部，也不覆盖已有可编辑目录。重复盘点可复用缓存；标题、规则、模式和引擎签名变化后重新判断。旧正文分类不能作为仅标题模式的证据，必须重算；只保留明确标记 `stage: title` 的有效人工审核，原包仍可回溯。

若需要 AI 协助处理标题歧义，只读取 `pending-titles.jsonl` 分批判断，给出标题证据和合法父子 ID；仍不确定就保留 pending。不要单凭旧类别、来源系列或常识补出标题未表达的交付物。

## 完整性与交付

- 原样保留 ID、标题、完整正文、负向正文、图片地址、来源及未知扩展字段；只更新嵌套分类位置与分类元数据。
- 去重、删条、翻译、润色、改标题、下载和安装不属于分类的隐含范围。
- 实际核对生成 JSON 的 ID 多重集合与逐字段内容、清单计数、父子分类合法性及跨包 ID 冲突。空正文保留并报告，不能静默删除；冲突阻止输出，不能依赖加载顺序覆盖。
- 如需发布，仅更新实际变化的平台包版本并运行 `scripts/build_catalog.py`；不改标签、画师和角色包。
- 修改脚本后运行 `tests/test_style_title_classify.py`。核心回归：正文再明确也不能影响默认分类；旧正文分类不被沿用；所有非分类内容原样保留。

交付说明输入范围、总数、明确到子类数、大类待细分数、全局待整理数、完整性检查与输出路径，并说明是否替换发布包。不要把规则覆盖数说成准确率，不声称已阅读正文或完成正文审核。

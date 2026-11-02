---
name: classify-style-packs
description: 仅按标题批量整理 Art Canvas 风格包，明确项归标准大类和子类，不明确项保留待分类；不使用提示词正文判断，保留完整资产并输出可核对的 JSON 和报告。不用于标签、画师或角色包。
---

# 风格包标题分类

## 分类依据

用户已明确要求：**只根据条目的标题（name）分类，不使用提示词正文、负向提示词、描述、原包分类或图片推断类别。** 正文只用于原样复制、完整性校验和内容摘要，不能把正文送给 AI 或通过相同正文复用分类。

- 开始前读取 [分类表](../../../docs/style-pack-taxonomy-v1.md) 和 [数据规范](../../../docs/style-pack-spec-v1.md)，使用现有父子 ID，不另建分类字典。
- 标题大类明确并命中一个或多个子类：保留全部明确子类，选一个主子类存储，其余通过 `classification.subcategories` 关联，不复制条目。记录为`stage: title`、`resolution: resolved`、`status: suggested`。
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

### 三阶段流水线（默认走完，不需要人工审核）

**第一阶段 规则初筛**：上面的 `title_classify.py`，把确定性强的标题直接归位。

**第二阶段 语义筛选与复审**（必需）：

```powershell
python -X utf8 .agents/skills/classify-style-packs/scripts/semantic_classify.py --input artifacts/标题分类批次/classified/platform-chatgpt --report-dir artifacts/标题分类批次
```

- 参考库默认复用 `packs/*` 中全部 `resolved` 样本（跨包借用），`--reference` 可指定；排除 `uncategorized`。
- 未分类项：类均衡 kNN 投票（`--k 20 --alpha 0.3`）。子类置信 ≥ `--accept-conf 0.70` 直接定子类；大类占比 ≥ `--catonly-conf 0.60` 且领先 ≥ `--cat-gap 0.12` 降级到 `<category>_pending`；其余转大模型。
- 已分类项：留一法重判，只有**跨大类**且置信 ≥ `--cross-conf 0.75`、领先 ≥ `--cross-gap 0.15` 才改判并记入 `semantic-revisions.jsonl`；同大类子类分歧视为粒度问题，不动。
- 模型 `BAAI/bge-small-zh-v1.5`（CLS 池化），CPU 约 10 秒处理万条；向量按标题缓存。缺 torch/transformers 或参考库样本 < 30 时自动降级，把全部未分类转大模型，不报错中断。
- 产出：`semantic-summary.json`、`semantic-revisions.jsonl`、`pending-ai.jsonl`、`taxonomy-options.json`。

**第三阶段 大模型兜底**：只读 `pending-ai.jsonl`（每行有序号 `n`），仅凭标题给合法父子 ID，写成 `ai-decisions.jsonl`，每行 `{"n": 12, "category": "photography", "subcategory": "photography_beauty"}`；确实无证据就跳过该条，保留 pending。然后：

```powershell
python -X utf8 .agents/skills/classify-style-packs/scripts/semantic_classify.py --input artifacts/标题分类批次/classified/platform-chatgpt --report-dir artifacts/标题分类批次 --apply-ai artifacts/标题分类批次/ai-decisions.jsonl
```

子类必须属于该父类、父类必须在该包 `pack.json` 内，否则拒绝并记入 `ai-apply-summary.json`；不得自造 ID 或新增大类。

**补充阶段 大类内二次判别**（可选，语义阶段后、大模型兜底前）：只处理落在 `<category>_pending` 的条目，把候选子类收窄到该大类内部再投票，阈值放宽到 `--refine-conf 0.45 --refine-gap 0.10`。

```powershell
python -X utf8 .agents/skills/classify-style-packs/scripts/semantic_classify.py --input artifacts/标题分类批次/classified/platform-chatgpt --report-dir artifacts/标题分类批次 --refine
```

- 产出 `refine-summary.json` 和 `pending-refine.jsonl`（序号 `n` 独立编号）；仍不明确的交大模型，判定文件格式同上，`--apply-ai` 同时识别这两个清单。
- 实测 `platform-chatgpt`：2,162 条待细分 → 1,564 条落定，剩 598 条转大模型。

- `classified/<packId>/`：重组后的完整 JSON 与清单，不生成 ZIP。
- `assignments.jsonl`：每条记录的旧路径、新分类、标题证据、阶段、审核状态及校验摘要。
- `pending-titles.jsonl`：未解决项，仅含标题与定位，不导出正文队列。
- `summary.json`：明确到子类、大类待细分、全局待整理、冲突、空正文及生成目录统计；`content_enabled` 应为 false，`content_attempted` 应为 0。
- 语义阶段另出 `semantic-summary.json`、`semantic-revisions.jsonl`、`pending-ai.jsonl`、`taxonomy-options.json`；大模型回填后出 `ai-apply-summary.json`。

输出目录不能在输入包内部，也不覆盖已有可编辑目录。重复盘点可复用缓存；标题、规则、模式和引擎签名变化后重新判断。旧正文分类不能作为仅标题模式的证据，必须重算；只保留明确标记 `stage: title` 的有效人工审核，原包仍可回溯。

若需要 AI 协助，只读取语义阶段产出的 `pending-ai.jsonl` 分批判断，给出标题证据和合法父子 ID；仍不确定就跳过保留 pending。不要单凭旧类别、来源系列或常识补出标题未表达的交付物。规则与模型判定都只是建议，`status` 保持 `suggested`，未人工确认不得标 `reviewed`。

## 完整性与交付

- 原样保留 ID、标题、完整正文、负向正文、图片地址、来源及未知扩展字段；只更新嵌套主分类位置与分类元数据（含多子类关联）。
- 去重、删条、翻译、润色、改标题、下载和安装不属于分类的隐含范围。
- 实际核对生成 JSON 的 ID 多重集合与逐字段内容、清单唯一条目数、所有子类关联的父子合法性及跨包 ID 冲突。各子类数可重叠，不能相加当大类总数。空正文保留并报告，不能静默删除；冲突阻止输出，不能依赖加载顺序覆盖。
- 如需发布，仅更新实际变化的平台包版本并运行 `scripts/build_catalog.py`；不改标签、画师和角色包。
- 修改脚本后运行 `tests/test_style_title_classify.py`。核心回归：正文再明确也不能影响默认分类；旧正文分类不被沿用；所有非分类内容原样保留。

交付说明输入范围、总数、明确到子类数、大类待细分数、全局待整理数、完整性检查与输出路径，并说明是否替换发布包。不要把规则覆盖数说成准确率，不声称已阅读正文或完成正文审核。

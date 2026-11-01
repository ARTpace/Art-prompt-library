# 提示词采集、整理与发布

本仓库是提示词资产和维护工具的唯一维护位置。Art Canvas 主工具只负责展示、搜索、用户编辑、平台包安装与更新。

## 目录职责

| 目录 | 内容 | Git 提交 |
|---|---|---|
| `packs/`、`catalog.json` | 发布的平台包和摘要清单 | 是 |
| `.agents/skills/` | 网站采集、分类整理 Skill | 是 |
| `tools/` | 采集、转换、去重、翻译工具 | 是 |
| `scripts/` | 平台拆分、清单构建 | 是 |
| `docs/`、`tests/` | 规范、操作说明、离线测试 | 是 |
| `data/` | 原始完整库和历史格式工作文件 | 默认否 |
| `artifacts/` | 下载数据库、图片、缓存、报告、迁移备份 | 否 |

本机目录为 `H:/AI-Tools/Art-prompt-library`。命令在本仓库根目录执行，脚本只依赖 Python 标准库或 Node 内置模块；无需安装或检出 Art Canvas 源码。

## 采集入口

| 来源／操作 | 入口 |
|---|---|
| CCPrompt 下载、状态、续传 | `python -X utf8 tools/ccprompt_download.py status`；详见 `docs/ccprompt-download.md` |
| OpenNana 增量采集 | `python -X utf8 tools/opennana-import/import.py --dry-run`；支持 `--offline` |
| 腾讯元宝浏览器导出、资源下载 | `tools/yuanbao-export/README.md` |
| 元宝数据转成中间风格库 | `python -X utf8 tools/import_yuanbao_styles.py 下载目录 --online` |
| Fooocus 官方预设采集 | `python -X utf8 tools/fooocus_importer.py --dry-run` |
| PromptImageAtlas／OpenNana JSONL 整理 | `tools/prompt-library-import/import.py`，随后可用 `tools/merge-pia-into-style-presets.py` 转历史单文件格式 |
| 历史风格单文件与目录互转 | `tools/style_pack_migrate.py` |
| 历史离线 ZIP 分发 | `tools/style_pack_split.py`，GitHub 发布优先使用 `scripts/` 中的新流程 |
| 风格重复分析 | `python -X utf8 -m tools.dedupe_styles --help` |
| 风格名称翻译 | `python -X utf8 tools/translate_styles/cli.py --help` |

历史导入工具的默认输出是本仓库 `data/style-presets.json` 或 `data/prompt_libraries.json` 等工作文件，不直接更新 `packs/`。元宝／Fooocus 图片工作目录为 `artifacts/assets/`，不是 Art Canvas 的系统用户目录。历史 `/api/thumbnails/` 引用若用于远程分发，需要转换为可访问的媒体地址；元宝采集建议使用 `--online` 保留原始在线地址。

## 分类后发布

1. 对指定原始目录或平台包执行分类 Skill 的脚本：

   ```powershell
   python -X utf8 .agents/skills/classify-style-packs/scripts/title_classify.py --input packs/platform-chatgpt --output artifacts/title-classification/新批次 --write-files
   ```

2. 核对报告和 `classified/<packId>/`，不确定项保留 pending。只更新受影响的平台文件和版本；ID、完整正文和未知扩展字段保留。
3. `python -X utf8 scripts/build_catalog.py` 校验发布数据并重建摘要。只有从仓库外完整库重新拆分时才使用 `scripts/split_platforms.py --source 原始目录`，不要用旧上游数据覆盖平台包的新编辑。
4. 推送已授权的变更。消费者在 Art Canvas 风格包管理中检查更新，只安装对应包。

分类标准只维护 `docs/style-pack-taxonomy-v1.md` 和 `docs/style-pack-spec-v1.md`。来源平台不是内容分类；不要从标题、包名或平台名直接猜内容大类。

## 本地迁移数据

2026-11-01 从 Art Canvas 迁入的完整源库位于 `data/style-packs-source/`，CCPrompt 断点数据位于 `artifacts/ccprompt/`；分类批次位于 `artifacts/title-classification/`。早期 `.agents/classify-output` 的临时文件和审核记录归档在 `artifacts/legacy-classify-output/`，不作为自动执行入口。

旧文件原始副本和 SHA256 迁移记录保存在 `artifacts/migration-20261101/`。历史日志／报告中的绝对路径可能仍指向旧项目，是原始记录，不代表当前工作目录。

CCPrompt 已改从本仓库断点续跑，当前日志为 `artifacts/ccprompt/migrated.stdout.log`。旧 Art Canvas 的 `artifacts/ccprompt/` 因 Windows 日志锁保留为静止迁移备份，其中 `MOVED_TO.txt` 指向新位置；不要从旧目录再启动下载。

## 验证

修改对应脚本后运行受影响的单个 Python／Node 测试。迁移这些工具时可运行独立维护测试：

```powershell
python -X utf8 -m unittest discover -s tests -p "test_*.py"
node --test tests/test_yuanbao_export.cjs
```

这套测试不联网采集，也不安装到主工具。发布资产再单独运行清单构建，核对完整字段和 ID，而不只看总数。

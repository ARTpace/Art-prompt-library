# Art Prompt Library

Art Canvas 独立风格提示词资产仓库。保存可编辑 JSON，与工具代码分开维护；无需先打包 ZIP。

网站提示词采集、下载、分类规范、整理 Skill、去重与翻译工具也统一在这里维护。AI 入口见 [AGENTS.md](AGENTS.md)，操作流程和文件位置见 [维护说明](docs/prompt-maintenance.md)。

## 在工具里安装

使用支持仓库来源的 Art Canvas：进入「资产库 → 提示词库 → 风格包管理」，点击「添加仓库」，输入：

```
https://github.com/ARTpace/Art-prompt-library
```

也可以使用清单原始地址：

```
https://raw.githubusercontent.com/ARTpace/Art-prompt-library/main/catalog.json
```

点击所需平台卡片「安装」；打开管理页时自动检查仓库（15 分钟内复用清单），也可以点击「检查更新」。有更新的包显示本地与仓库版本，并提供「更新此包」，确认后只替换该平台包，不重新安装其他包。网络失败保留缓存和已安装数据；「断开来源」也不会删除已安装包。

如果曾安装旧的 `art-canvas-core` 整库包，请先在管理界面选中它、导出备份并卸载，再安装所需平台包。新版会阻止整库包与平台包混装，避免重复条目。

## 当前数据

共 22,248 条，分类标准 v1.1；各平台包独立维护，当前版本均为 1.1.0：

| 平台包目录 | 条数 |
|---|---:|
| `packs/platform-chatgpt/` | 8,880 |
| `packs/platform-nano-banana/` | 8,065 |
| `packs/platform-pia/` | 2,150 |
| `packs/platform-yuanbao/` | 1,459 |
| `packs/platform-other/` | 1,694 |

| 本地规则处理结果 | 条数 |
|---|---:|
| 明确到子类的建议 | 9,620 |
| 大类明确、待细分 | 5,782 |
| 大类待定 | 6,846 |

这些是规则建议，并非人工审核结果；未知项保留在 `*_pending` 子类。2 条历史 Fooocus 条目正文为空，保留原状并在清单 `emptyPromptIds` 中记录。不删除数据、不补写正文、不修改条目 ID。

图片保留原有路径或远程地址，本仓库当前只发布提示词 JSON，不保证原项目本地缩略图在其他机器上可用。上游采集内容的版权和使用条件以原作者、原来源为准，本仓库未为第三方内容另行授予许可。

## 后续维护

1. 修改 `packs/<packId>/` 内的分类 JSON，保留完整正文、ID 和未知扩展字段。
2. 更新对应 `pack.json` 的版本；条目增删时同步 `entryCount`。
3. 在本仓库根目录运行 `python -X utf8 scripts/build_catalog.py`，检查条数、重复 ID 并更新文件 SHA256。
4. 将该平台的 JSON 和新的 `catalog.json` 一起提交、推送。用户检查仓库更新后，仅更新对应平台包。版本号按数字比较，不把仓库旧版本提示为升级；同版本的文件摘要发生变化也会提示更新。

新增平台时在 `packs/` 下新增独立包即可，不必改动其他包。`platforms.json` 记录从上游整库拆分时的来源匹配规则；新增来源时可在其中增加平台定义。

若维护的是仓库外的完整已分类数据，可用 `python -X utf8 scripts/split_platforms.py --source 完整JSON目录` 重新拆分：仅内容变化的平台包递增补丁版本，未变化包保持字节和版本不变。直接维护平台包时不必运行此拆分脚本，避免用旧上游数据覆盖平台内的新编辑。

清单是安装入口；每个包用 `path` 指向 JSON 目录，用 `sha256` 登记清单与各分类文件的摘要。工具下载后校验摘要、包 ID、版本、条目数和结构，再安装到用户目录。

## 画师库与角色库

采集、拆包脚本和发布资产已迁入本仓库。参见 [维护说明](docs/artist-character-maintenance.md)。发布数据位于 `libraries/artists/`、`libraries/characters/`。

根 `catalog.json` 现统一发布风格、画师、角色三类资产（`kind` 区分），主工具在「内容包管理」从 GitHub 按需安装与检查更新。

# Art Prompt Library

Art Canvas 独立风格提示词资产仓库。保存可编辑 JSON，与工具代码分开维护；无需先打包 ZIP。

## 在工具里安装

使用支持仓库来源的 Art Canvas：进入「资产库 → 提示词库 → 风格包管理」，点击「添加仓库」，输入：

```
https://github.com/ARTpace/Art-prompt-library
```

也可以使用清单原始地址：

```
https://raw.githubusercontent.com/ARTpace/Art-prompt-library/main/catalog.json
```

点击包卡片「安装」；已有版本需要替换时会要求确认。安装后保存在 Art Canvas 用户数据目录，可以在管理界面卸载。「刷新仓库」只更新清单，不自动替换已经安装的数据；「断开来源」也不会删除已安装包。

## 当前数据

`packs/art-canvas-core/`：22,248 条，分类标准 v1.1。

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
4. 将 JSON 和新的 `catalog.json` 一起提交、推送。用户在工具中刷新仓库，再按需安装仓库版本。

清单是安装入口；每个包用 `path` 指向 JSON 目录，用 `sha256` 登记清单与各分类文件的摘要。工具下载后校验摘要、包 ID、版本、条目数和结构，再安装到用户目录。

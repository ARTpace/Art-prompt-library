# 画师库与角色库维护

本仓库是采集、整理、拆包及发布的维护源。Art Canvas 中的 `artist_packs/`、`character_packs/`、UI 与运行测试仍属于主工具；运行时格式转换保留兼容实现，本仓库 `tools/library_formats/` 是独立的发布端格式实现，改格式时需保持消费兼容。

## 数据位置

- 画师原始数据：`data/artist-packs-source/<release>/`（本地，忽略 Git）。
- 角色原始数据：`data/character-packs-source/characters.json`（本地，忽略 Git）。
- 角色下载版本：`data/animadex-version.json`。
- 角色特征映射：`config/character-features.json`（发布配置）。
- 画师发布资产：`libraries/artists/`。
- 角色发布资产：`libraries/characters/`。

发布资产含种子目录、可选 ZIP 与各自 catalog。执行 `python -X utf8 scripts/build_catalog.py` 后展开可选包 JSON，并将三类资产统一发布到根 catalog，使用 kind 字段区分格式。所有资产数据进入 Git；原始下载、备份不进入 Git。

## 更新命令

在本仓库根执行：

```powershell
python -X utf8 tools/artist_pack_fetch.py fetch
python -X utf8 tools/artist_pack_split.py split
python -X utf8 tools/artist_pack_split.py verify
python -X utf8 tools/update_character_data.py
python -X utf8 tools/character_pack_split.py split
python -X utf8 tools/character_pack_split.py verify
```

角色采集需要 Python `httpx`；拆分与核验仅依赖标准库。不要为测试发起全量网络下载。

## 主工具消费

现有主工具的种子数据、`static/app/characters.json` 回退文件、特征映射以及 `dist/*-packs` 是运行/构建副本，迁移未删除或改写。后续维护只改本仓库。

主工具「内容包管理」统一按风格、画师、角色分类，支持 GitHub 仓库按包安装与检查更新，校验逐文件 SHA256 后调用对应类型的安全导入器。界面不再提供本地 ZIP 安装入口。已安装的内置基础包仍由程序管理；可选包可单独更新、卸载。

更新主工具打包资产时，将 `libraries/artists/artists-seed` 复制到主工具 `data/artist-packs/artists-seed`，将 `libraries/characters/characters-seed` 复制到 `data/character-packs/characters-seed`；两个目录的 ZIP 与 catalog 分别复制到主工具 `dist/artist-packs`、`dist/character-packs`。如更新特征配置，同步 `config/character-features.json` 到主工具 `data/character-features.json`。这些是发布产物同步，不应恢复采集脚本。

首次迁移核验：画师源 42,197 条，按既有规则归一去重后 42,189 条（原始数据保留）；角色 36,492 条。三档包均逐字段还原核验通过。

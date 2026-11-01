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

画师与角色库不再内置任何资产，精华包也从仓库显式安装、更新和卸载。主工具仅扫描用户已安装目录，不加载旧种子目录或旧单文件回退数据；未安装时显示空库。

主工具「内容包管理」统一按风格、画师、角色分类，支持 GitHub 按包安装与检查更新，校验逐文件 SHA256 后调用对应类型的安全导入器。界面不提供本地 ZIP 安装入口。

不要再将种子目录、ZIP 或 catalog 复制进主工具，构建脚本已排除这些资产。发布时在本仓库执行拆包及 `scripts/build_catalog.py`，然后发布变更；特征配置仍为主工具运行配置。旧内置资产和回退文件本机归档于 `artifacts/backups/removed-artist-character-builtins-20261101/`，不进 Git。

首次迁移核验：画师源 42,197 条，按既有规则归一去重后 42,189 条（原始数据保留）；角色 36,492 条。三档包均逐字段还原核验通过。

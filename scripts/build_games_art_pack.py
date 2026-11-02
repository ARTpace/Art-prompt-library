# -*- coding: utf-8 -*-
"""把 mygamesartstyle 提取产物组装成 Art-prompt-library 风格包。

输入：artifacts/external/mygamesartstyle/{styles-prompts.jsonl, scene-prompts.jsonl}
输出：packs/atlas-games-art/

42 条风格级提示词 + 965 条画面级提示词，全部归入 taxonomy-v1.2 新增的
`game_art` 大类，按其来源分组的 4 个子类存储。
"""
import collections
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "artifacts" / "external" / "mygamesartstyle"
DEST = ROOT / "packs" / "atlas-games-art"

TAX_VERSION = "1.2.0"
GROUP_SUB = {
    "pixel": "game_art_pixel",
    "paint": "game_art_paint",
    "shape": "game_art_shape",
    "3d": "game_art_3d",
}
SUB_NAME = {
    "game_art_pixel": "像素与复古",
    "game_art_paint": "绘画与线条",
    "game_art_shape": "图形与编排",
    "game_art_3d": "三维与影像",
}


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


styles = read_jsonl(SRC / "styles-prompts.jsonl")
scenes = read_jsonl(SRC / "scene-prompts.jsonl")

style_group = {s["id"]: s["group"] for s in styles}

# 文案里的空格/换行清理，避免标题带不可见字符
def clean(text):
    return re.sub(r"\s+", " ", (text or "")).strip()


def make_classification(groups, reason):
    subs = []
    for g in groups:
        sub = GROUP_SUB[g]
        if sub not in {x["id"] for x in subs}:
            subs.append({"id": sub, "name": SUB_NAME[sub]})
    return {
        "method": "source",
        "stage": "source",
        "resolution": "resolved",
        "status": "confirmed",
        "reason": reason,
        "taxonomy_version": TAX_VERSION,
        "rules_version": "",
        "subcategories": subs,
    }


buckets = collections.defaultdict(list)

# ---- 42 条风格级 ----
for s in styles:
    groups = [s["group"]]
    # 站点的副组不单独记；风格级一条对应一个组
    buckets[GROUP_SUB[s["group"]]].append({
        "id": "mgas_style_" + s["id"],
        "name": s["name"],
        "type": "prompt",
        "prompt": s["prompt"],
        "negative_prompt": "",
        "description": clean(
            f"{s['description']} 风格边界：{s['boundary']} 识别要点："
            + "；".join(f"{o['title']}（{o['text']}）" for o in s["observations"])
            + " 代表游戏：" + "、".join(f"{g['name']}/{g['developer']}" for g in s["games"][:3])
        ),
        "thumbnail": s["coverImage"] or "",
        "tags": list(s["tags"]),
        "source_url": s["sourceUrl"],
        "classification": make_classification(
            groups, f"来源策展归组：{s['groupName']}（风格级规范）"),
    })

# ---- 965 条画面级 ----
seen_name = collections.Counter()
for sc in scenes:
    groups = []
    for sid in [sc["styleId"]] + list(sc["secondaryStyleIds"]):
        g = style_group.get(sid)
        if g and g not in groups:
            groups.append(g)
    if not groups:
        continue
    role = clean(sc.get("role")) or "画面"
    base = f"{sc['gameName']} · {role}"
    seen_name[base] += 1
    name = base if seen_name[base] == 1 else f"{base}（{seen_name[base]}）"
    buckets[GROUP_SUB[groups[0]]].append({
        "id": "mgas_scene_" + sc["id"],
        "name": name,
        "type": "prompt",
        "prompt": sc["prompt"],
        "negative_prompt": "",
        "description": clean(sc.get("sceneNote")),
        "thumbnail": sc.get("image") or "",
        "tags": [sc["gameName"]] + ([sc["englishName"]] if sc.get("englishName") else []),
        "source_url": sc.get("sourceUrl") or "",
        "classification": make_classification(
            groups, f"来源策展归组：{sc['gameName']} 的截图画面（画面级提示词）"),
    })

total = sum(len(v) for v in buckets.values())

DEST.mkdir(parents=True, exist_ok=True)
content = {
    "categories": [{
        "id": "game_art",
        "name": "游戏美术",
        "subcategories": [
            {"id": sid, "name": SUB_NAME[sid], "presets": buckets.get(sid, [])}
            for sid in ("game_art_pixel", "game_art_paint", "game_art_shape", "game_art_3d")
        ],
    }]
}
(DEST / "game_art.json").write_text(
    json.dumps(content, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

manifest = {
    "schema": 1,
    "packId": "atlas-games-art",
    "name": "游戏美术风格图鉴",
    "version": "1.0.0",
    "author": "art-canvas",
    "description": "243 款游戏、42 种美术方向的成套风格规范，含 42 条风格级与 965 条画面级提示词",
    "kind": "styles",
    "order": 200,
    "categories": [{"id": "game_art", "name": "游戏美术", "file": "game_art.json", "order": 0}],
    "taxonomyVersion": TAX_VERSION,
    "dataVersion": "2026-11-02",
    "entryCount": total,
    "source": "https://mygamesartstyle.jupiterthewarlock.com",
    "replaces": [],
}
(DEST / "pack.json").write_text(
    json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

print(json.dumps({
    "entryCount": total,
    "bySub": {SUB_NAME[k]: len(v) for k, v in buckets.items()},
    "styleLevel": len(styles),
    "sceneLevel": len(scenes),
}, ensure_ascii=False, indent=1))

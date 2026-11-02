# -*- coding: utf-8 -*-
"""抓取 mygamesartstyle 站点数据并归一化为提示词 JSONL。

站点是静态 SPA，数据全部来自三个 JSON，不用逐页解析 HTML：
    /data/styles.json   42 个风格（含 promptZh 完整风格规范）
    /data/games.json    243 款游戏 / 965 张截图（每张一条画面级 prompt）
    /data/library.json  243 款游戏的策展清单

用法：
    python tools/games-art-atlas/fetch_and_extract.py
产出写入 artifacts/external/mygamesartstyle/，再由
scripts/build_games_art_pack.py 组装成 packs/atlas-games-art/。
"""
import csv
import json
import pathlib
import urllib.request

SITE = "https://mygamesartstyle.jupiterthewarlock.com"
BASE = pathlib.Path(__file__).resolve().parents[2] / "artifacts" / "external" / "mygamesartstyle"
RAW = BASE / "raw"


def fetch(name):
    url = f"{SITE}/data/{name}.json"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read()


RAW.mkdir(parents=True, exist_ok=True)
for name in ("styles", "games", "library"):
    blob = fetch(name)
    (RAW / f"{name}.json").write_bytes(blob)
    print(f"{name}.json {len(blob)} bytes")

styles_doc = json.loads((RAW / "styles.json").read_text(encoding="utf-8"))
games = json.loads((RAW / "games.json").read_text(encoding="utf-8"))
groups = {g["id"]: g["name"] for g in styles_doc["groups"]}
game_by_id = {g["id"]: g for g in games}

INTRO = (
    "为一个原创游戏建立「{name}」美术方向，覆盖角色、场景、道具、界面与视觉效果。"
    "产出应当能持续扩展成一套作品。"
)

records = []
for s in styles_doc["styles"]:
    cover = game_by_id.get(s["coverGame"], {})
    records.append({
        "id": s["id"],
        "group": s["group"],
        "groupName": groups.get(s["group"]),
        "name": s["name"],
        "description": s["description"],
        "boundary": s["boundary"],
        "tags": s["tags"],
        "observations": s["observations"],
        "coverImage": f"{SITE}/media/{cover.get('id')}/scene-{s['coverIndex']}.jpg" if cover else None,
        "imageCount": s["imageCount"],
        "games": [{
            "gameId": g["id"],
            "name": game_by_id.get(g["id"], {}).get("name"),
            "englishName": game_by_id.get(g["id"], {}).get("englishName"),
            "developer": game_by_id.get(g["id"], {}).get("developer"),
            "note": g.get("note"),
            "shotIds": g.get("shotIds", []),
        } for g in s.get("games", [])],
        "prompt": s["promptZh"],
        "sourceUrl": f"{SITE}/styles/{s['id']}/",
    })

with (BASE / "styles-prompts.jsonl").open("w", encoding="utf-8") as fh:
    for r in records:
        fh.write(json.dumps(r, ensure_ascii=False) + "\n")

scene_rows = []
for g in games:
    for sc in g["screenshots"]:
        scene_rows.append({
            "id": sc["id"],
            "styleId": g["primaryStyle"],
            "secondaryStyleIds": list(g.get("secondaryStyles") or []),
            "shotStyleIds": sc.get("styleIds") or [g["primaryStyle"]],
            "gameId": g["id"],
            "gameName": g["name"],
            "englishName": g.get("englishName"),
            "developer": g.get("developer"),
            "role": sc.get("role"),
            "sceneNote": sc.get("sceneNote"),
            "excerpt": sc.get("alt"),
            "prompt": sc.get("prompt"),
            "image": SITE + sc["src"] if sc.get("src") else None,
            "originalImage": sc.get("originalUrl"),
            "sourceUrl": sc.get("sourceUrl"),
        })

with (BASE / "scene-prompts.jsonl").open("w", encoding="utf-8") as fh:
    for r in scene_rows:
        fh.write(json.dumps(r, ensure_ascii=False) + "\n")

with (BASE / "games-index.csv").open("w", encoding="utf-8-sig", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["gameId", "name", "englishName", "developer",
                "primaryStyle", "secondaryStyles", "shots", "storeUrl"])
    for g in games:
        w.writerow([g["id"], g["name"], g.get("englishName") or "", g.get("developer") or "",
                    g["primaryStyle"], ";".join(g.get("secondaryStyles") or []),
                    len(g["screenshots"]), g.get("storeUrl") or ""])

print(f"styles {len(records)} 条 / scenes {len(scene_rows)} 条 -> {BASE}")

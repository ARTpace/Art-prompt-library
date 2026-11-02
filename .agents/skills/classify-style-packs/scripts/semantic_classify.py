#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""风格包语义分类阶段（BGE-small-zh-v1.5 + kNN 类均衡投票）。

定位：title_classify.py 之后的第二道工序，仍在“仅按标题”约束内。
  1. 复审：对已 resolved 条目做留一法（leave-one-out）重判，跨大类高置信分歧才改；
  2. 初筛：对 unresolved / category_only 条目做近邻判定，高置信直接定子类，
     中置信降级到大类 pending，低置信交给下游大模型；
  3. 输出 pending-ai.jsonl，供大模型只处理“语义也没线索”的残余。

不使用提示词正文。不删除、不改写任何非分类字段。

用法：
  # 语义阶段（写回 classified 目录）
  python semantic_classify.py --input artifacts/title-classification/batch/classified/platform-chatgpt \
      --reference packs/platform-chatgpt packs/platform-nano-banana

  # 应用大模型判定结果（第二段）
  python semantic_classify.py --input ... --apply-ai artifacts/.../ai-decisions.jsonl
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

try:
    import numpy as np
except ImportError:  # pragma: no cover
    sys.exit('需要 numpy：pip install numpy')

REPO = Path(__file__).resolve().parents[4]
TAXONOMY_DOC = REPO / 'docs' / 'style-pack-taxonomy-v1.md'
PACK_DIR = REPO / 'packs'

DEFAULTS = {
    'model': 'BAAI/bge-small-zh-v1.5',
    'k': 20,
    'alpha': 0.3,
    'accept_conf': 0.70,     # 直接定子类
    'catonly_conf': 0.60,    # 大类得票占比达此值即降级到大类 pending
    'cat_gap': 0.12,         # 大类领先幅度下限
    'cross_conf': 0.75,      # 跨大类改判需更高置信
    'cross_gap': 0.15,       # 跨大类改判需更高领先幅度
    'seed_weight': 0.5,      # taxonomy 文本锚点（仅零样本类）权重
}


# ---------------------------------------------------------------- 分类表解析

def parse_taxonomy(path: Path = TAXONOMY_DOC):
    """从分类表 markdown 抽出合法父子 ID、中文名与描述。"""
    text = path.read_text(encoding='utf-8')
    cats, subs = {}, defaultdict(dict)
    heading_cat = None
    row_re = re.compile(r'^\|(.+)\|\s*$')
    tick_re = re.compile(r'`([a-z0-9_]+)`')
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith('#'):
            hit = tick_re.search(stripped)
            heading_cat = hit.group(1) if hit else None
            continue
        m = row_re.match(stripped)
        if not m:
            continue
        cells = [c.strip() for c in m.group(1).split('|')]
        if len(cells) < 3:
            continue
        first = cells[0]
        if re.fullmatch(r'\d+', first):  # 大类总表：| 10 | `photography` | 摄影 | 说明 |
            hit = tick_re.search(cells[1])
            if hit:
                cats[hit.group(1)] = cells[2]
            continue
        hit = tick_re.fullmatch(first)
        if hit and heading_cat:
            sid = hit.group(1)
            name = cells[1]
            desc = cells[2] if len(cells) > 2 else ''
            subs[heading_cat][sid] = {'name': name, 'desc': desc}
    legal = {}
    for cat, children in subs.items():
        if cat in cats:
            legal[cat] = children
    return cats, legal


def sub_name(legal, cat, sub):
    return (legal.get(cat, {}).get(sub) or {}).get('name', sub)


# ---------------------------------------------------------------- 数据装载

class Store:
    """classified/<packId>/ 目录的内存视图，保持条目顺序与全部字段。"""

    def __init__(self, root: Path):
        self.root = root
        self.pack = json.loads((root / 'pack.json').read_text(encoding='utf-8'))
        self.files = {}   # filename -> doc
        self.slots = {}   # (cat, sub) -> list[preset]
        self.order = {}   # id(preset) -> 全局序号
        self.records = []  # 扁平记录
        seq = 0
        for path in sorted(root.glob('*.json')):
            if path.name == 'pack.json':
                continue
            doc = json.loads(path.read_text(encoding='utf-8'))
            self.files[path.name] = doc
            for cat in doc.get('categories', []):
                for sub in cat.get('subcategories', []):
                    key = (cat['id'], sub['id'])
                    bucket = self.slots.setdefault(key, [])
                    for preset in sub.get('presets', []):
                        bucket.append(preset)
                        self.order[id(preset)] = seq
                        seq += 1
                        cls = preset.get('classification') or {}
                        self.records.append({
                            'preset': preset,
                            'id': preset.get('id'),
                            'title': (preset.get('name') or '').strip(),
                            'cat': cat['id'],
                            'sub': sub['id'],
                            'resolution': cls.get('resolution') or 'unresolved',
                            'method': cls.get('method') or '',
                        })
        self.total = len(self.records)

    def category_ids(self):
        return [c['id'] for c in self.pack.get('categories', [])]

    def move(self, targets):
        """把若干 (record, cat, sub) 挪到目标子类，缺失子类按需创建。"""
        for rec, cat, sub in targets:
            src = (rec['cat'], rec['sub'])
            preset = rec['preset']
            self.slots.setdefault((cat, sub), [])
            if src == (cat, sub):
                continue
            bucket = self.slots.get(src, [])
            if preset in bucket:
                bucket.remove(preset)
            self.slots[(cat, sub)].append(preset)
            rec['cat'], rec['sub'] = cat, sub

    def rebuild(self, legal, cats_meta):
        """按 slots 回写各分类 JSON（原地覆盖，不增删条目）。"""
        present = {c['id'] for doc in self.files.values() for c in doc.get('categories', [])}
        for filename, doc in self.files.items():
            for cat in doc.get('categories', []):
                cat_id = cat['id']
                existing = {s['id']: s for s in cat.get('subcategories', [])}
                # 目标落在本文件的子类
                wanted = [sub for (c, sub) in self.slots if c == cat_id]
                for sub_id in wanted:
                    if sub_id not in existing:
                        existing[sub_id] = {
                            'id': sub_id,
                            'name': sub_name(legal, cat_id, sub_id),
                            'presets': [],
                        }
                for sub_id, sub_obj in existing.items():
                    bucket = self.slots.get((cat_id, sub_id), [])
                    sub_obj['presets'] = sorted(bucket, key=lambda p: self.order.get(id(p), 0))
                cat['subcategories'] = list(existing.values())
            (self.root / filename).write_text(
                json.dumps(doc, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        return present


# ---------------------------------------------------------------- 向量编码

def load_encoder(model_name: str, cache_dir: Path, threads: int = 0):
    os.environ.setdefault('HF_ENDPOINT', 'https://hf-mirror.com')
    try:
        import torch
        from transformers import AutoModel, AutoTokenizer
    except ImportError:
        return None, None, 'torch/transformers 未安装，跳过语义阶段，全部条目转大模型'
    if threads:
        torch.set_num_threads(threads)
    # 本地已有权重就直接离线加载，避免每次联网校验被代理拖死
    for offline in (True, False):
        try:
            tokenizer = AutoTokenizer.from_pretrained(
                model_name, cache_dir=str(cache_dir), local_files_only=offline)
            model = AutoModel.from_pretrained(
                model_name, cache_dir=str(cache_dir), local_files_only=offline)
            model.eval()
            return tokenizer, model, ''
        except Exception as exc:  # 首次运行无缓存时联网下载
            if not offline:
                return None, None, f'模型加载失败：{exc}'
    return None, None, '模型加载失败'


def encode(texts, tokenizer, model, cache_path: Path, batch_size: int = 64):
    """BGE：CLS 池化 + L2 归一化；按标题哈希缓存。"""
    import torch

    vectors, missing = {}, []
    if cache_path.exists():
        try:
            blob = np.load(cache_path, allow_pickle=False)
            keys = blob['keys'].tolist()
            mat = blob['vecs']          # 只解压一次，切勿在循环里反复取
            vectors = {str(k): mat[i] for i, k in enumerate(keys)}
        except Exception:
            vectors = {}  # 旧缓存格式不兼容，重建
    for text in dict.fromkeys(texts):
        if text and text not in vectors:
            missing.append(text)

    if missing:
        for start in range(0, len(missing), batch_size):
            chunk = missing[start:start + batch_size]
            batch = tokenizer(chunk, padding=True, truncation=True,
                              max_length=64, return_tensors='pt')
            with torch.no_grad():
                out = model(**batch)
            pooled = torch.nn.functional.normalize(out.last_hidden_state[:, 0], dim=-1)
            for text, vec in zip(chunk, pooled.numpy()):
                vectors[text] = vec.astype(np.float32)
        keys = list(vectors)
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(cache_path,
                            keys=np.array(keys, dtype=str),
                            vecs=np.vstack([vectors[k] for k in keys]))
        print(f'  编码 {len(missing)} 条标题（缓存累计 {len(keys)}）', flush=True)
    return vectors


# ---------------------------------------------------------------- 近邻打分

def class_vote(sims, labels, cats, alpha, k):
    """类均衡 kNN 投票：同类相似度求和 / 类样本数^alpha。

    同时聚合成大类票数：子类之间互相分票时，大类仍可能很确定。
    """
    if sims.size == 0:
        return None
    kk = min(k, sims.size)
    if kk < sims.size:
        top_idx = np.argpartition(-sims, kk - 1)[:kk]
    else:
        top_idx = np.arange(sims.size)
    scores = defaultdict(float)
    for idx in top_idx:
        scores[labels[idx]] += float(sims[idx])
    for sub in list(scores):
        scores[sub] /= (float(cats[sub]) ** alpha) or 1.0
    ranked = sorted(scores.items(), key=lambda kv: -kv[1])
    total = sum(scores.values()) or 1.0
    best, best_score = ranked[0]
    conf = best_score / total
    gap = (best_score - ranked[1][1]) / total if len(ranked) > 1 else 1.0
    second = ranked[1][0] if len(ranked) > 1 else None

    cat_scores = defaultdict(float)
    for sub, value in scores.items():
        cat_scores[top_level(sub)] += value
    cat_ranked = sorted(cat_scores.items(), key=lambda kv: -kv[1])
    cat_total = sum(cat_scores.values()) or 1.0
    cat_conf = cat_ranked[0][1] / cat_total
    cat_gap = ((cat_ranked[0][1] - cat_ranked[1][1]) / cat_total) if len(cat_ranked) > 1 else 1.0

    return {'sub': best, 'conf': conf, 'gap': gap, 'second': second,
            'cat': cat_ranked[0][0], 'cat_conf': cat_conf, 'cat_gap': cat_gap}


def top_level(sub):
    return sub.split('_')[0] if sub else None


# ---------------------------------------------------------------- 主流程

def run(args):
    started = time.perf_counter()
    report_dir = Path(args.report_dir) if args.report_dir else Path(args.input).parent
    report_dir.mkdir(parents=True, exist_ok=True)
    cats_meta, legal = parse_taxonomy()
    store = Store(Path(args.input))
    pack_cats = set(store.category_ids())
    print(f'输入 {store.root}：{store.total} 条，{len(pack_cats)} 个大类')

    if args.apply_ai:
        return apply_ai(store, legal, pack_cats, Path(args.apply_ai), report_dir, started)

    # 参考库：默认跨包复用所有已发布包
    ref_dirs = [Path(p) for p in (args.reference or [])] or sorted(
        p for p in PACK_DIR.iterdir() if (p / 'pack.json').exists())
    ref_titles, ref_labels, ref_ids = [], [], set()
    for root in ref_dirs:
        if not (root / 'pack.json').exists():
            continue
        for path in sorted(root.glob('*.json')):
            if path.name == 'pack.json':
                continue
            doc = json.loads(path.read_text(encoding='utf-8'))
            for cat in doc.get('categories', []):
                if cat['id'] == 'uncategorized':
                    continue  # 未分类不是可学习的类
                for sub in cat.get('subcategories', []):
                    for preset in sub.get('presets', []):
                        cls = preset.get('classification') or {}
                        if cls.get('resolution') != 'resolved':
                            continue
                        title = (preset.get('name') or '').strip()
                        if not title or sub['id'] not in legal.get(cat['id'], {}):
                            continue
                        ref_titles.append(title)
                        ref_labels.append(sub['id'])
                        ref_ids.add(preset.get('id'))
    print(f'参考库 {len(set(ref_dirs))} 个包：{len(ref_titles)} 条已分类样本，{len(set(ref_labels))} 个子类')
    if len(ref_titles) < 30:
        print('参考库样本过少，跳过语义阶段，全部条目转大模型')
        return fallback_all(store, report_dir, started, '参考库不足')

    cache_dir = Path(args.cache or (report_dir / '.model-cache'))
    print('  加载编码模型…', flush=True)
    tokenizer, model, err = load_encoder(args.model, cache_dir, args.threads)
    if err:
        print(err)
        return fallback_all(store, report_dir, started, err)
    print('  模型就绪', flush=True)
    cache_path = report_dir / 'semantic-vec-cache.npz'
    all_titles = ref_titles + [r['title'] for r in store.records]
    vectors = encode(all_titles, tokenizer, model, cache_path)
    print(f'  向量就绪 {len(vectors)} 条', flush=True)

    labels = np.array(ref_labels)
    class_count = Counter(ref_labels)
    X = np.vstack([vectors[t] for t in ref_titles])
    # 零样本类：用分类表的“大类名+子类名+描述”做锚点
    seed_labels, seed_vecs = [], []
    if args.seeds:
        anchor_texts = []
        for cat, children in legal.items():
            if cat not in pack_cats or cat == 'uncategorized':
                continue
            for sid, meta in children.items():
                if class_count.get(sid, 0) > 0:
                    continue
                text = f'{cats_meta.get(cat, cat)} {meta["name"]} {meta["desc"]}'
                if text.strip():
                    anchor_texts.append((sid, text))
        if anchor_texts:
            vectors = encode(all_titles + [t for _, t in anchor_texts],
                             tokenizer, model, cache_path)
            for sid, text in anchor_texts:
                seed_labels.append(sid)
                seed_vecs.append(vectors[text] * args.seed_weight)
            X = np.vstack([X] + [v.reshape(1, -1) for v in seed_vecs])
            labels = np.concatenate([labels, np.array(seed_labels)])
            for sid in seed_labels:
                class_count[sid] = max(1, class_count.get(sid, 0))
            print(f'  零样本锚点 {len(seed_labels)} 个（权重 {args.seed_weight}）')

    n_ref = len(ref_titles)
    query_idx = [i for i, r in enumerate(store.records) if r['title']]
    ref_by_title = defaultdict(list)
    for i, title in enumerate(ref_titles):
        ref_by_title[title].append(i)

    decisions, revisions, skipped = [], [], Counter()
    changed = []

    chunk_size = 256
    chunk_state = {'start': -1, 'sims': None}

    def score_row(row, exclude_title):
        """分块计算相似度，避免一次生成 (查询数 × 参考库) 大矩阵。"""
        start = (row // chunk_size) * chunk_size
        if chunk_state['start'] != start:
            block = query_idx[start:start + chunk_size]
            Qb = np.vstack([vectors[store.records[i]['title']] for i in block])
            chunk_state['sims'] = Qb @ X.T
            chunk_state['start'] = start
        sims = chunk_state['sims'][row - start].copy()
        if exclude_title:
            blocked = ref_by_title.get(exclude_title)
            if blocked:
                sims[blocked] = -1.0
        return class_vote(sims, labels, class_count, args.alpha, args.k)

    for row, rec_idx in enumerate(query_idx):
        rec = store.records[rec_idx]
        if rec['resolution'] == 'resolved':
            res = score_row(row, rec['title'])
            if not res:
                skipped['no_neighbor'] += 1
                continue
            gold_cat, pred_cat = rec['cat'], top_level(res['sub'])
            if res['sub'] == rec['sub'] or (gold_cat == pred_cat and res['second']
                                           and top_level(res['second']) == gold_cat):
                continue  # 同类一致，或仅子类分歧，保持不动
            if gold_cat != pred_cat:
                if res['conf'] >= args.cross_conf and res['gap'] >= args.cross_gap:
                    target_cat = pred_cat if pred_cat in pack_cats else gold_cat
                    if target_cat != pred_cat:
                        skipped['target_cat_missing'] += 1
                        continue
                    revisions.append({
                        'id': rec['id'], 'title': rec['title'],
                        'from': f'{rec["cat"]}/{rec["sub"]}',
                        'to': f'{res["sub"]}',
                        'conf': round(res['conf'], 4), 'gap': round(res['gap'], 4),
                        'reason': '留一法跨大类高置信分歧',
                    })
                    changed.append((rec, pred_cat, res['sub'], 'semantic_review', res))
                else:
                    skipped['audit_uncertain'] += 1
            else:
                skipped['sub_only'] += 1
            continue

        # 未分类 / 仅大类
        res = score_row(row, None)
        if not res:
            skipped['no_neighbor'] += 1
            continue
        pred_cat = res['cat']
        same_cat_second = res['second'] and top_level(res['second']) == pred_cat
        confident = res['conf'] >= args.cross_conf and res['gap'] >= args.cross_gap
        if same_cat_second and res['conf'] >= args.accept_conf:
            confident = True
        if pred_cat == 'uncategorized':
            skipped['vote_uncategorized'] += 1
            decisions.append({
                'n': len(decisions), 'id': rec['id'], 'title': rec['title'],
                'current': f'{rec["cat"]}/{rec["sub"]}',
                'guess': res['sub'], 'conf': round(res['conf'], 4),
                'note': '近邻无有效结论',
            })
            continue
        if pred_cat not in pack_cats:
            skipped['target_cat_missing'] += 1
            decisions.append({
                'n': len(decisions), 'id': rec['id'], 'title': rec['title'],
                'current': f'{rec["cat"]}/{rec["sub"]}',
                'guess': res['sub'], 'conf': round(res['conf'], 4),
                'note': '近邻指向本包不存在的大类',
            })
            continue
        if confident:
            changed.append((rec, pred_cat, res['sub'], 'semantic', res))
        elif res['cat_conf'] >= args.catonly_conf and res['cat_gap'] >= args.cat_gap:
            changed.append((rec, pred_cat, f'{pred_cat}_pending', 'semantic_category', res))
        else:
            decisions.append({
                'n': len(decisions), 'id': rec['id'], 'title': rec['title'],
                'current': f'{rec["cat"]}/{rec["sub"]}',
                'guess': res['sub'], 'conf': round(res['conf'], 4),
                'cat_conf': round(res['cat_conf'], 4),
            })

    # 应用改动（先记录原位置，再搬动）
    origin = {id(rec): (rec['cat'], rec['sub']) for rec, *_ in changed}
    store.move([(rec, cat, sub) for rec, cat, sub, _m, _s in changed])
    for rec, cat, sub, method, res in changed:
        cls = dict(rec['preset'].get('classification') or {})
        old_cat, old_sub = origin[id(rec)]
        cls.update({
            'method': method,
            'stage': 'title',
            'resolution': 'resolved' if method in ('semantic', 'semantic_review') else 'category_only',
            'status': 'suggested',
            'reason': f'语义近邻投票：{res["sub"]} 置信 {res["conf"]:.2f} / 领先 {res["gap"]:.2f}',
            'taxonomy_version': store.pack.get('taxonomyVersion', '1.1.0'),
            'semantic': {'model': args.model, 'k': args.k, 'alpha': args.alpha,
                         'confidence': round(res['conf'], 4), 'runner_up': res['second']},
            'subcategories': [{'id': sub, 'name': sub_name(legal, cat, sub)}],
        })
        if method == 'semantic_review':
            cls['previous_location'] = f'{old_cat}/{old_sub}'
        rec['preset']['classification'] = cls
    store.rebuild(legal, cats_meta)

    print(f'改写完成：{len(changed)} 条（含复审改判 {len(revisions)} 条），转大模型 {len(decisions)} 条')

    summary = {
        'input': str(store.root),
        'total': store.total,
        'model': args.model, 'k': args.k, 'alpha': args.alpha,
        'thresholds': {'accept_conf': args.accept_conf, 'catonly_conf': args.catonly_conf,
                       'cat_gap': args.cat_gap, 'cross_conf': args.cross_conf, 'cross_gap': args.cross_gap},
        'reference': {'packs': len(ref_dirs), 'samples': n_ref,
                      'subcategories': len(set(ref_labels)), 'seeds': len(seed_labels)},
        'applied': dict(Counter(c[3] for c in changed)),
        'revisions': len(revisions),
        'to_ai': len(decisions),
        'skipped': dict(skipped),
        'elapsed_seconds': round(time.perf_counter() - started, 2),
        'note': '仅按标题判定；置信度不足一律不猜，残余交大模型。',
    }
    (report_dir / 'semantic-summary.json').write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    write_jsonl(report_dir / 'semantic-revisions.jsonl', revisions)
    write_jsonl(report_dir / 'pending-ai.jsonl', decisions)
    write_taxonomy_options(report_dir / 'taxonomy-options.json', cats_meta, legal, pack_cats)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return summary


def apply_ai(store, legal, pack_cats, decisions_path, report_dir, started):
    decisions = [json.loads(line) for line in decisions_path.read_text(encoding='utf-8').splitlines() if line.strip()]
    by_id = {r['id']: r for r in store.records}
    pending_file = report_dir / 'pending-ai.jsonl'
    if pending_file.exists():
        for line in pending_file.read_text(encoding='utf-8').splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            if 'n' in row and row.get('id'):
                by_id[f'n{row["n"]}'] = by_id.get(row['id'])
    applied, rejected = [], []
    for item in decisions:
        key = item.get('id')
        if key is None and 'n' in item:
            key = f'n{item["n"]}'
        rec = by_id.get(key)
        if not rec:
            rejected.append({'id': item.get('id'), 'why': 'id 不存在'})
            continue
        cat, sub = item.get('category'), item.get('subcategory')
        if cat in ('uncategorized', 'pending', ''):
            rejected.append({'id': item['id'], 'why': '大模型判定为无法分类'})
            continue
        if cat not in pack_cats:
            rejected.append({'id': item['id'], 'why': f'大类 {cat} 不在该包'})
            continue
        if sub not in legal.get(cat, {}):
            rejected.append({'id': item['id'], 'why': f'非法子类 {sub}'})
            continue
        rec['_target'] = (cat, sub)
        applied.append(rec)
    store.move([(r, r['_target'][0], r['_target'][1]) for r in applied])
    for rec in applied:
        cat, sub = rec['_target']
        cls = dict(rec['preset'].get('classification') or {})
        cls.update({
            'method': 'llm',
            'stage': 'title',
            'resolution': 'resolved',
            'status': 'suggested',
            'reason': '规则与语义近邻均无结论，由大模型按标题判定',
            'taxonomy_version': store.pack.get('taxonomyVersion', '1.1.0'),
            'subcategories': [{'id': sub, 'name': sub_name(legal, cat, sub)}],
        })
        rec['preset']['classification'] = cls
        rec.pop('_target', None)
    store.rebuild(legal, {})
    summary = {'applied': len(applied), 'rejected': rejected[:50],
               'rejected_count': len(rejected),
               'elapsed_seconds': round(time.perf_counter() - started, 2)}
    (report_dir / 'ai-apply-summary.json').write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return summary


def fallback_all(store, report_dir, started, why):
    pending = [{'id': r['id'], 'title': r['title'],
                'current': f'{r["cat"]}/{r["sub"]}'}
               for r in store.records if r['resolution'] != 'resolved' and r['title']]
    write_jsonl(report_dir / 'pending-ai.jsonl', pending)
    summary = {'skipped_reason': why, 'to_ai': len(pending),
               'elapsed_seconds': round(time.perf_counter() - started, 2)}
    (report_dir / 'semantic-summary.json').write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return summary


def write_taxonomy_options(path, cats_meta, legal, pack_cats):
    options = {}
    for cat, children in legal.items():
        if cat not in pack_cats:
            continue
        options[cat] = {'name': cats_meta.get(cat, cat),
                        'subcategories': {sid: meta['name'] for sid, meta in children.items()}}
    path.write_text(json.dumps(options, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def write_jsonl(path, rows):
    with open(path, 'w', encoding='utf-8') as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + '\n')


def main():
    parser = argparse.ArgumentParser(description='风格包语义分类（BGE + kNN）')
    parser.add_argument('--input', required=True, help='title_classify.py 产出的 classified/<packId> 目录')
    parser.add_argument('--reference', nargs='*', help='参考库包目录，默认全部 packs/*')
    parser.add_argument('--report-dir', help='报告输出目录，默认 input 的上级')
    parser.add_argument('--model', default=DEFAULTS['model'])
    parser.add_argument('--cache', help='模型与向量缓存目录')
    parser.add_argument('--k', type=int, default=DEFAULTS['k'])
    parser.add_argument('--alpha', type=float, default=DEFAULTS['alpha'])
    parser.add_argument('--accept-conf', type=float, default=DEFAULTS['accept_conf'])
    parser.add_argument('--catonly-conf', type=float, default=DEFAULTS['catonly_conf'])
    parser.add_argument('--cat-gap', type=float, default=DEFAULTS['cat_gap'])
    parser.add_argument('--cross-conf', type=float, default=DEFAULTS['cross_conf'])
    parser.add_argument('--cross-gap', type=float, default=DEFAULTS['cross_gap'])
    parser.add_argument('--threads', type=int, default=0)
    parser.add_argument('--no-seeds', dest='seeds', action='store_false', help='不使用分类表文本锚点')
    parser.add_argument('--seed-weight', type=float, default=DEFAULTS['seed_weight'])
    parser.add_argument('--apply-ai', help='应用大模型判定 JSONL（id/category/subcategory）')
    args = parser.parse_args()
    run(args)


if __name__ == '__main__':
    main()

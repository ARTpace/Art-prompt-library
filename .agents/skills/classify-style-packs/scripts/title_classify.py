"""离线风格分类（默认仅标题）：不调用 AI、不改输入；--write-files 写 JSON 目录，--write-packs 另行打包。"""
import argparse
from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
import time
import zipfile

ROOT = Path(__file__).resolve().parents[4]
RULE_FILE = Path(__file__).with_name('title_rules.json')
TAXONOMY = ROOT / 'docs' / 'style-pack-taxonomy-v1.md'
CONTENT_RULE_FILE = Path(__file__).with_name('content_rules.json')
ENGINE_VERSION = '2.3.0'


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode('utf-8')).hexdigest()


def write_json(path, value):
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temp.replace(path)


def write_jsonl(path, values):
    temp = path.with_suffix(path.suffix + '.tmp')
    with temp.open('w', encoding='utf-8') as stream:
        for value in values:
            stream.write(json.dumps(value, ensure_ascii=False) + '\n')
    temp.replace(path)


def load_taxonomy(path=TAXONOMY):
    text = path.read_text(encoding='utf-8')
    parent_part = text.split('## 2. 大类总表')[1].split('## 3.')[0]
    parents = {id: name.strip() for id, name in re.findall(r'^\| \d+ \| `([^`]+)` \| ([^|]+)\|', parent_part, re.M)}
    sub_part = text.split('## 3.')[1].split('## 13.')[0]
    children = {}
    for id, name in re.findall(r'^\| `([^`]+)` \| ([^|]+)\|', sub_part, re.M):
        parent = next((key for key in sorted(parents, key=len, reverse=True) if id.startswith(key + '_')), None)
        if not parent or id in children:
            raise ValueError('Invalid or duplicate taxonomy ID: ' + id)
        children[id] = {'name': name.strip(), 'parent': parent}
    version = re.search(r'分类表 v(\d+\.\d+)', text)
    if not version or not parents or not children:
        raise ValueError('Taxonomy format changed; inspect the canonical document before proceeding')
    return {'parents': parents, 'children': children, 'version': version[1] + '.0', 'hash': digest(text)}


def load_rules(path, taxonomy):
    data = json.loads(path.read_text(encoding='utf-8'))
    compiled = {}
    for category, entry in data['categories'].items():
        if category not in taxonomy['parents'] or category + '_pending' not in taxonomy['children']:
            raise ValueError('Unknown rule category: ' + category)
        children = {}
        for sub, pattern in entry['subcategories'].items():
            if taxonomy['children'].get(sub, {}).get('parent') != category:
                raise ValueError('Invalid rule subcategory: ' + sub)
            children[sub] = re.compile(pattern, re.I)
        overrides = {}
        for other, pattern in entry.get('overrides', {}).items():
            if other not in data['categories'] or other == category:
                raise ValueError('Invalid category override: ' + other)
            overrides[other] = re.compile(pattern, re.I)
        sub_overrides = {}
        for winner, others in entry.get('sub_overrides', {}).items():
            if winner not in children or any(other not in children or other == winner for other in others):
                raise ValueError('Invalid subcategory override: ' + winner)
            sub_overrides[winner] = others
        compiled[category] = (re.compile(entry['pattern'], re.I), children, overrides, sub_overrides)
    return compiled, data['version'], digest(data)


def classify_title(title, rules):
    hits = [(category, entry[0].search(title)) for category, entry in rules.items()]
    hits = [(category, match) for category, match in hits if match]
    original_hits = len(hits)
    # 明确交付物可覆盖表现媒介；比较或混合任务仍保留冲突，不机械选第一项。
    if not re.search(r'对比|比较|两种|混合|融合|\bversus\b|\bvs\b', title, re.I):
        suppressed = {other for category, _ in hits for other, pattern in rules[category][2].items() if pattern.search(title)}
        hits = [(category, match) for category, match in hits if category not in suppressed]
    if len(hits) != 1:
        return {'new_category': 'uncategorized', 'new_subcategory': 'uncategorized_pending',
                'resolution': 'unresolved', 'reason': '未命中明确规则' if not hits else '大类冲突：' + ', '.join(key for key, _ in hits)}
    category, match = hits[0]
    subs = [(sub, pattern.search(title)) for sub, pattern in rules[category][1].items()]
    subs = [(sub, hit) for sub, hit in subs if hit]
    priority_note = '；按明确交付物优先于媒介' if original_hits > 1 else ''
    if subs:
        ids = {key for key, _ in subs}
        suppressed = {other for winner, others in rules[category][3].items() if winner in ids for other in others}
        preferred = [(key, hit) for key, hit in subs if key not in suppressed]
        sub, hit = (preferred or subs)[0]
        return {'new_category': category, 'new_subcategory': sub, 'new_subcategories': [sub] + [key for key, _ in subs if key != sub], 'resolution': 'resolved',
                'reason': '标题规则证据：' + match[0] + ' / ' + '、'.join(hit[0] for _, hit in subs) + priority_note}
    return {'new_category': category, 'new_subcategory': category + '_pending', 'resolution': 'category_only',
            'reason': '大类证据：' + match[0] + priority_note + ('；子类冲突：' + ', '.join(key for key, _ in subs) if subs else '；未命中明确子类')}


def safe_member(name):
    return isinstance(name, str) and bool(name) and '/' not in name and '\\' not in name and ':' not in name and name not in ('.', '..') and name.endswith('.json')


def load_content_rules(path, taxonomy):
    data = json.loads(path.read_text(encoding='utf-8'))
    compiled = {}
    for category, entry in data['categories'].items():
        if category not in taxonomy['parents'] or not entry['support']:
            raise ValueError('Invalid content category: ' + category)
        children = {}
        for sub, pattern in entry['subcategories'].items():
            if taxonomy['children'].get(sub, {}).get('parent') != category:
                raise ValueError('Invalid content subcategory: ' + sub)
            children[sub] = re.compile(pattern, re.I)
        compiled[category] = (re.compile(entry['anchor'], re.I), [re.compile(pattern, re.I) for pattern in entry['support']], children)
    return compiled, data['version'], digest(data)


def positive_content(prompt):
    # 只读取结构化提示词的明确正向字段，防止 negative_prompt 和示例元数据参与分类。
    decoder = json.JSONDecoder()
    for start in re.finditer(r'\{\s*"', prompt):
        try:
            value, end = decoder.raw_decode(prompt, start.start())
        except ValueError:
            continue
        if prompt[end:].strip().strip('`').strip():
            continue
        if isinstance(value, dict):
            fields = [value[key] for key in ('prompt', 'positive_prompt', 'positive', '提示词', '正向提示词')
                      if isinstance(value.get(key), str)]
            if fields:
                prompt = '\n'.join(fields)
                break
    # 匹配整个正文的正向片段，排除显式负向段和含否定词的子句，宁可少判不反向命中。
    text = re.split(r'negative[ _]*prompt["\']?\s*[:：]|负(?:面|向)提示词["\']?\s*[:：]', prompt, maxsplit=1, flags=re.I)[0]
    clauses = re.split(r'[\n,，;；。!?！？]+|(?<=[a-z])\.(?=\s|$)', text, flags=re.I)
    negative = re.compile(r'\b(?:no|not|without|avoid|exclude|never)\b|\bnon[- ]|不要|避免|禁止|不含|没有|不是|不使用|不需要|不得', re.I)
    return '\n'.join(clause for clause in clauses if not negative.search(clause))


def classify_content(prompt, content_rules, title_rules, category_hint=''):
    text = positive_content(prompt)
    eligible, evidence = [], {}
    for category, (anchor, supports, _) in content_rules.items():
        anchors = list(anchor.finditer(text))
        corroboration = []
        for support in supports:
            match = next((match for match in support.finditer(text) if not any(match.start() < other.end() and other.start() < match.end() for other in anchors)), None)
            if match:
                corroboration.append(match[0])
        if anchors and corroboration:
            eligible.append(category)
            evidence[category] = [anchors[0][0], *corroboration]
    if category_hint:
        category = category_hint
        conflicts = [candidate for candidate in eligible if candidate != category]
        if conflicts:
            return {'new_category': category, 'new_subcategory': category + '_pending', 'resolution': 'category_only',
                    'reason': '正文与标题大类存在冲突：' + ', '.join(conflicts), 'evidence': evidence}
    elif len(eligible) == 1:
        category = eligible[0]
    else:
        return {'new_category': 'uncategorized', 'new_subcategory': 'uncategorized_pending', 'resolution': 'unresolved',
                'reason': '正文缺少独立佐证' if not eligible else '正文大类冲突：' + ', '.join(eligible), 'evidence': evidence}
    entry = content_rules.get(category)
    subs = [(sub, pattern.search(text)) for sub, pattern in entry[2].items()] if entry else []
    subs = [(sub, match) for sub, match in subs if match]
    sub_ids = {sub for sub, _ in subs}
    overrides = title_rules[category][3] if category in title_rules else {}
    suppressed = {other for winner, others in overrides.items() if winner in sub_ids for other in others}
    subs = [(sub, match) for sub, match in subs if sub not in suppressed]
    if len(subs) == 1:
        sub, match = subs[0]
        return {'new_category': category, 'new_subcategory': sub, 'resolution': 'resolved',
                'reason': ('标题大类＋正文子类证据：' if category_hint else '正文任务及独立佐证＋子类证据：') + match[0],
                'evidence': evidence}
    return {'new_category': category, 'new_subcategory': category + '_pending', 'resolution': 'category_only',
            'reason': '正文大类明确；' + ('子类冲突：' + ', '.join(sub for sub, _ in subs) if subs else '未找到明确子类'), 'evidence': evidence}


def read_pack(path):
    if path.is_dir():
        def read(name):
            target = (path / name).resolve()
            target.relative_to(path.resolve())
            return json.loads(target.read_text(encoding='utf-8'))
        manifest = read('pack.json')
        contents = {entry['file']: read(entry['file']) for entry in manifest.get('categories', []) if safe_member(entry.get('file'))}
    else:
        with zipfile.ZipFile(path) as archive:
            if sum(info.file_size for info in archive.infolist()) > 256 * 1024 * 1024:
                raise ValueError('Pack exceeds the 256 MiB uncompressed limit')
            manifests = [name for name in archive.namelist() if name == 'pack.json' or name.endswith('/pack.json')]
            if len(manifests) != 1:
                raise ValueError('Expected exactly one pack.json')
            prefix = manifests[0][:-len('pack.json')]
            if prefix.startswith('/') or '..' in prefix.split('/') or ':' in prefix or '\\' in prefix:
                raise ValueError('Unsafe ZIP prefix')
            manifest = json.loads(archive.read(manifests[0]))
            contents = {entry['file']: json.loads(archive.read(prefix + entry['file'])) for entry in manifest.get('categories', []) if safe_member(entry.get('file'))}
    if manifest.get('kind', 'styles') != 'styles' or manifest.get('schema') != 1:
        raise ValueError('Expected schema 1 styles pack')
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]{1,39}', manifest.get('packId', '')):
        raise ValueError('Invalid pack ID')
    if not manifest.get('categories') or len(contents) != len(manifest['categories']):
        raise ValueError('Empty, duplicate, or unsafe category file declarations')
    records, seen = [], set()
    for entry in manifest['categories']:
        for cat in contents[entry['file']].get('categories', []):
            if cat.get('id') != entry['id']:
                raise ValueError('Manifest/category ID mismatch')
            for sub in cat.get('subcategories', []):
                for item in sub.get('presets', []):
                    id = item.get('id')
                    if not isinstance(id, str) or not id or id in seen:
                        raise ValueError('Missing or duplicate item ID in pack: ' + str(id))
                    if not isinstance(item.get('prompt'), str):
                        raise ValueError('Non-string or missing original prompt: ' + id)
                    if not isinstance(item.get('name', ''), str):
                        raise ValueError('Non-string title: ' + id)
                    seen.add(id)
                    records.append({'pack_id': manifest['packId'], 'file': entry['file'], 'item_id': id,
                                    'old_category': cat['id'], 'old_subcategory': sub['id'],
                                    'invalid_fields': ['prompt'] if not item['prompt'].strip() else [], 'item': item})
    if not records:
        raise ValueError('No presets in pack')
    return manifest, records


def validate_subcategory_memberships(item, category, primary, taxonomy):
    classification = item.get('classification') or {}
    if not isinstance(classification, dict) or 'subcategories' not in classification:
        return
    entries = classification['subcategories']
    if not isinstance(entries, list) or not entries or any(not isinstance(entry, dict) or not isinstance(entry.get('id'), str) for entry in entries):
        raise ValueError('Invalid subcategory memberships: ' + str(item.get('id')))
    ids = [entry['id'] for entry in entries]
    if len(ids) != len(set(ids)) or primary not in ids or any(taxonomy['children'].get(sub, {}).get('parent') != category for sub in ids):
        raise ValueError('Invalid, duplicate or cross-category membership: ' + str(item.get('id')))
    if len(ids) > 1 and any(sub.endswith('_pending') for sub in ids):
        raise ValueError('Pending cannot coexist with resolved memberships: ' + str(item.get('id')))


def create_pack(manifest, records, assignments, taxonomy, destination, directory=False):
    categories = {}
    original = {record['item_id']: record['item'] for record in records}
    for row in assignments:
        item = deepcopy(original[row['item_id']])
        if not row['preserved']:
            item['classification'] = {key: row[key] for key in ('method', 'stage', 'resolution', 'status', 'reason', 'taxonomy_version', 'rules_version')}
            if row.get('evidence'):
                item['classification']['evidence'] = row['evidence']
            item['classification']['subcategories'] = [{'id': sub, 'name': taxonomy['children'][sub]['name']} for sub in row.get('new_subcategories', [row['new_subcategory']])]
        cat, sub = row['new_category'], row['new_subcategory']
        validate_subcategory_memberships(item, cat, sub, taxonomy)
        groups = categories.setdefault(cat, {})
        groups.setdefault(sub, []).append(item)
    result = deepcopy(manifest)
    result.pop('builtin', None)
    result['taxonomyVersion'] = taxonomy['version']
    result['entryCount'] = len(records)
    version = re.fullmatch(r'(\d+)\.(\d+)\.(\d+)', str(result.get('version', '')))
    result['version'] = f'{version[1]}.{version[2]}.{int(version[3]) + 1}' if version else '1.0.1'
    result['categories'] = []
    files = {}
    for cat in taxonomy['parents']:
        if cat not in categories:
            continue
        result['categories'].append({'id': cat, 'name': taxonomy['parents'][cat], 'file': cat + '.json', 'order': len(result['categories']) * 10})
        files[cat + '.json'] = {'categories': [{'id': cat, 'name': taxonomy['parents'][cat], 'subcategories': [
            {'id': sub, 'name': info['name'], 'presets': categories[cat][sub]}
            for sub, info in taxonomy['children'].items() if sub in categories[cat]]}]}
    files['pack.json'] = result
    target = destination / (result['packId'] + ('' if directory else '.zip'))
    temp = target.with_name(target.name + '.tmp')
    if directory:
        # ponytail: 编辑目录不覆盖，避免续跑丢失用户对输出 JSON 的修改。
        if target.exists() or temp.exists():
            raise ValueError('Classified directory already exists: ' + str(target))
        temp.mkdir()
        for name, data in files.items():
            write_json(temp / name, data)
    else:
        with zipfile.ZipFile(temp, 'w', zipfile.ZIP_DEFLATED) as archive:
            for name, data in files.items():
                archive.writestr(name, json.dumps(data, ensure_ascii=False, indent=2))
    _, restored = read_pack(temp)
    restored_items = {row['item_id']: row['item'] for row in restored}
    assert set(original) == set(restored_items), 'Item set changed'
    for id, item in original.items():
        before = {key: value for key, value in item.items() if key != 'classification'}
        after = {key: value for key, value in restored_items[id].items() if key != 'classification'}
        assert before == after, 'Original fields changed: ' + id
    temp.replace(target)
    return str(target.resolve())


def run(inputs, output, write_packs=False, rule_file=RULE_FILE, use_content=False, content_rule_file=CONTENT_RULE_FILE, write_files=False):
    started = time.perf_counter()
    for path in inputs:
        if path.is_dir() and output.resolve().is_relative_to(path.resolve()):
            raise ValueError('Output must be outside the original pack directory')
    taxonomy = load_taxonomy()
    rules, rule_version, rules_hash = load_rules(rule_file, taxonomy)
    content_rules, content_version, content_hash = load_content_rules(content_rule_file, taxonomy) if use_content else ({}, '', '')
    combined_version = rule_version + ('+content-' + content_version if use_content else '')
    packs = [read_pack(path) for path in inputs]
    pack_ids = [manifest['packId'] for manifest, _ in packs]
    if len(set(pack_ids)) != len(pack_ids):
        raise ValueError('Duplicate pack IDs across inputs')
    output.mkdir(parents=True, exist_ok=True)
    cached_path = output / 'assignments.jsonl'
    cached = {row['record_key']: row for row in map(json.loads, cached_path.read_text(encoding='utf-8').splitlines())} if cached_path.is_file() else {}
    rows, pending, conflicts, seen = [], [], [], {}
    cache_hits = 0
    content_cache = {}
    body_evaluated = body_reused = 0
    for manifest, records in packs:
        for record in records:
            item = record['item']
            key = json.dumps([record[field] for field in ('pack_id', 'file', 'old_category', 'old_subcategory', 'item_id')], ensure_ascii=False)
            old_classification = item.get('classification') or {}
            signature = digest([item.get('name', ''), item['prompt'], old_classification, taxonomy['hash'], rules_hash, content_hash, use_content, ENGINE_VERSION])
            previous = cached.get(key)
            valid_old = taxonomy['children'].get(record['old_subcategory'], {}).get('parent') == record['old_category']
            valid_cached = previous and taxonomy['children'].get(previous.get('new_subcategory'), {}).get('parent') == previous.get('new_category')
            if valid_cached and previous.get('signature') == signature:
                row = previous
                cache_hits += 1
            else:
                preserve = valid_old and ((old_classification.get('stage') == 'title' and old_classification.get('status') == 'reviewed') or (use_content and (old_classification.get('status') == 'reviewed' or (old_classification.get('stage') == 'content' and old_classification.get('method') != 'rules'))))
                decision = ({'new_category': record['old_category'], 'new_subcategory': record['old_subcategory'],
                             'resolution': old_classification.get('resolution') or ('unresolved' if record['old_category'] == 'uncategorized' else 'category_only' if record['old_subcategory'].endswith('_pending') else 'resolved'),
                             'reason': '保留已有审核（符合当前证据模式）'} if preserve else classify_title(item.get('name', ''), rules))
                if preserve:
                    saved = old_classification.get('subcategories', [])
                    extra = [entry['id'] for entry in saved if isinstance(entry, dict) and taxonomy['children'].get(entry.get('id'), {}).get('parent') == record['old_category']]
                    decision['new_subcategories'] = list(dict.fromkeys([decision['new_subcategory'], *extra]))
                title_resolution = decision['resolution']
                content_attempted = False
                if use_content and not preserve and decision['resolution'] != 'resolved' and item['prompt'].strip():
                    content_attempted = True
                    hint = decision['new_category'] if decision['resolution'] == 'category_only' else ''
                    body_key = (digest(item['prompt']), hint)
                    if body_key in content_cache:
                        decision = deepcopy(content_cache[body_key])
                        body_reused += 1
                    else:
                        decision = classify_content(item['prompt'], content_rules, rules, hint)
                        content_cache[body_key] = deepcopy(decision)
                        body_evaluated += 1
                decision.setdefault('new_subcategories', [decision['new_subcategory']])
                row = {key: value for key, value in record.items() if key != 'item'} | decision
                row.update({'record_key': key, 'signature': signature, 'title': item.get('name', ''),
                            'title_hash': digest(item.get('name', '')), 'prompt_hash': digest(item['prompt']),
                            'taxonomy_version': taxonomy['version'], 'rules_version': combined_version,
                            'title_resolution': title_resolution, 'content_attempted': content_attempted,
                            'method': old_classification.get('method', 'assisted') if preserve else 'rules',
                            'stage': old_classification.get('stage', 'content') if preserve else 'content' if content_attempted else 'title',
                            'status': old_classification.get('status', 'suggested') if preserve else ('suggested' if decision['resolution'] == 'resolved' else 'needs_review'),
                            'preserved': preserve})
            rows.append(row)
            fingerprint = digest([item['prompt'], row['new_category'], row['new_subcategory']])
            if record['item_id'] in seen and seen[record['item_id']] != fingerprint:
                conflicts.append({'item_id': record['item_id'], 'pack_id': record['pack_id'], 'reason': '跨包同 ID 正文或分类不一致'})
            seen[record['item_id']] = fingerprint
            if row['resolution'] != 'resolved':
                pending.append({'record_key': key, 'item_id': record['item_id'], 'title': item.get('name', ''),
                                'category': row['new_category'], 'subcategory': row['new_subcategory'],
                                'resolution': row['resolution'], 'reason': row['reason'], **({'prompt': item['prompt']} if use_content else {})})
    write_jsonl(cached_path, rows)
    write_jsonl(output / 'pending-titles.jsonl', ({key: value for key, value in row.items() if key != 'prompt'} for row in pending))
    if use_content:
        write_jsonl(output / 'pending-content.jsonl', pending)
    else:
        (output / 'pending-content.jsonl').unlink(missing_ok=True)
    packages = []
    directories = []
    invalid_items = [{'record_key': row['record_key'], 'item_id': row['item_id'], 'fields': row['invalid_fields']} for row in rows if row['invalid_fields']]
    if write_files and not conflicts:
        destination = output / 'classified'
        destination.mkdir(exist_ok=True)
        for manifest, records in packs:
            directories.append(create_pack(manifest, records, [row for row in rows if row['pack_id'] == manifest['packId']], taxonomy, destination, directory=True))
    if write_packs and not conflicts and not invalid_items:
        destination = output / 'packs'
        destination.mkdir(exist_ok=True)
        for manifest, records in packs:
            target = destination / (manifest['packId'] + '.zip')
            if any(target.resolve() == path.resolve() for path in inputs):
                raise ValueError('Refusing to overwrite original input')
            packages.append(create_pack(manifest, records, [row for row in rows if row['pack_id'] == manifest['packId']], taxonomy, destination))
    summary = {'total': len(rows), 'resolution': dict(Counter(row['resolution'] for row in rows)),
               'title_resolution': dict(Counter(row['title_resolution'] for row in rows)),
               'multi_subcategory_items': sum(len(row.get('new_subcategories', [row['new_subcategory']])) > 1 for row in rows),
               'subcategory_memberships': sum(len(row.get('new_subcategories', [row['new_subcategory']])) for row in rows),
               'content_enabled': use_content, 'content_attempted': sum(row['content_attempted'] for row in rows),
               'content_unique_evaluations': body_evaluated, 'content_reuse_hits': body_reused,
               'content_resolved': sum(row['content_attempted'] and row['resolution'] == 'resolved' for row in rows),
               'cache_hits': cache_hits, 'preserved': sum(row['preserved'] for row in rows),
               'categories': dict(Counter(row['new_category'] for row in rows)), 'conflicts': conflicts,
               'invalid_items': invalid_items,
               'packs': packages, 'directories': directories,
               'write_blocked': bool((write_packs and (conflicts or invalid_items)) or (write_files and conflicts)),
               'elapsed_seconds': round(time.perf_counter() - started, 3), 'ai_calls': 0,
               'note': '本地规则建议，不代表人工审核；仅按标题判断，正文只保留与校验' if not use_content else '本地规则建议，不代表人工审核；正文辅助已显式启用'}
    write_json(output / 'summary.json', summary)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, nargs='+', required=True, help='原始包目录或 ZIP，可多个')
    parser.add_argument('--output', type=Path, required=True, help='独立输出目录；相同目录支持缓存复用')
    parser.add_argument('--rules', type=Path, default=RULE_FILE)
    parser.add_argument('--write-packs', action='store_true', help='额外生成分类后的 ZIP 副本，不安装')
    parser.add_argument('--write-files', action='store_true', help='写出分类后的可编辑 JSON 目录，不打包；空正文保留并报告')
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--title-only', action='store_true', help='仅按标题分类（默认），不启用正文辅助')
    mode.add_argument('--content-assisted', action='store_true', help='显式启用历史正文辅助；仅在用户明确要求时使用')
    parser.add_argument('--content-rules', type=Path, default=CONTENT_RULE_FILE)
    args = parser.parse_args()
    summary = run(args.input, args.output, args.write_packs, args.rules, args.content_assisted, args.content_rules, args.write_files)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if summary['write_blocked']:
        raise SystemExit('跨包冲突或不完整条目已记录；未生成分类包')


if __name__ == '__main__':
    main()

"""将已分类的完整 JSON 库按来源拆分；仅变化的平台包递增补丁版本。"""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import re

from build_catalog import main as build_catalog

ROOT = Path(__file__).resolve().parents[1]


def encode(data):
    return (json.dumps(data, ensure_ascii=False, indent=2) + '\n').encode('utf-8')


def split(source):
    source = Path(source).resolve()
    assert not source.is_relative_to(ROOT / 'packs'), '输入应是仓库外保留的完整数据，避免拆分时覆盖输入'
    original = json.loads((source / 'pack.json').read_text(encoding='utf-8'))
    config = json.loads((ROOT / 'platforms.json').read_text(encoding='utf-8'))
    groups = {}
    for entry in original['categories']:
        for cat in json.loads((source / entry['file']).read_text(encoding='utf-8'))['categories']:
            for sub in cat['subcategories']:
                for item in sub['presets']:
                    structured = item.get('source')
                    provider = structured.get('provider') if isinstance(structured, dict) else ''
                    text = str(provider or item.get('description') or '').casefold()
                    platform = next((p['id'] for p in config['platforms'] if any(word.casefold() in text for word in p['match'])), config['defaultPlatform'])
                    groups.setdefault(platform, {}).setdefault(cat['id'], {}).setdefault(sub['id'], []).append(item)
    reports = []
    for platform in config['platforms']:
        pid = platform['id']
        if pid not in groups:
            continue
        pack_id = 'platform-' + pid
        target = ROOT / 'packs' / pack_id
        contents = {}
        manifest = deepcopy(original)
        manifest.update({'packId': pack_id, 'name': platform['name'] + ' 风格包',
                         'description': platform['description'], 'order': platform['order'],
                         'replaces': ['art-canvas-core'], 'categories': []})
        manifest.pop('builtin', None)
        count = 0
        for entry in original['categories']:
            if entry['id'] not in groups[pid]:
                continue
            data = json.loads((source / entry['file']).read_text(encoding='utf-8'))
            cats = []
            for cat in data['categories']:
                if cat['id'] not in groups[pid]:
                    continue
                kept = []
                for sub in cat['subcategories']:
                    items = groups[pid][cat['id']].get(sub['id'])
                    if items:
                        kept.append({**sub, 'presets': items})
                        count += len(items)
                cats.append({**cat, 'subcategories': kept})
            contents[entry['file']] = encode({**data, 'categories': cats})
            manifest['categories'].append(deepcopy(entry))
        manifest['entryCount'] = count
        previous = json.loads((target / 'pack.json').read_text(encoding='utf-8')) if (target / 'pack.json').exists() else None
        manifest['version'] = previous['version'] if previous else '1.1.0'
        changed = not previous or previous != manifest or any(not (target / name).exists() or (target / name).read_bytes() != data for name, data in contents.items())
        if previous and changed:
            version = re.fullmatch(r'(\d+)\.(\d+)\.(\d+)', previous['version'])
            assert version, '平台版本必须是三段数字'
            manifest['version'] = f'{version[1]}.{version[2]}.{int(version[3]) + 1}'
        if changed:
            target.mkdir(parents=True, exist_ok=True)
            for name, data in contents.items():
                (target / name).write_bytes(data)
            (target / 'pack.json').write_bytes(encode(manifest))
            for old in target.glob('*.json'):
                if old.name != 'pack.json' and old.name not in contents:
                    old.unlink()
        reports.append({'packId': pack_id, 'entries': count, 'version': manifest['version'], 'changed': changed})
    print(json.dumps(reports, ensure_ascii=False, indent=2))
    return reports


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True, help='已分类完整 JSON 目录（仓库外）')
    args = parser.parse_args()
    split(args.source)
    build_catalog()

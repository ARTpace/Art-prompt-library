"""校验 packs 下的 JSON 并生成工具可加载的 catalog.json，不生成 ZIP。"""
from collections import Counter
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    entries = []
    all_ids = set()
    for path in sorted((ROOT / 'packs').glob('*/pack.json')):
        manifest = json.loads(path.read_text(encoding='utf-8'))
        assert manifest['packId'] == path.parent.name, 'packId 与目录名不一致'
        files = [path]
        ids = set()
        statuses = Counter()
        empty = []
        for category in manifest['categories']:
            name = category['file']
            assert Path(name).name == name and name.endswith('.json') and '..' not in name and '\\' not in name
            source = path.parent / name
            files.append(source)
            content = json.loads(source.read_text(encoding='utf-8'))
            assert len(content['categories']) == 1 and content['categories'][0]['id'] == category['id']
            for sub in content['categories'][0]['subcategories']:
                for item in sub['presets']:
                    assert item['id'] not in ids and item['id'] not in all_ids, '重复条目 ID：' + item['id']
                    assert isinstance(item['prompt'], str)
                    ids.add(item['id'])
                    statuses[item.get('classification', {}).get('resolution', 'unknown')] += 1
                    if not item['prompt'].strip():
                        empty.append(item['id'])
        assert len(ids) == manifest['entryCount'], 'entryCount 与实际条数不符'
        assert len(files) == len({p.name for p in files}), '重复分类文件'
        all_ids.update(ids)
        entries.append({
            **{k: manifest[k] for k in ('packId', 'name', 'version', 'entryCount')},
            'description': manifest.get('description', ''),
            'path': path.parent.relative_to(ROOT).as_posix(),
            'categoryCount': len(manifest['categories']),
            'sizeBytes': sum(f.stat().st_size for f in files),
            'sha256': {f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in files},
            'classificationSummary': dict(statuses), 'emptyPromptIds': empty,
            'replaces': manifest.get('replaces', []),
            'order': manifest.get('order', 500),
        })
    assert entries, '没有可发布的数据'
    entries.sort(key=lambda entry: (entry['order'], entry['packId']))
    catalog = {'schema': 1, 'name': 'Art Prompt Library', 'totalEntries': len(all_ids), 'packs': entries}
    (ROOT / 'catalog.json').write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'packs': len(entries), 'entries': len(all_ids), 'classification': [e['classificationSummary'] for e in entries]}, ensure_ascii=False))


if __name__ == '__main__':
    main()

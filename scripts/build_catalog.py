"""校验 packs 下的 JSON 并生成工具可加载的 catalog.json，不生成 ZIP。"""
from collections import Counter
import hashlib
import json
import zipfile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.agents' / 'skills' / 'classify-style-packs' / 'scripts'))
from title_classify import load_taxonomy, validate_subcategory_memberships


def content_entries():
    entries = []
    for kind, folder in [('artists', 'artists'), ('characters', 'characters')]:
        base = ROOT / 'libraries' / folder
        for archive in sorted(base.glob('*.zip')):
            # Splitters emit one flat JSON directory per pack; reject unexpected members.
            with zipfile.ZipFile(archive) as zf:
                for name in zf.namelist():
                    parts = name.split('/')
                    assert len(parts) == 2 and parts[0] == archive.stem and parts[1].endswith('.json')
                    assert Path(parts[1]).name == parts[1] and '\\' not in parts[1] and '..' not in parts[1]
                    target = base / archive.stem / parts[1]
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(zf.read(name))
        for path in sorted(base.glob('*/pack.json')):
            manifest = json.loads(path.read_text(encoding='utf-8'))
            assert manifest['kind'] == kind and manifest['packId'] == path.parent.name
            files = sorted(path.parent.glob('*.json'))
            index = json.loads((path.parent / 'index.json').read_text(encoding='utf-8'))
            ids = [item['id'] for item in index['items']]
            assert len(ids) == len(set(ids)) == manifest['entryCount']
            if kind == 'characters':
                import sys
                sys.path.insert(0, str(ROOT / 'tools'))
                from library_formats.paths import detail_filename, detail_shard_of
                shards = {f.name: json.loads(f.read_text(encoding='utf-8')) for f in files if f.name.startswith('detail-')}
                assert all(cid in shards[detail_filename(detail_shard_of(cid))] for cid in ids)
            entries.append({
                **{key: manifest[key] for key in ('packId', 'name', 'version', 'kind', 'entryCount')},
                'description': manifest.get('description', ''),
                'path': path.parent.relative_to(ROOT).as_posix(),
                'order': manifest.get('order', 500),
                'sizeBytes': sum(f.stat().st_size for f in files),
                'sha256': {f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in files},
            })
    return entries


def main():
    taxonomy = load_taxonomy()
    entries = []
    all_ids = set()
    for path in sorted(list((ROOT / 'packs').glob('*/pack.json')) + list((ROOT / 'libraries' / 'tags').glob('*/pack.json'))):
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
                    if manifest.get('kind', 'styles') == 'styles':
                        validate_subcategory_memberships(item, category['id'], sub['id'], taxonomy)
                    ids.add(item['id'])
                    statuses[item.get('classification', {}).get('resolution', 'unknown')] += 1
                    if not item['prompt'].strip():
                        empty.append(item['id'])
        assert len(ids) == manifest['entryCount'], 'entryCount 与实际条数不符'
        assert len(files) == len({p.name for p in files}), '重复分类文件'
        all_ids.update(ids)
        entries.append({
            **{k: manifest[k] for k in ('packId', 'name', 'version', 'entryCount')},
            'kind': manifest.get('kind', 'styles'),
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
    entries.extend(content_entries())
    entries.sort(key=lambda entry: (entry['order'], entry['packId']))
    catalog = {'schema': 1, 'name': 'Art Prompt Library', 'totalEntries': sum(e['entryCount'] for e in entries), 'packs': entries}
    (ROOT / 'catalog.json').write_bytes((json.dumps(catalog, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
    print(json.dumps({'packs': len(entries), 'entries': sum(e['entryCount'] for e in entries), 'classification': [e['classificationSummary'] for e in entries if 'classificationSummary' in e]}, ensure_ascii=False))


if __name__ == '__main__':
    main()

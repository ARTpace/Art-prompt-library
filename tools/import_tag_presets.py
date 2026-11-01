"""将原始标签分类转换为可独立安装的标签包，保留所有内容及原 ID。"""
import argparse
import copy
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
ORDER = ['quality','animals','character','clothing','pose','photography','scene','lighting','effects','objects','misc','celebrity','game_anime','nsfw']

def convert(source):
    total = 0
    for path in sorted(Path(source).glob('*.json')):
        data = copy.deepcopy(json.loads(path.read_text(encoding='utf-8')))
        categories = data.get('categories', [])
        if not categories:
            continue
        seen = set()
        count = 0
        for cat in categories:
            cat['type'] = 'tag'
            for sub in cat.get('subcategories', []):
                for index, item in enumerate(sub.get('presets', [])):
                    original = item.get('id', '')
                    item['original_id'] = original
                    pid = 'tag-' + path.stem + '-' + str(original)
                    if pid in seen:
                        pid += '-' + str(sub.get('id', 'sub')) + '-' + str(index)
                    assert pid not in seen
                    item['id'] = pid
                    item['type'] = 'tag'
                    seen.add(pid)
                    count += 1
        pack_id = 'tags-' + path.stem.replace('_','-')
        target = ROOT / 'libraries' / 'tags' / pack_id
        target.mkdir(parents=True, exist_ok=True)
        category_files = []
        for index, cat in enumerate(categories):
            name = 'category-' + str(index) + '.json'
            (target / name).write_bytes((json.dumps({'categories':[cat]},ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
            category_files.append({'id':cat['id'],'name':cat.get('name',cat['id']),'file':name})
        manifest = {'schema':1,'kind':'tags','packId':pack_id,'name':'标签包 · '+categories[0].get('name',path.stem),
                    'version':'1.0.0','description':'按需安装的标签提示词，保留原分类与完整内容。','entryCount':count,
                    'categories':category_files,'order':1000+(ORDER.index(path.stem) if path.stem in ORDER else 99)}
        (target/'pack.json').write_bytes((json.dumps(manifest,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
        total += count
        print(pack_id, count)
    print('total',total)

if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,default=ROOT/'data/tag-presets-source')
    convert(parser.parse_args().source)

"""下载 CCPrompt 公开图片提示词并生成 Art Canvas 风格包（不自动安装）。

python tools/ccprompt_download.py download --limit 36
python tools/ccprompt_download.py download
python tools/ccprompt_download.py build
python tools/ccprompt_download.py status
使用同一 output 目录可续跑；原始响应保存在 SQLite，图片仅保留远程地址。
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urljoin
from urllib.request import Request, urlopen
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SITE = 'https://ccprompt.com/'
UA = 'ArtCanvas-CCPrompt-Exporter/1.0 (public image prompts; resumable)'


def write_json(path, data):
    path = Path(path)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temp.replace(path)


def open_database(output):
    output.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(output / 'source.sqlite3')
    db.execute('CREATE TABLE IF NOT EXISTS pages (page INTEGER PRIMARY KEY, payload TEXT NOT NULL)')
    db.execute('CREATE TABLE IF NOT EXISTS items (id TEXT PRIMARY KEY, listing TEXT NOT NULL, detail TEXT, error TEXT)')
    db.execute('CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)')
    db.commit()
    return db


def fetch_json(path, params, delay=0.15):
    url = urljoin(SITE, path) + '?' + urlencode(params)
    for attempt in range(4):
        time.sleep(delay)
        try:
            request = Request(url, headers={'User-Agent': UA, 'Referer': SITE + 'gallery.html'})
            with urlopen(request, timeout=35) as response:
                payload = json.load(response)
            if not payload.get('ok'):
                raise ValueError(payload.get('error') or 'Public API returned ok=false')
            auth = payload.get('auth') or {}
            if any(auth.get(key) for key in ('requiresLogin', 'limitReached', 'reachedGuestLimit')):
                raise PermissionError('Public API requires login or reached its guest limit')
            return payload
        except HTTPError as error:
            if error.code in (401, 403):
                raise PermissionError(f'Public API access denied: HTTP {error.code}') from error
            if error.code not in (408, 429, 500, 502, 503, 504) or attempt == 3:
                raise
            retry = error.headers.get('Retry-After', '')
            time.sleep(min(60, int(retry)) if retry.isdigit() else 2 ** (attempt + 1))
        except (URLError, TimeoutError, ValueError):
            if attempt == 3:
                raise
            time.sleep(2 ** (attempt + 1))


def save_page(db, number, payload):
    if payload.get('page') != number or not isinstance(payload.get('items'), list):
        raise ValueError('Unexpected page response; stopping to avoid incomplete paging')
    if number < payload.get('totalPages', number) and not payload['items']:
        raise ValueError('Empty non-final page')
    for item in payload['items']:
        if not isinstance(item.get('id'), str) or not item['id']:
            raise ValueError('Listing item has no stable ID')
        if item.get('mediaType') != 'image':
            raise ValueError('Image feed unexpectedly includes non-image content')
        db.execute('INSERT OR IGNORE INTO items(id, listing) VALUES (?,?)',
                   (item['id'], json.dumps(item, ensure_ascii=False)))
    db.execute('INSERT OR REPLACE INTO pages VALUES (?,?)', (number, json.dumps(payload, ensure_ascii=False)))
    db.commit()


def preset_from_detail(detail):
    prompt = detail.get('prompt')
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError('Detail has no non-empty original prompt')
    if detail.get('mediaType') != 'image':
        raise ValueError('Detail is not an image prompt')
    native_id = detail['id']
    preview = detail.get('thumb') or detail.get('cover') or detail.get('image') or ''
    return {
        'id': 'ccprompt_' + native_id,
        'name': detail.get('title') or detail.get('imageAlt') or native_id,
        'prompt': prompt,
        'negative_prompt': detail.get('negative_prompt') or '',
        'thumbnail': urljoin('https://media.ccprompt.com/', preview) if preview else '',
        'description': 'CCPrompt / 西西提示词',
        'source': {'provider': 'ccprompt', 'external_id': native_id,
                   'url': urljoin(SITE, detail.get('detailUrl') or '/item/' + native_id),
                   'author': detail.get('author') or ''},
        'tags': [],
        'source_tags': detail.get('tags') or [],
        'source_metadata': detail,
        'classification': {'taxonomy_version': '1.0.0', 'method': 'legacy',
                           'status': 'needs_review', 'reason': '网站未提供标准分类，保留原文，待按项目 Skill 审核分类'},
    }


def status(db):
    counts = db.execute('SELECT COUNT(*), SUM(detail IS NOT NULL), SUM(error IS NOT NULL) FROM items').fetchone()
    first = db.execute('SELECT payload FROM pages WHERE page=1').fetchone()
    payload = json.loads(first[0]) if first else {}
    return {'snapshot_total': payload.get('total', 0), 'snapshot_pages': payload.get('totalPages', 0),
            'cached_pages': db.execute('SELECT COUNT(*) FROM pages').fetchone()[0],
            'listed': counts[0], 'downloaded': counts[1] or 0, 'failed': counts[2] or 0}


def build(db, output, pack_size=3000):
    export = output / 'packs'
    export.mkdir(exist_ok=True)
    batch, packages, count = [], [], 0
    def flush():
        number = len(packages) + 1
        pack_id = f'ccprompt-images-{number:03d}'
        manifest = {'schema': 1, 'kind': 'styles', 'packId': pack_id,
                    'name': f'CCPrompt 图片提示词 {number:03d}', 'version': '1.0.0',
                    'dataVersion': datetime.now(timezone.utc).isoformat(), 'taxonomyVersion': '1.0.0',
                    'author': '原作者见每条 source.author', 'description': 'CCPrompt 公开图片提示词采集，待审核分类；预览图片在线加载。',
                    'order': 600 + number, 'entryCount': len(batch),
                    'categories': [{'id': 'uncategorized', 'name': '待分类', 'file': 'uncategorized.json', 'order': 999}]}
        content = {'categories': [{'id': 'uncategorized', 'name': '待分类', 'subcategories': [
            {'id': 'uncategorized_pending', 'name': '待人工判断', 'presets': list(batch)}]}]}
        target = export / f'{pack_id}.zip'
        temp = target.with_suffix('.zip.tmp')
        with zipfile.ZipFile(temp, 'w', zipfile.ZIP_DEFLATED) as archive:
            for name, value in [('pack.json', manifest), ('uncategorized.json', content)]:
                archive.writestr(name, json.dumps(value, ensure_ascii=False, indent=2))
        with zipfile.ZipFile(temp) as archive:
            assert archive.testzip() is None
            restored = json.loads(archive.read('uncategorized.json'))['categories'][0]['subcategories'][0]['presets']
            assert [(p['id'], p['prompt']) for p in restored] == [(p['id'], p['prompt']) for p in batch]
        temp.replace(target)
        packages.append({'file': str(target.resolve()), 'entryCount': len(batch),
                         'sha256': hashlib.sha256(target.read_bytes()).hexdigest()})
        batch.clear()
    for (raw,) in db.execute('SELECT detail FROM items WHERE detail IS NOT NULL ORDER BY id'):
        batch.append(preset_from_detail(json.loads(raw)))
        count += 1
        if len(batch) >= pack_size:
            flush()
    if batch:
        flush()
    info = status(db)
    errors = [{'id': row[0], 'error': row[1]} for row in db.execute('SELECT id,error FROM items WHERE error IS NOT NULL')]
    report = {**info, 'packed': count, 'packages': packages, 'errors': errors,
              'complete': info['cached_pages'] == info['snapshot_pages'] and info['listed'] == info['snapshot_total'] and count == info['listed'] and not errors,
              'classification': '全部保留在待分类；尚未执行 AI 或人工分类',
              'images': '仅保存远程图片地址，不下载图片二进制',
              'updated_at': datetime.now(timezone.utc).isoformat()}
    assert count == info['downloaded']
    write_json(output / 'report.json', report)
    return report


def download(db, output, limit, workers, delay, pack_size):
    def page(number):
        return fetch_json('/api/public/items', {'page': number, 'pageSize': 36, 'media': 'image', 'sort': 'newest'}, delay)
    first = db.execute('SELECT payload FROM pages WHERE page=1').fetchone()
    if not first:
        save_page(db, 1, page(1))
    snapshot = json.loads(db.execute('SELECT payload FROM pages WHERE page=1').fetchone()[0])
    page_size = int(snapshot['pageSize'])
    end = min(snapshot['totalPages'], (limit + page_size - 1) // page_size) if limit else snapshot['totalPages']
    done = {row[0] for row in db.execute('SELECT page FROM pages')}
    pending = [number for number in range(1, end + 1) if number not in done]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        # 每批有限数量任务，避免一次创建几万个 future。
        for start in range(0, len(pending), workers):
            numbers = pending[start:start + workers]
            for number, payload in zip(numbers, pool.map(page, numbers)):
                if payload.get('total') != snapshot['total']:
                    raise ValueError('Website total changed during paging; resume a new snapshot directory to avoid missed items')
                save_page(db, number, payload)
            info = status(db)
            write_json(output / 'progress.json', info)
            print('pages', info, flush=True)
        ids = [row[0] for row in db.execute('SELECT id FROM items ORDER BY id')]
        if limit:
            ids = ids[:limit]
        done_details = {row[0] for row in db.execute('SELECT id FROM items WHERE detail IS NOT NULL')}
        ids = [id for id in ids if id not in done_details]
        def detail(id):
            try:
                payload = fetch_json('/api/public/item', {'id': id}, delay)
                item = payload.get('item')
                if not isinstance(item, dict) or item.get('id') != id:
                    raise ValueError('Detail ID mismatch')
                preset_from_detail(item)
                return id, item, None
            except PermissionError:
                raise
            except Exception as error:
                return id, None, str(error)
        for start in range(0, len(ids), workers):
            for id, item, error in pool.map(detail, ids[start:start + workers]):
                db.execute('UPDATE items SET detail=?,error=? WHERE id=?',
                           (json.dumps(item, ensure_ascii=False) if item else None, error, id))
            db.commit()
            info = status(db)
            print('details', info, flush=True)
            if (start // workers) % 50 == 0:
                write_json(output / 'progress.json', info)
            if (start // workers) % 250 == 0:
                build(db, output, pack_size)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['download', 'build', 'status'])
    parser.add_argument('--output', type=Path, default=ROOT / 'artifacts' / 'ccprompt')
    parser.add_argument('--limit', type=int, default=0, help='0=全部，仅限制本次详情数量；沿用已有缓存')
    parser.add_argument('--workers', type=int, default=4)
    parser.add_argument('--delay', type=float, default=0.15)
    parser.add_argument('--pack-size', type=int, default=3000)
    args = parser.parse_args()
    if args.limit < 0 or not 1 <= args.workers <= 8 or args.delay < 0 or args.pack_size < 1:
        parser.error('limit >= 0, workers 1..8, delay >= 0, pack-size >= 1')
    db = open_database(args.output)
    try:
        if args.command == 'status':
            print(json.dumps(status(db), ensure_ascii=False, indent=2))
        else:
            if args.command == 'download':
                try:
                    download(db, args.output, args.limit, args.workers, args.delay, args.pack_size)
                finally:
                    report = build(db, args.output, args.pack_size)
                    print('saved', json.dumps({k:v for k,v in report.items() if k not in ('packages', 'errors')}, ensure_ascii=False), flush=True)
                if not args.limit and not report['complete']:
                    raise SystemExit('Full snapshot is incomplete; see report.json and resume with the same output directory')
            else:
                print(json.dumps(build(db, args.output, args.pack_size), ensure_ascii=False, indent=2))
    finally:
        db.close()


if __name__ == '__main__':
    main()

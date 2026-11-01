import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile


MODULE = Path(__file__).parents[1] / 'tools' / 'ccprompt_download.py'
spec = importlib.util.spec_from_file_location('ccprompt_download', MODULE)
cc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cc)


class CCPromptDownloadTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.output = Path(self.temp.name)
        self.db = cc.open_database(self.output)
        self.addCleanup(self.db.close)

    def item(self, id='a'):
        return {'id': id, 'title': '原始标题', 'mediaType': 'image',
                'prompt': '  Original prompt\n保持换行与原文  ', 'thumb': 'data/a.jpg',
                'author': 'original author', 'tags': ['网站原标签'],
                'promptEnrichment': {'cleanPrompt': {'zh': '中文版本', 'en': 'English version'}}}

    def test_roundtrip_package_is_importable_and_preserves_original(self):
        items = [self.item('a'), self.item('b')]
        cc.save_page(self.db, 1, {'page': 1, 'pageSize': 36, 'total': 2, 'totalPages': 1, 'items': items})
        for item in items:
            self.db.execute('UPDATE items SET detail=? WHERE id=?', (json.dumps(item), item['id']))
        self.db.commit()
        report = cc.build(self.db, self.output, pack_size=1)
        self.assertTrue(report['complete'])
        self.assertEqual(report['packed'], 2)
        self.assertEqual(len(report['packages']), 2)
        for package, original in zip(report['packages'], items):
            with zipfile.ZipFile(package['file']) as archive:
                data = json.loads(archive.read('uncategorized.json'))
                item = data['categories'][0]['subcategories'][0]['presets'][0]
                self.assertEqual(item['prompt'], original['prompt'])
                self.assertEqual(item['source_metadata'], original)
                self.assertEqual(item['thumbnail'], 'https://media.ccprompt.com/data/a.jpg')
                self.assertEqual(item['classification']['status'], 'needs_review')
            with zipfile.ZipFile(package['file']) as archive:
                manifest = json.loads(archive.read('pack.json'))
            self.assertEqual(manifest['entryCount'], 1)
            self.assertEqual(manifest['kind'], 'styles')

    def test_resume_does_not_download_cached_detail(self):
        original = self.item()
        page = {'ok': True, 'page': 1, 'pageSize': 36, 'total': 1, 'totalPages': 1, 'items': [original]}
        cc.save_page(self.db, 1, page)
        self.db.execute('UPDATE items SET detail=? WHERE id=?', (json.dumps(original), 'a'))
        self.db.commit()
        with patch.object(cc, 'fetch_json', side_effect=AssertionError('cached data must not refetch')):
            cc.download(self.db, self.output, 0, 1, 0, 3000)
        self.assertEqual(cc.status(self.db)['downloaded'], 1)

    def test_missing_prompt_is_recorded_and_report_is_incomplete(self):
        listing = self.item()
        cc.save_page(self.db, 1, {'page': 1, 'pageSize': 36, 'total': 1, 'totalPages': 1, 'items': [listing]})
        with patch.object(cc, 'fetch_json', return_value={'ok': True, 'item': {**listing, 'prompt': ''}}):
            cc.download(self.db, self.output, 0, 1, 0, 3000)
        report = cc.build(self.db, self.output)
        self.assertFalse(report['complete'])
        self.assertEqual(report['failed'], 1)
        self.assertEqual(report['packed'], 0)

    def test_video_is_not_silently_imported_as_image(self):
        with self.assertRaises(ValueError):
            cc.preset_from_detail({**self.item(), 'mediaType': 'video'})


if __name__ == '__main__':
    unittest.main()

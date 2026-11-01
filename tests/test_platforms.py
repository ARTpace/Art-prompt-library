import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import split_platforms
import build_catalog


class PlatformSplitTests(unittest.TestCase):
    def test_split_preserves_fields_and_only_changed_platform_increments_version(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / 'repo'
            root.mkdir()
            source = Path(temp) / 'source'
            source.mkdir()
            config = {'defaultPlatform': 'other', 'platforms': [
                {'id': 'chatgpt', 'name': 'ChatGPT', 'description': 'ChatGPT', 'order': 1, 'match': ['chatgpt']},
                {'id': 'other', 'name': '其它', 'description': '其它', 'order': 2, 'match': []}]}
            (root / 'platforms.json').write_text(json.dumps(config), encoding='utf-8')
            manifest = {'schema': 1, 'packId': 'full-pack', 'name': 'Full', 'version': '1.0.0', 'entryCount': 2,
                        'categories': [{'id': 'painting', 'file': 'painting.json'}]}
            content = {'categories': [{'id': 'painting', 'name': '绘画', 'subcategories': [{'id': 'painting_watercolor', 'name': '水彩', 'presets': [
                {'id': 'a', 'description': 'ChatGPT', 'prompt': 'Original A', 'custom': {'retained': True}},
                {'id': 'b', 'description': 'Other', 'prompt': 'Original B', 'negative_prompt': 'Original negative'}]}]}]}
            (source / 'pack.json').write_text(json.dumps(manifest), encoding='utf-8')
            (source / 'painting.json').write_text(json.dumps(content), encoding='utf-8')
            with patch.object(split_platforms, 'ROOT', root), patch.object(build_catalog, 'ROOT', root), contextlib.redirect_stdout(io.StringIO()):
                first = split_platforms.split(source)
                self.assertTrue(all(row['changed'] for row in first))
                second = split_platforms.split(source)
                self.assertTrue(all(not row['changed'] for row in second))
                kept = (root / 'packs/platform-other/painting.json').read_bytes()
                actual = json.loads(kept)['categories'][0]['subcategories'][0]['presets'][0]
                self.assertEqual(actual, content['categories'][0]['subcategories'][0]['presets'][1])
                content['categories'][0]['subcategories'][0]['presets'][0]['prompt'] = 'Updated A'
                (source / 'painting.json').write_text(json.dumps(content), encoding='utf-8')
                third = split_platforms.split(source)
                self.assertEqual([(r['packId'], r['version'], r['changed']) for r in third],
                                 [('platform-chatgpt', '1.1.1', True), ('platform-other', '1.1.0', False)])
                self.assertEqual((root / 'packs/platform-other/painting.json').read_bytes(), kept)
                build_catalog.main()
                catalog = json.loads((root / 'catalog.json').read_text(encoding='utf-8'))
                self.assertEqual(catalog['totalEntries'], 2)
                self.assertEqual(len(catalog['packs']), 2)
                self.assertTrue(all(p['replaces'] == ['art-canvas-core'] for p in catalog['packs']))


if __name__ == '__main__':
    unittest.main()

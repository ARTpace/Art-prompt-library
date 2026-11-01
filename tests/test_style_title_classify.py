import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import shutil


SCRIPT = Path(__file__).parents[1] / '.agents/skills/classify-style-packs/scripts/title_classify.py'
spec = importlib.util.spec_from_file_location('style_title_classify', SCRIPT)
classifier = importlib.util.module_from_spec(spec)
spec.loader.exec_module(classifier)


class StyleTitleClassifyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'original'
        self.source.mkdir()
        self.output = self.root / 'classified'
        self.taxonomy = classifier.load_taxonomy()
        self.rules, _, _ = classifier.load_rules(classifier.RULE_FILE, self.taxonomy)

    def make_pack(self):
        items = [{'id': str(index), 'name': title, 'prompt': '  原文\n不得修改 ' + str(index),
                  'thumbnail': 'https://example.com/a.png', 'custom': {'unchanged': True}}
                 for index, title in enumerate(['自然光人像摄影', '摄影实验合集', '梦境之光', '水彩人像摄影海报'])]
        manifest = {'schema': 1, 'kind': 'styles', 'packId': 'test-title-pack', 'name': '测试包',
                    'version': '1.0.0', 'entryCount': 4,
                    'categories': [{'id': 'misc', 'name': '综合', 'file': 'misc.json'}]}
        classifier.write_json(self.source / 'pack.json', manifest)
        classifier.write_json(self.source / 'misc.json', {'categories': [{'id': 'misc', 'subcategories': [{'id': 'misc', 'presets': items}]}]})

    def test_default_title_only_ignores_content_and_historical_body_classification(self):
        self.make_pack()
        path = self.source / 'misc.json'
        data = json.loads(path.read_text(encoding='utf-8'))
        cat = data['categories'][0]
        cat['id'] = 'photography'
        cat['subcategories'][0]['id'] = 'photography_portrait'
        items = cat['subcategories'][0]['presets']
        for item in items:
            item['name'] = '梦境之光'
            item['prompt'] = 'A portrait photograph of a person, 85mm lens, studio lighting.'
            item['classification'] = {'method':'manual', 'status':'reviewed', 'stage':'content'}
        classifier.write_json(path, data)
        manifest = json.loads((self.source / 'pack.json').read_text(encoding='utf-8'))
        manifest['categories'][0]['id'] = 'photography'
        classifier.write_json(self.source / 'pack.json', manifest)
        from unittest.mock import patch
        with patch.object(classifier, 'load_content_rules', side_effect=AssertionError('正文规则不得加载')), patch.object(classifier, 'classify_content', side_effect=AssertionError('正文不得参与判断')):
            report = classifier.run([self.source], self.output, write_files=True)
        self.assertFalse(report['content_enabled'])
        self.assertEqual(report['content_attempted'], 0)
        self.assertEqual(report['preserved'], 0)
        self.assertEqual(report['resolution'], {'unresolved':4})
        self.assertFalse((self.output / 'pending-content.jsonl').exists())
        pending = [json.loads(line) for line in (self.output / 'pending-titles.jsonl').read_text(encoding='utf-8').splitlines()]
        self.assertTrue(all('prompt' not in row for row in pending))
        _, records = classifier.read_pack(Path(report['directories'][0]))
        self.assertTrue(all(row['item']['classification']['stage'] == 'title' for row in records))
        self.assertTrue(all(row['item']['prompt'] == items[0]['prompt'] for row in records))

    def test_three_way_routing_and_conflicts(self):
        cases = [('自然光人像摄影', 'photography_portrait', 'resolved'),
                 ('摄影实验合集', 'photography_pending', 'category_only'),
                 ('梦境之光', 'uncategorized_pending', 'unresolved'),
                 ('水彩人像摄影海报', 'commercial_poster', 'resolved'),
                 ('微距珠宝摄影', 'photography_pending', 'category_only'),
                 ('自然光人像', 'uncategorized_pending', 'unresolved'),
                 ('studio product photography', 'photography_product', 'resolved')]
        for title, subcategory, resolution in cases:
            with self.subTest(title=title):
                row = classifier.classify_title(title, self.rules)
                self.assertEqual(row['new_subcategory'], subcategory)
                self.assertEqual(row['resolution'], resolution)

    def test_importable_roundtrip_original_preservation_and_cache(self):
        self.make_pack()
        before = {path.name: path.read_bytes() for path in self.source.iterdir()}
        report = classifier.run([self.source], self.output, write_packs=True)
        self.assertEqual(report['total'], 4)
        self.assertEqual(report['resolution'], {'resolved': 2, 'category_only': 1, 'unresolved': 1})
        self.assertEqual(report['ai_calls'], 0)
        self.assertEqual({path.name: path.read_bytes() for path in self.source.iterdir()}, before)
        imported, imported_items = classifier.read_pack(Path(report['packs'][0]))
        self.assertEqual(imported['entryCount'], 4)
        self.assertEqual(len(imported_items), 4)
        _, old = classifier.read_pack(self.source)
        _, new = classifier.read_pack(Path(report['packs'][0]))
        self.assertEqual({r['item_id']: r['item']['prompt'] for r in old}, {r['item_id']: r['item']['prompt'] for r in new})
        self.assertTrue(all(r['item']['custom']['unchanged'] for r in new))
        self.assertEqual(classifier.run([self.source], self.output)['cache_hits'], 4)
        path = self.source / 'misc.json'
        data = json.loads(path.read_text(encoding='utf-8'))
        data['categories'][0]['subcategories'][0]['presets'][0]['prompt'] += ' changed'
        classifier.write_json(path, data)
        self.assertEqual(classifier.run([self.source], self.output)['cache_hits'], 3)

    def test_content_classification_is_preserved(self):
        self.make_pack()
        path = self.source / 'misc.json'
        data = json.loads(path.read_text(encoding='utf-8'))
        cat = data['categories'][0]
        cat['id'] = 'photography'
        cat['subcategories'][0]['id'] = 'photography_portrait'
        reviewed = {'method': 'manual', 'status': 'reviewed', 'stage': 'content'}
        cat['subcategories'][0]['presets'][2]['classification'] = reviewed
        classifier.write_json(path, data)
        manifest = json.loads((self.source / 'pack.json').read_text(encoding='utf-8'))
        manifest['categories'][0]['id'] = 'photography'
        classifier.write_json(self.source / 'pack.json', manifest)
        report = classifier.run([self.source], self.output, write_packs=True, use_content=True)
        self.assertEqual(report['preserved'], 1)
        _, records = classifier.read_pack(Path(report['packs'][0]))
        item = next(r for r in records if r['item_id'] == '2')
        self.assertEqual(item['old_subcategory'], 'photography_portrait')
        self.assertEqual(item['item']['classification'], reviewed)

    def test_editable_files_preserve_empty_prompts_and_refuse_overwrite(self):
        self.make_pack()
        path = self.source / 'misc.json'
        data = json.loads(path.read_text(encoding='utf-8'))
        data['categories'][0]['subcategories'][0]['presets'][0]['prompt'] = ''
        classifier.write_json(path, data)
        before = {p.name: p.read_bytes() for p in self.source.iterdir()}
        report = classifier.run([self.source], self.output, write_files=True)
        self.assertEqual(report['packs'], [])
        self.assertEqual(len(report['invalid_items']), 1)
        self.assertFalse(report['write_blocked'])
        target = Path(report['directories'][0])
        _, records = classifier.read_pack(target)
        self.assertEqual(len(records), 4)
        self.assertEqual(next(r['item']['prompt'] for r in records if r['item_id'] == '0'), '')
        self.assertTrue(all(r['item']['custom']['unchanged'] for r in records))
        self.assertEqual({p.name: p.read_bytes() for p in self.source.iterdir()}, before)
        self.assertFalse(list(self.output.rglob('*.zip')))
        with self.assertRaisesRegex(ValueError, 'already exists'):
            classifier.run([self.source], self.output, write_files=True)

    def test_invalid_rules_and_input_overwrite_rejected(self):
        self.make_pack()
        with self.assertRaises(ValueError):
            classifier.run([self.source], self.source / 'output')
        invalid = self.root / 'rules.json'
        classifier.write_json(invalid, {'version': '1', 'categories': {'photography': {'pattern': 'test', 'subcategories': {'commercial_poster': 'test'}}}})
        with self.assertRaises(ValueError):
            classifier.load_rules(invalid, self.taxonomy)

    def test_empty_legacy_prompt_is_reported_without_silent_deletion(self):
        self.make_pack()
        path = self.source / 'misc.json'
        data = json.loads(path.read_text(encoding='utf-8'))
        data['categories'][0]['subcategories'][0]['presets'][0]['prompt'] = ''
        classifier.write_json(path, data)
        report = classifier.run([self.source], self.output, write_packs=True)
        self.assertEqual(report['total'], 4)
        self.assertEqual(len(report['invalid_items']), 1)
        self.assertTrue(report['write_blocked'])
        self.assertEqual(report['packs'], [])

    def test_cross_pack_conflict_blocks_writing(self):
        self.make_pack()
        second = self.root / 'second'
        shutil.copytree(self.source, second)
        manifest = json.loads((second / 'pack.json').read_text(encoding='utf-8'))
        manifest['packId'] = 'second-pack'
        classifier.write_json(second / 'pack.json', manifest)
        data = json.loads((second / 'misc.json').read_text(encoding='utf-8'))
        data['categories'][0]['subcategories'][0]['presets'][0]['prompt'] += ' different'
        classifier.write_json(second / 'misc.json', data)
        report = classifier.run([self.source, second], self.output, write_packs=True)
        self.assertEqual(len(report['conflicts']), 1)
        self.assertTrue(report['write_blocked'])
        self.assertEqual(report['packs'], [])

    def test_delivery_priority_aliases_and_ambiguous_cases(self):
        cases = [
            ('vintage watercolor poster', 'commercial_poster'),
            ('3D动漫角色全身渲染', 'digital_3d_character'),
            ('paper-cut illustration', 'uncategorized_pending'),
            ('手工剪纸插画', 'crafts_paper'),
            ('动漫主题插画', 'anime_manga_illustration'),
            ('3D等距室内场景', 'digital_3d_diorama'),
            ('Rococo', 'art_movements_classical'),
            ('MK Vitreous Enamel', 'crafts_metal'),
            ('手机自拍人像', 'photography_portrait'),
            ('摄影与油画风格对比海报', 'uncategorized_pending'),
            ('素描人物跃出纸面的3D幻觉', 'uncategorized_pending'),
            ('咖啡女孩', 'uncategorized_pending'),
            ('梦幻少女', 'uncategorized_pending'),
            ('疯狂吐槽涂鸦与批注', 'uncategorized_pending'),
            ('电影质感冰镇饮料微距特写', 'photography_pending'),
        ]
        for title, expected in cases:
            with self.subTest(title=title):
                self.assertEqual(classifier.classify_title(title, self.rules)['new_subcategory'], expected)

    def test_content_requires_independent_evidence_and_ignores_negatives(self):
        content, _, _ = classifier.load_content_rules(classifier.CONTENT_RULE_FILE, self.taxonomy)
        cases = [
            ('A portrait photograph of a woman, 85mm lens, soft studio lighting.', '', 'photography_portrait'),
            ('Create a watercolor painting on textured paper with visible brush strokes.', '', 'painting_watercolor'),
            ('Design a poster with brand headline typography and a clear layout.', '', 'commercial_poster'),
            ('A portrait of a woman.', 'photography', 'photography_portrait'),
            ('A portrait of a woman.', '', 'uncategorized_pending'),
            ('A photograph.', '', 'uncategorized_pending'),
            ('Blender.', '', 'uncategorized_pending'),
            ('A photograph with a lens of a watercolor painting on paper with brush strokes.', '', 'uncategorized_pending'),
            ('A portrait photograph, 85mm lens. No poster, no typography. Negative prompt: watercolor painting on paper, brush strokes.', '', 'photography_portrait'),
            ('Not a photograph with a lens. No poster with typography. A mysterious dream.', '', 'uncategorized_pending'),
            ('Design a poster with headline typography and brand layout.', 'photography', 'photography_pending'),
            ('使用135mm镜头拍摄时装，光圈f/2.4，工作室照明。', '', 'photography_fashion'),
            ('3D角色，全局照明。', '', 'digital_3d_character'),
            ('3D插画，一个女孩，场景中使用全局照明。', '', 'digital_3d_pending'),
            ('拍摄一位女士，85mm镜头，淡雅妆容。', '', 'photography_pending'),
            ('美妆摄影，拍摄妆容特写，85mm镜头。', '', 'photography_beauty'),
            ('A portrait shot on a camera, 85mm lens.', '', 'photography_portrait'),
            ('不要拍摄时装，不要使用镜头。', '', 'uncategorized_pending'),
            ('```json\n{"negative_prompt":"watercolor painting on paper with brush strokes", "prompt":"portrait photograph, 85mm lens"}\n```', '', 'photography_portrait'),
            ('{subject}, {"prompt":"portrait photograph, 85mm lens", "negative_prompt":"poster with typography", "metadata":"watercolor painting on paper with brush strokes"}', '', 'photography_portrait'),
            ('{"positive_prompt":"3D角色，全局照明", "negative_prompt":"摄影，镜头，肖像"}', '', 'digital_3d_character'),
            ('portrait photograph, 85mm lens, "negative_prompt": "poster with typography"', '', 'photography_portrait'),
        ]
        for prompt, hint, expected in cases:
            with self.subTest(prompt=prompt):
                self.assertEqual(classifier.classify_content(prompt, content, self.rules, hint)['new_subcategory'], expected)

    def test_identical_body_reuse_cache_and_title_only_mode(self):
        self.make_pack()
        path = self.source / 'misc.json'
        data = json.loads(path.read_text(encoding='utf-8'))
        items = data['categories'][0]['subcategories'][0]['presets']
        for item in items:
            item['name'] = '梦境之光'
            item['prompt'] = 'A portrait photograph of a person, 85mm lens, studio lighting.'
        classifier.write_json(path, data)
        report = classifier.run([self.source], self.output, write_packs=True, use_content=True)
        self.assertEqual(report['resolution'], {'resolved': 4})
        self.assertEqual(report['title_resolution'], {'unresolved': 4})
        self.assertEqual(report['content_unique_evaluations'], 1)
        self.assertEqual(report['content_reuse_hits'], 3)
        self.assertEqual(report['ai_calls'], 0)
        self.assertEqual(classifier.run([self.source], self.output, use_content=True)['cache_hits'], 4)
        title_only = classifier.run([self.source], self.output, use_content=False)
        self.assertEqual(title_only['cache_hits'], 0)
        self.assertEqual(title_only['resolution'], {'unresolved': 4})
        _, records = classifier.read_pack(Path(report['packs'][0]))
        self.assertTrue(all(row['item']['classification']['stage'] == 'content' for row in records))
        self.assertTrue(all(row['item']['classification']['status'] == 'suggested' for row in records))
        items[0]['name'] = '插画实验合集'
        classifier.write_json(path, data)
        scoped = classifier.run([self.source], self.output, use_content=True)
        self.assertEqual(scoped['content_unique_evaluations'], 2)
        self.assertEqual(scoped['content_reuse_hits'], 2)
        self.assertEqual(scoped['resolution'], {'category_only': 1, 'resolved': 3})


if __name__ == '__main__':
    unittest.main()

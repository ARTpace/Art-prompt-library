from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools import fooocus_importer as fooocus
from tools.workspace_paths import ROOT, asset_data_dir
from tools.dedupe_styles import config


class LocalWorkspaceTests(unittest.TestCase):
    def test_maintenance_defaults_stay_in_this_repository(self):
        self.assertEqual(config.ART_CANVAS_DIR, ROOT)
        self.assertTrue(config.THUMBS_DIR.is_relative_to(ROOT / 'artifacts'))
        self.assertEqual(Path(asset_data_dir()), ROOT / 'artifacts/assets')
        self.assertEqual(fooocus.TARGET_FILE, ROOT / 'data/style-presets.json')

    def test_fooocus_reads_and_writes_only_local_work_file(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            target = root / 'workspace/data/style-presets.json'
            other = root / 'consumer/data/style-presets.json'
            other.parent.mkdir(parents=True)
            other.write_bytes(b'consumer must remain unchanged')
            with patch.object(fooocus, 'TARGET_FILE', target), patch.object(fooocus, '_USER_DATA', root / 'consumer'):
                self.assertEqual(fooocus.load_presets(), {'categories': []})
                data = {'categories': [], 'custom': {'original': True}}
                fooocus.save_presets(data)
                self.assertEqual(fooocus.load_presets(), data)
            self.assertEqual(other.read_bytes(), b'consumer must remain unchanged')


if __name__ == '__main__':
    unittest.main()

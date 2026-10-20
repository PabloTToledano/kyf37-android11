"""Bundled ROM selection and release integrity checks; no phone access."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from kyf37_resources import bundled_rom
spec = importlib.util.spec_from_file_location('verifier', Path(__file__).resolve().parents[1] / 'verify-release.py')
V = importlib.util.module_from_spec(spec)
spec.loader.exec_module(V)


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.rom = self.root / 'rom/template.zip'
        self.rom.parent.mkdir()
        self.rom.write_bytes(b'public test ROM')
        self.record = {'bytes': self.rom.stat().st_size, 'sha256': hashlib.sha256(self.rom.read_bytes()).hexdigest()}
        (self.root / 'release.json').write_text(json.dumps({'rom': {'path': 'rom/template.zip', 'sha256': self.record['sha256']}, 'files': {'rom/template.zip': self.record}}))

    def test_bundled_rom_selected(self):
        self.assertEqual(bundled_rom(self.root), self.rom)

    def test_tampered_rom_refused(self):
        self.rom.write_bytes(b'altered')
        with self.assertRaisesRegex(RuntimeError, 'SHA-256'):
            bundled_rom(self.root)

    def test_release_verifier_detects_tamper(self):
        self.assertEqual(V.verify(self.root), 1)
        self.rom.write_bytes(b'altered')
        with self.assertRaises(ValueError): V.verify(self.root)

    def test_bundle_cannot_escape_folder(self):
        metadata = json.loads((self.root / 'release.json').read_text())
        metadata['rom']['path'] = '../outside.zip'
        (self.root / 'release.json').write_text(json.dumps(metadata))
        with self.assertRaisesRegex(RuntimeError, 'outside'):
            bundled_rom(self.root)

    def test_unbundled_checkout_uses_download_fallback(self):
        (self.root / 'release.json').unlink()
        self.assertIsNone(bundled_rom(self.root))

"""Download tests use in-memory HTTP responses; no network or phone needed."""
import io
import os
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import kyf37_resources as R


class Response(io.BytesIO):
    url = 'https://example.com/file'


class DownloadTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_verified_cache_never_redownloads(self):
        p = self.root / 'rom.zip'
        p.write_bytes(b'original')
        with patch.object(R.urllib.request, 'urlopen', side_effect=AssertionError('network')):
            self.assertEqual(R.download('https://example.com/rom', p, R.sha256(p)), p)

    def test_bad_download_preserves_old_file(self):
        p = self.root / 'rom.zip'
        p.write_bytes(b'original')
        with patch.object(R.urllib.request, 'urlopen', return_value=Response(b'bad')):
            with self.assertRaisesRegex(ValueError, 'SHA-256'):
                R.download('https://example.com/rom', p, '0' * 64)
        self.assertEqual(p.read_bytes(), b'original')
        self.assertFalse(p.with_name('rom.zip.download').exists())

    def test_http_rejected(self):
        with self.assertRaisesRegex(ValueError, 'HTTPS'):
            R.download('http://example.com/file', self.root / 'file')

    def test_rom_url_requires_published_digest(self):
        with self.assertRaisesRegex(ValueError, 'requires'):
            R.release_rom(self.root, 'https://example.com/rom')

    def test_no_silent_android_version_substitution(self):
        response = Response(json.dumps({'assets': [{'name': 'android10-twrp.zip'}]}).encode())
        with patch.object(R.urllib.request, 'urlopen', return_value=response):
            with self.assertRaisesRegex(RuntimeError, 'no unique Android 11'):
                R.release_rom(self.root)

    def test_windows_platform_tools_layout(self):
        archive = self.root / 'tools.zip'
        with zipfile.ZipFile(archive, 'w') as z:
            z.writestr('platform-tools/adb.exe', b'fake adb')
            z.writestr('platform-tools/AdbWinApi.dll', b'fake dll')
        with patch.object(R.platform, 'system', return_value='Windows'), patch.object(R.platform, 'machine', return_value='AMD64'), patch.object(R, 'download', return_value=archive):
            adb = R.platform_tools(self.root)
        self.assertTrue(Path(adb).is_file())
        self.assertTrue((Path(adb).parent / 'AdbWinApi.dll').is_file())

    @unittest.skipIf(os.name == 'nt', 'Linux executable permission bits')
    def test_linux_adb_is_executable(self):
        archive = self.root / 'tools.zip'
        with zipfile.ZipFile(archive, 'w') as z:
            z.writestr('platform-tools/adb', b'fake adb')
        with patch.object(R.platform, 'system', return_value='Linux'), patch.object(R.platform, 'machine', return_value='x86_64'), patch.object(R, 'download', return_value=archive):
            adb = R.platform_tools(self.root)
        self.assertTrue(Path(adb).stat().st_mode & 0o100)

    def test_zip_path_traversal_rejected(self):
        archive = self.root / 'tools.zip'
        with zipfile.ZipFile(archive, 'w') as z:
            z.writestr('../escaped', b'no')
        with patch.object(R.platform, 'system', return_value='Linux'), patch.object(R.platform, 'machine', return_value='x86_64'), patch.object(R, 'download', return_value=archive):
            with self.assertRaisesRegex(ValueError, 'Unsafe'):
                R.platform_tools(self.root)
        self.assertFalse((self.root.parent / 'escaped').exists())


if __name__ == '__main__':
    unittest.main()

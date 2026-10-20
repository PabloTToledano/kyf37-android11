"""Offline state/backup/resume tests: no ADB, USB or real signing keys."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
crypto = types.ModuleType('kyf37_crypto')
with patch.dict(sys.modules, {'kyf37_crypto': crypto}):
    spec = importlib.util.spec_from_file_location('installer', ROOT / 'kyf37-installer/kyf37_installer.py')
    I = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(I)


class ResumeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        I.WORK = Path(self.tmp.name)
        I.STATE = {'serial': 'TEST1234'}
        I.DRY = False

    def test_dry_run_never_persists_completion(self):
        I.DRY = True
        I.done('root')
        self.assertNotIn('done', I.STATE)
        self.assertFalse((I.WORK / 'state.json').exists())

    def test_completion_is_atomic_and_versioned(self):
        I.done('backup')
        self.assertEqual(json.loads((I.WORK / 'state.json').read_text())['schema'], 2)
        self.assertFalse((I.WORK / 'state.json.tmp').exists())

    def test_adb_always_targets_selected_phone(self):
        I.ADB, I.SERIAL = 'adb', 'TEST1234'
        result = subprocess.CompletedProcess([], 0, 'ok', '')
        with patch.object(I.subprocess, 'run', return_value=result) as run:
            I.adb('get-state')
            self.assertEqual(run.call_args.args[0], ['adb', '-s', 'TEST1234', 'get-state'])
            I.adb('devices')
            self.assertEqual(run.call_args.args[0], ['adb', 'devices'])

    def test_backup_reuses_verified_original_even_if_live_changed(self):
        parts = {n: 512 for n in ('aboot', 'boot', 'recovery', 'keystore', 'misc')}
        manifest = {n: {'bytes': size, 'md5': 'a' * 32} for n, size in parts.items()}
        (I.WORK / 'backup-progress.json').write_text(json.dumps(manifest))
        calls = []
        def su(cmd, **kw):
            calls.append(cmd)
            if cmd.startswith('test -e'): return 'EXISTS'
            if 'md5sum' in cmd: return 'a' * 32 + ' file'
            return ''
        with patch.object(I, 'getprop', return_value='5.1'), patch.object(I, 'ensure_root', return_value=True), patch.object(I, 'sd_path', return_value='/storage/sdcard1'), patch.object(I, 'by_name', return_value=parts), patch.object(I, 'confirm_write', return_value=True), patch.object(I, 'shell', return_value='Filesystem 1K-blocks Used Available Use%\n/card 999999 100 999899 1%'), patch.object(I, 'su', side_effect=su), patch.object(I, 'adb', side_effect=RuntimeError('stop before host copy')):
            with self.assertRaisesRegex(RuntimeError, 'host copy'):
                I.stage_backup()
        self.assertFalse(any(' dd ' in c or '/by-name/' in c for c in calls))

    def test_untracked_backup_is_never_overwritten(self):
        parts = {n: 512 for n in ('aboot', 'boot', 'recovery', 'keystore', 'misc')}
        with patch.object(I, 'getprop', return_value='5.1'), patch.object(I, 'ensure_root', return_value=True), patch.object(I, 'sd_path', return_value='/card'), patch.object(I, 'by_name', return_value=parts), patch.object(I, 'confirm_write', return_value=True), patch.object(I, 'shell', return_value='Filesystem 1K-blocks Used Available Use%\n/card 999999 100 999899 1%'), patch.object(I, 'su', return_value='EXISTS') as su:
            with self.assertRaisesRegex(RuntimeError, 'Untracked existing backup'):
                I.stage_backup()
            self.assertEqual(su.call_count, 1)

    def test_dry_rescue_does_not_wait_or_probe_usb(self):
        I.DRY = True
        with patch.object(I, 'getprop', return_value='5.1'), patch.object(I, 'ensure_root', return_value=True), patch.object(I, 'sd_path', return_value='/card'), patch.object(I, 'pause', side_effect=AssertionError('interactive wait')):
            self.assertTrue(I.stage_sdtest())
        self.assertNotIn('done', I.STATE)

    def run_twrp_retry(self, current, phase_a=False):
        names = ('boot-user-signed.img', 'recovery-stock-user-signed.img', 'keystore-user.img', 'twrp-user-signed.img')
        manifest = {name: {'md5': str(i) * 32} for i, name in enumerate(names, 1)}
        manifest['stock'] = {name: {'md5': '0' * 32} for name in ('boot', 'recovery', 'keystore')}
        (I.WORK / 'images').mkdir()
        (I.WORK / 'images' / 'manifest.json').write_text(json.dumps(manifest))
        I.STATE['done'] = dict.fromkeys(('backup', 'sdtest', 'keys'), 'test')
        calls = []
        def su(cmd, **kw):
            calls.append(cmd)
            if 'md5sum' in cmd:
                return current[cmd.rsplit('/', 1)[-1]] + ' partition'
            if 'phase-b.sh' in cmd:
                return 'TWRP_FLASH_READBACK_VERIFIED'
            raise AssertionError('Unexpected write: ' + cmd)
        with patch.object(I, 'ensure_root', return_value=True), patch.object(I, 'confirm_write', return_value=True), patch.object(I, 'adb', return_value=''), patch.object(I, 'push_script'), patch.object(I, 'su', side_effect=su), patch.object(I, 'getprop', return_value='3.7' if not phase_a else ''), patch.object(I, 'wait_adb', return_value=True), patch.object(I, 'ask', return_value='yes'), patch.object(I.time, 'sleep'):
            result = I.stage_twrp()
        return result, calls

    def test_completed_phase_b_never_rewrites_partitions(self):
        result, calls = self.run_twrp_retry({'boot': '1' * 32, 'recovery': '4' * 32, 'keystore': '3' * 32})
        self.assertTrue(result)
        self.assertFalse(any('sh /data' in c for c in calls))

    def test_completed_phase_a_runs_only_phase_b(self):
        result, calls = self.run_twrp_retry({'boot': '1' * 32, 'recovery': '2' * 32, 'keystore': '3' * 32}, phase_a=True)
        self.assertTrue(result)
        self.assertFalse(any('phase-a.sh' in c for c in calls))
        self.assertEqual(sum('phase-b.sh' in c for c in calls), 1)

    def test_mixed_partition_state_fails_closed(self):
        with self.assertRaisesRegex(RuntimeError, 'partially converted'):
            self.run_twrp_retry({'boot': '0' * 32, 'recovery': '2' * 32, 'keystore': '3' * 32})

    @unittest.skipUnless((ROOT / 'flip_pokedex/dist/FlipPokedex.apk').exists(), 'Full reproduction requires release APK inputs')
    def test_patch_script_is_rerunnable(self):
        p = ROOT / 'kyf37-installer/kyf37_installer.py'
        before = p.read_bytes()
        subprocess.run([sys.executable, str(ROOT / 'device-inspection/fix-kyf37-installer-resume.py')], check=True)
        subprocess.run([sys.executable, str(ROOT / 'device-inspection/fix-kyf37-installer-guards.py')], check=True)
        subprocess.run([sys.executable, str(ROOT / 'device-inspection/fix-kyf37-installer-downloads.py')], check=True)
        subprocess.run([sys.executable, str(ROOT / 'device-inspection/fix-kyf37-installer-release-layout.py')], check=True)
        subprocess.run([sys.executable, str(ROOT / 'device-inspection/fix-kyf37-installer-apps.py')], check=True)
        self.assertEqual(before, p.read_bytes())


if __name__ == '__main__':
    unittest.main()

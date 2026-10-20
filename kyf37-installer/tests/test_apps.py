"""Simulated app installation. No real ADB, USB, credentials or app data."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import kyf37_apps as A


class AppTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.apps = []
        for package, name, version in [('org.kyf37.pokedex', 'Pokedex', 2), ('org.kyf37.walker', 'Walker', 9)]:
            payload = ('fake APK ' + name).encode()
            (self.root / (name + '.apk')).write_bytes(payload)
            self.apps.append({'name': name, 'file': name + '.apk', 'package': package,
                              'versionCode': version, 'versionName': str(version), 'minSdk': 26,
                              'bytes': len(payload), 'sha256': hashlib.sha256(payload).hexdigest()})
        (self.root / 'apps.json').write_text(json.dumps({'apps': self.apps}))
        self.installed = {}
        self.writes = []
        self.checkpoints = {}
        self.fail_walker = False
        self.wrong_hash = False
        self.confirmed = True
        self.properties = {'ro.product.model': 'KYF37', 'sys.boot_completed': '1',
                           'ro.build.version.sdk': '30', 'ro.product.cpu.abilist': 'armeabi-v7a,armeabi'}

    def adb(self, *args, **kw):
        if args == ('get-state',): return 'device'
        self.assertEqual(args[:2], ('install', '-r'))
        self.assertTrue(kw['write'])
        app = next(a for a in self.apps if Path(args[2]).name == a['file'])
        self.writes.append(app['package'])
        if self.fail_walker and app['package'].endswith('.walker'):
            return 'Failure [INSTALL_FAILED_UPDATE_INCOMPATIBLE]'
        self.installed[app['package']] = (app['versionCode'], '0' * 64 if self.wrong_hash else app['sha256'])
        return 'Performing Streamed Install\nSuccess'

    def shell(self, cmd, **kw):
        if cmd.startswith('dumpsys package '):
            package = cmd.split()[-1]
            return 'versionCode=' + str(self.installed[package][0]) if package in self.installed else 'Unable to find package'
        if cmd.startswith('pm path '):
            package = cmd.split()[-1]
            return f'package:/data/app/{package}/base.apk' if package in self.installed else ''
        if cmd.startswith('sha256sum '):
            package = cmd.split('/')[3]
            return self.installed[package][1] + '  base.apk'
        self.fail('Unexpected phone operation: ' + cmd)

    def run_apps(self, dry=False):
        return A.install(self.root, dry=dry, adb=self.adb, shell=self.shell,
                         getprop=lambda key: self.properties.get(key, ''), say=lambda msg: None,
                         confirm=lambda text: self.confirmed,
                         checkpoint=lambda package, entry: self.checkpoints.update({package: entry}))

    def test_install_then_repeat_is_idempotent(self):
        self.assertTrue(self.run_apps())
        self.assertEqual(len(self.writes), 2)
        self.assertTrue(self.run_apps())
        self.assertEqual(len(self.writes), 2)
        self.assertTrue(all(c['status'] == 'verified' for c in self.checkpoints.values()))

    def test_newer_versions_are_kept_without_downgrade(self):
        self.installed = {a['package']: (a['versionCode'] + 1, '0' * 64) for a in self.apps}
        self.assertTrue(self.run_apps())
        self.assertFalse(self.writes)
        self.assertTrue(all(c['status'] == 'kept-newer' for c in self.checkpoints.values()))

    def test_same_version_different_apk_updated(self):
        self.installed = {a['package']: (a['versionCode'], '0' * 64) for a in self.apps}
        self.assertTrue(self.run_apps())
        self.assertEqual(len(self.writes), 2)

    def test_partial_failure_resumes_only_missing_app(self):
        self.fail_walker = True
        with self.assertRaisesRegex(RuntimeError, 'did not report success'):
            self.run_apps()
        self.assertEqual(list(self.checkpoints), ['org.kyf37.pokedex'])
        self.fail_walker = False
        self.assertTrue(self.run_apps())
        self.assertEqual(self.writes.count('org.kyf37.pokedex'), 1)
        self.assertEqual(self.writes.count('org.kyf37.walker'), 2)

    def test_postinstall_hash_failure_does_not_checkpoint(self):
        self.wrong_hash = True
        with self.assertRaisesRegex(RuntimeError, 'verification failed'): self.run_apps()
        self.assertFalse(self.checkpoints)

    def test_corrupt_second_apk_stops_before_first_install(self):
        (self.root / 'Walker.apk').write_bytes(b'corrupt')
        with self.assertRaisesRegex(ValueError, 'checksum mismatch'): self.run_apps()
        self.assertFalse(self.writes)

    def test_dry_run_does_not_contact_phone_or_wait(self):
        with patch.object(A, 'wait_for_android', side_effect=AssertionError('wait')):
            self.assertTrue(self.run_apps(dry=True))
        self.assertFalse(self.writes)
        self.assertFalse(self.checkpoints)

    def test_old_android_refused(self):
        self.properties['ro.build.version.sdk'] = '22'
        with self.assertRaisesRegex(RuntimeError, 'too old'): self.run_apps()
        self.assertFalse(self.writes)

    def test_wrong_phone_refused(self):
        self.properties['ro.product.model'] = 'OTHER'
        with self.assertRaisesRegex(RuntimeError, 'only for KYF37'): self.run_apps()
        self.assertFalse(self.writes)

    def test_boot_timeout_leaves_pending(self):
        with patch.object(A, 'wait_for_android', return_value=False):
            self.assertFalse(self.run_apps())
        self.assertFalse(self.writes)
        self.assertFalse(self.checkpoints)

    def test_cancel_does_not_install(self):
        self.confirmed = False
        self.assertFalse(self.run_apps())
        self.assertFalse(self.writes)

    def test_transient_adb_timeout_during_boot_is_retried(self):
        calls = iter([subprocess.TimeoutExpired('adb', 15), 'device'])
        def adb(*args, **kw):
            result = next(calls)
            if isinstance(result, Exception): raise result
            return result
        with patch.object(A.time, 'sleep'):
            self.assertTrue(A.wait_for_android(adb, lambda name: '1', lambda msg: None))


if __name__ == '__main__':
    unittest.main()

#!/usr/bin/env python3
"""Additional fail-closed installer guards. Offline, rerunnable source changes."""
from pathlib import Path
root = Path(__file__).resolve().parents[1]
p = root / 'kyf37-installer/kyf37_installer.py'
s = p.read_text()
marker = '# Installer safety guards v1'
if marker not in s:
    def change(old, new):
        global s
        if old not in s:
            raise RuntimeError('Source drift: ' + old[:70])
        s = s.replace(old, new)
    change("    total = sum(parts.values())", "    if not getprop('ro.build.version.release').startswith('5.1'):\n        raise RuntimeError('Original firmware backup requires stock Android 5.1; refusing to back up a converted ROM as stock')\n    total = sum(parts.values())")
    change("    if current == phase_a:\n", "    if current not in (phase_a, {n: stock[n]['md5'] for n in ('boot', 'recovery', 'keystore')}):\n        raise RuntimeError('Unexpected or partially converted partition set; preserve backups and investigate before writing')\n    if current == phase_a:\n")
    change("        say('Phase A did not verify; the script restored the previous partitions. Nothing else was changed. Stopping.'); return False", "        say('Phase A did not verify. Rollback may have been attempted; inspect the output and partition hashes before proceeding.'); return False")
    change("        say('Phase B did not verify; recovery was restored. Stopping.'); return False", "        say('Phase B did not verify. Check rollback output and recovery readback before proceeding.'); return False")
    change("    done('rom'); return True", "    say('Install readback verified; Android first-boot and hardware checks remain pending.')\n    done('rom'); return True")
    p.write_text(s + '\n' + marker + '\n')
readme = root / 'kyf37-installer/README.md'
s = readme.read_text()
s = s.replace('if the first boot loops, do a factory reset from TWRP\n  (Wipe).', 'if the first boot loops, preserve userdata and seek help; do not wipe it.')
if '## Safe reruns' not in s:
    s += '''
## Safe reruns

Use the same workspace and `--serial SERIAL` on every run. Only one installer may use a phone workspace at once.
A dry run never marks a stage complete. Old unversioned completion markers are discarded because previous versions
could record dry runs as completed installs. Backups and signing keys are preserved during migration.

* Backups are checkpointed per partition. A rerun checks saved originals against their recorded checksums and skips
  copying them. Existing untracked or damaged backups cause a stop, never an overwrite. The backup stage requires
  stock Android 5.1; never use it to replace the stock backup after conversion.
* Signed images and personalized ZIPs are reused after their inputs and output checksums match. A missing signing
  key never causes the ROM stage to silently create a replacement. Keep the entire per-phone workspace.
* Recovery retries inspect boot/recovery/keystore hashes. A completed phase A resumes at the Android boot check;
  completed phase B skips partition writes and enters recovery. Unexpected or partial partition sets stop for
  investigation. Power loss during a partition write is not automatically recoverable.
* A ROM retry skips sideload when boot and system already match the personalized ZIP. Otherwise sideload must
  succeed and new recovery log output must confirm readback. Installation completion does not prove first boot
  or hardware functionality.
* Single-stage failures return a nonzero exit status. The menu completion timestamps describe successful live
  stages; rerun an individual stage when you want it to recheck its current state.

This workflow remains **unverified end to end on stock hardware**. Offline tests simulate ADB and do not test
USB drivers, diagnostic rooting, bootloader acceptance, rescue behavior or real flash recovery.

Run offline checks with `python3 -m unittest discover -s kyf37-installer/tests -v` from the project root.
Source patches are reproducible with `device-inspection/fix-kyf37-installer-resume.py` followed by
`device-inspection/fix-kyf37-installer-guards.py`.
'''
readme.write_text(s)

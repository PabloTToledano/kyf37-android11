#!/usr/bin/env python3
"""Rerunnable: register the full-emulation mode (EmulatedWalkerActivity + libpwcore.so)."""
from pathlib import Path
root = Path(__file__).resolve().parents[1]
def patch(path, old, new, tag):
    t = path.read_text()
    if tag in t: return
    assert old in t, f'{path.name}: anchor for {tag}'
    path.write_text(t.replace(old, new, 1)); print('applied', tag)
m = root / 'templates/AndroidManifest.xml'
patch(m, '<uses-permission android:name="android.permission.FOREGROUND_SERVICE"/>',
      '<uses-permission android:name="android.permission.FOREGROUND_SERVICE"/>\n  <!-- full-emulation: import the owner\'s ROM dump once --><uses-permission android:name="android.permission.READ_EXTERNAL_STORAGE"/>',
      'full-emulation: import')
patch(m, 'android:extractNativeLibs="true">', 'android:extractNativeLibs="true" android:requestLegacyExternalStorage="true">', 'requestLegacyExternalStorage')
patch(m, '    <service android:name=".StepService"',
      '    <activity android:name=".EmulatedWalkerActivity" android:label="Pokéwalker" android:screenOrientation="portrait" android:exported="false" android:theme="@android:style/Theme.Material.NoActionBar"></activity>\n    <service android:name=".StepService"',
      'EmulatedWalkerActivity" android:label')
b = root / 'tools/build.sh'
patch(b, 'python3 "$ROOT/tools/build_native.py"', 'python3 "$ROOT/tools/build_native.py"\npython3 "$ROOT/tools/stage_pwcore.py"\npython3 "$ROOT/tools/build_pwcore.py"  # full-emulation core',
      'full-emulation core')
patch(b, "    z.write(r/'app/libs/armeabi-v7a/libwalker_ir.so','lib/armeabi-v7a/libwalker_ir.so')",
      "    z.write(r/'app/libs/armeabi-v7a/libwalker_ir.so','lib/armeabi-v7a/libwalker_ir.so')\n    z.write(r/'app/libs/armeabi-v7a/libpwcore.so','lib/armeabi-v7a/libpwcore.so')  # full-emulation",
      "lib/armeabi-v7a/libpwcore.so'")

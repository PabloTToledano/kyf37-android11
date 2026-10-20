#!/usr/bin/env python3
"""Exercise the flash wrapper with a fake ADB; never contacts a device."""
from pathlib import Path
import tempfile,json,subprocess,os,hashlib,re
p=Path(__file__).resolve().parents[2]
boot=p/'kyf37-rom/android11-walker-ir-v6-sd/boot-magisk-owner-signed.img'
audit=json.loads((boot.parent/'magisk-audit/images.json').read_text())
with tempfile.TemporaryDirectory(prefix='kyf37-boot-guard-') as folder:
 r=Path(folder);fake=r/'fake-adb';calls=r/'calls.jsonl'
 fake.write_text('''#!/usr/bin/env python3
import os,json,sys
a=sys.argv[1:];open(os.environ['MOCK_CALLS'],'a').write(json.dumps(a)+'\\n')
cmd=' '.join(a)
if 'get-state' in a:print('recovery')
elif 'sha256sum /dev/block/bootdevice/by-name/system' in cmd:print(os.environ['MOCK_SYSTEM']+'  /dev/block/bootdevice/by-name/system')
elif 'sha256sum /tmp/kyf37-validated-boot.img' in cmd:print(os.environ['MOCK_BOOT']+'  /tmp/kyf37-validated-boot.img')
elif 'sha256sum /dev/block/bootdevice/by-name/recovery' in cmd:print('stable-recovery\\nstable-keystore')
elif 'echo BOOT_READBACK_OK' in cmd:print('BOOT_READBACK_OK')
''');fake.chmod(0o755)
 env=os.environ.copy();env.update(KYF37_ADB=str(fake),MOCK_CALLS=str(calls),MOCK_BOOT=hashlib.sha256(boot.read_bytes()).hexdigest())
 command=[str(p/'flip_pokedex/cache/powershell/runtime/pwsh'),'-NoProfile','-File',str(p/'tools/flash-validated-boot.ps1'),'-Boot',str(boot),'-Audit',str(r/'audit.json'),'-LockOwner','flip-walker-ir']
 for case in ['invalid-boot-audit','wrong-installed-system','matching-images']:
  if calls.exists():calls.unlink()
  report=dict(audit)
  if case=='invalid-boot-audit':report['boot_sha256']='0'*64
  (r/'audit.json').write_text(json.dumps(report))
  env['MOCK_SYSTEM']='0'*64 if case=='wrong-installed-system' else audit['raw_sha256']
  result=subprocess.run(command,env=env,capture_output=True,text=True,timeout=60)
  records=[json.loads(x) for x in calls.read_text().splitlines()] if calls.exists() else []
  writes=[a for a in records if any('dd if=/tmp/kyf37-validated-boot.img' in x for x in a)]
  assert bool(writes)==(case=='matching-images'),(case,result.stdout,result.stderr)
  assert (result.returncode==0)==(case=='matching-images'),(case,result.stderr)
  if case=='invalid-boot-audit':assert records==[]
  if writes:
   destinations=re.findall(r'\bof=([^\s;]+)',' '.join(' '.join(a) for a in records))
   assert set(destinations)<={'/dev/block/bootdevice/by-name/boot','/dev/block/bootdevice/by-name/misc'},destinations
  print('PASS',case,flush=True)
print('BOOT_UPDATE_GUARDS=3; real_phone_accessed=false')

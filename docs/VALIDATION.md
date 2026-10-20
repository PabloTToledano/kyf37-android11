# Verification and limitations

The 2026-10-20 release passed 35 offline installer tests. These cover device selection, dry runs, backup
preservation, signing-phase retries, corrupt-download handling, Windows/Linux tool layouts, ROM selection,
app install retries, app checksum verification, data-preserving updates and refusal to downgrade newer apps.
APK signatures, ROM boot/system payload hashes, per-phone ZIP personalization with a temporary test key,
release file checksums and ZIP CRCs were checked. Linux first-run bootstrap and ADB download/startup were checked.
No owner private key was accessed; no phone was modified during release preparation.

Source-only CI skips the one reproduction test requiring the full binary app inputs. All other installer
unit tests run without USB, credentials, firmware, network access, a signing key or an Android build tree.

Stock-to-custom conversion has not been exercised end to end on a stock KYF37. Native Windows launcher and
driver behavior are unverified. The ROM candidate manifest explicitly reports hardware_verified=false.
Pokédex model accuracy, real-game/Walker infrared exchange, radio features, and complete hardware behavior
are not certified by the packaging or offline installer tests. Keep all existing rollback backups.

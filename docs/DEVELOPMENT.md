# Developer notes and source locations

End users should download the complete release. This Git repository intentionally contains text sources
and metadata only. The ROM, recovery, APKs, platform-tools and host executables are GitHub Release assets.
A source checkout by itself is not an installable phone package.

Run offline installer checks from the repository root:

```sh
python3 -m unittest discover -s kyf37-installer/tests -v
```

`kyf37-installer/` contains the exact installer sources. `flip_pokedex/templates/` and
`flip_walker/templates/` contain canonical app sources; `tools/stage.py` regenerates app source trees.
The app import/build tools and native helper sources are included. Dataset and binary dependency downloads
are handled by their pinned import/build scripts. Full Android builds need the documented Android source
workspace; no one-step ROM rebuild is claimed for this installer repository.

The existing [ROM development repository](https://github.com/PabloTToledano/kyf37_rom) contains the
ROM staging/fix scripts and custom recovery device source. The full upstream bases are
[LineageOS](https://github.com/LineageOS) and [TeamWin](https://github.com/TeamWin).
Magisk source: https://github.com/topjohnwu/Magisk (v23 for stock bootstrap; v30.7 in the supplied ROM).
BusyBox source: https://busybox.net/ (the supplied binary includes its build version).
Zadig/libwdi source: https://github.com/pbatard/libwdi/tree/v1.5.1.
Google platform-tools retain their upstream distribution terms and bundled notices.

Application licenses and third-party source/provenance references are in each app directory.
The app APKs include their original asset/model notices. No private keys, stock partition backups,
calibration images, personal device logs, credentials or host environments belong in this repository.

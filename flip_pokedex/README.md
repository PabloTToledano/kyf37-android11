# Flip Pokédex

An offline Android Pokédex made for the Kyocera KYF37 (480 × 854, Android 10/11,
D-pad and keypad). All app work lives in this folder. No device or protected
partition is modified by the importer, staging or APK build scripts.

## What is included

- 1,025 National species (Gen I-IX) and the **301-entry Black 2 / White 2 Unova dex**,
  including Victini at #000. 84 alternate battle/cosmetic forms, all Gen V. Species
  #650-#1025 (Gen VI-IX) have current stats, types, abilities, newest-game learnsets,
  latest Pokédex text, static front/back sprites (normal and shiny) and latest cries.
  They have no B2W2 entries or animated sprites. ZONA now imports all cached-game
  wild encounters and supplements missing species/version pairs from WikiDex.
- 8,140 sprite assets: 6,636 Gen V (animated front/back, normal/shiny, female variants
  where available) plus 1,504 static Gen VI-IX sprites; 1,049 cries (673 legacy, 376
  latest). Only one animated sprite is decoded at a time, with a 2 MiB list-icon cache.
- B2W2 English entries, types, historical base stats and abilities, Gen V
  defensive matchups, height/weight, breeding metadata, evolution families,
  exact version-group-14 learnsets and an all-game wild encounter location index.
- Number and T9 prefix search, type/collection filters, number/name sorting,
  persistent caught/favorite marks, and Diamond/Platinum/White shell palettes.
- Animated sprites and scan transitions; an animation-off option; an app-owned
  four-corner key guide. No network permission, accounts or WebView.

- Experimental offline photo/artwork identification for 649 species, using a
  bundled INT8 MobileNetV2 and the ARMv7 LiteRT runtime. Camera/import, keypad
  crop, up to three suggestions and explicit confirmation. See
  [classifier implementation](AI-CLASSIFIER.md) for measured accuracy and limits.

## Keys

| Action | Key |
|---|---|
| Move selection / scroll details | D-pad up/down |
| List page / detail tab | D-pad left/right |
| Open entry; switch B2/W2 text; inspect highlighted move | OK |
| Return; erase a search digit first | Clear / Back |
| Search | F1 / **0** on list |
| Options | F2 / **\*** on list; **\*** in an entry |
| Mark caught | F3 / **5** |
| Unova / National | F4 / **#** on list |
| Next detail tab | F4 / D-pad right |
| Identify a photo/artwork | **9** on list, or Options → Identify |
| Move crop; zoom; reset; analyze | D-pad; **2 / 8**; **5**; OK |
| Favorite | **1** |
| Previous / next entry; page list | **2 / 8** |
| Cycle alternate forms | **3** in entry |
| Play legacy cry | **6** in entry |
| Front / back | **7** in entry |
| Female / default sprite | **9** in entry |
| Shiny / normal | F2 / **#** in entry |
| Number / T9-name search | F2 / **\*** while searching |
| Erase search digit | F1 / **#** / Clear while searching |

T9 matches the start of a name: `745` → Pikachu. Number search matches an exact
number in the chosen dex, including `000`. Settings and every feature remain
reachable with D-pad, OK, Clear and numeric keys on existing ROMs that intercept
corner keys. Held OK/corner/digit keys act once; D-pad repeat remains enabled.

## Reproduce

Canonical source files are in `templates/`. **Edit templates, then rerun
`tools/stage.py`**; `app/` is generated. `tools/fetch_data.py` is the rerunnable,
pinned importer; downloaded inputs are cached. It runs without building Android:

```sh
python3 flip_pokedex/tools/stage.py
python3 flip_pokedex/tools/fetch_data.py
python3 flip_pokedex/tools/verify_data.py
```

Spanish text from WikiDex is cached in `cache/es_fill.json`, each entry with its page
URL or its status `translated`. Refresh it with `tools/scrape_es_wikidex*.py --fetch`
(the scrapers rate-limit themselves), then apply the data patches in order:
`tools/apply_wikidex_es.py`, `tools/apply_wikidex_es_gaps.py`, and then the three commands
above. `tools/apply_wikidex_es_gaps.py` adds encounter-area, place, move-text, form and
evolution-condition Spanish; `verify_data.py` fails if any of them falls back to English.

The bundled AI weights must first be exported using the steps in
[AI-CLASSIFIER.md](AI-CLASSIFIER.md); building does not train automatically.
All compilation must use the project lock:

```sh
bash device-inspection/build-locked.sh "$PWD/flip_pokedex/host-test.log" \
  --script "$PWD/flip_pokedex/tools/test-host.sh"
bash device-inspection/build-locked.sh "$PWD/flip_pokedex/build.log" \
  --script "$PWD/flip_pokedex/tools/build.sh"
```

The build uses the project's Android 30 platform jar and JDK11, plus official
Android build-tools 30.0.3 downloaded once into `cache/` and checksum-verified; set
`FLIP_POKEDEX_ANDROID_TREE` to another matching Android source checkout if needed.
The output is `dist/FlipPokedex.apk`, signed with the **public AOSP test key**
for local sideloading. It does not access the owner's recovery signing key.
No Gradle, Maven or full ROM build is needed. The app supports Android 6+.

## ROM integration and the app-specific bottom bar

The marker `assets/kyf37-native-softkeys/package.txt` tells the existing KYF37
framework that this app supplies its own key guide. The app draws its own
Pokédex shell/footer; it does not change the global guide's appearance.

The existing ROM's input policy passes F1–F4 only to an explicit package list.
For full physical-corner-key support in a **future matching ROM build**, stage:

```sh
python3 flip_pokedex/tools/stage.py --tree /path/to/android-tree --keypad-policy
```

This rerunnable script adds only `org.kyf37.pokedex` to that list and stages the
`FlipPokedex` Soong module. Add `FlipPokedex` to `PRODUCT_PACKAGES` only if it
should be bundled in a ROM. The package exception applies only while that app
has focus and native keyguard is unlocked. Authentication and the default dialer
are untouched. Never deploy an isolated framework/SystemUI update to the phone;
use the project's matching-image process. Numeric alternatives work without
this optional policy change.

## Data provenance and limits

Inputs are pinned in `tools/fetch_data.py`; SHA-256 hashes for every asset and
CSV are in `app/assets/data/manifest.json`.

- [PokéAPI data](https://github.com/PokeAPI/pokeapi): commit
  `81d20919845b6a445969b9265aab5cec6b04cece`, version group 14, versions 21/22.
  Past-type, past-stat, past-ability, move-changelog and type-efficacy tables
  restore Gen V values, including no Fairy type and Steel's old resistances.
- [Veekun Pokédex](https://github.com/veekun/pokedex): frozen 2012 commit
  `e71bfba357a85c11ef551262ebab76991f81091f` supplies Gen V species catch rates,
  friendship and breeding metadata. Friendship evolutions use the Gen V 220
  threshold. Later evolution methods are excluded.
- [PokeAPI/sprites](https://github.com/PokeAPI/sprites): commit
  `ba403973fdf9d0ac59175813861e6a1f8ed5020c`, generation-v/black-white directory for
  #1-#649; static `sprites/pokemon` front, shiny, back and back-shiny images for #650-#1025.
- [PokeAPI/cries](https://github.com/PokeAPI/cries): commit
  `b3a9044bb839b5e3152aaa536c7b463a0fcf0140`, legacy set for #1-#649 and the latest set
  for #650-#1025.
- Gen VI-IX data (#650-#1025) uses the same pinned PokeAPI CSVs with their newest
  version group. Matchups for #1-#649 keep the Gen V chart; #650-#1025 use the Gen VI+
  chart with Fairy. Upstream has no Spanish genus or Pokédex text for #899-#1025. Those
  127 species use official Spanish text from the Spanish WikiDex (Escarlata, Púrpura,
  Leyendas: Z-A or Leyendas: Arceus, in that order), stored with source URLs in
  `cache/es_fill.json` by `tools/scrape_es_wikidex.py`; the importer merges it offline.
  The 36 Gen IX abilities (68 species rows) with no Spanish text in PokeAPI are
  translated in that cache file only (`status: "translated"`) and are not shown; they
  keep English text. `tools/apply_national_1025.py` and `tools/apply_es_fill.py` are the
  rerunnable source patches for this extension.

The upstream Gen V sprite collection shares Black/White animation assets; it
**does not guarantee every changed Black 2/White 2 animation**. Female sprites
fall back to the matching default when no alternate image exists. Some species
lack B2W2 flavor text; the app explicitly labels earlier-dex fallback records.
Wild encounters retain game, location/area, method and level range; slot
probabilities and conditional availability are omitted. The screen warns that
conditions may apply. Gifts/events/trades/transfers are excluded. Some old forms have no separate
learnset in the source. Evolution families provide source conditions, not a
walkthrough of every in-game special case. No game ROM is downloaded or used.

Pokémon names, characters, sprites and cries belong to Nintendo, Creatures and
GAME FREAK and their respective contributors. This is an unofficial personal
fan app; public availability is not a blanket redistribution license. See
`THIRD_PARTY.md` for repository attribution and license references.

## Validation status

See `VALIDATION.md` for concrete build and emulator evidence. An APK or emulator
result is **not hardware verification**. Installation on the KYF37 requires
checking `tools/phone-lock.ps1 status`, other agents' current logs, and holding
the phone lock. The scripts here do not install, reboot, flash or wipe the phone.

## Camera/artwork recognition

[AI-CLASSIFIER.md](AI-CLASSIFIER.md) documents the implemented offline classifier,
reproduction and hardware acceptance gates. [MODEL-CARD.md](MODEL-CARD.md) reports
held-out INT8 accuracy and limitations. The original plan remains in
[AI-CLASSIFIER-PLAN.md](AI-CLASSIFIER-PLAN.md) as historical context.

### Encounter areas for all games (offline)

`tools/scrape_wikidex_encounters.py --fetch` walks WikiDex location categories for
Kanto, Johto, Hoenn, Sinnoh, Teselia, Kalos, Alola, Galar, Paldea and Hisui, then
caches the main-series `Localización` template of all 1025 species. Every original
API response and its query are saved under `cache/wikidex-encounters/raw/`.
Requests are sequential, at least 1.5 seconds apart, with the existing polite
import User-Agent. Rerunning resumes from raw cache; omit `--fetch` for offline
reconstruction. No original cached data is deleted.

Run `python3 tools/apply_all_game_encounters.py` **after older source apply scripts**.
It patches the generator/UI idempotently and applies cached CSV/WikiDex encounter
data to the generated assets without downloading sprites or rebuilding other data.
The generator also invokes this offline apply step at its end. Build/stage never
needs WikiDex. `python3 tools/test_encounters.py` validates the generated rows.

ZONA: **OK** selects the next game group, **0** the previous; **up/down** pages
three areas at a time. Left/right still select tabs. Every row retains its exact
version, including exclusives. All cached versions appear in the selector, with
`Sin datos para este juego` for empty species/form/game combinations.

Rows are a compact location index: exact duplicate version/area/method/level rows
are removed; encounter chances and conditional availability are not represented.
The screen warns that conditions may apply. Gifts/trades and other distribution
methods are excluded. WikiDex supplements use only explicit wild-location links
in its main-series template, validated against the location category inventory
and cached per-page categories (including redirected aliases);
unspecified levels/methods remain unspecified. Explicit short region-wide
habitat prose is retained; raids with no place specified say so. Regional forms are not inferred
from a species page. Noroteo and Biodomo location categories assign explicit Scarlet/Violet
DLC locations to their corresponding versions; explicitly dimensional Z-A
locations are assigned to Mega Dimension. Ambiguous DLC clauses are not inferred.
Spanish names retain per-location provenance/status in
`cache/wikidex-encounters/resolved-names.json`; unmatched names are marked
`translated`. Unmatched detailed subareas retain a stable numeric sector label
rather than an invented translation. Coverage totals are in
`cache/wikidex-encounters/report.json`.

# Attribution

Public data sources are downloaded directly and cached, not scraped from sites
that require an account. Pins and asset hashes are recorded in the import
manifest. Upstream repositories and their licensing/attribution notices:

- PokéAPI: https://github.com/PokeAPI/pokeapi (BSD-3-Clause project code).
- Veekun Pokédex: https://github.com/veekun/pokedex (MIT project code; see LICENSE).
- Pokémon sprites: https://github.com/PokeAPI/sprites, including the original
  game sprites and community-contributor credits in that repository's README.
- Pokémon cries: https://github.com/PokeAPI/cries.

Repository code licenses do not transfer ownership of Pokémon artwork/audio.
Pokémon © Nintendo / Creatures Inc. / GAME FREAK inc. Original rights and upstream
credits remain with their owners. Flip Pokédex has no affiliation with them.
The icon and shell layout are newly drawn vector/Canvas UI. Game ROMs, firmware,
and private signing credentials are not inputs or bundled assets.


AI feature additions:

- Google LiteRT 1.4.2 Interpreter/API, official Maven AARs, SHA-256 pinned in
  `tools/ml/prepare_runtime.py`. Apache-2.0 and embedded third-party notices
  are preserved in APK assets `ml/licenses/`.
- Keras/TensorFlow MobileNetV2 ImageNet initialization; trained and INT8-converted
  locally. Pipeline and dependency pins are in `tools/ml/`.
- JJMack/pokemon-classification-gen1-9, revision
  `959ff557b102fc3b4f912d0ca769273be5b9ca7f`, CC-BY-NC-SA-4.0 per dataset card.
  Model distribution is treated as noncommercial, share-alike; original artwork
  rights remain with their owners.
- uoft-cs/cifar10 generic-object negatives, revision
  `0b2714987fa478483af9968de7c934580d0bb9a2`. Original CIFAR-10 by Alex
  Krizhevsky, Vinod Nair and Geoffrey Hinton, University of Toronto.

See `AI-CLASSIFIER.md` and bundled `ml/model.json` for provenance, download
hashes, split counts and limitations. Public download availability is not an
independent audit of every image's rights or provenance.

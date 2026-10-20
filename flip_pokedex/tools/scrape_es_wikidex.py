#!/usr/bin/env python3
"""Fill Spanish Pokedex text that the pinned PokeAPI CSVs lack, from the Spanish WikiDex.

Writes cache/es_fill.json (every value carries its source URL). Run it with --fetch to refresh the
cache from the network; without --fetch it only reports what is missing. tools/fetch_data.py merges
the cache offline, so the build never needs the network.

Only official in-game text is written as a usable entry: the Spanish Pokedex text from the newest
main-series game listed (Escarlata, Púrpura, Leyendas: Z-A, Leyendas: Arceus, Escudo, Espada, then BDSP). Entries that must be
translated are recorded under "translated" in the cache and are never shown in the app.
"""
import argparse, csv, html, json, re, time, urllib.parse, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / 'cache'
OUT = CACHE / 'es_fill.json'
UA = 'FlipPokedex-offline-import/1.0 (personal offline dex; contact: owner)'
GAME_ORDER = ['Escarlata', 'Púrpura', 'Leyendas: Z-A', 'Leyendas: Arceus', 'Escudo', 'Espada', 'Diamante Brillante', 'Perla Reluciente']
# WikiDex writes this instead of text when a game has no entry for the species.
PLACEHOLDER = re.compile(r'(^No hay entrada|no aparece en|^Sin entrada|^No existe)', re.I)
SITE = 'https://www.wikidex.net/wiki/'

# English short text (as in PokeAPI) -> Spanish translation, keyed by English ability name: (name_es, text_es).
ABILITY_EN = {
    'Anger Shell': 'When an attack causes its HP to drop to half or less, the Pokémon gets angry. This lowers its Defense and Sp. Def stats but boosts its Attack, Sp. Atk, and Speed stats.',
    'Armor Tail': "The mysterious tail covering the Pokémon's head makes opponents unable to use priority moves against the Pokémon or its allies.",
    'Beads of Ruin': "The power of the Pokémon's ruinous beads lowers the Sp. Def stats of all Pokémon except itself.",
    'Commander': 'When the Pokémon enters a battle, it goes inside the mouth of an ally Dondozo if one is on the field. The Pokémon then issues commands from there.',
    'Costar': "When the Pokémon enters a battle, it copies an ally's stat changes.",
    'Cud Chew': 'When the Pokémon eats a Berry, it will regurgitate that Berry at the end of the next turn and eat it one more time.',
    'Earth Eater': 'If hit by a Ground-type move, the Pokémon has its HP restored instead of taking damage.',
    'Electromorphosis': 'The Pokémon becomes charged when it takes damage, boosting the power of the next Electric-type move the Pokémon uses.',
    'Good as Gold': "A body of pure, solid gold gives the Pokémon full immunity to other Pokémon's status moves.",
    'Guard Dog': 'Boosts the Pokémon’s Attack stat if intimidated. Moves and items that would force the Pokémon to switch out also fail to work.',
    'Hadron Engine': 'Turns the ground into Electric Terrain when the Pokémon enters a battle. The futuristic engine within the Pokémon also boosts its Sp. Atk stat on Electric Terrain.',
    'Hospitality': "When the Pokémon enters a battle, it showers its ally with hospitality, restoring a small amount of the ally's HP",
    'Lingering Aroma': "Contact with the Pokémon changes the attacker's Ability to Lingering Aroma.",
    'Mycelium Might': 'The Pokémon will always act more slowly when using status moves, but these moves will be unimpeded by the Ability of the target.',
    'Opportunist': "If an opponent's stat is boosted, the Pokémon seizes the opportunity to boost the same stat for itself.",
    'Orichalcum Pulse': 'Turns the sunlight harsh when the Pokémon enters a battle. The ancient pulse thrumming through the Pokémon also boosts its Attack stat in harsh sunlight.',
    'Poison Puppeteer': "Pokémon poisoned by Pecharunt's moves will also become confused.",
    'Protosynthesis': "Boosts the Pokémon's most proficient stat in harsh sunlight or if the Pokémon is holding Booster Energy.",
    'Purifying Salt': "The Pokémon's pure salt protects it from status conditions and halves the damage taken from Ghost-type moves.",
    'Quark Drive': "Boosts the Pokémon's most proficient stat on Electric Terrain or if the Pokémon is holding Booster Energy.",
    'Rocky Payload': 'Powers up Rock-type moves.',
    'Seed Sower': 'Turns the ground into Grassy Terrain when the Pokémon is hit by an attack.',
    'Sharpness': 'Powers up slicing moves.',
    'Supersweet Syrup': 'Lowers the evasion of opposing Pokémon by 1 stage when first sent into battle',
    'Supreme Overlord': 'When the Pokémon enters a battle, its Attack and Sp. Atk stats are slightly boosted for each of the allies in its party that have already been defeated.',
    'Sword of Ruin': "The power of the Pokémon's ruinous sword lowers the Defense stats of all Pokémon except itself.",
    'Tablets of Ruin': "The power of the Pokémon's ruinous wooden tablets lowers the Attack stats of all Pokémon except itself.",
    'Tera Shift': 'When the Pokémon enters a battle, it absorbs the energy around itself and transforms into its Terastal Form.',
    'Thermal Exchange': 'Boosts the Attack stat when the Pokémon is hit by a Fire-type move. The Pokémon also cannot be burned.',
    'Toxic Chain': "The power of the Pokémon's toxic chain may badly poison any target the Pokémon hits with a move",
    'Toxic Debris': 'Scatters poison spikes at the feet of the opposing team when the Pokémon takes damage from physical moves.',
    'Vessel of Ruin': "The power of the Pokémon's ruinous vessel lowers the Sp. Atk stats of all Pokémon except itself.",
    'Well-Baked Body': 'The Pokémon takes no damage when hit by Fire-type moves. Instead, its Defense stat is sharply boosted.',
    'Wind Power': 'The Pokémon becomes charged when it is hit by a wind move, boosting the power of the next Electric-type move the Pokémon uses.',
    'Wind Rider': "Boosts the Pokémon's Attack stat if Tailwind takes effect or if the Pokémon is hit by a wind move. The Pokémon also takes no damage from wind moves.",
    'Zero to Hero': 'The Pokémon transforms into its Hero Form when it switches out.',
}
ABILITY_TRANSLATED = {
    'Anger Shell': ('Coraza Ira', 'Cuando un ataque reduce sus PS a la mitad o menos, el Pokémon se enfurece. Esto reduce su Defensa y Defensa Esp., pero aumenta su Ataque, Ataque Esp. y Velocidad.'),
    'Armor Tail': ('Cola Armadura', 'La misteriosa cola que cubre la cabeza del Pokémon impide que los rivales usen movimientos de prioridad contra él o sus aliados.'),
    'Beads of Ruin': ('Abalorio Debacle', 'El poder de las cuentas de la debacle del Pokémon reduce la Defensa Esp. de todos los demás Pokémon.'),
    'Commander': ('Comandar', 'Al entrar en combate, si hay un Dondozo aliado en el campo, este Pokémon se mete en su boca y da órdenes desde allí.'),
    'Costar': ('Unísono', 'Al entrar en combate, copia los cambios de características de un aliado.'),
    'Cud Chew': ('Rumia', 'Cuando el Pokémon come una baya, la regurgita al final del siguiente turno y se la vuelve a comer.'),
    'Earth Eater': ('Geofagia', 'Si le golpea un movimiento de tipo Tierra, el Pokémon recupera PS en lugar de recibir daño.'),
    'Electromorphosis': ('Dinamo', 'El Pokémon se carga al recibir daño, lo que aumenta la potencia del siguiente movimiento de tipo Eléctrico que use.'),
    'Good as Gold': ('Cuerpo Áureo', 'Un cuerpo de oro puro y sólido hace al Pokémon totalmente inmune a los movimientos de estado de otros Pokémon.'),
    'Guard Dog': ('Perro Guardián', 'Aumenta su Ataque si se le aplica Intimidación. Los movimientos y objetos que obligarían al Pokémon a cambiar también fallan.'),
    'Hadron Engine': ('Motor Hadrónico', 'Al entrar en combate, convierte el terreno en Campo Eléctrico. El motor futurista del Pokémon también aumenta su Ataque Esp. en Campo Eléctrico.'),
    'Hospitality': ('Hospitalidad', 'Al entrar en combate, brinda hospitalidad a su aliado y le restaura una pequeña cantidad de PS.'),
    'Lingering Aroma': ('Olor Persistente', 'El contacto con el Pokémon cambia la habilidad del atacante a Olor Persistente.'),
    'Mycelium Might': ('Poder Fúngico', 'El Pokémon siempre actúa más lento al usar movimientos de estado, pero estos no se ven afectados por la habilidad del objetivo.'),
    'Opportunist': ('Oportunista', 'Si una característica de un rival aumenta, el Pokémon aprovecha la ocasión para aumentar la misma característica propia.'),
    'Orichalcum Pulse': ('Latido Oricalco', 'Al entrar en combate, el sol se vuelve intenso. El pulso antiguo que recorre al Pokémon también aumenta su Ataque con sol intenso.'),
    'Poison Puppeteer': ('Títere Tóxico', 'Los Pokémon envenenados por los movimientos de Pecharunt también quedan confundidos.'),
    'Protosynthesis': ('Paleosíntesis', 'Aumenta su característica más destacada con sol intenso o si lleva equipada la Energía Potenciadora.'),
    'Purifying Salt': ('Sal Purificadora', 'La sal pura del Pokémon lo protege de los estados alterados y reduce a la mitad el daño de los movimientos de tipo Fantasma que recibe.'),
    'Quark Drive': ('Carga Cuark', 'Aumenta su característica más destacada en Campo Eléctrico o si lleva equipada la Energía Potenciadora.'),
    'Rocky Payload': ('Transportarrocas', 'Potencia los movimientos de tipo Roca.'),
    'Seed Sower': ('Disemillar', 'Al recibir un ataque, convierte el terreno en Campo Hierba.'),
    'Sharpness': ('Cortante', 'Potencia los movimientos de corte.'),
    'Supersweet Syrup': ('Néctar Dulce', 'Al entrar en combate, reduce en 1 nivel la evasión de los Pokémon rivales.'),
    'Supreme Overlord': ('General Supremo', 'Al entrar en combate, su Ataque y Ataque Esp. aumentan ligeramente por cada aliado debilitado de su equipo.'),
    'Sword of Ruin': ('Espada Debacle', 'El poder de la espada de la debacle del Pokémon reduce la Defensa de todos los demás Pokémon.'),
    'Tablets of Ruin': ('Tablilla Debacle', 'El poder de las tablillas de la debacle del Pokémon reduce el Ataque de todos los demás Pokémon.'),
    'Tera Shift': ('Teracambio', 'Al entrar en combate, absorbe la energía de su entorno y se transforma en su Forma Teracristal.'),
    'Thermal Exchange': ('Termoconversión', 'Aumenta su Ataque cuando le golpea un movimiento de tipo Fuego. Además, no puede sufrir quemaduras.'),
    'Toxic Chain': ('Cadena Tóxica', 'El poder de la cadena tóxica del Pokémon puede envenenar gravemente a cualquier objetivo que golpee con un movimiento.'),
    'Toxic Debris': ('Capa Tóxica', 'Esparce púas tóxicas a los pies del equipo rival cuando recibe daño de movimientos físicos.'),
    'Vessel of Ruin': ('Caldero Debacle', 'El poder del caldero de la debacle del Pokémon reduce el Ataque Esp. de todos los demás Pokémon.'),
    'Well-Baked Body': ('Cuerpo Horneado', 'El Pokémon no recibe daño de movimientos de tipo Fuego. En su lugar, su Defensa aumenta mucho.'),
    'Wind Power': ('Energía Eólica', 'El Pokémon se carga cuando le golpea un movimiento de viento, lo que aumenta la potencia de su siguiente movimiento de tipo Eléctrico.'),
    'Wind Rider': ('Surcavientos', 'Aumenta su Ataque si entra en efecto Viento Afín o si le golpea un movimiento de viento. Además, no recibe daño de movimientos de viento.'),
    'Zero to Hero': ('Cambio Heroico', 'El Pokémon se transforma en su Forma Heroica al cambiar de Pokémon.'),
}


def text_of(fragment):
    fragment = re.sub(r'<style.*?</style>|<script.*?</script>', '', fragment, flags=re.S)
    return ' '.join(html.unescape(re.sub(r'<[^>]+>', ' ', fragment)).split())


def fetch(title):
    url = SITE + urllib.parse.quote(title.replace(' ', '_'))
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return url, r.read().decode('utf-8')


def parse_species(page):
    """Return (genus_es, {game: text}) from one WikiDex Pokemon page."""
    m = re.search(r'Categoría</a>\s*</th>\s*<td[^>]*>(.*?)</td>', page, flags=re.S)
    genus = text_of(m.group(1)) if m else ''
    # The main-series table follows the sentence "en los videojuegos principales"; other tables come later.
    start = page.find('en los videojuegos principales')
    entries = {}
    if start >= 0:
        t = re.search(r'<table class="pokedex[^"]*".*?</table>', page[start:], flags=re.S)
        if t:
            for th, td in re.findall(r'<th[^>]*class="tfx-w[^"]*"[^>]*>(.*?)</th>\s*<td[^>]*class="tfx-fw"[^>]*>(.*?)</td>', t.group(0), flags=re.S):
                game = text_of(th)
                if game and game not in entries:
                    entries[game] = text_of(td)
    return genus, entries


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--fetch', action='store_true', help='query WikiDex for missing entries')
    ap.add_argument('--only', help='comma-separated species ids (debug)')
    args = ap.parse_args()

    names_es = {}
    for r in csv.DictReader(open(CACHE / 'pokemon_species_names.csv', encoding='utf-8-sig')):
        if r['local_language_id'] == '7' and r['name']:
            names_es[int(r['pokemon_species_id'])] = r['name']
    flavor_es = set()
    for r in csv.DictReader(open(CACHE / 'pokemon_species_flavor_text.csv', encoding='utf-8-sig')):
        if r['language_id'] == '7':
            flavor_es.add(int(r['species_id']))
    genus_es = {}
    for r in csv.DictReader(open(CACHE / 'pokemon_species_names.csv', encoding='utf-8-sig')):
        if r['local_language_id'] == '7' and r['genus']:
            genus_es[int(r['pokemon_species_id'])] = r['genus']

    data = json.loads(OUT.read_text(encoding='utf-8')) if OUT.exists() else {}
    data.setdefault('source', SITE)
    data.setdefault('species', {})
    wanted = [i for i in range(1, 1026) if i not in flavor_es or i not in genus_es]
    if args.only:
        wanted = [int(x) for x in args.only.split(',')]
    print('species missing Spanish CSV text:', len(wanted), flush=True)

    if args.fetch:
        for sid in wanted:
            if str(sid) in data['species']:
                continue
            title = names_es.get(sid)
            rec = {'name_es': title}
            try:
                url, page = fetch(title)
                genus, entries = parse_species(page)
                rec['url'] = url
                rec['genus_es'] = ('Pokémon ' + genus) if genus and not genus.startswith('Pokémon') else genus
                rec['entries'] = entries
                game = next((g for g in GAME_ORDER if entries.get(g) and not PLACEHOLDER.search(entries[g])), None)
                if game:
                    rec['flavor_es'] = entries[game]
                    rec['flavor_game'] = game
            except Exception as exc:  # keep going; the miss is recorded
                rec['error'] = repr(exc)
            data['species'][str(sid)] = rec
            print(sid, rec.get('name_es'), rec.get('genus_es'), rec.get('flavor_game'), rec.get('error', ''), flush=True)
            time.sleep(0.6)
    # Gen IX abilities with no Spanish text in PokeAPI. WikiDex has only the long encyclopedic "Efecto"
    # section for these, not an in-game short text, so they are translated here. Status "translated" means
    # the text is kept in the cache for review and is NOT merged into the app (the app shows English).
    data['abilities'] = {name: {'name_es': v[0], 'text_es': v[1], 'status': 'translated',
                                'source_en': ABILITY_EN[name]} for name, v in sorted(ABILITY_TRANSLATED.items())}
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print('wrote', OUT)


if __name__ == '__main__':
    main()

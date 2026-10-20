#!/usr/bin/env python3
"""Spanish move descriptions for the moves that PokeAPI leaves without Spanish text.

Covers the Gen IX moves with no Spanish flavor text upstream (69 moves, shown on 722 learnset rows).
- The Spanish move name and its WikiDex page are confirmed with the English interlanguage link.
- WikiDex move pages carry no in-game description section (checked with --fetch: "descripcion_wikidex"
  is recorded per move), so the description is translated here from the English Pokedex text
  and recorded with status "translated". Everything is stored under "moves" in cache/es_fill.json,
  keyed by PokeAPI move id, with the page URL.

Run with --fetch to query WikiDex; without it the cached records are used unchanged.
"""
import argparse, csv, json, re, time, urllib.error, urllib.parse, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / 'cache'
OUT = CACHE / 'es_fill.json'
API = 'https://www.wikidex.net/api.php'
SITE = 'https://www.wikidex.net/wiki/'
UA = 'FlipPokedex-offline-import/1.0 (personal offline dex; contact: owner)'
DELAY = 1.5

# Spanish Pokedex-style descriptions, translated from the English PokeAPI text (keyed by move id).
MOVE_TEXT_ES = {
    '827': 'El usuario ataca al objetivo con garras ruinosas. También puede envenenarlo, paralizarlo o dormirlo.',
    '828': 'Envuelto en energía psíquica, el usuario embiste al objetivo. Además, aumenta su Defensa.',
    '830': 'El usuario blande sus hachas de piedra contra el objetivo. Las astillas de piedra que deja el ataque flotan alrededor del objetivo.',
    '831': 'El usuario ataca envolviendo a los Pokémon rivales en vientos feroces llenos de amor y odio. También puede reducir su Ataque.',
    '833': 'El usuario arrasa a su alrededor escupiendo llamas durante dos o tres turnos. Después queda confundido.',
    '834': 'El usuario se envuelve en agua y embiste al objetivo con todo el cuerpo para causarle daño. También le causa bastante daño a sí mismo.',
    '838': 'El usuario embiste al objetivo con todo el cuerpo. Además, reduce su Defensa y su Defensa Esp.',
    '839': 'El usuario lanza innumerables púas tóxicas para causar daño. Puede envenenar al objetivo. El poder del movimiento se duplica si el objetivo ya está envenenado.',
    '851': 'Si el usuario se ha teracristalizado, libera energía de su teratipo. Causa daño con el Ataque o el Ataque Esp. del usuario, el que sea más alto.',
    '852': 'El usuario teje una trampa de seda que lo protege del daño y reduce la Velocidad de cualquier atacante que lo toque directamente.',
    '853': 'El usuario ataca lanzando una patada hacia arriba y golpeando al objetivo con el talón. Puede confundir al objetivo. Si falla, el usuario recibe daño.',
    '854': 'El usuario ataca para vengar a sus aliados. Cuantos más aliados derrotados haya en su equipo, mayor será el poder del movimiento.',
    '855': 'El usuario ataca con una luz extraña que afecta incluso a la mente. Además, reduce mucho la Defensa Esp. del objetivo.',
    '856': 'El usuario ataca con elegante aplomo. Si tiene un Tatsugiri en la boca, aumenta una de sus características según la forma de ese Tatsugiri.',
    '857': 'El usuario invoca un torrente alrededor de su puño y golpea a una velocidad cegadora. Este movimiento siempre actúa primero.',
    '858': 'El usuario emite un extracto muy picante que aumenta mucho el Ataque del objetivo y reduce mucho su Defensa.',
    '859': 'El usuario gira con furia tensando las patas y causa daño al objetivo. Además, reduce mucho su propia Velocidad.',
    '860': 'Sus compañeros se reúnen en gran número para realizar un ataque combinado que golpea al objetivo de una a diez veces seguidas.',
    '861': 'El usuario cubre sus pies con hielo fino, gira y embiste al objetivo. El movimiento de giro también destruye el terreno.',
    '862': 'El usuario se lanza a una carga temeraria con todo su cuerpo. Después, los ataques contra el usuario no pueden fallar y le causan el doble de daño hasta su siguiente turno.',
    '863': 'El usuario concede una bendición cariñosa que revive a un Pokémon de su equipo que se ha debilitado y restaura la mitad de sus PS máximos.',
    '864': 'El usuario cura al objetivo con sal, causándole daño en cada turno. Los Pokémon de tipo Acero y Agua se ven más afectados.',
    '865': 'El usuario realiza un triple buceo perfectamente sincronizado y golpea al objetivo tres veces seguidas con salpicaduras de agua.',
    '866': 'El usuario gira en un ataque que también puede eliminar los efectos de movimientos como Atadura, Constricción o Drenadoras. Además, envenena a los Pokémon rivales.',
    '867': 'El usuario captura la esencia del objetivo en un dibujo. Cambia la habilidad del usuario y la de sus aliados a la del objetivo.',
    '868': 'El usuario aumenta mucho su Ataque, su Ataque Esp. y su Velocidad usando sus propios PS.',
    '869': 'El usuario hace una reverencia para que el objetivo baje la guardia y luego lo ataca con un tajo. Este ataque nunca falla.',
    '870': 'El usuario lanza al objetivo un ramo de flores trucado. Este ataque nunca falla y siempre es un golpe crítico.',
    '871': 'El usuario expulsa llamas furiosas como si cantara una canción y quema al objetivo. Además, aumenta su Ataque Esp.',
    '872': 'El usuario juega con el objetivo y lo ataca con pasos de danza ligeros y fluidos. Además, aumenta su Velocidad.',
    '874': 'El usuario ataca lanzando una lluvia de monedas. Además, reduce su Ataque Esp. Se gana dinero después del combate.',
    '875': 'El usuario desgarra al objetivo con una hoja etérea. Su poder aumenta un 50 % si el usuario está en un campo eléctrico.',
    '876': 'El usuario golpea al objetivo con agua hirviendo. Bajo sol intenso su poder no se reduce, sino que aumenta un 50 %.',
    '877': 'El usuario invoca una calamidad que reduce a la mitad los PS del objetivo.',
    '878': 'El usuario se transforma y cae al suelo provocando una enorme explosión prehistórica. Su poder aumenta más de lo normal si el golpe es supereficaz.',
    '879': 'El usuario avanza a velocidad ultrarrápida y atraviesa al objetivo con una electricidad futurista. Su poder aumenta más de lo normal si el golpe es supereficaz.',
    '880': 'El usuario crea un sustituto con sus propios PS y después cambia de sitio con un Pokémon de su equipo que espera.',
    '882': 'El usuario limpia el campo y elimina los efectos de Púas, Roca Afilada, Red Viscosa, Púas Tóxicas y Sustituto. Además, aumenta su Ataque y su Velocidad.',
    '883': 'El usuario invoca una ventisca durante cinco turnos. Aumenta la Defensa de los Pokémon de tipo Hielo.',
    '884': 'El usuario ataca saltando sobre el objetivo. Además, reduce la Velocidad del objetivo.',
    '885': 'El usuario ataca de repente, como si saliera de un salto desde la hierba alta. Su ágil movimiento de pies aumenta su Velocidad.',
    '886': 'El usuario ataca con una lluvia tan fría que le quita fuerza al objetivo. Además, reduce su Ataque.',
    '887': 'El usuario gira la punta de su cuerpo a gran velocidad para atravesar al objetivo. Este ataque puede alcanzar a un objetivo que use movimientos como Protección o Detección.',
    '888': 'El usuario dispara rayos místicos desde los ojos para causar daño. El objetivo recibe dos golpes seguidos.',
    '889': 'El usuario convierte su rabia en energía para atacar. Cuantas más veces haya sido golpeado el usuario, mayor será el poder del movimiento.',
    '890': 'El usuario lanza su propia armadura como proyectiles ardientes. Además, reduce su Defensa y su Defensa Esp.',
    '891': 'El usuario concentra sus sentimientos amargos hacia el mundo de los vivos en un tajo. Sus PS se restauran hasta la mitad del daño causado al objetivo.',
    '892': 'El usuario libera toda la electricidad de su cuerpo para realizar un ataque muy potente. Después de usarlo, deja de ser de tipo Eléctrico.',
    '893': 'El usuario balancea todo su cuerpo para atacar con su enorme martillo. No puede usarse dos veces seguidas.',
    '894': 'El usuario devuelve el golpe con mucha más fuerza al rival que le causó daño por última vez.',
    '895': 'El usuario expulsa agua a presión para cortar al objetivo como si fuera una cuchilla. Tiene mayor probabilidad de causar un golpe crítico.',
    '902': 'El usuario dispara una ráfaga del té que ha mezclado. Sus PS se restauran hasta la mitad del daño causado al objetivo. Además, puede quemar al objetivo.',
    '903': 'El usuario provoca una explosión de almíbar pegajoso que cubre al objetivo y reduce su Velocidad cada turno durante tres turnos.',
    '904': 'El usuario golpea con un garrote enredado en hiedra. Su tipo cambia según la máscara que lleve el usuario y tiene mayor probabilidad de causar un golpe crítico.',
    '905': 'El usuario reúne electricidad en el primer turno, lo que aumenta su Ataque Esp., y dispara un rayo de alto voltaje en el siguiente. Con lluvia se dispara de inmediato.',
    '906': 'Con el poder de sus cristales, el usuario bombardea y elimina al objetivo. Si lo usa Terapagos en su forma astral, daña a todos los Pokémon rivales.',
    '907': 'El usuario dispara un rayo de luz para causar daño. A veces todas sus cabezas disparan a la vez y el poder del movimiento se duplica.',
    '908': 'Su pelaje ardiente lo protege de los ataques y además quema a cualquier atacante que lo toque directamente.',
    '909': 'Este movimiento permite al usuario atacar primero con una descarga eléctrica. Falla si el objetivo no está preparando un ataque.',
    '910': 'El usuario empuña la luz acumulada sobre su cabeza para partir al objetivo. Acierta aunque el objetivo se proteja.',
    '911': 'El usuario ataca lanzando dos veces seguidas cuchillas de partículas al objetivo. Este ataque nunca falla.',
    '912': 'El objetivo es aplastado con un brazo, una garra o algo similar para causarle daño. Cuantos más PS le queden al objetivo, mayor será el poder del movimiento.',
    '913': 'El usuario anima a sus aliados con un grito dracónico para que sus ataques tengan más probabilidad de causar golpes críticos. Anima más a los Pokémon de tipo Dragón.',
    '914': 'El usuario ataca al objetivo con su voz angelical. También confunde al objetivo si sus características han aumentado durante el turno.',
    '915': 'Impulsado por la desesperación, el usuario ataca al objetivo. El poder del movimiento se duplica si el movimiento anterior del usuario falló.',
    '916': 'El usuario electrifica su cuerpo y cae sobre el objetivo para causarle daño. Si el movimiento falla, el usuario recibe daño.',
    '917': 'El usuario ataca al objetivo con ondas sonoras desagradables. Durante dos turnos, el objetivo no puede recuperar PS con movimientos, habilidades u objetos.',
    '918': 'El usuario reacciona al movimiento del objetivo y lo golpea con el talón de la mano, haciendo que retroceda. Falla si el objetivo no está preparando un movimiento de prioridad.',
    '919': 'El usuario vierte toxinas sobre el objetivo envolviéndolo en una cadena tóxica y corrosiva. Puede dejar al objetivo gravemente envenenado.',
    '836': 'El usuario lanza enormes trozos de hielo contra el objetivo para causarle daño. También puede hacer que retroceda.',
    '842': 'El usuario endurece su piel como un escudo de hierro, lo que aumenta mucho su Defensa.',
    '843': 'El usuario patea y luego dispara tres flechas. Tiene mayor probabilidad de causar un golpe crítico y puede reducir la Defensa del objetivo o hacer que retroceda.',
    '901': 'El usuario libera toda la fuerza de su espíritu desde una luna llena tan roja como la sangre. No puede usarse dos veces seguidas.',
}


def api(**params):
    params.update(format='json', action='query')
    url = API + '?' + urllib.parse.urlencode(params)
    for attempt in range(6):
        time.sleep(DELAY)
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': UA}), timeout=60) as r:
                return json.load(r)
        except urllib.error.HTTPError as exc:
            if exc.code != 429:
                raise
            time.sleep(10 * (attempt + 1))
    raise RuntimeError('WikiDex still rate-limiting after retries')


def read_csv(name):
    return list(csv.DictReader(open(CACHE / name, encoding='utf-8-sig')))


def moves_without_spanish():
    """Moves in the learnsets the app shows (version group 14 for #1-649, newest group for #650+) with no Spanish text."""
    rows = read_csv('pokemon_moves.csv')
    species = {r['id']: int(r['species_id']) for r in read_csv('pokemon.csv')}
    newest = {}
    for r in rows:
        if species.get(r['pokemon_id'], 0) > 649:
            newest[r['pokemon_id']] = max(newest.get(r['pokemon_id'], 0), int(r['version_group_id']))
    used = set()
    for r in rows:
        sid = species.get(r['pokemon_id'])
        if sid is None:
            continue
        if (int(r['version_group_id']) == newest.get(r['pokemon_id'])) if sid > 649 else r['version_group_id'] == '14':
            used.add(r['move_id'])
    es = {r['move_id'] for r in read_csv('move_flavor_text.csv') if r['language_id'] == '7'}
    en_name, es_name = {}, {}
    for r in read_csv('move_names.csv'):
        if r['local_language_id'] == '9':
            en_name[r['move_id']] = r['name']
        if r['local_language_id'] == '7' and r['name']:
            es_name[r['move_id']] = r['name']
    text_en = {}
    for r in sorted(read_csv('move_flavor_text.csv'), key=lambda r: int(r['version_group_id'])):
        if r['language_id'] == '9':
            text_en[r['move_id']] = ' '.join(r['flavor_text'].split())
    return {mid: (en_name[mid], es_name.get(mid, ''), text_en.get(mid, '')) for mid in used if mid not in es and mid in en_name}


def wikidex_check(title, english):
    """(url, has_description_section) for the WikiDex move page, or (None, False) when it is not the move."""
    d = api(titles=title, prop='langlinks|revisions', lllang='en', rvprop='content', rvslots='main')
    page = list(d['query']['pages'].values())[0]
    if 'missing' in page:
        return None, False
    links = [l['*'] for l in page.get('langlinks', [])]
    if not any(l == english or l == english + ' (move)' for l in links):
        return None, False
    text = page['revisions'][0]['slots']['main']['*']
    has_desc = bool(re.search(r'^==+\s*(Descripci[oó]n|Pokédex|Entrada)', text, re.M | re.I))
    return SITE + urllib.parse.quote(title.replace(' ', '_')), has_desc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--fetch', action='store_true')
    args = ap.parse_args()
    data = json.loads(OUT.read_text(encoding='utf-8'))
    wanted = moves_without_spanish()
    # Keep only the records for the current set (cached WikiDex checks are reused for these).
    moves = {k: v for k, v in data.get('moves', {}).items() if k in wanted}
    data['moves'] = moves
    for mid, (en, es_title, text_en) in sorted(wanted.items(), key=lambda kv: int(kv[0])):
        rec = moves.get(mid, {})
        rec.update({'name_en': en, 'name_es': es_title, 'text_en': text_en})
        if args.fetch and es_title:
            url, has_desc = wikidex_check(es_title, en)
            rec['wikidex_url'] = url or ''
            rec['wikidex_in_game_description'] = has_desc
        if mid in MOVE_TEXT_ES:
            rec['text_es'] = MOVE_TEXT_ES[mid]
            rec['status'] = 'translated'
        else:
            rec['status'] = 'missing'
        moves[mid] = rec
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    have = sum(1 for m in moves.values() if m.get('text_es'))
    print('moves with Spanish text', have, 'of', len(moves), '| missing', [k for k, v in moves.items() if not v.get('text_es')])
    print('wikidex pages with in-game description', sum(1 for m in moves.values() if m.get('wikidex_in_game_description')))


if __name__ == '__main__':
    main()

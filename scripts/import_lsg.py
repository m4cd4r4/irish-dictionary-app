"""
Import LSG Irish WordNet into DictionaryEntry format.

Source: https://github.com/kscanne/wordnet-gaeilge
License: GFDL 1.2+ (entries tagged source='lsg')
Format: Gettext .po files (ga-data.noun.po, ga-data.verb.po, etc.)

Each .po entry structure:
  # Irish headwords (comma-separated)
  # English headwords (comma-separated)
  msgctxt "synset_id pos_letter"
  msgid "English definition (long)"
  msgstr "Irish definition/translation"

Usage:
    pip install requests tqdm
    python import_lsg.py

Output: output/lsg_entries.json
"""

import json
import re
import sys
from pathlib import Path

try:
    import requests
    from tqdm import tqdm
except ImportError:
    print("Missing dependencies. Run: pip install requests tqdm")
    sys.exit(1)

from utils import (
    make_id, build_search_terms, is_valid_irish_word, map_pos,
    WORDNET_DOMAIN_TO_CATEGORY,
)

LSG_BASE = "https://raw.githubusercontent.com/kscanne/wordnet-gaeilge/master/"
PO_FILES = [
    ("ga-data.noun.po", "noun"),
    ("ga-data.verb.po", "verb"),
    ("ga-data.adj.po",  "adj"),
    ("ga-data.adv.po",  "adv"),
]

OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_FILE = OUTPUT_DIR / "lsg_entries.json"


def download_po(filename: str) -> Path:
    dest = OUTPUT_DIR / filename
    if dest.exists():
        print(f"  Using cached {dest.name}")
        return dest

    url = LSG_BASE + filename
    print(f"  Downloading {filename} ...")
    r = requests.get(url, timeout=60)
    r.raise_for_status()

    OUTPUT_DIR.mkdir(exist_ok=True)
    dest.write_bytes(r.content)
    print(f"  Saved {dest.name} ({len(r.content):,} bytes)")
    return dest


def parse_po_entries(text: str) -> list[dict]:
    """
    Parse a gettext .po file and return a list of raw entry dicts.
    Structure per entry:
      # Irish words (comma-separated)
      # English words (comma-separated)
      msgctxt "synset_id pos"
      msgid "English definition"
      msgstr "Irish definition"
    """
    entries = []
    blocks = re.split(r'\n\n+', text.strip())

    for block in blocks:
        lines = block.strip().splitlines()
        if not lines:
            continue

        irish_comment = None
        english_comment = None
        msgctxt = None
        msgid_parts = []
        in_msgid = False

        for line in lines:
            if line.startswith('#') and not line.startswith('#,') and not line.startswith('#.') and not line.startswith('#:'):
                comment_text = line[1:].strip()
                if comment_text:
                    if irish_comment is None:
                        irish_comment = comment_text
                    elif english_comment is None:
                        english_comment = comment_text
            elif line.startswith('msgctxt '):
                m = re.match(r'msgctxt\s+"(.+)"', line)
                if m:
                    msgctxt = m.group(1)
                in_msgid = False
            elif line.startswith('msgid '):
                m = re.match(r'msgid\s+"(.*)"', line)
                if m:
                    msgid_parts = [m.group(1)]
                in_msgid = True
            elif line.startswith('"') and in_msgid:
                # continuation line
                m = re.match(r'"(.*)"', line)
                if m:
                    msgid_parts.append(m.group(1))
            elif line.startswith('msgstr'):
                in_msgid = False

        if not irish_comment or not msgctxt:
            continue

        # Parse Irish headwords from first comment
        irish_words = [w.strip() for w in irish_comment.split(',') if w.strip()]
        irish_words = [w for w in irish_words if is_valid_irish_word(w)]
        if not irish_words:
            continue

        # English: use second comment (short form), fallback to msgid
        english_short = english_comment.strip() if english_comment else ''
        msgid_text = ''.join(msgid_parts).strip()
        english = english_short if english_short else msgid_text
        if not english:
            continue

        # POS from synset_id: "00001740 n" -> 'n'
        parts = msgctxt.split()
        synset_id = parts[0] if parts else ''
        pos_letter = parts[1] if len(parts) > 1 else 'n'

        entries.append({
            'irish_words': irish_words,
            'english': english,
            'english_long': msgid_text if english_short else '',
            'pos_letter': pos_letter,
            'synset_id': synset_id,
        })

    return entries


POS_LETTER_MAP = {
    'n': 'noun',
    'v': 'verb',
    'a': 'adjective',
    's': 'adjective',  # satellite adjective
    'r': 'adverb',
}


def infer_category(synset_id: str, pos_letter: str, english: str) -> str:
    """Simple heuristic category from English gloss."""
    e = english.lower()
    if any(w in e for w in ('family', 'mother', 'father', 'sister', 'brother', 'child', 'parent')):
        return 'family'
    if any(w in e for w in ('food', 'eat', 'drink', 'meal', 'cook')):
        return 'food'
    if any(w in e for w in ('animal', 'bird', 'fish', 'insect', 'mammal')):
        return 'animals'
    if any(w in e for w in ('plant', 'tree', 'flower', 'grass', 'leaf')):
        return 'plants'
    if any(w in e for w in ('body', 'hand', 'foot', 'head', 'heart', 'blood')):
        return 'body'
    if any(w in e for w in ('weather', 'rain', 'wind', 'sun', 'cloud', 'storm')):
        return 'weather'
    if any(w in e for w in ('sport', 'game', 'play', 'athletic')):
        return 'sports'
    if any(w in e for w in ('music', 'song', 'instrument', 'melody')):
        return 'music'
    if any(w in e for w in ('school', 'learn', 'teach', 'student', 'education')):
        return 'school'
    if any(w in e for w in ('church', 'god', 'prayer', 'religion', 'saint')):
        return 'religion'
    if any(w in e for w in ('law', 'court', 'judge', 'legal', 'crime')):
        return 'law'
    if any(w in e for w in ('science', 'chemistry', 'physics', 'biology', 'scientific')):
        return 'science'
    if any(w in e for w in ('technology', 'computer', 'machine', 'device', 'software')):
        return 'technology'
    if any(w in e for w in ('farm', 'agriculture', 'crop', 'harvest', 'livestock')):
        return 'agriculture'
    if any(w in e for w in ('myth', 'legend', 'hero', 'deity', 'folklore')):
        return 'mythology'
    if any(w in e for w in ('art', 'paint', 'sculpt', 'draw', 'creative')):
        return 'arts'
    if any(w in e for w in ('military', 'soldier', 'army', 'war', 'battle')):
        return 'military'
    if any(w in e for w in ('politic', 'government', 'parliament', 'election', 'vote')):
        return 'politics'
    if any(w in e for w in ('business', 'trade', 'market', 'commerce', 'economy')):
        return 'business'
    if any(w in e for w in ('place', 'country', 'city', 'location', 'region', 'geography')):
        return 'geography'
    if any(w in e for w in ('color', 'colour', 'red', 'blue', 'green', 'yellow')):
        return 'colors'
    if any(w in e for w in ('number', 'count', 'digit', 'numeral')):
        return 'numbers'
    if any(w in e for w in ('time', 'day', 'month', 'year', 'hour', 'minute')):
        return 'time'
    if any(w in e for w in ('home', 'house', 'room', 'kitchen', 'furniture')):
        return 'home'
    if any(w in e for w in ('travel', 'journey', 'transport', 'vehicle', 'road')):
        return 'travel'
    if any(w in e for w in ('cloth', 'wear', 'dress', 'shirt', 'trouser')):
        return 'clothing'
    if pos_letter == 'v':
        return 'common'
    return 'common'


def build_lsg_entries(po_entries: list[dict]) -> list[dict]:
    """Convert raw PO entries into DictionaryEntry-compatible dicts."""
    entries = []
    seen_ids: set[str] = set()

    for pe in po_entries:
        pos_raw = POS_LETTER_MAP.get(pe['pos_letter'], 'noun')
        pos = map_pos(pos_raw)
        english = pe['english']
        english_long = pe.get('english_long', '')
        english_alt = [english_long] if english_long and english_long != english else []

        category = infer_category(pe['synset_id'], pe['pos_letter'], english)

        # Create one entry per Irish headword in the synset
        synset_irish = pe['irish_words']
        synonym_ids = []  # will fill with entry IDs after first pass

        for irish in synset_irish:
            entry_id = make_id(irish)
            unique_id = entry_id
            suffix = 2
            while unique_id in seen_ids:
                unique_id = f"{entry_id}-{suffix}"
                suffix += 1
            seen_ids.add(unique_id)

            entry = {
                'id': unique_id,
                'irish': irish,
                'english': english,
                'partOfSpeech': pos,
                'category': category,
                'searchTerms': build_search_terms(irish, english, english_alt, []),
                'source': 'lsg',
            }
            if english_alt:
                entry['englishAlt'] = english_alt[:2]

            entries.append(entry)

    # Second pass: link synonyms within each synset
    # Group by synset_id, then assign synonymIds across headwords
    # (kept simple - skip for now, merge.py can handle this)

    return entries


def main():
    OUTPUT_DIR.mkdir(exist_ok=True)

    all_entries = []
    for po_filename, pos_hint in PO_FILES:
        print(f"\n--- {po_filename} ---")
        po_path = download_po(po_filename)
        text = po_path.read_text(encoding='utf-8', errors='replace')
        raw = parse_po_entries(text)
        print(f"  Raw PO entries: {len(raw):,}")
        built = build_lsg_entries(raw)
        print(f"  Dictionary entries: {len(built):,}")
        all_entries.extend(built)

    print(f"\nTotal LSG entries: {len(all_entries):,}")

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(all_entries, f, ensure_ascii=False, indent=2)
    print(f"Saved to {OUTPUT_FILE}")

    from collections import Counter
    cats = Counter(e['category'] for e in all_entries)
    print("\nTop categories:")
    for cat, count in cats.most_common(10):
        print(f"  {cat}: {count:,}")


if __name__ == '__main__':
    main()

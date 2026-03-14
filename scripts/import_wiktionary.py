"""
Import Irish entries from kaikki.org Wiktextract dump.

Source: https://kaikki.org/dictionary/Irish/index.html
License: CC BY-SA 4.0 (entries tagged source='wiktionary')
Format: JSONL (one JSON object per line)

Usage:
    pip install requests tqdm
    python import_wiktionary.py

Output: output/wiktionary_entries.json
"""

import json
import sys
from collections import Counter
from pathlib import Path

try:
    import requests
    from tqdm import tqdm
except ImportError:
    print("Missing dependencies. Run: pip install requests tqdm")
    sys.exit(1)

from utils import (
    make_id, build_search_terms, is_valid_irish_word, map_pos,
    WIKTIONARY_TOPIC_TO_CATEGORY,
)

# Weekly updated Irish JSONL from kaikki.org (deprecated URL still works as of 2025)
KAIKKI_URL = "https://kaikki.org/dictionary/Irish/kaikki.org-dictionary-Irish.jsonl"

OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_FILE = OUTPUT_DIR / "wiktionary_entries.json"
RAW_FILE = OUTPUT_DIR / "kaikki_irish.jsonl"


def download_kaikki():
    if RAW_FILE.exists():
        print(f"Using cached {RAW_FILE}")
        return

    print(f"Downloading kaikki.org Irish JSONL (~111 MB) ...")
    r = requests.get(KAIKKI_URL, timeout=120, stream=True)
    r.raise_for_status()

    total = int(r.headers.get('content-length', 0))
    OUTPUT_DIR.mkdir(exist_ok=True)

    with open(RAW_FILE, 'wb') as f, tqdm(total=total, unit='B', unit_scale=True, desc='kaikki_irish.jsonl') as bar:
        for chunk in r.iter_content(chunk_size=65536):
            f.write(chunk)
            bar.update(len(chunk))
    print(f"Saved to {RAW_FILE}")


def infer_category(entry_data: dict) -> str:
    """Infer category from Wiktionary topics, categories, and POS."""
    # Check topics first
    for topic in entry_data.get('topics', []):
        cat = WIKTIONARY_TOPIC_TO_CATEGORY.get(topic)
        if cat:
            return cat

    # Check categories array
    for cat_item in entry_data.get('categories', []):
        name = cat_item if isinstance(cat_item, str) else cat_item.get('name', '')
        for topic, cat in WIKTIONARY_TOPIC_TO_CATEGORY.items():
            if topic.lower() in name.lower():
                return cat

    # Fall back on POS
    pos = entry_data.get('pos', '')
    if pos in ('num', 'numeral', 'number'):
        return 'numbers'

    return 'common'


def extract_pronunciation(entry_data: dict) -> str | None:
    """Extract first IPA pronunciation string."""
    for sound in entry_data.get('sounds', []):
        ipa = sound.get('ipa', '').strip()
        if ipa:
            return ipa
    return None


def extract_inflections(entry_data: dict) -> list[str]:
    """Extract inflected forms from 'forms' array."""
    seen = set()
    forms = []
    base = entry_data.get('word', '')
    for form_item in entry_data.get('forms', []):
        form = form_item.get('form', '').strip()
        if form and form != base and is_valid_irish_word(form) and form not in seen:
            seen.add(form)
            forms.append(form)
        if len(forms) >= 10:
            break
    return forms


def parse_kaikki(jsonl_path: Path) -> list[dict]:
    """Stream-parse JSONL and return DictionaryEntry-compatible dicts."""
    print(f"Parsing {jsonl_path} ...")
    entries = []
    seen_ids: set[str] = set()
    skipped = 0

    with open(jsonl_path, encoding='utf-8') as f:
        for line_num, line in enumerate(tqdm(f, desc='Wiktionary entries', unit='line')):
            line = line.strip()
            if not line:
                continue

            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                skipped += 1
                continue

            irish = data.get('word', '').strip()
            if not irish or not is_valid_irish_word(irish):
                skipped += 1
                continue

            # Only process Irish-language entries (lang_code = 'ga')
            if data.get('lang_code', '') != 'ga':
                skipped += 1
                continue

            senses = data.get('senses', [])
            if not senses:
                skipped += 1
                continue

            # Extract English glosses
            glosses = []
            for sense in senses:
                for gloss in sense.get('glosses', []):
                    if gloss and isinstance(gloss, str):
                        # Strip wikitext artifacts
                        gloss = gloss.strip().rstrip('.')
                        if len(gloss) > 3 and len(gloss) < 200:
                            glosses.append(gloss)
                if len(glosses) >= 5:
                    break

            if not glosses:
                skipped += 1
                continue

            english = glosses[0]
            english_alt = list(dict.fromkeys(glosses[1:4]))  # dedup, cap at 3

            pos = map_pos(data.get('pos', 'noun'))
            category = infer_category(data)
            pronunciation = extract_pronunciation(data)
            inflections = extract_inflections(data)

            entry_id = make_id(irish)
            unique_id = entry_id
            suffix = 2
            while unique_id in seen_ids:
                unique_id = f"{entry_id}-{suffix}"
                suffix += 1
            seen_ids.add(unique_id)

            entry: dict = {
                'id': unique_id,
                'irish': irish,
                'english': english,
                'partOfSpeech': pos,
                'category': category,
                'searchTerms': build_search_terms(irish, english, english_alt, inflections),
                'source': 'wiktionary',
            }

            if english_alt:
                entry['englishAlt'] = english_alt
            if pronunciation:
                entry['pronunciation'] = pronunciation
            if inflections:
                entry['inflections'] = inflections

            entries.append(entry)

    print(f"\nExtracted: {len(entries):,} | Skipped: {skipped:,}")
    return entries


def main():
    OUTPUT_DIR.mkdir(exist_ok=True)
    download_kaikki()

    entries = parse_kaikki(RAW_FILE)

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)

    print(f"Saved {len(entries):,} entries to {OUTPUT_FILE}")

    cats = Counter(e['category'] for e in entries)
    print("\nTop categories:")
    for cat, count in cats.most_common(10):
        print(f"  {cat}: {count:,}")

    with_ipa = sum(1 for e in entries if e.get('pronunciation'))
    with_forms = sum(1 for e in entries if e.get('inflections'))
    print(f"\nWith IPA: {with_ipa:,} | With inflections: {with_forms:,}")


if __name__ == '__main__':
    main()

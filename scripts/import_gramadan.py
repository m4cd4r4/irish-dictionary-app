"""
Import BuNaMo (National Morphology Database) as inflection enrichment.

Source: https://github.com/michmech/BuNaMo
License: ODbL 1.0 (enriched entries tagged source='gramadan')
Format: ZIP of XML files per lemma (one XML per noun/verb/adjective)

XML structure (noun example):
  <noun default="Aifreann" declension="1" ...>
    <sgNom default="Aifreann" gender="masc" />
    <sgGen default="Aifrinn" gender="masc" />
    <plNom default="Aifrinn" />
    <plGen default="Aifreann" />
  </noun>

Usage:
    pip install lxml requests tqdm
    python import_gramadan.py

Output: output/gramadan_inflections.json
  A map of { normalizedIrishLemma: { lemma, inflections, gender? } }
  Applied during merge to enrich existing entries with inflected forms.
"""

import io
import json
import sys
import zipfile
from pathlib import Path

try:
    from lxml import etree
    import requests
    from tqdm import tqdm
except ImportError:
    print("Missing dependencies. Run: pip install lxml requests tqdm")
    sys.exit(1)

from utils import normalize_irish, is_valid_irish_word

BUNAMO_ZIP_URL = "https://github.com/michmech/BuNaMo/archive/refs/heads/master.zip"

OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_FILE = OUTPUT_DIR / "gramadan_inflections.json"
RAW_FILE = OUTPUT_DIR / "bunamo.zip"


def download_bunamo():
    if RAW_FILE.exists():
        print(f"Using cached {RAW_FILE}")
        return

    print(f"Downloading BuNaMo from GitHub ...")
    r = requests.get(BUNAMO_ZIP_URL, timeout=120, stream=True)
    r.raise_for_status()

    total = int(r.headers.get('content-length', 0))
    OUTPUT_DIR.mkdir(exist_ok=True)

    with open(RAW_FILE, 'wb') as f:
        if total:
            from tqdm import tqdm as _tqdm
            with _tqdm(total=total, unit='B', unit_scale=True, desc='bunamo.zip') as bar:
                for chunk in r.iter_content(chunk_size=65536):
                    f.write(chunk)
                    bar.update(len(chunk))
        else:
            for chunk in r.iter_content(chunk_size=65536):
                f.write(chunk)

    print(f"Saved to {RAW_FILE} ({RAW_FILE.stat().st_size:,} bytes)")


def extract_noun_forms(root) -> tuple[str, str | None, list[str]]:
    """Return (lemma, gender, inflected_forms) from a noun XML root."""
    lemma = root.get('default', '').strip()
    if not lemma:
        return '', None, []

    gender = None
    forms = set()

    for child in root:
        tag = child.tag
        # sgNom carries the gender
        if tag == 'sgNom':
            g = child.get('gender', '')
            if g in ('masc', 'fem'):
                gender = 'masculine' if g == 'masc' else 'feminine'
            f = child.get('default', '').strip()
            if f and f != lemma and is_valid_irish_word(f):
                forms.add(f)
        elif tag in ('sgGen', 'sgDat', 'sgVoc', 'plNom', 'plGen', 'plVoc', 'plDat'):
            f = child.get('default', '').strip()
            if f and f != lemma and is_valid_irish_word(f):
                forms.add(f)
            # Handle strength variants (weak/strong)
            f2 = child.get('defaultStrong', '').strip()
            if f2 and f2 != lemma and is_valid_irish_word(f2):
                forms.add(f2)

    return lemma, gender, sorted(forms)


def extract_verb_forms(root) -> tuple[str, list[str]]:
    """Return (lemma, conjugated_forms) from a verb XML root."""
    lemma = root.get('default', '').strip()
    if not lemma:
        return '', []

    forms = set()

    # Collect verbal noun and adjective
    for tag in ('verbalNoun', 'verbalAdjective'):
        el = root.find(tag)
        if el is not None:
            f = el.get('default', '').strip()
            if f and f != lemma and is_valid_irish_word(f):
                forms.add(f)

    # Collect tense forms
    for tense_el in root.findall('tenseForm'):
        f = tense_el.get('value', '').strip()
        if not f:
            f = tense_el.get('default', '').strip()
        if f and f != lemma and is_valid_irish_word(f):
            forms.add(f)

    # Collect mood forms
    for mood_el in root.findall('moodForm'):
        f = mood_el.get('value', '').strip()
        if not f:
            f = mood_el.get('default', '').strip()
        if f and f != lemma and is_valid_irish_word(f):
            forms.add(f)

    return lemma, sorted(forms)


def extract_adj_forms(root) -> tuple[str, list[str]]:
    """Return (lemma, forms) from an adjective XML root."""
    lemma = root.get('default', '').strip()
    if not lemma:
        return '', []

    forms = set()
    for child in root:
        f = child.get('default', '').strip()
        if f and f != lemma and is_valid_irish_word(f):
            forms.add(f)

    return lemma, sorted(forms)


def parse_bunamo(zip_path: Path) -> dict:
    """Parse all BuNaMo XML files and return inflection map."""
    print(f"Parsing BuNaMo ZIP ...")
    inflection_map = {}
    skipped = 0

    with zipfile.ZipFile(zip_path) as zf:
        xml_files = [n for n in zf.namelist() if n.endswith('.xml')]
        # Filter to noun/, verb/, adjective/ directories
        xml_files = [n for n in xml_files if any(
            f'/{d}/' in n for d in ('noun', 'verb', 'adjective')
        )]
        print(f"  Found {len(xml_files):,} XML files (noun/verb/adjective)")

        for xml_name in tqdm(xml_files, desc='BuNaMo XML files'):
            try:
                with zf.open(xml_name) as f:
                    tree = etree.parse(f)
                    root = tree.getroot()

                tag = root.tag.lower()

                if tag == 'noun':
                    lemma, gender, forms = extract_noun_forms(root)
                    if lemma and is_valid_irish_word(lemma):
                        key = normalize_irish(lemma)
                        record: dict = {'lemma': lemma, 'inflections': forms}
                        if gender:
                            record['gender'] = gender
                        inflection_map[key] = record

                elif tag == 'verb':
                    lemma, forms = extract_verb_forms(root)
                    if lemma and is_valid_irish_word(lemma):
                        key = normalize_irish(lemma)
                        inflection_map[key] = {'lemma': lemma, 'inflections': forms}

                elif tag == 'adjective':
                    lemma, forms = extract_adj_forms(root)
                    if lemma and is_valid_irish_word(lemma):
                        key = normalize_irish(lemma)
                        inflection_map[key] = {'lemma': lemma, 'inflections': forms}

            except Exception as exc:
                skipped += 1
                continue

    print(f"Extracted inflection data for {len(inflection_map):,} lemmas (skipped {skipped})")
    return inflection_map


def main():
    OUTPUT_DIR.mkdir(exist_ok=True)
    download_bunamo()

    inflection_map = parse_bunamo(RAW_FILE)

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(inflection_map, f, ensure_ascii=False, indent=2)

    print(f"Saved inflection map to {OUTPUT_FILE}")

    total_forms = sum(len(v['inflections']) for v in inflection_map.values())
    print(f"Total inflected forms: {total_forms:,}")
    print(f"Average forms per lemma: {total_forms / max(len(inflection_map), 1):.1f}")

    with_gender = sum(1 for v in inflection_map.values() if v.get('gender'))
    print(f"Entries with gender: {with_gender:,}")


if __name__ == '__main__':
    main()

"""
Merge all data sources into the final irish-dictionary-data.json.

Priority order (higher wins on conflict):
  1. curated   — existing hand-curated entries
  2. lsg       — LSG Irish WordNet
  3. wiktionary — Wiktextract
  4. gramadan  — morphology enrichment only (no new entries)
  5. paracrawl — mined term pairs

Usage:
    python merge.py [--dry-run]

Output: ../src/data/irish-dictionary-data.json
"""

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

from utils import normalize_irish, build_search_terms

OUTPUT_DIR = Path(__file__).parent / "output"
DATA_DIR = Path(__file__).parent.parent / "src" / "data"
FINAL_OUTPUT = DATA_DIR / "irish-dictionary-data.json"

SOURCE_PRIORITY = ['curated', 'lsg', 'wiktionary', 'paracrawl']


def load_json(path: Path) -> list[dict]:
    if not path.exists():
        print(f"  WARNING: {path} not found — skipping")
        return []
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def load_gramadan_inflections() -> dict:
    path = OUTPUT_DIR / "gramadan_inflections.json"
    if not path.exists():
        print(f"  WARNING: gramadan_inflections.json not found — skipping morphology enrichment")
        return {}
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def dedup_key(entry: dict) -> str:
    """Deduplication key: normalized Irish + lowercased English."""
    return f"{normalize_irish(entry['irish'])}:{entry['english'].lower()}"


def apply_gramadan_enrichment(entries: list[dict], gramadan_map: dict) -> list[dict]:
    """Add inflections from Gramadan to existing entries."""
    enriched = 0
    for entry in entries:
        key = normalize_irish(entry['irish'])
        gram_data = gramadan_map.get(key)
        if not gram_data:
            continue

        new_inflections = gram_data.get('inflections', [])
        if not new_inflections:
            continue

        existing = set(entry.get('inflections', []))
        merged = sorted(existing | set(new_inflections))

        if merged != entry.get('inflections'):
            entry['inflections'] = merged[:12]  # cap at 12
            # Rebuild searchTerms to include inflected forms
            entry['searchTerms'] = build_search_terms(
                entry['irish'],
                entry['english'],
                entry.get('englishAlt', []),
                merged,
            )
            enriched += 1

    print(f"  Gramadan enriched {enriched:,} entries with inflections")
    return entries


def merge_sources(sources: dict[str, list[dict]]) -> list[dict]:
    """
    Merge entries from all sources using priority-based deduplication.
    Higher priority entries win; lower priority entries only fill gaps.
    """
    seen: dict[str, dict] = {}  # dedup_key → winning entry
    order: list[str] = []       # maintain insertion order

    for source_name in SOURCE_PRIORITY:
        source_entries = sources.get(source_name, [])
        added = 0
        for entry in source_entries:
            # Ensure source field is set
            if 'source' not in entry:
                entry['source'] = source_name

            key = dedup_key(entry)
            if key not in seen:
                seen[key] = entry
                order.append(key)
                added += 1
            else:
                # Higher priority already present - but may enrich with new fields
                existing = seen[key]
                # Enrich: if existing lacks pronunciation/inflections, take from new
                if not existing.get('pronunciation') and entry.get('pronunciation'):
                    existing['pronunciation'] = entry['pronunciation']
                if not existing.get('inflections') and entry.get('inflections'):
                    existing['inflections'] = entry['inflections']
                if not existing.get('synonymIds') and entry.get('synonymIds'):
                    existing['synonymIds'] = entry['synonymIds']

        print(f"  {source_name}: {len(source_entries):,} input -> {added:,} new entries added")

    return [seen[k] for k in order]


def validate_entry(entry: dict) -> bool:
    """Basic validation — reject malformed entries."""
    required = ('id', 'irish', 'english', 'partOfSpeech', 'category', 'searchTerms')
    for field in required:
        if not entry.get(field):
            return False
    if len(entry['id']) > 100 or len(entry['irish']) > 100:
        return False
    return True


def print_stats(entries: list[dict]):
    print(f"\n{'='*50}")
    print(f"FINAL STATS")
    print(f"{'='*50}")
    print(f"Total entries: {len(entries):,}")

    by_source = Counter(e.get('source', 'unknown') for e in entries)
    print("\nBy source:")
    for src, count in sorted(by_source.items(), key=lambda x: -x[1]):
        print(f"  {src:12s}: {count:>8,}")

    by_category = Counter(e['category'] for e in entries)
    print("\nTop 15 categories:")
    for cat, count in by_category.most_common(15):
        print(f"  {cat:14s}: {count:>8,}")

    with_ipa = sum(1 for e in entries if e.get('pronunciation'))
    with_forms = sum(1 for e in entries if e.get('inflections'))
    with_syns = sum(1 for e in entries if e.get('synonymIds'))
    print(f"\nWith IPA pronunciation: {with_ipa:,}")
    print(f"With inflected forms:   {with_forms:,}")
    print(f"With synonym IDs:       {with_syns:,}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true', help="Don't write output file")
    args = parser.parse_args()

    print("Loading data sources ...")

    # Load existing curated data
    curated_path = DATA_DIR / "irish-dictionary-data.json"
    curated = load_json(curated_path)
    for e in curated:
        if 'source' not in e:
            e['source'] = 'curated'
    print(f"  curated: {len(curated):,} existing entries")

    # Load pipeline outputs
    lsg = load_json(OUTPUT_DIR / "lsg_entries.json")
    wiktionary = load_json(OUTPUT_DIR / "wiktionary_entries.json")
    paracrawl = load_json(OUTPUT_DIR / "paracrawl_entries.json")

    gramadan_map = load_gramadan_inflections()

    sources = {
        'curated': curated,
        'lsg': lsg,
        'wiktionary': wiktionary,
        'paracrawl': paracrawl,
    }

    print("\nMerging sources (priority: curated > lsg > wiktionary > paracrawl) ...")
    merged = merge_sources(sources)

    # Validate
    valid = [e for e in merged if validate_entry(e)]
    invalid = len(merged) - len(valid)
    if invalid:
        print(f"  Removed {invalid} invalid entries")
    merged = valid

    # Apply Gramadan morphology enrichment
    print("\nApplying Gramadan morphology enrichment ...")
    merged = apply_gramadan_enrichment(merged, gramadan_map)

    print_stats(merged)

    if args.dry_run:
        print("\nDRY RUN — not writing output file")
        return

    DATA_DIR.mkdir(exist_ok=True)
    with open(FINAL_OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(merged, f, ensure_ascii=False, separators=(',', ':'))

    size_mb = FINAL_OUTPUT.stat().st_size / 1_000_000
    print(f"\nWrote {len(merged):,} entries to {FINAL_OUTPUT} ({size_mb:.1f} MB)")
    print("\nNext: npm run build")


if __name__ == '__main__':
    main()

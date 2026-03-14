# Cupla Focail — Irish-English Dictionary

> **Live:** https://cuplafocail.ie · **API:** https://cuplafocail.ie/api/search

A free, open-source Irish-English dictionary with **135,708 entries** across 35 categories. Built from four open data sources and designed to be integrated into Irish language apps, learning tools, and messaging platforms.

---

## Integration Options

### Option 1 — Widget (1 line of HTML)

Drop a floating Irish dictionary button onto any web page:

```html
<script src="https://cuplafocail.ie/widget.js" defer></script>
```

A 🍀 button appears in the bottom-right corner. Click to open a full dictionary panel.

**Options via `data-*` attributes:**

```html
<script
  src="https://cuplafocail.ie/widget.js"
  data-position="bottom-left"
  data-color="#16a34a"
  data-category="greetings"
  defer
></script>
```

| Attribute | Default | Options |
|-----------|---------|---------|
| `data-position` | `bottom-right` | `bottom-left` |
| `data-color` | `#16a34a` | Any CSS color |
| `data-category` | _(none)_ | Any category name |

---

### Option 2 — iframe Embed

Embed the full dictionary UI inside your app:

```html
<iframe
  src="https://cuplafocail.ie/embed"
  width="100%"
  height="600"
  style="border:none; border-radius:12px;"
  title="Irish-English Dictionary"
  loading="lazy"
></iframe>
```

Pre-select a category:

```html
<iframe src="https://cuplafocail.ie/embed?category=greetings" ...></iframe>
```

Available categories: `family`, `greetings`, `emotions`, `conversation`, `food`, `home`, `time`, `nature`, `body`, `school`, `travel`, `numbers`, `colors`, `common`, `health`, `weather`, `sports`, `work`, `places`, `clothing`, `music`, `culture`, `animals`, `plants`, `religion`, `mythology`, `science`, `technology`, `agriculture`, `arts`, `geography`, `law`, `politics`, `military`, `business`

---

### Option 3 — REST API

Language-agnostic. Works with any backend or mobile app.

```bash
# Search (English or Irish, fada-insensitive)
GET https://cuplafocail.ie/api/search?q=mother
GET https://cuplafocail.ie/api/search?q=máthair
GET https://cuplafocail.ie/api/search?q=mathair   # same result

# Filter by category + limit
GET https://cuplafocail.ie/api/search?q=hello&category=greetings&limit=10

# Filter by data source
GET https://cuplafocail.ie/api/search?source=lsg,wiktionary

# All categories with counts
GET https://cuplafocail.ie/api/categories

# All sources with counts
GET https://cuplafocail.ie/api/sources

# Word of the day (deterministic per calendar day)
GET https://cuplafocail.ie/api/word-of-the-day

# Single entry by ID
GET https://cuplafocail.ie/api/entry/mathair
```

**Response schema:**

```json
{
  "entries": [
    {
      "id": "mathair",
      "irish": "máthair",
      "english": "mother",
      "englishAlt": ["mom", "mam", "mammy"],
      "partOfSpeech": "noun",
      "category": "family",
      "gender": "feminine",
      "pronunciation": "/ˈmˠɑːhəɾʲ/",
      "inflections": ["máthar", "máithreacha", "máitheacha"],
      "source": "curated",
      "searchTerms": ["mathair", "mother", "mom", "mam", "mammy", "mathar", "maithreacha"]
    }
  ],
  "total": 3,
  "query": "mother"
}
```

All API endpoints return `Access-Control-Allow-Origin: *` — safe to call from any origin.

---

### Option 4 — npm Package (TypeScript/JavaScript)

Zero dependencies, works in React, Vue, Svelte, Next.js, Node.js, Deno:

```bash
npm install irish-dictionary
```

```typescript
import { DICTIONARY_ENTRIES, search, wordOfTheDay } from 'irish-dictionary';

// Search English -> Irish
const results = search(DICTIONARY_ENTRIES, 'mother');

// Search Irish -> English (fada-insensitive)
const results2 = search(DICTIONARY_ENTRIES, 'mathair');

// Filter by category
const family = search(DICTIONARY_ENTRIES, '', { category: 'family', limit: 50 });

// Word of the day
const wotd = wordOfTheDay(DICTIONARY_ENTRIES);
console.log(`${wotd.irish} - ${wotd.english}`);
```

-> [npm package repo](https://github.com/m4cd4r4/irish-dictionary)

---

## Data

**135,708 entries** across 35 categories from four open data sources:

| Source | License | Entries | Notes |
|--------|---------|---------|-------|
| Hand-curated | MIT | 28,553 | Original entries — highest quality |
| LSG Irish WordNet | GFDL 1.2+ | 73,863 | Irish WordNet with noun/verb/adj/adv |
| Wiktextract (kaikki.org) | CC BY-SA 4.0 | 33,292 | IPA pronunciations, inflected forms |
| ParaCrawl v9 | CC0 | — | Pending (Phase 5) |

**Coverage by category:**

| Category | Irish | Entries |
|----------|-------|---------|
| common | coitianta | 105,273 |
| body | corp | 2,966 |
| food | bia | 2,559 |
| colors | dathanna | 2,008 |
| time | am | 1,457 |
| nature | nádúr | 1,533 |
| animals | ainmhithe | 1,738 |
| numbers | uimhreacha | 1,614 |
| home | baile | 1,310 |
| arts | ealaíona | 1,290 |
| travel | taisteal | 1,283 |
| school | scoil | 1,152 |
| weather | aimsir | 1,124 |
| sports | spórt | 1,016 |
| clothing | éadaí | 968 |
| family | teaghlach | 959 |
| health | sláinte | 848 |
| military | míleata | 813 |
| health | sláinte | 848 |
| conversation | comhrá | 752 |
| work | obair | 601 |
| places | áiteanna | 593 |
| emotions | mothúcháin | 527 |
| geography | tíreolaíocht | 466 |
| plants | plandaí | 415 |
| greetings | beannachtaí | 379 |
| law | dlí | 378 |
| music | ceol | 612 |
| culture | cultúr | 329 |
| religion | reiligiún | 137 |
| agriculture | talmhaíocht | 144 |
| technology | teicneolaíocht | 133 |
| business | gnó | 147 |
| politics | polaitíocht | 95 |
| mythology | miotaseolaíocht | 58 |
| science | eolaíocht | 31 |

**Entry structure:**

```typescript
interface DictionaryEntry {
  id: string;               // ASCII slug: "mathair"
  irish: string;            // with fadas: "máthair"
  english: string;          // primary: "mother"
  englishAlt?: string[];    // alternatives: ["mom", "mam"]
  partOfSpeech: PartOfSpeech;
  category: DictionaryCategory;
  gender?: 'masculine' | 'feminine';
  pronunciation?: string;   // IPA: "/ˈmˠɑːhəɾʲ/" (13k+ entries)
  inflections?: string[];   // declined/conjugated forms (97k+ entries)
  source?: DataSource;      // 'curated' | 'lsg' | 'wiktionary' | 'paracrawl'
  searchTerms: string[];    // pre-computed, fada-stripped, lowercase
}
```

---

## Data Pipeline

The dictionary is built from open data sources using a Python pipeline in `scripts/`:

```bash
cd scripts
pip install -r requirements.txt

python import_lsg.py        # LSG Irish WordNet (.po files)
python import_wiktionary.py # kaikki.org JSONL dump (~111 MB)
python import_gramadan.py   # BuNaMo morphology (inflections)
python merge.py             # merge all sources -> irish-dictionary-data.json
```

Output: `src/data/irish-dictionary-data.json` (53 MB, ~136k entries)

---

## Local Development

```bash
git clone https://github.com/m4cd4r4/cupla-focail
cd cupla-focail
npm install
npm run dev        # -> http://localhost:5173
```

**Routes:**
- `/` — Full demo app
- `/embed` — Minimal iframe-embeddable view
- `/embed?category=greetings` — Pre-filtered embed
- `/api/search?q=mother` — REST API (Vercel Functions)
- `/widget.js` — Embeddable floating button script

---

## Deploy Your Own

One-click deploy to Vercel (free):

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https://github.com/m4cd4r4/cupla-focail)

```bash
# Or via CLI
npm install -g vercel
vercel --prod
```

---

## Domain & DNS Configuration

**cuplafocail.ie** is registered at [hostingireland.ie](https://hostingireland.ie) and pointed to Vercel.

### DNS Records

| Name | TTL | Type | Record |
|------|-----|------|--------|
| `cuplafocail.ie` | 14400 | A | `76.76.21.21` |
| `www.cuplafocail.ie` | 14400 | CNAME | `cname.vercel-dns.com` |

---

## Tech Stack

- **Vite** + React 18 + TypeScript
- **Tailwind CSS** — dark Celtic theme
- **React Router** — `/` and `/embed` routes
- **Vercel** — hosting + Node.js serverless API function
- **Python data pipeline** — `scripts/` (import_lsg, import_wiktionary, import_gramadan, merge)

---

## Contributing

Contributions welcome — especially:
- Additional curated entries (accuracy over quantity)
- Example sentences
- Grammar notes (verb conjugations, declensions)
- Corrections to existing entries

Please open an issue before large PRs.

---

## Related

- [**irish-dictionary**](https://github.com/m4cd4r4/irish-dictionary) — npm package (data + search logic only)
- [**Chlann**](https://chlann.com) — Irish-language family messaging app (where this dictionary originated)

---

## License

MIT © [Macdara Mac Domhnaill](https://github.com/m4cd4r4)

Dictionary data licenses:
- LSG Irish WordNet entries: GFDL 1.2+ (tagged `source: 'lsg'`)
- Wiktextract entries: CC BY-SA 4.0 (tagged `source: 'wiktionary'`)
- Hand-curated + ParaCrawl entries: MIT / CC0

*Go n-éirí leat le do chuid Gaeilge!* — Good luck with your Irish!

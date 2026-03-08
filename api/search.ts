import type { VercelRequest, VercelResponse } from '@vercel/node';

// Self-contained: load pre-built JSON so there are no module resolution issues
// eslint-disable-next-line @typescript-eslint/no-require-imports
const ENTRIES: Entry[] = require('./dictionary.json');

interface Entry {
  id: string; irish: string; english: string; englishAlt?: string[];
  partOfSpeech: string; category: string; gender?: string; searchTerms: string[];
}

function normalize(t: string) {
  return t.toLowerCase().replace(/á/g,'a').replace(/é/g,'e').replace(/í/g,'i').replace(/ó/g,'o').replace(/ú/g,'u');
}

function searchEntries(entries: Entry[], query: string, category: string | null, limit: number) {
  const q = normalize(query.trim());
  let pool = category ? entries.filter(e => e.category === category) : entries;
  if (!q) return { entries: pool.slice(0, limit), total: pool.length, query };
  const matched = pool.filter(e => e.searchTerms.some(t => t.includes(q)));
  return { entries: matched.slice(0, limit), total: matched.length, query };
}

function wordOfTheDay(entries: Entry[]) {
  const day = Math.floor((Date.now() - new Date(new Date().getFullYear(), 0, 0).getTime()) / 86_400_000);
  return entries[day % entries.length];
}

function categoryCounts(entries: Entry[]) {
  const counts: Record<string, number> = {};
  for (const e of entries) counts[e.category] = (counts[e.category] ?? 0) + 1;
  return counts;
}

function setCors(res: VercelResponse) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  res.setHeader('Cache-Control', 'public, s-maxage=60, stale-while-revalidate=3600');
}

export default function handler(req: VercelRequest, res: VercelResponse) {
  setCors(res);

  if (req.method === 'OPTIONS') { res.status(204).end(); return; }

  const rawUrl = req.url ?? '/api/search';
  const url = new URL(rawUrl, 'https://focloir.vercel.app');
  const path = url.pathname;

  if (path === '/api/word-of-the-day') {
    res.status(200).json({ entry: wordOfTheDay(ENTRIES) });
    return;
  }

  const entryMatch = path.match(/^\/api\/entry\/(.+)$/);
  if (entryMatch) {
    const entry = ENTRIES.find(e => e.id === decodeURIComponent(entryMatch[1]));
    if (!entry) { res.status(404).json({ error: 'Not found' }); return; }
    res.status(200).json({ entry });
    return;
  }

  if (path === '/api/categories') {
    res.status(200).json({ categories: categoryCounts(ENTRIES), total: ENTRIES.length });
    return;
  }

  const q     = ((req.query['q']       as string) ?? '').trim();
  const cat   = (req.query['category'] as string) ?? '';
  const limit = Math.min(parseInt((req.query['limit'] as string) ?? '20', 10) || 20, 200);
  res.status(200).json(searchEntries(ENTRIES, q, cat || null, limit));
}

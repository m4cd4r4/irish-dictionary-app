// Node.js serverless function — JSON is loaded once and cached in memory
export const config = { runtime: 'nodejs' };

import rawEntries from '../src/data/irish-dictionary-data.json';

interface Entry {
  id: string; irish: string; english: string; englishAlt?: string[];
  partOfSpeech: string; category: string; gender?: string; searchTerms: string[];
  source?: string; pronunciation?: string; inflections?: string[]; synonymIds?: string[];
}

const ENTRIES = rawEntries as unknown as Entry[];

const CORS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type',
  'Cache-Control': 'public, s-maxage=300, stale-while-revalidate=3600',
};

function json(data: unknown, status = 200): Response {
  return new Response(JSON.stringify(data), {
    status,
    headers: { ...CORS, 'Content-Type': 'application/json' },
  });
}

function normalize(t: string) {
  return t.toLowerCase()
    .replace(/á/g, 'a').replace(/é/g, 'e')
    .replace(/í/g, 'i').replace(/ó/g, 'o').replace(/ú/g, 'u');
}

function doSearch(
  entries: Entry[],
  query: string,
  category: string | null,
  source: string | null,
  limit: number,
) {
  const q = normalize(query.trim());
  let pool = category ? entries.filter(e => e.category === category) : entries;
  if (source) {
    const sources = source.split(',').map(s => s.trim());
    pool = pool.filter(e => e.source && sources.includes(e.source));
  }
  if (!q) return { entries: pool.slice(0, limit), total: pool.length, query };
  const matched = pool.filter(e => e.searchTerms.some(t => t.includes(q)));
  return { entries: matched.slice(0, limit), total: matched.length, query };
}

function wordOfTheDay(entries: Entry[]) {
  const day = Math.floor(Date.now() / 86_400_000);
  return entries[day % entries.length];
}

function categoryCounts(entries: Entry[]) {
  const counts: Record<string, number> = {};
  for (const e of entries) counts[e.category] = (counts[e.category] ?? 0) + 1;
  return counts;
}

function sourceCounts(entries: Entry[]) {
  const counts: Record<string, number> = {};
  for (const e of entries) {
    const s = e.source ?? 'curated';
    counts[s] = (counts[s] ?? 0) + 1;
  }
  return counts;
}

export default function handler(request: Request): Response {
  if (request.method === 'OPTIONS') {
    return new Response(null, { status: 204, headers: CORS });
  }

  const url = new URL(request.url);
  const path = url.pathname;

  if (path === '/api/word-of-the-day') {
    return json({ entry: wordOfTheDay(ENTRIES) });
  }

  const entryMatch = path.match(/^\/api\/entry\/(.+)$/);
  if (entryMatch) {
    const entry = ENTRIES.find(e => e.id === decodeURIComponent(entryMatch[1]));
    if (!entry) return json({ error: 'Not found' }, 404);
    return json({ entry });
  }

  if (path === '/api/categories') {
    return json({ categories: categoryCounts(ENTRIES), total: ENTRIES.length });
  }

  if (path === '/api/sources') {
    return json({ sources: sourceCounts(ENTRIES), total: ENTRIES.length });
  }

  const q = (url.searchParams.get('q') ?? '').trim();
  const cat = url.searchParams.get('category') ?? '';
  const src = url.searchParams.get('source') ?? '';
  const limit = Math.min(parseInt(url.searchParams.get('limit') ?? '20', 10) || 20, 200);

  return json(doSearch(ENTRIES, q, cat || null, src || null, limit));
}

import type { VercelRequest, VercelResponse } from '@vercel/node';

// Inline data to avoid ESM import issues in Vercel API functions
// The dictionary is small enough to bundle directly
import { DICTIONARY_ENTRIES } from '../src/data/irish-dictionary';
import { search, categoryCounts, wordOfTheDay, findById } from '../src/search';
import type { DictionaryCategory } from '../src/data/irish-dictionary';

const CORS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type',
  'Cache-Control': 'public, s-maxage=60, stale-while-revalidate=3600',
};

export default function handler(req: VercelRequest, res: VercelResponse) {
  if (req.method === 'OPTIONS') {
    return res.status(204).set(CORS).end();
  }

  const rawUrl = req.url ?? '/api/search';
  const url = new URL(rawUrl, 'https://focloir.vercel.app');
  const path = url.pathname;

  // GET /api/word-of-the-day
  if (path === '/api/word-of-the-day') {
    return res.status(200).set(CORS).json({ entry: wordOfTheDay(DICTIONARY_ENTRIES) });
  }

  // GET /api/entry/:id
  const entryMatch = path.match(/^\/api\/entry\/(.+)$/);
  if (entryMatch) {
    const id = decodeURIComponent(entryMatch[1]);
    const entry = findById(DICTIONARY_ENTRIES, id);
    if (!entry) return res.status(404).set(CORS).json({ error: 'Not found' });
    return res.status(200).set(CORS).json({ entry });
  }

  // GET /api/categories
  if (path === '/api/categories') {
    return res.status(200).set(CORS).json({
      categories: categoryCounts(DICTIONARY_ENTRIES),
      total: DICTIONARY_ENTRIES.length,
    });
  }

  // GET /api/search
  const q      = ((req.query['q']        as string) ?? '').trim();
  const cat    = (req.query['category']  as string) ?? '';
  const limit  = Math.min(parseInt((req.query['limit'] as string) ?? '20', 10) || 20, 200);

  const result = search(DICTIONARY_ENTRIES, q, {
    category: (cat as DictionaryCategory) || null,
    limit,
  });

  return res.status(200).set(CORS).json(result);
}

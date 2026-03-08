// Node.js serverless function
// dictionary.json is co-deployed via vercel.json "includeFiles"
import type { VercelRequest, VercelResponse } from '@vercel/node';
import { readFileSync, existsSync } from 'fs';
import { join } from 'path';

interface Entry {
  id: string; irish: string; english: string; englishAlt?: string[];
  partOfSpeech: string; category: string; gender?: string; searchTerms: string[];
}

// Try multiple paths to find the dictionary JSON
function loadEntries(): Entry[] {
  const candidates = [
    join(__dirname, 'dictionary.json'),
    join(__dirname, '..', 'api', 'dictionary.json'),
    join(process.cwd(), 'api', 'dictionary.json'),
    '/var/task/api/dictionary.json',
  ];
  for (const p of candidates) {
    if (existsSync(p)) {
      return JSON.parse(readFileSync(p, 'utf-8')) as Entry[];
    }
  }
  throw new Error(`dictionary.json not found. Tried: ${candidates.join(', ')}`);
}

let ENTRIES: Entry[];
try {
  ENTRIES = loadEntries();
} catch (e) {
  // Will be reported at request time
  ENTRIES = [];
  console.error('Failed to load dictionary:', e);
}

const CORS: Record<string, string> = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type',
  'Cache-Control': 'public, s-maxage=300, stale-while-revalidate=3600',
};

function normalize(t: string) {
  return t.toLowerCase()
    .replace(/á/g, 'a').replace(/é/g, 'e')
    .replace(/í/g, 'i').replace(/ó/g, 'o').replace(/ú/g, 'u');
}

function doSearch(entries: Entry[], query: string, category: string | null, limit: number) {
  const q = normalize(query.trim());
  const pool = category ? entries.filter(e => e.category === category) : entries;
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

export default function handler(req: VercelRequest, res: VercelResponse) {
  if (req.method === 'OPTIONS') {
    res.writeHead(204, CORS).end();
    return;
  }

  Object.entries(CORS).forEach(([k, v]) => res.setHeader(k, v));
  res.setHeader('Content-Type', 'application/json');

  if (ENTRIES.length === 0) {
    return res.status(500).json({ error: 'Dictionary not loaded', __dirname, cwd: process.cwd() });
  }

  const path = (req.url ?? '').split('?')[0];

  if (path === '/api/word-of-the-day') {
    return res.json({ entry: wordOfTheDay(ENTRIES) });
  }

  const entryMatch = path.match(/^\/api\/entry\/(.+)$/);
  if (entryMatch) {
    const entry = ENTRIES.find(e => e.id === decodeURIComponent(entryMatch[1]));
    if (!entry) return res.status(404).json({ error: 'Not found' });
    return res.json({ entry });
  }

  if (path === '/api/categories') {
    return res.json({ categories: categoryCounts(ENTRIES), total: ENTRIES.length });
  }

  const q = ((req.query['q'] as string) ?? '').trim();
  const cat = (req.query['category'] as string) ?? '';
  const limit = Math.min(parseInt((req.query['limit'] as string) ?? '20', 10) || 20, 200);

  return res.json(doSearch(ENTRIES, q, cat || null, limit));
}

import { useState, useEffect, useRef, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import { SearchInput } from './components/SearchInput';
import { CategoryFilter } from './components/CategoryFilter';
import { EntryCard } from './components/EntryCard';
import { WordOfTheDay } from './components/WordOfTheDay';
import type { DictionaryCategory, DictionaryEntry } from './data/irish-dictionary';

const API_BASE = '/api/search';

interface SearchResult {
  entries: DictionaryEntry[];
  total: number;
  query: string;
}

async function apiFetch<T>(url: string): Promise<T> {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`API error ${r.status}`);
  return r.json() as Promise<T>;
}

export function Embed() {
  const [searchParams] = useSearchParams();
  const initialCategory = searchParams.get('category') as DictionaryCategory | null;

  const [query, setQuery] = useState('');
  const [category, setCategory] = useState<DictionaryCategory | null>(initialCategory);
  const [results, setResults] = useState<SearchResult | null>(null);
  const [wotd, setWotd] = useState<DictionaryEntry | null>(null);
  const [counts, setCounts] = useState<Record<string, number>>({});
  const [total, setTotal] = useState(0);
  const [metaLoaded, setMetaLoaded] = useState(false);

  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    Promise.all([
      apiFetch<{ entry: DictionaryEntry }>('/api/word-of-the-day'),
      apiFetch<{ categories: Record<string, number>; total: number }>('/api/categories'),
    ]).then(([wotdRes, catRes]) => {
      setWotd(wotdRes.entry);
      setCounts(catRes.categories);
      setTotal(catRes.total);
      setMetaLoaded(true);
    }).catch(() => setMetaLoaded(true));
  }, []);

  const runSearch = useCallback((q: string, cat: DictionaryCategory | null) => {
    const params = new URLSearchParams({ limit: '40' });
    if (q) params.set('q', q);
    if (cat) params.set('category', cat);
    apiFetch<SearchResult>(`${API_BASE}?${params}`)
      .then(setResults)
      .catch(() => setResults(null));
  }, []);

  useEffect(() => {
    if (!query && !category) { setResults(null); return; }
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => runSearch(query, category), 250);
    return () => { if (debounceRef.current) clearTimeout(debounceRef.current); };
  }, [query, category, runSearch]);

  const showWotd = !query && !category;

  return (
    <div className="flex flex-col h-full min-h-screen bg-dark-900 text-gray-100">
      {/* Compact header */}
      <div className="flex items-center gap-2 px-4 py-3 border-b border-white/8 bg-dark-900/90 backdrop-blur sticky top-0 z-10">
        <span className="text-lg select-none">🍀</span>
        <span className="font-semibold text-sm text-white">Cupla Focail</span>
        <span className="text-gray-600 text-xs ml-1">Irish-English Dictionary</span>
        <a
          href="/"
          target="_top"
          className="ml-auto text-xs text-shamrock-500 hover:text-shamrock-300 transition-colors"
        >
          Open full site
        </a>
      </div>

      {/* Search */}
      <div className="px-4 pt-4 pb-3">
        <SearchInput value={query} onChange={setQuery} autoFocus />
      </div>

      {/* Category chips */}
      <div className="px-4 pb-3">
        <CategoryFilter selected={category} onChange={setCategory} counts={counts} />
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto px-4 pb-6">
        {!metaLoaded && (
          <div className="flex justify-center pt-12">
            <div className="w-6 h-6 border-2 border-shamrock-600 border-t-transparent rounded-full animate-spin" />
          </div>
        )}

        {metaLoaded && showWotd && wotd && (
          <div className="mb-4">
            <WordOfTheDay entry={wotd} />
          </div>
        )}

        {results && (query || category) && (
          <>
            <p className="text-xs text-gray-600 mb-3" aria-live="polite">
              {results.total} result{results.total !== 1 ? 's' : ''}
            </p>
            <div className="flex flex-col gap-2">
              {results.entries.map(entry => (
                <EntryCard key={entry.id} entry={entry} query={query} />
              ))}
            </div>
            {results.total === 0 && (
              <div className="text-center py-12">
                <p className="text-gray-500 text-sm">No results for "{query}"</p>
              </div>
            )}
          </>
        )}
      </div>

      {/* Footer */}
      <div className="px-4 py-2 border-t border-white/5 flex items-center justify-between">
        <span className="text-xs text-gray-700">
          Powered by{' '}
          <a href="/" target="_top" className="text-shamrock-700 hover:text-shamrock-500 transition-colors">
            cuplafocail.ie
          </a>
        </span>
        <span className="text-xs text-gray-700">{total.toLocaleString()} entries</span>
      </div>
    </div>
  );
}

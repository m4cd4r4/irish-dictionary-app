import { useState, useEffect, useRef, useCallback } from 'react';
import { SearchInput } from './components/SearchInput';
import { CategoryFilter } from './components/CategoryFilter';
import { EntryCard } from './components/EntryCard';
import { WordOfTheDay } from './components/WordOfTheDay';
import { IntegrationPanel } from './components/IntegrationPanel';
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

export function App() {
  const [query, setQuery] = useState('');
  const [category, setCategory] = useState<DictionaryCategory | null>(null);
  const [results, setResults] = useState<SearchResult | null>(null);
  const [wotd, setWotd] = useState<DictionaryEntry | null>(null);
  const [counts, setCounts] = useState<Record<string, number>>({});
  const [total, setTotal] = useState(0);
  const [searching, setSearching] = useState(false);
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
    const params = new URLSearchParams({ limit: '60' });
    if (q) params.set('q', q);
    if (cat) params.set('category', cat);
    setSearching(true);
    apiFetch<SearchResult>(`${API_BASE}?${params}`)
      .then(setResults)
      .catch(() => setResults(null))
      .finally(() => setSearching(false));
  }, []);

  useEffect(() => {
    if (!query && !category) { setResults(null); return; }
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => runSearch(query, category), 250);
    return () => { if (debounceRef.current) clearTimeout(debounceRef.current); };
  }, [query, category, runSearch]);

  const showWotd = !query && !category;

  return (
    <div className="min-h-screen bg-dark-900 flex flex-col">
      <header className="border-b border-white/8 bg-dark-900/80 backdrop-blur-xl sticky top-0 z-20">
        <div className="max-w-5xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-2xl select-none">🍀</span>
            <div>
              <h1 className="text-lg font-bold text-white leading-none">Cupla Focail</h1>
              <p className="text-xs text-gray-500">Irish-English Dictionary</p>
            </div>
          </div>
          <a href="https://github.com/m4cd4r4/cupla-focail" target="_blank" rel="noopener noreferrer"
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-sm text-gray-400 hover:text-gray-200 transition-colors">
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
              <path d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" />
            </svg>
            GitHub
          </a>
        </div>
      </header>

      <section className="relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-b from-shamrock-900/20 to-transparent pointer-events-none" />
        <div className="max-w-3xl mx-auto px-4 py-12 relative">
          <div className="text-center mb-8">
            <h2 className="text-3xl sm:text-4xl font-bold text-white mb-3">Irish-English Dictionary</h2>
            <p className="text-gray-400 text-lg">
              {metaLoaded ? total.toLocaleString() : '135,000+'} entries · Fada-insensitive search · Free &amp; open source
            </p>
          </div>
          <SearchInput value={query} onChange={setQuery} autoFocus />
          {searching && <p className="text-center text-xs text-gray-600 mt-3 animate-pulse">Searching...</p>}
        </div>
      </section>

      <main className="max-w-3xl mx-auto px-4 pb-16 flex-1 w-full">
        <div className="mb-6">
          <CategoryFilter selected={category} onChange={setCategory} counts={counts} />
        </div>

        {showWotd && wotd && (
          <div className="mb-8 animate-fade-in">
            <WordOfTheDay entry={wotd} />
          </div>
        )}

        {results && (query || category) && (
          <div>
            <div className="flex items-center justify-between mb-3">
              <p className="text-sm text-gray-500" aria-live="polite">
                {results.total === 0 ? 'No results'
                  : `${results.total.toLocaleString()} result${results.total === 1 ? '' : 's'}${results.total > 60 ? ' · showing first 60' : ''}`}
              </p>
              {(query || category) && (
                <button onClick={() => { setQuery(''); setCategory(null); }}
                  className="text-xs text-gray-600 hover:text-gray-400 transition-colors">
                  Clear
                </button>
              )}
            </div>
            <div className="flex flex-col gap-2">
              {results.entries.map(entry => <EntryCard key={entry.id} entry={entry} query={query} />)}
            </div>
            {results.total === 0 && (
              <div className="text-center py-16">
                <p className="text-4xl mb-4">🔍</p>
                <p className="text-gray-500">No entries found for "{query}"</p>
                <p className="text-gray-600 text-sm mt-1">Try searching in Irish or English</p>
              </div>
            )}
          </div>
        )}

        {showWotd && metaLoaded && (
          <section className="mt-16">
            <div className="text-center mb-8">
              <h2 className="text-2xl font-bold text-white mb-2">Integrate Anywhere</h2>
              <p className="text-gray-400">Add the Irish dictionary to your app in seconds</p>
            </div>
            <IntegrationPanel />
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mt-8">
              {[
                { icon: '⚡', title: 'Zero Dependencies', desc: 'Pure TypeScript, no external packages required' },
                { icon: '🔍', title: 'Fada-Insensitive', desc: 'Search "mathair" or "máthair" - both work' },
                { icon: '🌐', title: 'Any Framework', desc: 'React, Vue, Svelte, vanilla JS, or REST API' },
              ].map(({ icon, title, desc }) => (
                <div key={title} className="glass rounded-xl p-5 text-center">
                  <div className="text-3xl mb-3">{icon}</div>
                  <h3 className="font-semibold text-gray-200 mb-1">{title}</h3>
                  <p className="text-sm text-gray-500">{desc}</p>
                </div>
              ))}
            </div>
          </section>
        )}
      </main>

      <footer className="border-t border-white/8 bg-dark-950/50">
        <div className="max-w-5xl mx-auto px-4 py-6 flex flex-col sm:flex-row items-center justify-between gap-3">
          <p className="text-sm text-gray-600">
            🍀 Cupla Focail · MIT License · {metaLoaded ? total.toLocaleString() : '135,000+'} entries
          </p>
          <div className="flex items-center gap-4 text-sm">
            <a href="https://github.com/m4cd4r4/cupla-focail" target="_blank" rel="noopener noreferrer" className="text-gray-600 hover:text-gray-400 transition-colors">GitHub</a>
            <a href="https://www.npmjs.com/package/irish-dictionary" target="_blank" rel="noopener noreferrer" className="text-gray-600 hover:text-gray-400 transition-colors">npm</a>
            <a href="/embed" className="text-gray-600 hover:text-gray-400 transition-colors">Embed</a>
            <a href="/api/search?q=hello" className="text-gray-600 hover:text-gray-400 transition-colors">API</a>
          </div>
        </div>
      </footer>
    </div>
  );
}

/**
 * Search Page
 * ===========
 *
 * Semantic code search interface that allows users to:
 *   - Search code using natural language queries
 *   - Filter by repository, entity type
 *   - Choose between semantic, structural, or hybrid search
 *   - View and navigate to search results
 *
 * VISUAL LAYOUT:
 *   ┌─────────────────────────────────────────────────────────┐
 *   │  Search Header                                          │
 *   │  ┌───────────────────────────────────────┬───────────┐ │
 *   │  │ Search Input                          │  Search   │ │
 *   │  └───────────────────────────────────────┴───────────┘ │
 *   ├─────────────────────────────────────────────────────────┤
 *   │  Filters: [Repository ▼] [Type ▼] [Semantic ✓]         │
 *   ├─────────────────────────────────────────────────────────┤
 *   │  Results (X matches)                                    │
 *   │  ┌─────────────────────────────────────────────────┐   │
 *   │  │ Result Card                                      │   │
 *   │  │ - Entity Name, Type, Score                      │   │
 *   │  │ - Code Snippet                                  │   │
 *   │  │ - File Path                                     │   │
 *   │  └─────────────────────────────────────────────────┘   │
 *   └─────────────────────────────────────────────────────────┘
 *
 * SEARCH MODES:
 *   - Semantic: Uses vector embeddings to find similar code
 *   - Structural: Uses Neo4j graph to find by relationships
 *   - Hybrid: Combines both for best results
 */

import { useState, useCallback } from 'react';
import { useQuery, useMutation } from 'react-query';
import {
  MagnifyingGlassIcon,
  FunnelIcon,
  CodeBracketIcon,
  DocumentIcon,
  CubeIcon,
  ArrowPathIcon,
  ClockIcon,
} from '@heroicons/react/24/outline';
import { api, SearchRequest, SearchResult, Repository } from '../services/api';
import { useStore } from '../store/useStore';

// Entity type options for filtering
const entityTypes = [
  { value: '', label: 'All Types' },
  { value: 'function', label: 'Functions' },
  { value: 'class', label: 'Classes' },
  { value: 'method', label: 'Methods' },
  { value: 'module', label: 'Modules' },
  { value: 'variable', label: 'Variables' },
];

// Search mode options
const searchModes = [
  { value: 'hybrid', label: 'Hybrid (Best)', description: 'Combines semantic and structural search' },
  { value: 'semantic', label: 'Semantic', description: 'Natural language understanding' },
  { value: 'structural', label: 'Structural', description: 'Graph-based relationships' },
];

/**
 * Get icon for entity type
 */
function getEntityIcon(type: string) {
  switch (type) {
    case 'function':
    case 'method':
      return CodeBracketIcon;
    case 'class':
      return CubeIcon;
    default:
      return DocumentIcon;
  }
}

/**
 * Score Badge Component
 */
function ScoreBadge({ score }: { score: number }) {
  const percentage = Math.round(score * 100);
  let color = 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400';

  if (percentage >= 80) {
    color = 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400';
  } else if (percentage >= 60) {
    color = 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400';
  } else if (percentage >= 40) {
    color = 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-400';
  }

  return (
    <span className={`px-2 py-1 rounded-full text-xs font-medium ${color}`}>
      {percentage}% match
    </span>
  );
}

/**
 * Search Result Card Component
 */
function ResultCard({ result }: { result: SearchResult }) {
  const { entity, similarity_score, match_type } = result;
  const Icon = getEntityIcon(entity.entity_type);

  return (
    <div className="card p-4 hover:shadow-md transition-shadow">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-primary-100 dark:bg-primary-900/30">
            <Icon className="w-5 h-5 text-primary-600 dark:text-primary-400" />
          </div>
          <div>
            <h3 className="font-semibold text-gray-900 dark:text-white">
              {entity.name}
            </h3>
            <div className="flex items-center gap-2 mt-1">
              <span className="text-xs bg-gray-100 dark:bg-dark-bg text-gray-600 dark:text-gray-400 px-2 py-0.5 rounded">
                {entity.entity_type}
              </span>
              <span className="text-xs text-gray-500 dark:text-gray-400">
                via {match_type}
              </span>
            </div>
          </div>
        </div>
        <ScoreBadge score={similarity_score} />
      </div>

      {/* Code Snippet */}
      {entity.code_snippet && (
        <div className="mt-4">
          <pre className="code-block text-xs overflow-x-auto">
            <code>{entity.code_snippet.slice(0, 300)}
              {entity.code_snippet.length > 300 && '...'}</code>
          </pre>
        </div>
      )}

      {/* Footer */}
      <div className="mt-4 flex items-center justify-between text-sm">
        <span className="text-gray-500 dark:text-gray-400 truncate max-w-md">
          {entity.file_path}:{entity.start_line}-{entity.end_line}
        </span>
      </div>
    </div>
  );
}

/**
 * Recent Searches Component
 */
function RecentSearches({
  searches,
  onSelect,
  onClear,
}: {
  searches: string[];
  onSelect: (query: string) => void;
  onClear: () => void;
}) {
  if (searches.length === 0) return null;

  return (
    <div className="card p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 flex items-center gap-2">
          <ClockIcon className="w-4 h-4" />
          Recent Searches
        </h3>
        <button
          onClick={onClear}
          className="text-xs text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
        >
          Clear
        </button>
      </div>
      <div className="flex flex-wrap gap-2">
        {searches.map((search, index) => (
          <button
            key={index}
            onClick={() => onSelect(search)}
            className="px-3 py-1 text-sm bg-gray-100 dark:bg-dark-bg rounded-full hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
          >
            {search}
          </button>
        ))}
      </div>
    </div>
  );
}

/**
 * Main Search Page Component
 */
function SearchPage() {
  // Local state
  const [query, setQuery] = useState('');
  const [selectedRepo, setSelectedRepo] = useState('');
  const [selectedType, setSelectedType] = useState('');
  const [searchMode, setSearchMode] = useState('hybrid');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [hasSearched, setHasSearched] = useState(false);

  // Global state
  const { recentSearches, addRecentSearch, clearRecentSearches } = useStore();

  // Fetch repositories for filter dropdown
  const { data: repositories } = useQuery('repositories', () =>
    api.repositories.list()
  );

  // Search mutation
  const searchMutation = useMutation(
    (request: SearchRequest) => api.search.query(request),
    {
      onSuccess: (data) => {
        setResults(data);
        setHasSearched(true);
        if (query.trim()) {
          addRecentSearch(query.trim());
        }
      },
    }
  );

  // Handle search
  const handleSearch = useCallback((e?: React.FormEvent) => {
    e?.preventDefault();
    if (!query.trim()) return;

    const request: SearchRequest = {
      query: query.trim(),
      repository_id: selectedRepo || undefined,
      entity_types: selectedType ? [selectedType] : undefined,
      limit: 20,
      use_semantic: searchMode === 'semantic' || searchMode === 'hybrid',
      use_structural: searchMode === 'structural' || searchMode === 'hybrid',
    };

    searchMutation.mutate(request);
  }, [query, selectedRepo, selectedType, searchMode, searchMutation, addRecentSearch]);

  // Handle recent search selection
  const handleRecentSearch = (searchQuery: string) => {
    setQuery(searchQuery);
    // Trigger search after state update
    setTimeout(() => {
      const request: SearchRequest = {
        query: searchQuery,
        repository_id: selectedRepo || undefined,
        entity_types: selectedType ? [selectedType] : undefined,
        limit: 20,
        use_semantic: searchMode === 'semantic' || searchMode === 'hybrid',
        use_structural: searchMode === 'structural' || searchMode === 'hybrid',
      };
      searchMutation.mutate(request);
    }, 0);
  };

  return (
    <div className="space-y-6 animate-fadeIn">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
          Search Code
        </h1>
        <p className="text-gray-500 dark:text-gray-400 mt-1">
          Find code using natural language queries or structural patterns
        </p>
      </div>

      {/* Search Form */}
      <form onSubmit={handleSearch} className="space-y-4">
        {/* Search Input */}
        <div className="flex gap-2">
          <div className="relative flex-1">
            <MagnifyingGlassIcon className="absolute left-4 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search for code... (e.g., 'function that parses JSON')"
              className="input pl-12 pr-4 py-3"
            />
          </div>
          <button
            type="submit"
            disabled={searchMutation.isLoading || !query.trim()}
            className="btn-primary px-6 flex items-center gap-2"
          >
            {searchMutation.isLoading ? (
              <ArrowPathIcon className="w-5 h-5 animate-spin" />
            ) : (
              <MagnifyingGlassIcon className="w-5 h-5" />
            )}
            Search
          </button>
        </div>

        {/* Filters */}
        <div className="card p-4">
          <div className="flex items-center gap-2 mb-4">
            <FunnelIcon className="w-4 h-4 text-gray-500" />
            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
              Filters
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Repository Filter */}
            <div>
              <label className="block text-sm text-gray-600 dark:text-gray-400 mb-1">
                Repository
              </label>
              <select
                value={selectedRepo}
                onChange={(e) => setSelectedRepo(e.target.value)}
                className="input"
              >
                <option value="">All Repositories</option>
                {repositories?.map((repo) => (
                  <option key={repo.id} value={repo.id}>
                    {repo.name}
                  </option>
                ))}
              </select>
            </div>

            {/* Entity Type Filter */}
            <div>
              <label className="block text-sm text-gray-600 dark:text-gray-400 mb-1">
                Entity Type
              </label>
              <select
                value={selectedType}
                onChange={(e) => setSelectedType(e.target.value)}
                className="input"
              >
                {entityTypes.map((type) => (
                  <option key={type.value} value={type.value}>
                    {type.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Search Mode */}
            <div>
              <label className="block text-sm text-gray-600 dark:text-gray-400 mb-1">
                Search Mode
              </label>
              <select
                value={searchMode}
                onChange={(e) => setSearchMode(e.target.value)}
                className="input"
              >
                {searchModes.map((mode) => (
                  <option key={mode.value} value={mode.value}>
                    {mode.label}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>
      </form>

      {/* Recent Searches */}
      {!hasSearched && (
        <RecentSearches
          searches={recentSearches}
          onSelect={handleRecentSearch}
          onClear={clearRecentSearches}
        />
      )}

      {/* Results */}
      {hasSearched && (
        <div>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
              {results.length > 0
                ? `${results.length} result${results.length !== 1 ? 's' : ''} found`
                : 'No results'}
            </h2>
            {results.length > 0 && (
              <span className="text-sm text-gray-500 dark:text-gray-400">
                Sorted by relevance
              </span>
            )}
          </div>

          {searchMutation.isLoading ? (
            <div className="card p-12 text-center">
              <ArrowPathIcon className="w-8 h-8 text-primary-500 animate-spin mx-auto" />
              <p className="mt-4 text-gray-500 dark:text-gray-400">
                Searching code...
              </p>
            </div>
          ) : results.length > 0 ? (
            <div className="space-y-4">
              {results.map((result, index) => (
                <ResultCard key={`${result.entity.id}-${index}`} result={result} />
              ))}
            </div>
          ) : (
            <div className="card p-12 text-center">
              <MagnifyingGlassIcon className="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto" />
              <h3 className="mt-4 text-lg font-medium text-gray-900 dark:text-white">
                No results found
              </h3>
              <p className="text-gray-500 dark:text-gray-400 mt-1 max-w-sm mx-auto">
                Try adjusting your search query or filters to find what you're looking for.
              </p>
            </div>
          )}
        </div>
      )}

      {/* Initial State */}
      {!hasSearched && recentSearches.length === 0 && (
        <div className="card p-12 text-center">
          <MagnifyingGlassIcon className="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto" />
          <h3 className="mt-4 text-lg font-medium text-gray-900 dark:text-white">
            Search your codebase
          </h3>
          <p className="text-gray-500 dark:text-gray-400 mt-1 max-w-md mx-auto">
            Enter a natural language query to find relevant code. You can search for functions,
            classes, or any code pattern using plain English.
          </p>
          <div className="mt-6 flex flex-wrap justify-center gap-2">
            <span className="text-sm text-gray-500 dark:text-gray-400">Try:</span>
            {['function that validates email', 'user authentication', 'database connection'].map((example) => (
              <button
                key={example}
                onClick={() => handleRecentSearch(example)}
                className="px-3 py-1 text-sm bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300 rounded-full hover:bg-primary-200 dark:hover:bg-primary-900/50 transition-colors"
              >
                {example}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default SearchPage;

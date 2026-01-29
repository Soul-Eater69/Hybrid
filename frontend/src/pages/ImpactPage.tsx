/**
 * Impact Analysis Page
 * ====================
 *
 * This page helps users understand the impact of changing code:
 *   - Select an entity (function, class, etc.) to analyze
 *   - View all impacted entities in a visual/list format
 *   - Understand dependency chains and risk levels
 *
 * VISUAL LAYOUT:
 *   ┌─────────────────────────────────────────────────────────┐
 *   │  Header: "Impact Analysis"                              │
 *   ├─────────────────────────────────────────────────────────┤
 *   │  Entity Search / Selection                              │
 *   │  ┌───────────────────────────────────────────────────┐ │
 *   │  │ [Search for entity...]          [Analyze Impact]  │ │
 *   │  └───────────────────────────────────────────────────┘ │
 *   ├─────────────────────────────────────────────────────────┤
 *   │  Impact Summary                                         │
 *   │  [Critical: X] [High: X] [Medium: X] [Low: X]         │
 *   ├─────────────────────────────────────────────────────────┤
 *   │  Impacted Entities List                                 │
 *   │  ┌─────────────────────────────────────────────────┐   │
 *   │  │ Entity | Level | Score | Path                   │   │
 *   │  └─────────────────────────────────────────────────┘   │
 *   └─────────────────────────────────────────────────────────┘
 *
 * HOW IMPACT ANALYSIS WORKS:
 *   1. User selects an entity they want to change
 *   2. System traverses the knowledge graph
 *   3. Finds all entities that depend on the selected one
 *   4. Calculates impact scores based on:
 *      - Distance (direct vs indirect dependency)
 *      - Relationship type (calls, inherits, imports)
 *      - Usage frequency
 */

import { useState, useCallback } from 'react';
import { useQuery, useMutation } from 'react-query';
import {
  BoltIcon,
  MagnifyingGlassIcon,
  ExclamationTriangleIcon,
  ArrowPathIcon,
  ChevronRightIcon,
  CodeBracketIcon,
  CubeIcon,
  DocumentIcon,
} from '@heroicons/react/24/outline';
import { api, ImpactAnalysis, ImpactedEntity, CodeEntity, SearchResult } from '../services/api';

// Impact level colors and styles
const impactLevelConfig = {
  critical: {
    color: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400',
    borderColor: 'border-l-red-500',
    label: 'Critical',
  },
  high: {
    color: 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-400',
    borderColor: 'border-l-orange-500',
    label: 'High',
  },
  medium: {
    color: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400',
    borderColor: 'border-l-yellow-500',
    label: 'Medium',
  },
  low: {
    color: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400',
    borderColor: 'border-l-green-500',
    label: 'Low',
  },
};

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
 * Impact Level Badge Component
 */
function ImpactBadge({ level }: { level: ImpactedEntity['impact_level'] }) {
  const config = impactLevelConfig[level];
  return (
    <span className={`px-2 py-1 rounded-full text-xs font-medium ${config.color}`}>
      {config.label}
    </span>
  );
}

/**
 * Impact Summary Cards
 */
function ImpactSummary({ analysis }: { analysis: ImpactAnalysis }) {
  const counts = {
    critical: 0,
    high: 0,
    medium: 0,
    low: 0,
  };

  analysis.impacted_entities.forEach((entity) => {
    counts[entity.impact_level]++;
  });

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      {(Object.keys(counts) as Array<keyof typeof counts>).map((level) => (
        <div key={level} className={`card p-4 border-l-4 ${impactLevelConfig[level].borderColor}`}>
          <p className="text-2xl font-bold text-gray-900 dark:text-white">
            {counts[level]}
          </p>
          <p className="text-sm text-gray-500 dark:text-gray-400 capitalize">
            {level} Impact
          </p>
        </div>
      ))}
    </div>
  );
}

/**
 * Source Entity Display
 */
function SourceEntityCard({ entity }: { entity: CodeEntity }) {
  const Icon = getEntityIcon(entity.entity_type);

  return (
    <div className="card p-4 border-l-4 border-l-primary-500">
      <div className="flex items-center gap-3">
        <div className="p-2 rounded-lg bg-primary-100 dark:bg-primary-900/30">
          <Icon className="w-5 h-5 text-primary-600 dark:text-primary-400" />
        </div>
        <div>
          <h3 className="font-semibold text-gray-900 dark:text-white">
            {entity.name}
          </h3>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            {entity.entity_type} in {entity.file_path}
          </p>
        </div>
      </div>
      {entity.docstring && (
        <p className="mt-3 text-sm text-gray-600 dark:text-gray-400 italic">
          "{entity.docstring}"
        </p>
      )}
    </div>
  );
}

/**
 * Impacted Entity Card
 */
function ImpactedEntityCard({ impacted }: { impacted: ImpactedEntity }) {
  const { entity, impact_level, impact_score, relationship_path, reason } = impacted;
  const Icon = getEntityIcon(entity.entity_type);
  const config = impactLevelConfig[impact_level];

  return (
    <div className={`card p-4 border-l-4 ${config.borderColor}`}>
      <div className="flex items-start justify-between">
        <div className="flex items-start gap-3">
          <div className="p-2 rounded-lg bg-gray-100 dark:bg-dark-bg">
            <Icon className="w-5 h-5 text-gray-600 dark:text-gray-400" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h4 className="font-medium text-gray-900 dark:text-white">
                {entity.name}
              </h4>
              <ImpactBadge level={impact_level} />
            </div>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
              {entity.entity_type} - Score: {Math.round(impact_score * 100)}%
            </p>
          </div>
        </div>
      </div>

      {/* Reason */}
      <p className="mt-3 text-sm text-gray-600 dark:text-gray-400">
        {reason}
      </p>

      {/* Relationship Path */}
      {relationship_path.length > 0 && (
        <div className="mt-3 flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400 flex-wrap">
          <span className="font-medium">Path:</span>
          {relationship_path.map((step, index) => (
            <span key={index} className="flex items-center">
              {index > 0 && <ChevronRightIcon className="w-3 h-3 mx-1" />}
              <span className="bg-gray-100 dark:bg-dark-bg px-2 py-0.5 rounded">
                {step}
              </span>
            </span>
          ))}
        </div>
      )}

      {/* File Location */}
      <p className="mt-2 text-xs text-gray-400 dark:text-gray-500">
        {entity.file_path}:{entity.start_line}
      </p>
    </div>
  );
}

/**
 * Entity Search Result for Selection
 */
function SearchResultItem({
  result,
  onSelect,
}: {
  result: SearchResult;
  onSelect: (entity: CodeEntity) => void;
}) {
  const Icon = getEntityIcon(result.entity.entity_type);

  return (
    <button
      onClick={() => onSelect(result.entity)}
      className="w-full p-3 flex items-center gap-3 hover:bg-gray-50 dark:hover:bg-dark-bg rounded-lg transition-colors text-left"
    >
      <div className="p-2 rounded-lg bg-gray-100 dark:bg-dark-bg">
        <Icon className="w-4 h-4 text-gray-600 dark:text-gray-400" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="font-medium text-gray-900 dark:text-white truncate">
          {result.entity.name}
        </p>
        <p className="text-xs text-gray-500 dark:text-gray-400 truncate">
          {result.entity.entity_type} - {result.entity.file_path}
        </p>
      </div>
    </button>
  );
}

/**
 * Main Impact Analysis Page Component
 */
function ImpactPage() {
  // State
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedEntity, setSelectedEntity] = useState<CodeEntity | null>(null);
  const [analysis, setAnalysis] = useState<ImpactAnalysis | null>(null);
  const [changeDescription, setChangeDescription] = useState('');
  const [showSearch, setShowSearch] = useState(false);

  // Search for entities
  const searchMutation = useMutation(
    (query: string) =>
      api.search.query({
        query,
        limit: 10,
        use_semantic: true,
        use_structural: true,
      }),
    {
      onSuccess: () => {
        setShowSearch(true);
      },
    }
  );

  // Analyze impact
  const analyzeMutation = useMutation(
    () =>
      api.impact.analyze({
        entity_id: selectedEntity!.id,
        change_description: changeDescription || undefined,
        max_depth: 5,
      }),
    {
      onSuccess: (data) => {
        setAnalysis(data);
      },
    }
  );

  // Handle search
  const handleSearch = useCallback((e: React.FormEvent) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      searchMutation.mutate(searchQuery);
    }
  }, [searchQuery, searchMutation]);

  // Handle entity selection
  const handleSelectEntity = (entity: CodeEntity) => {
    setSelectedEntity(entity);
    setShowSearch(false);
    setAnalysis(null);
  };

  // Handle analyze
  const handleAnalyze = () => {
    if (selectedEntity) {
      analyzeMutation.mutate();
    }
  };

  // Clear selection
  const handleClear = () => {
    setSelectedEntity(null);
    setAnalysis(null);
    setSearchQuery('');
    setChangeDescription('');
  };

  return (
    <div className="space-y-6 animate-fadeIn">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
          Impact Analysis
        </h1>
        <p className="text-gray-500 dark:text-gray-400 mt-1">
          Understand the ripple effects of changing code entities
        </p>
      </div>

      {/* Entity Selection */}
      <div className="card p-6">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          Select Entity to Analyze
        </h2>

        {selectedEntity ? (
          <div className="space-y-4">
            <SourceEntityCard entity={selectedEntity} />

            {/* Change Description */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Describe the planned change (optional)
              </label>
              <textarea
                value={changeDescription}
                onChange={(e) => setChangeDescription(e.target.value)}
                placeholder="e.g., Refactoring this function to use async/await..."
                className="input min-h-[80px]"
              />
            </div>

            <div className="flex gap-3">
              <button onClick={handleClear} className="btn-secondary">
                Select Different Entity
              </button>
              <button
                onClick={handleAnalyze}
                disabled={analyzeMutation.isLoading}
                className="btn-primary flex items-center gap-2"
              >
                {analyzeMutation.isLoading ? (
                  <>
                    <ArrowPathIcon className="w-5 h-5 animate-spin" />
                    Analyzing...
                  </>
                ) : (
                  <>
                    <BoltIcon className="w-5 h-5" />
                    Analyze Impact
                  </>
                )}
              </button>
            </div>
          </div>
        ) : (
          <form onSubmit={handleSearch} className="space-y-4">
            <div className="relative">
              <MagnifyingGlassIcon className="absolute left-4 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search for a function, class, or module..."
                className="input pl-12"
              />
            </div>

            <button
              type="submit"
              disabled={searchMutation.isLoading || !searchQuery.trim()}
              className="btn-primary flex items-center gap-2"
            >
              {searchMutation.isLoading ? (
                <ArrowPathIcon className="w-5 h-5 animate-spin" />
              ) : (
                <MagnifyingGlassIcon className="w-5 h-5" />
              )}
              Search Entities
            </button>

            {/* Search Results */}
            {showSearch && searchMutation.data && (
              <div className="border border-gray-200 dark:border-dark-border rounded-lg max-h-64 overflow-y-auto">
                {searchMutation.data.length > 0 ? (
                  searchMutation.data.map((result, index) => (
                    <SearchResultItem
                      key={`${result.entity.id}-${index}`}
                      result={result}
                      onSelect={handleSelectEntity}
                    />
                  ))
                ) : (
                  <p className="p-4 text-center text-gray-500 dark:text-gray-400">
                    No entities found
                  </p>
                )}
              </div>
            )}
          </form>
        )}
      </div>

      {/* Analysis Results */}
      {analysis && (
        <div className="space-y-6">
          {/* Summary */}
          <div>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                Impact Summary
              </h2>
              <span className="text-sm text-gray-500 dark:text-gray-400">
                Analysis time: {analysis.analysis_time_ms}ms
              </span>
            </div>
            <ImpactSummary analysis={analysis} />
          </div>

          {/* Impacted Entities */}
          <div>
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              Impacted Entities ({analysis.total_impacted})
            </h2>

            {analysis.impacted_entities.length > 0 ? (
              <div className="space-y-3">
                {analysis.impacted_entities.map((impacted, index) => (
                  <ImpactedEntityCard
                    key={`${impacted.entity.id}-${index}`}
                    impacted={impacted}
                  />
                ))}
              </div>
            ) : (
              <div className="card p-8 text-center">
                <ExclamationTriangleIcon className="w-12 h-12 text-green-500 mx-auto" />
                <h3 className="mt-4 text-lg font-medium text-gray-900 dark:text-white">
                  No Impact Detected
                </h3>
                <p className="text-gray-500 dark:text-gray-400 mt-1">
                  This entity appears to be isolated with no dependent code.
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Initial State */}
      {!selectedEntity && !showSearch && (
        <div className="card p-12 text-center">
          <BoltIcon className="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto" />
          <h3 className="mt-4 text-lg font-medium text-gray-900 dark:text-white">
            Understand Change Impact
          </h3>
          <p className="text-gray-500 dark:text-gray-400 mt-1 max-w-md mx-auto">
            Select a code entity (function, class, or module) to see what other parts
            of the codebase would be affected by changing it.
          </p>
        </div>
      )}
    </div>
  );
}

export default ImpactPage;

/**
 * Dashboard Page
 * ==============
 *
 * The home page of the application.
 * Shows an overview with:
 *   - Quick stats (repos, entities, etc.)
 *   - Quick actions (analyze repo, search, etc.)
 *   - Recent activity
 *   - System health status
 *
 * VISUAL LAYOUT:
 *   ┌─────────────────────────────────────────────────────────┐
 *   │  Welcome Banner                                         │
 *   ├────────────┬────────────┬────────────┬────────────────┤
 *   │  Stat Card │  Stat Card │  Stat Card │  Stat Card     │
 *   │  (Repos)   │  (Entities)│  (Searches)│  (Chats)       │
 *   ├────────────┴────────────┴────────────┴────────────────┤
 *   │  Quick Actions                                         │
 *   │  [Analyze Repo] [Search Code] [Impact] [Generate]     │
 *   ├─────────────────────────────────────────────────────────┤
 *   │  Recent Repositories                                   │
 *   └─────────────────────────────────────────────────────────┘
 */

import { useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from 'react-query';
import {
  FolderIcon,
  CodeBracketIcon,
  MagnifyingGlassIcon,
  BoltIcon,
  ChatBubbleLeftRightIcon,
  ArrowRightIcon,
  CheckCircleIcon,
  ExclamationCircleIcon,
} from '@heroicons/react/24/outline';
import { api, Repository, HealthStatus } from '../services/api';
import { useStore } from '../store/useStore';

/**
 * Stat Card Component
 * Displays a single statistic with icon and label
 */
function StatCard({
  icon: Icon,
  label,
  value,
  color,
}: {
  icon: React.ElementType;
  label: string;
  value: string | number;
  color: string;
}) {
  return (
    <div className="card p-6">
      <div className="flex items-center gap-4">
        <div className={`p-3 rounded-lg ${color}`}>
          <Icon className="w-6 h-6 text-white" />
        </div>
        <div>
          <p className="text-2xl font-bold text-gray-900 dark:text-white">
            {value}
          </p>
          <p className="text-sm text-gray-500 dark:text-gray-400">{label}</p>
        </div>
      </div>
    </div>
  );
}

/**
 * Quick Action Button Component
 */
function QuickAction({
  to,
  icon: Icon,
  label,
  description,
}: {
  to: string;
  icon: React.ElementType;
  label: string;
  description: string;
}) {
  return (
    <Link
      to={to}
      className="card p-4 hover:shadow-md transition-shadow group"
    >
      <div className="flex items-start gap-4">
        <div className="p-2 rounded-lg bg-primary-100 dark:bg-primary-900/30 text-primary-600 dark:text-primary-400 group-hover:bg-primary-200 dark:group-hover:bg-primary-900/50 transition-colors">
          <Icon className="w-5 h-5" />
        </div>
        <div className="flex-1">
          <h3 className="font-medium text-gray-900 dark:text-white flex items-center gap-2">
            {label}
            <ArrowRightIcon className="w-4 h-4 opacity-0 group-hover:opacity-100 transition-opacity" />
          </h3>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            {description}
          </p>
        </div>
      </div>
    </Link>
  );
}

/**
 * Repository Status Badge
 */
function StatusBadge({ status }: { status: Repository['status'] }) {
  const statusConfig = {
    ready: { color: 'badge-success', label: 'Ready' },
    analyzing: { color: 'badge-warning', label: 'Analyzing' },
    pending: { color: 'badge-info', label: 'Pending' },
    error: { color: 'badge-error', label: 'Error' },
  };

  const config = statusConfig[status];

  return <span className={config.color}>{config.label}</span>;
}

/**
 * Main Dashboard Page Component
 */
function DashboardPage() {
  const { setRepositories, repositories } = useStore();

  // Fetch repositories list
  const { data: reposData, isLoading: isLoadingRepos } = useQuery(
    'repositories',
    () => api.repositories.list(),
    {
      onSuccess: (data) => setRepositories(data),
    }
  );

  // Fetch health status
  const { data: health } = useQuery('health', () => api.health.check(), {
    retry: false,
  });

  // Calculate stats
  const totalRepos = reposData?.length || 0;
  const readyRepos = reposData?.filter((r) => r.status === 'ready').length || 0;
  const totalEntities = reposData?.reduce((sum, r) => sum + (r.entity_count || 0), 0) || 0;

  return (
    <div className="space-y-8 animate-fadeIn">
      {/* Welcome Banner */}
      <div className="bg-gradient-to-r from-primary-600 to-primary-800 rounded-xl p-8 text-white">
        <h1 className="text-3xl font-bold mb-2">Welcome to Hybrid</h1>
        <p className="text-primary-100 max-w-2xl">
          Your intelligent code analysis platform. Analyze repositories, search
          code semantically, understand impact of changes, and generate code
          using AI.
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          icon={FolderIcon}
          label="Repositories"
          value={isLoadingRepos ? '...' : totalRepos}
          color="bg-blue-500"
        />
        <StatCard
          icon={CodeBracketIcon}
          label="Code Entities"
          value={isLoadingRepos ? '...' : totalEntities.toLocaleString()}
          color="bg-green-500"
        />
        <StatCard
          icon={MagnifyingGlassIcon}
          label="Ready to Search"
          value={isLoadingRepos ? '...' : readyRepos}
          color="bg-purple-500"
        />
        <StatCard
          icon={ChatBubbleLeftRightIcon}
          label="Conversations"
          value="--"
          color="bg-orange-500"
        />
      </div>

      {/* Quick Actions */}
      <div>
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          Quick Actions
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <QuickAction
            to="/repositories"
            icon={FolderIcon}
            label="Analyze Repository"
            description="Clone and analyze a GitHub repository"
          />
          <QuickAction
            to="/search"
            icon={MagnifyingGlassIcon}
            label="Search Code"
            description="Find code using natural language"
          />
          <QuickAction
            to="/impact"
            icon={BoltIcon}
            label="Impact Analysis"
            description="Understand change dependencies"
          />
          <QuickAction
            to="/generate"
            icon={CodeBracketIcon}
            label="Generate Code"
            description="Create code using AI assistance"
          />
        </div>
      </div>

      {/* Recent Repositories */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
            Recent Repositories
          </h2>
          <Link
            to="/repositories"
            className="text-sm text-primary-600 dark:text-primary-400 hover:underline flex items-center gap-1"
          >
            View all
            <ArrowRightIcon className="w-4 h-4" />
          </Link>
        </div>

        {isLoadingRepos ? (
          <div className="card p-8 text-center">
            <div className="animate-spin w-8 h-8 border-4 border-primary-500 border-t-transparent rounded-full mx-auto" />
            <p className="mt-4 text-gray-500 dark:text-gray-400">
              Loading repositories...
            </p>
          </div>
        ) : reposData && reposData.length > 0 ? (
          <div className="card overflow-hidden">
            <table className="w-full">
              <thead className="bg-gray-50 dark:bg-dark-bg">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Repository
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Language
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Entities
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Status
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-dark-border">
                {reposData.slice(0, 5).map((repo) => (
                  <tr
                    key={repo.id}
                    className="hover:bg-gray-50 dark:hover:bg-dark-bg transition-colors"
                  >
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        <FolderIcon className="w-5 h-5 text-gray-400" />
                        <div>
                          <p className="font-medium text-gray-900 dark:text-white">
                            {repo.name}
                          </p>
                          <p className="text-sm text-gray-500 dark:text-gray-400 truncate max-w-xs">
                            {repo.url || repo.local_path}
                          </p>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-500 dark:text-gray-400">
                      {repo.language || 'Unknown'}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-500 dark:text-gray-400">
                      {repo.entity_count?.toLocaleString() || 0}
                    </td>
                    <td className="px-6 py-4">
                      <StatusBadge status={repo.status} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="card p-8 text-center">
            <FolderIcon className="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto mb-4" />
            <p className="text-gray-500 dark:text-gray-400 mb-4">
              No repositories analyzed yet
            </p>
            <Link to="/repositories" className="btn-primary">
              Analyze Your First Repository
            </Link>
          </div>
        )}
      </div>

      {/* System Health */}
      <div>
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          System Health
        </h2>
        <div className="card p-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="flex items-center gap-3">
              {health?.services.neo4j ? (
                <CheckCircleIcon className="w-6 h-6 text-green-500" />
              ) : (
                <ExclamationCircleIcon className="w-6 h-6 text-red-500" />
              )}
              <div>
                <p className="font-medium text-gray-900 dark:text-white">
                  Neo4j Database
                </p>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  {health?.services.neo4j ? 'Connected' : 'Disconnected'}
                </p>
              </div>
            </div>

            <div className="flex items-center gap-3">
              {health?.services.vector_db ? (
                <CheckCircleIcon className="w-6 h-6 text-green-500" />
              ) : (
                <ExclamationCircleIcon className="w-6 h-6 text-red-500" />
              )}
              <div>
                <p className="font-medium text-gray-900 dark:text-white">
                  Vector Database
                </p>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  {health?.services.vector_db ? 'Connected' : 'Disconnected'}
                </p>
              </div>
            </div>

            <div className="flex items-center gap-3">
              {health?.services.cosmos_db ? (
                <CheckCircleIcon className="w-6 h-6 text-green-500" />
              ) : (
                <ExclamationCircleIcon className="w-6 h-6 text-yellow-500" />
              )}
              <div>
                <p className="font-medium text-gray-900 dark:text-white">
                  Cosmos DB
                </p>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  {health?.services.cosmos_db ? 'Connected' : 'Not Configured'}
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default DashboardPage;

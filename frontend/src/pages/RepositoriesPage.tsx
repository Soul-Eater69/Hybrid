/**
 * Repositories Page
 * =================
 *
 * This page manages code repositories:
 *   - List all analyzed repositories
 *   - Add new repository (by URL or local path)
 *   - View repository details
 *   - Delete repositories
 *
 * VISUAL LAYOUT:
 *   ┌─────────────────────────────────────────────────────────┐
 *   │  Header: "Repositories"        [+ Add Repository]       │
 *   ├─────────────────────────────────────────────────────────┤
 *   │  Repository Card                                        │
 *   │  ┌─────────────────────────────────────────────────┐   │
 *   │  │ Name          | Status | Entities | Actions     │   │
 *   │  └─────────────────────────────────────────────────┘   │
 *   │  (repeat for each repository)                          │
 *   └─────────────────────────────────────────────────────────┘
 *
 * DATA FLOW:
 *   1. Page loads -> fetch repositories list
 *   2. User clicks "Add Repository" -> show modal
 *   3. User enters URL -> POST to /api/repositories/analyze
 *   4. Backend clones + analyzes -> poll for status
 *   5. Repository ready -> show in list
 */

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from 'react-query';
import {
  FolderIcon,
  PlusIcon,
  TrashIcon,
  ArrowPathIcon,
  XMarkIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  ClockIcon,
} from '@heroicons/react/24/outline';
import toast from 'react-hot-toast';
import { api, Repository, AnalyzeRequest } from '../services/api';
import { useStore } from '../store/useStore';

/**
 * Add Repository Modal Component
 */
function AddRepositoryModal({
  isOpen,
  onClose,
}: {
  isOpen: boolean;
  onClose: () => void;
}) {
  const [url, setUrl] = useState('');
  const [localPath, setLocalPath] = useState('');
  const [activeTab, setActiveTab] = useState<'url' | 'local'>('url');
  const queryClient = useQueryClient();
  const { addRepository } = useStore();

  // Mutation for analyzing repository
  const analyzeMutation = useMutation(
    (request: AnalyzeRequest) => api.repositories.analyze(request),
    {
      onSuccess: (repo) => {
        addRepository(repo);
        queryClient.invalidateQueries('repositories');
        toast.success(`Repository "${repo.name}" added successfully!`);
        onClose();
        setUrl('');
        setLocalPath('');
      },
      onError: (error: { message: string }) => {
        toast.error(error.message || 'Failed to analyze repository');
      },
    }
  );

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (activeTab === 'url' && url) {
      analyzeMutation.mutate({ url });
    } else if (activeTab === 'local' && localPath) {
      analyzeMutation.mutate({ local_path: localPath });
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative bg-white dark:bg-dark-card rounded-xl shadow-xl w-full max-w-lg mx-4 animate-fadeIn">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-dark-border">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
            Add Repository
          </h2>
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700"
          >
            <XMarkIcon className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        {/* Body */}
        <form onSubmit={handleSubmit} className="p-6">
          {/* Tab Buttons */}
          <div className="flex gap-2 mb-6">
            <button
              type="button"
              onClick={() => setActiveTab('url')}
              className={`flex-1 py-2 px-4 rounded-lg font-medium transition-colors ${
                activeTab === 'url'
                  ? 'bg-primary-100 dark:bg-primary-900/30 text-primary-600 dark:text-primary-400'
                  : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700'
              }`}
            >
              GitHub URL
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('local')}
              className={`flex-1 py-2 px-4 rounded-lg font-medium transition-colors ${
                activeTab === 'local'
                  ? 'bg-primary-100 dark:bg-primary-900/30 text-primary-600 dark:text-primary-400'
                  : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700'
              }`}
            >
              Local Path
            </button>
          </div>

          {/* URL Input */}
          {activeTab === 'url' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Repository URL
              </label>
              <input
                type="url"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="https://github.com/owner/repo"
                className="input"
                required
              />
              <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
                Enter a public GitHub repository URL to clone and analyze.
              </p>
            </div>
          )}

          {/* Local Path Input */}
          {activeTab === 'local' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Local Path
              </label>
              <input
                type="text"
                value={localPath}
                onChange={(e) => setLocalPath(e.target.value)}
                placeholder="/path/to/repository"
                className="input"
                required
              />
              <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
                Enter the absolute path to a local repository on the server.
              </p>
            </div>
          )}

          {/* Actions */}
          <div className="flex gap-3 mt-6">
            <button
              type="button"
              onClick={onClose}
              className="btn-secondary flex-1"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={analyzeMutation.isLoading}
              className="btn-primary flex-1 flex items-center justify-center gap-2"
            >
              {analyzeMutation.isLoading ? (
                <>
                  <ArrowPathIcon className="w-5 h-5 animate-spin" />
                  Analyzing...
                </>
              ) : (
                <>
                  <PlusIcon className="w-5 h-5" />
                  Add Repository
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

/**
 * Repository Status Icon
 */
function StatusIcon({ status }: { status: Repository['status'] }) {
  switch (status) {
    case 'ready':
      return <CheckCircleIcon className="w-5 h-5 text-green-500" />;
    case 'analyzing':
      return <ArrowPathIcon className="w-5 h-5 text-yellow-500 animate-spin" />;
    case 'pending':
      return <ClockIcon className="w-5 h-5 text-blue-500" />;
    case 'error':
      return <ExclamationTriangleIcon className="w-5 h-5 text-red-500" />;
    default:
      return null;
  }
}

/**
 * Repository Card Component
 */
function RepositoryCard({
  repo,
  onDelete,
}: {
  repo: Repository;
  onDelete: (id: string) => void;
}) {
  const [isDeleting, setIsDeleting] = useState(false);

  const handleDelete = async () => {
    if (window.confirm(`Are you sure you want to delete "${repo.name}"?`)) {
      setIsDeleting(true);
      onDelete(repo.id);
    }
  };

  return (
    <div className="card p-6 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between">
        {/* Repo Info */}
        <div className="flex items-start gap-4">
          <div className="p-3 rounded-lg bg-gray-100 dark:bg-dark-bg">
            <FolderIcon className="w-6 h-6 text-gray-600 dark:text-gray-400" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                {repo.name}
              </h3>
              <StatusIcon status={repo.status} />
            </div>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1 truncate max-w-md">
              {repo.url || repo.local_path}
            </p>

            {/* Metadata */}
            <div className="flex items-center gap-4 mt-3 text-sm text-gray-500 dark:text-gray-400">
              <span className="flex items-center gap-1">
                <span className="font-medium">Language:</span>
                {repo.language || 'Unknown'}
              </span>
              <span className="flex items-center gap-1">
                <span className="font-medium">Entities:</span>
                {repo.entity_count?.toLocaleString() || 0}
              </span>
              <span className="flex items-center gap-1">
                <span className="font-medium">Status:</span>
                <span className={`capitalize ${
                  repo.status === 'ready' ? 'text-green-600 dark:text-green-400' :
                  repo.status === 'error' ? 'text-red-600 dark:text-red-400' :
                  repo.status === 'analyzing' ? 'text-yellow-600 dark:text-yellow-400' :
                  ''
                }`}>
                  {repo.status}
                </span>
              </span>
            </div>

            {/* Error message if any */}
            {repo.error_message && (
              <p className="mt-2 text-sm text-red-600 dark:text-red-400">
                Error: {repo.error_message}
              </p>
            )}
          </div>
        </div>

        {/* Actions */}
        <button
          onClick={handleDelete}
          disabled={isDeleting}
          className="p-2 rounded-lg hover:bg-red-100 dark:hover:bg-red-900/30 text-red-600 dark:text-red-400 transition-colors"
          title="Delete repository"
        >
          <TrashIcon className="w-5 h-5" />
        </button>
      </div>
    </div>
  );
}

/**
 * Main Repositories Page Component
 */
function RepositoriesPage() {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const queryClient = useQueryClient();
  const { setRepositories, removeRepository } = useStore();

  // Fetch repositories
  const { data: repositories, isLoading, error } = useQuery(
    'repositories',
    () => api.repositories.list(),
    {
      onSuccess: (data) => setRepositories(data),
      // Poll for status updates if any repo is analyzing
      refetchInterval: (data) =>
        data?.some((r) => r.status === 'analyzing' || r.status === 'pending')
          ? 3000
          : false,
    }
  );

  // Delete mutation
  const deleteMutation = useMutation(
    (id: string) => api.repositories.delete(id),
    {
      onSuccess: (_, id) => {
        removeRepository(id);
        queryClient.invalidateQueries('repositories');
        toast.success('Repository deleted successfully');
      },
      onError: (error: { message: string }) => {
        toast.error(error.message || 'Failed to delete repository');
      },
    }
  );

  return (
    <div className="space-y-6 animate-fadeIn">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            Repositories
          </h1>
          <p className="text-gray-500 dark:text-gray-400 mt-1">
            Manage and analyze your code repositories
          </p>
        </div>
        <button
          onClick={() => setIsModalOpen(true)}
          className="btn-primary flex items-center gap-2"
        >
          <PlusIcon className="w-5 h-5" />
          Add Repository
        </button>
      </div>

      {/* Content */}
      {isLoading ? (
        <div className="card p-12 text-center">
          <ArrowPathIcon className="w-8 h-8 text-primary-500 animate-spin mx-auto" />
          <p className="mt-4 text-gray-500 dark:text-gray-400">
            Loading repositories...
          </p>
        </div>
      ) : error ? (
        <div className="card p-12 text-center">
          <ExclamationTriangleIcon className="w-12 h-12 text-red-500 mx-auto" />
          <p className="mt-4 text-gray-900 dark:text-white font-medium">
            Failed to load repositories
          </p>
          <p className="text-gray-500 dark:text-gray-400 mt-1">
            {(error as { message: string }).message}
          </p>
        </div>
      ) : repositories && repositories.length > 0 ? (
        <div className="space-y-4">
          {repositories.map((repo) => (
            <RepositoryCard
              key={repo.id}
              repo={repo}
              onDelete={(id) => deleteMutation.mutate(id)}
            />
          ))}
        </div>
      ) : (
        <div className="card p-12 text-center">
          <FolderIcon className="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto" />
          <h3 className="mt-4 text-lg font-medium text-gray-900 dark:text-white">
            No repositories yet
          </h3>
          <p className="text-gray-500 dark:text-gray-400 mt-1 max-w-sm mx-auto">
            Add your first repository to start analyzing code and building your knowledge graph.
          </p>
          <button
            onClick={() => setIsModalOpen(true)}
            className="btn-primary mt-6"
          >
            Add Your First Repository
          </button>
        </div>
      )}

      {/* Add Repository Modal */}
      <AddRepositoryModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
      />
    </div>
  );
}

export default RepositoriesPage;

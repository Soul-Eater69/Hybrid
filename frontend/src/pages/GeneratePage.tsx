/**
 * Code Generation Page
 * ====================
 *
 * AI-powered code generation interface that:
 *   - Takes natural language prompts
 *   - Uses RAG (Retrieval Augmented Generation) with similar code
 *   - Generates code in context of the repository
 *   - Shows similar examples used for context
 *
 * VISUAL LAYOUT:
 *   ┌─────────────────────────────────────────────────────────┐
 *   │  Header: "Code Generation"                              │
 *   ├─────────────────────────────────────────────────────────┤
 *   │  Configuration                                          │
 *   │  [Repository ▼]  [Language ▼]                          │
 *   ├─────────────────────────────────────────────────────────┤
 *   │  Prompt Input                                           │
 *   │  ┌───────────────────────────────────────────────────┐ │
 *   │  │ Describe the code you want to generate...         │ │
 *   │  │                                                   │ │
 *   │  │                                    [Generate]     │ │
 *   │  └───────────────────────────────────────────────────┘ │
 *   ├─────────────────────────────────────────────────────────┤
 *   │  Generated Code                                         │
 *   │  ┌───────────────────────────────────────────────────┐ │
 *   │  │ // Generated code appears here                    │ │
 *   │  │ function example() { ... }          [Copy]        │ │
 *   │  └───────────────────────────────────────────────────┘ │
 *   ├─────────────────────────────────────────────────────────┤
 *   │  Similar Examples (Context)                             │
 *   │  [Entity 1] [Entity 2] [Entity 3]                      │
 *   └─────────────────────────────────────────────────────────┘
 *
 * HOW IT WORKS:
 *   1. User provides a natural language prompt
 *   2. System searches for similar code in the repository
 *   3. LangChain creates a context with similar examples
 *   4. GPT generates code using the context
 *   5. Result includes generated code and examples used
 */

import { useState, useCallback } from 'react';
import { useQuery, useMutation } from 'react-query';
import {
  CodeBracketIcon,
  SparklesIcon,
  DocumentDuplicateIcon,
  ArrowPathIcon,
  LightBulbIcon,
  CheckIcon,
  CubeIcon,
  DocumentIcon,
} from '@heroicons/react/24/outline';
import toast from 'react-hot-toast';
import { api, GenerationRequest, GenerationResult, CodeEntity } from '../services/api';

// Language options for code generation
const languages = [
  { value: '', label: 'Auto-detect' },
  { value: 'python', label: 'Python' },
  { value: 'javascript', label: 'JavaScript' },
  { value: 'typescript', label: 'TypeScript' },
  { value: 'java', label: 'Java' },
  { value: 'go', label: 'Go' },
  { value: 'rust', label: 'Rust' },
  { value: 'csharp', label: 'C#' },
];

// Example prompts to help users get started
const examplePrompts = [
  'Write a function to validate email addresses',
  'Create a class for managing user sessions',
  'Implement a binary search algorithm',
  'Write a utility to parse CSV files',
  'Create an async function to fetch API data with retry logic',
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
 * Confidence Badge Component
 */
function ConfidenceBadge({ score }: { score: number }) {
  const percentage = Math.round(score * 100);
  let color = 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400';

  if (percentage >= 80) {
    color = 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400';
  } else if (percentage >= 60) {
    color = 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400';
  }

  return (
    <span className={`px-3 py-1 rounded-full text-sm font-medium ${color}`}>
      {percentage}% confidence
    </span>
  );
}

/**
 * Copy Button Component
 */
function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      toast.success('Code copied to clipboard!');
      setTimeout(() => setCopied(false), 2000);
    } catch {
      toast.error('Failed to copy code');
    }
  };

  return (
    <button
      onClick={handleCopy}
      className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-gray-700 hover:bg-gray-600 text-gray-200 transition-colors"
    >
      {copied ? (
        <>
          <CheckIcon className="w-4 h-4 text-green-400" />
          Copied!
        </>
      ) : (
        <>
          <DocumentDuplicateIcon className="w-4 h-4" />
          Copy
        </>
      )}
    </button>
  );
}

/**
 * Similar Example Card
 */
function SimilarExampleCard({ entity }: { entity: CodeEntity }) {
  const Icon = getEntityIcon(entity.entity_type);

  return (
    <div className="card p-4 hover:shadow-md transition-shadow">
      <div className="flex items-start gap-3">
        <div className="p-2 rounded-lg bg-gray-100 dark:bg-dark-bg">
          <Icon className="w-4 h-4 text-gray-600 dark:text-gray-400" />
        </div>
        <div className="flex-1 min-w-0">
          <h4 className="font-medium text-gray-900 dark:text-white truncate">
            {entity.name}
          </h4>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
            {entity.entity_type}
          </p>
          <p className="text-xs text-gray-400 dark:text-gray-500 mt-1 truncate">
            {entity.file_path}
          </p>
        </div>
      </div>
      {entity.code_snippet && (
        <pre className="mt-3 text-xs code-block p-2 overflow-x-auto max-h-24">
          <code>{entity.code_snippet.slice(0, 200)}
            {entity.code_snippet.length > 200 && '...'}</code>
        </pre>
      )}
    </div>
  );
}

/**
 * Main Code Generation Page Component
 */
function GeneratePage() {
  // State
  const [prompt, setPrompt] = useState('');
  const [selectedRepo, setSelectedRepo] = useState('');
  const [language, setLanguage] = useState('');
  const [result, setResult] = useState<GenerationResult | null>(null);

  // Fetch repositories
  const { data: repositories } = useQuery('repositories', () =>
    api.repositories.list()
  );

  // Generation mutation
  const generateMutation = useMutation(
    (request: GenerationRequest) => api.generate.code(request),
    {
      onSuccess: (data) => {
        setResult(data);
        toast.success('Code generated successfully!');
      },
      onError: (error: { message: string }) => {
        toast.error(error.message || 'Failed to generate code');
      },
    }
  );

  // Handle generate
  const handleGenerate = useCallback((e: React.FormEvent) => {
    e.preventDefault();
    if (!prompt.trim()) return;

    const request: GenerationRequest = {
      prompt: prompt.trim(),
      repository_id: selectedRepo || undefined,
      language: language || undefined,
    };

    generateMutation.mutate(request);
  }, [prompt, selectedRepo, language, generateMutation]);

  // Handle example prompt selection
  const handleExampleClick = (example: string) => {
    setPrompt(example);
  };

  return (
    <div className="space-y-6 animate-fadeIn">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
          Code Generation
        </h1>
        <p className="text-gray-500 dark:text-gray-400 mt-1">
          Generate code using AI with context from your codebase
        </p>
      </div>

      {/* Configuration */}
      <div className="card p-6">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          Configuration
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Repository Selection */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Context Repository
            </label>
            <select
              value={selectedRepo}
              onChange={(e) => setSelectedRepo(e.target.value)}
              className="input"
            >
              <option value="">No repository context</option>
              {repositories?.filter(r => r.status === 'ready').map((repo) => (
                <option key={repo.id} value={repo.id}>
                  {repo.name}
                </option>
              ))}
            </select>
            <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
              Select a repository to use similar code as context
            </p>
          </div>

          {/* Language Selection */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Target Language
            </label>
            <select
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
              className="input"
            >
              {languages.map((lang) => (
                <option key={lang.value} value={lang.value}>
                  {lang.label}
                </option>
              ))}
            </select>
            <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
              Choose the programming language for generated code
            </p>
          </div>
        </div>
      </div>

      {/* Prompt Input */}
      <form onSubmit={handleGenerate} className="card p-6">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          What would you like to generate?
        </h2>

        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="Describe the code you want to generate in natural language...

Example: Write a function that takes a list of numbers and returns the sum of all even numbers."
          className="input min-h-[150px] resize-y"
          required
        />

        {/* Example Prompts */}
        <div className="mt-4">
          <p className="text-sm text-gray-500 dark:text-gray-400 mb-2 flex items-center gap-2">
            <LightBulbIcon className="w-4 h-4" />
            Try an example:
          </p>
          <div className="flex flex-wrap gap-2">
            {examplePrompts.map((example, index) => (
              <button
                key={index}
                type="button"
                onClick={() => handleExampleClick(example)}
                className="px-3 py-1 text-sm bg-gray-100 dark:bg-dark-bg rounded-full hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
              >
                {example}
              </button>
            ))}
          </div>
        </div>

        <div className="mt-6 flex justify-end">
          <button
            type="submit"
            disabled={generateMutation.isLoading || !prompt.trim()}
            className="btn-primary flex items-center gap-2 px-6"
          >
            {generateMutation.isLoading ? (
              <>
                <ArrowPathIcon className="w-5 h-5 animate-spin" />
                Generating...
              </>
            ) : (
              <>
                <SparklesIcon className="w-5 h-5" />
                Generate Code
              </>
            )}
          </button>
        </div>
      </form>

      {/* Generated Code */}
      {result && (
        <div className="space-y-6">
          {/* Code Output */}
          <div className="card overflow-hidden">
            <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-dark-border">
              <div className="flex items-center gap-3">
                <CodeBracketIcon className="w-5 h-5 text-primary-500" />
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                  Generated Code
                </h2>
                <ConfidenceBadge score={result.confidence_score} />
              </div>
              <CopyButton text={result.generated_code} />
            </div>

            <pre className="p-6 bg-gray-900 text-gray-100 overflow-x-auto">
              <code>{result.generated_code}</code>
            </pre>
          </div>

          {/* Explanation */}
          {result.explanation && (
            <div className="card p-6">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-3">
                Explanation
              </h3>
              <p className="text-gray-600 dark:text-gray-400 whitespace-pre-wrap">
                {result.explanation}
              </p>
            </div>
          )}

          {/* Similar Examples */}
          {result.similar_examples && result.similar_examples.length > 0 && (
            <div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                Context Used ({result.similar_examples.length} similar examples)
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {result.similar_examples.map((entity, index) => (
                  <SimilarExampleCard key={`${entity.id}-${index}`} entity={entity} />
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Initial State */}
      {!result && !generateMutation.isLoading && (
        <div className="card p-12 text-center">
          <SparklesIcon className="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto" />
          <h3 className="mt-4 text-lg font-medium text-gray-900 dark:text-white">
            AI-Powered Code Generation
          </h3>
          <p className="text-gray-500 dark:text-gray-400 mt-1 max-w-md mx-auto">
            Describe what you want to build in natural language. The AI will use
            similar code from your repository as context to generate relevant,
            high-quality code.
          </p>
        </div>
      )}
    </div>
  );
}

export default GeneratePage;

/**
 * API Service Layer
 * ==================
 *
 * This file provides a centralized way to communicate with the FastAPI backend.
 *
 * HOW IT WORKS:
 *   1. We create an axios instance with base configuration
 *   2. Each API endpoint has its own function
 *   3. Functions return typed data (TypeScript)
 *   4. Errors are handled consistently
 *
 * DATA FLOW:
 *   React Component
 *        ↓
 *   API Service (this file)
 *        ↓
 *   Axios HTTP Request
 *        ↓
 *   FastAPI Backend (/api/...)
 *        ↓
 *   Response back to Component
 *
 * USAGE EXAMPLE:
 *   import { api } from '@/services/api';
 *   const repos = await api.repositories.list();
 */

import axios, { AxiosError } from 'axios';

// ============================================================================
// BASE CONFIGURATION
// ============================================================================

// Create axios instance with default config
// The proxy in vite.config.ts forwards /api requests to the backend
const apiClient = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000, // 30 seconds timeout
});

// ============================================================================
// TYPE DEFINITIONS
// ============================================================================

/**
 * Repository Types
 */
export interface Repository {
  id: string;
  name: string;
  url: string;
  local_path: string;
  language: string;
  status: 'pending' | 'analyzing' | 'ready' | 'error';
  created_at: string;
  updated_at: string;
  entity_count?: number;
  error_message?: string;
}

export interface AnalyzeRequest {
  url?: string;
  local_path?: string;
}

/**
 * Code Entity Types
 */
export interface CodeEntity {
  id: string;
  name: string;
  entity_type: 'function' | 'class' | 'module' | 'variable' | 'method';
  file_path: string;
  start_line: number;
  end_line: number;
  code_snippet?: string;
  docstring?: string;
  repository_id: string;
}

/**
 * Search Types
 */
export interface SearchResult {
  entity: CodeEntity;
  similarity_score: number;
  match_type: 'semantic' | 'structural' | 'hybrid';
}

export interface SearchRequest {
  query: string;
  repository_id?: string;
  entity_types?: string[];
  limit?: number;
  use_semantic?: boolean;
  use_structural?: boolean;
}

/**
 * Impact Analysis Types
 */
export interface ImpactedEntity {
  entity: CodeEntity;
  impact_level: 'critical' | 'high' | 'medium' | 'low';
  impact_score: number;
  relationship_path: string[];
  reason: string;
}

export interface ImpactAnalysis {
  source_entity: CodeEntity;
  impacted_entities: ImpactedEntity[];
  total_impacted: number;
  analysis_time_ms: number;
}

export interface ImpactRequest {
  entity_id: string;
  change_description?: string;
  max_depth?: number;
}

/**
 * Code Generation Types
 */
export interface GenerationRequest {
  prompt: string;
  repository_id?: string;
  context_entity_ids?: string[];
  language?: string;
  max_tokens?: number;
}

export interface GenerationResult {
  generated_code: string;
  explanation: string;
  similar_examples: CodeEntity[];
  confidence_score: number;
}

/**
 * Chat Types
 */
export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
  metadata?: Record<string, unknown>;
}

export interface Conversation {
  id: string;
  title: string;
  repository_id?: string;
  messages: Message[];
  created_at: string;
  updated_at: string;
}

export interface ChatRequest {
  message: string;
  conversation_id?: string;
  repository_id?: string;
}

export interface ChatResponse {
  message: Message;
  conversation_id: string;
  related_entities?: CodeEntity[];
}

/**
 * Health Check Types
 */
export interface HealthStatus {
  status: string;
  version: string;
  services: {
    neo4j: boolean;
    vector_db: boolean;
    cosmos_db: boolean;
  };
}

/**
 * API Error Type
 */
export interface ApiError {
  message: string;
  status: number;
  details?: Record<string, unknown>;
}

// ============================================================================
// ERROR HANDLING
// ============================================================================

/**
 * Converts axios errors to our ApiError format
 */
function handleError(error: AxiosError): never {
  const apiError: ApiError = {
    message: 'An unexpected error occurred',
    status: 500,
  };

  if (error.response) {
    // Server responded with error status
    apiError.status = error.response.status;
    const data = error.response.data as Record<string, unknown>;
    apiError.message = (data?.detail as string) || (data?.message as string) || error.message;
    apiError.details = data;
  } else if (error.request) {
    // Request made but no response received
    apiError.message = 'Unable to connect to server. Please check your connection.';
    apiError.status = 0;
  } else {
    // Error setting up request
    apiError.message = error.message;
  }

  throw apiError;
}

// ============================================================================
// API FUNCTIONS
// ============================================================================

/**
 * API object containing all endpoint functions.
 * Organized by feature area for easy discovery.
 */
export const api = {
  // --------------------------------------------------------------------------
  // Health Check
  // --------------------------------------------------------------------------
  health: {
    /**
     * Check if the backend is running and services are connected
     */
    async check(): Promise<HealthStatus> {
      try {
        const response = await apiClient.get<HealthStatus>('/health');
        return response.data;
      } catch (error) {
        throw handleError(error as AxiosError);
      }
    },
  },

  // --------------------------------------------------------------------------
  // Repository Management
  // --------------------------------------------------------------------------
  repositories: {
    /**
     * Get all repositories
     */
    async list(): Promise<Repository[]> {
      try {
        const response = await apiClient.get<Repository[]>('/repositories');
        return response.data;
      } catch (error) {
        throw handleError(error as AxiosError);
      }
    },

    /**
     * Get a single repository by ID
     */
    async get(id: string): Promise<Repository> {
      try {
        const response = await apiClient.get<Repository>(`/repositories/${id}`);
        return response.data;
      } catch (error) {
        throw handleError(error as AxiosError);
      }
    },

    /**
     * Analyze a new repository (clone and parse)
     */
    async analyze(request: AnalyzeRequest): Promise<Repository> {
      try {
        const response = await apiClient.post<Repository>('/repositories/analyze', request);
        return response.data;
      } catch (error) {
        throw handleError(error as AxiosError);
      }
    },

    /**
     * Delete a repository and its data
     */
    async delete(id: string): Promise<void> {
      try {
        await apiClient.delete(`/repositories/${id}`);
      } catch (error) {
        throw handleError(error as AxiosError);
      }
    },

    /**
     * Get repository status (for polling during analysis)
     */
    async getStatus(id: string): Promise<Repository> {
      try {
        const response = await apiClient.get<Repository>(`/repositories/${id}/status`);
        return response.data;
      } catch (error) {
        throw handleError(error as AxiosError);
      }
    },

    /**
     * Get entities in a repository
     */
    async getEntities(id: string, entityType?: string): Promise<CodeEntity[]> {
      try {
        const params = entityType ? { entity_type: entityType } : {};
        const response = await apiClient.get<CodeEntity[]>(`/repositories/${id}/entities`, { params });
        return response.data;
      } catch (error) {
        throw handleError(error as AxiosError);
      }
    },
  },

  // --------------------------------------------------------------------------
  // Search
  // --------------------------------------------------------------------------
  search: {
    /**
     * Search for code entities using semantic and/or structural search
     */
    async query(request: SearchRequest): Promise<SearchResult[]> {
      try {
        const response = await apiClient.post<SearchResult[]>('/search', request);
        return response.data;
      } catch (error) {
        throw handleError(error as AxiosError);
      }
    },

    /**
     * Get search suggestions based on partial query
     */
    async suggestions(query: string, repositoryId?: string): Promise<string[]> {
      try {
        const params = { q: query, repository_id: repositoryId };
        const response = await apiClient.get<string[]>('/search/suggestions', { params });
        return response.data;
      } catch (error) {
        throw handleError(error as AxiosError);
      }
    },
  },

  // --------------------------------------------------------------------------
  // Impact Analysis
  // --------------------------------------------------------------------------
  impact: {
    /**
     * Analyze the impact of changing a code entity
     */
    async analyze(request: ImpactRequest): Promise<ImpactAnalysis> {
      try {
        const response = await apiClient.post<ImpactAnalysis>('/impact/analyze', request);
        return response.data;
      } catch (error) {
        throw handleError(error as AxiosError);
      }
    },

    /**
     * Get entity details for impact analysis
     */
    async getEntity(id: string): Promise<CodeEntity> {
      try {
        const response = await apiClient.get<CodeEntity>(`/impact/entity/${id}`);
        return response.data;
      } catch (error) {
        throw handleError(error as AxiosError);
      }
    },
  },

  // --------------------------------------------------------------------------
  // Code Generation
  // --------------------------------------------------------------------------
  generate: {
    /**
     * Generate code based on prompt and context
     */
    async code(request: GenerationRequest): Promise<GenerationResult> {
      try {
        const response = await apiClient.post<GenerationResult>('/generate', request);
        return response.data;
      } catch (error) {
        throw handleError(error as AxiosError);
      }
    },
  },

  // --------------------------------------------------------------------------
  // Chat / Conversations
  // --------------------------------------------------------------------------
  chat: {
    /**
     * Send a chat message and get a response
     */
    async send(request: ChatRequest): Promise<ChatResponse> {
      try {
        const response = await apiClient.post<ChatResponse>('/chat', request);
        return response.data;
      } catch (error) {
        throw handleError(error as AxiosError);
      }
    },

    /**
     * Get all conversations
     */
    async listConversations(): Promise<Conversation[]> {
      try {
        const response = await apiClient.get<Conversation[]>('/chat/conversations');
        return response.data;
      } catch (error) {
        throw handleError(error as AxiosError);
      }
    },

    /**
     * Get a single conversation with messages
     */
    async getConversation(id: string): Promise<Conversation> {
      try {
        const response = await apiClient.get<Conversation>(`/chat/conversations/${id}`);
        return response.data;
      } catch (error) {
        throw handleError(error as AxiosError);
      }
    },

    /**
     * Delete a conversation
     */
    async deleteConversation(id: string): Promise<void> {
      try {
        await apiClient.delete(`/chat/conversations/${id}`);
      } catch (error) {
        throw handleError(error as AxiosError);
      }
    },

    /**
     * Create a new conversation
     */
    async createConversation(title: string, repositoryId?: string): Promise<Conversation> {
      try {
        const response = await apiClient.post<Conversation>('/chat/conversations', {
          title,
          repository_id: repositoryId,
        });
        return response.data;
      } catch (error) {
        throw handleError(error as AxiosError);
      }
    },
  },
};

// Export types for use in components
export type { ApiError };
export default api;

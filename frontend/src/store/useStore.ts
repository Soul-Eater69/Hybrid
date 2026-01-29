/**
 * Global State Store (Zustand)
 * ============================
 *
 * This file manages global application state using Zustand.
 * Zustand is a lightweight state management library.
 *
 * WHY USE ZUSTAND?
 *   - Simple API (no boilerplate like Redux)
 *   - No providers needed
 *   - Works great with React hooks
 *   - TypeScript support out of the box
 *
 * HOW IT WORKS:
 *   1. Define your state shape (interface)
 *   2. Create actions to modify state
 *   3. Use the hook in any component
 *
 * USAGE EXAMPLE:
 *   const { repositories, setRepositories } = useStore();
 */

import { create } from 'zustand';
import { Repository, Conversation, CodeEntity } from '../services/api';

// ============================================================================
// STATE INTERFACE
// ============================================================================

interface AppState {
  // Repository state
  repositories: Repository[];
  selectedRepository: Repository | null;
  isLoadingRepositories: boolean;

  // Search state
  recentSearches: string[];

  // Chat state
  conversations: Conversation[];
  activeConversation: Conversation | null;

  // Selected entity (for impact analysis)
  selectedEntity: CodeEntity | null;

  // UI state
  isSidebarCollapsed: boolean;

  // Actions
  setRepositories: (repos: Repository[]) => void;
  addRepository: (repo: Repository) => void;
  updateRepository: (id: string, updates: Partial<Repository>) => void;
  removeRepository: (id: string) => void;
  setSelectedRepository: (repo: Repository | null) => void;
  setIsLoadingRepositories: (loading: boolean) => void;

  addRecentSearch: (query: string) => void;
  clearRecentSearches: () => void;

  setConversations: (convos: Conversation[]) => void;
  addConversation: (convo: Conversation) => void;
  updateConversation: (id: string, updates: Partial<Conversation>) => void;
  removeConversation: (id: string) => void;
  setActiveConversation: (convo: Conversation | null) => void;

  setSelectedEntity: (entity: CodeEntity | null) => void;

  toggleSidebar: () => void;
}

// ============================================================================
// STORE CREATION
// ============================================================================

/**
 * Main application store.
 * Access using: const state = useStore();
 * Or select specific values: const repos = useStore(state => state.repositories);
 */
export const useStore = create<AppState>((set) => ({
  // --------------------------------------------------------------------------
  // Initial State
  // --------------------------------------------------------------------------

  repositories: [],
  selectedRepository: null,
  isLoadingRepositories: false,

  recentSearches: JSON.parse(localStorage.getItem('recentSearches') || '[]'),

  conversations: [],
  activeConversation: null,

  selectedEntity: null,

  isSidebarCollapsed: false,

  // --------------------------------------------------------------------------
  // Repository Actions
  // --------------------------------------------------------------------------

  setRepositories: (repos) =>
    set({ repositories: repos }),

  addRepository: (repo) =>
    set((state) => ({
      repositories: [...state.repositories, repo],
    })),

  updateRepository: (id, updates) =>
    set((state) => ({
      repositories: state.repositories.map((repo) =>
        repo.id === id ? { ...repo, ...updates } : repo
      ),
    })),

  removeRepository: (id) =>
    set((state) => ({
      repositories: state.repositories.filter((repo) => repo.id !== id),
      // Clear selected if it was the deleted one
      selectedRepository:
        state.selectedRepository?.id === id ? null : state.selectedRepository,
    })),

  setSelectedRepository: (repo) =>
    set({ selectedRepository: repo }),

  setIsLoadingRepositories: (loading) =>
    set({ isLoadingRepositories: loading }),

  // --------------------------------------------------------------------------
  // Search Actions
  // --------------------------------------------------------------------------

  addRecentSearch: (query) =>
    set((state) => {
      // Add to beginning, remove duplicates, limit to 10
      const searches = [
        query,
        ...state.recentSearches.filter((s) => s !== query),
      ].slice(0, 10);

      // Persist to localStorage
      localStorage.setItem('recentSearches', JSON.stringify(searches));

      return { recentSearches: searches };
    }),

  clearRecentSearches: () => {
    localStorage.removeItem('recentSearches');
    return set({ recentSearches: [] });
  },

  // --------------------------------------------------------------------------
  // Chat Actions
  // --------------------------------------------------------------------------

  setConversations: (convos) =>
    set({ conversations: convos }),

  addConversation: (convo) =>
    set((state) => ({
      conversations: [convo, ...state.conversations],
    })),

  updateConversation: (id, updates) =>
    set((state) => ({
      conversations: state.conversations.map((c) =>
        c.id === id ? { ...c, ...updates } : c
      ),
      // Also update active conversation if it matches
      activeConversation:
        state.activeConversation?.id === id
          ? { ...state.activeConversation, ...updates }
          : state.activeConversation,
    })),

  removeConversation: (id) =>
    set((state) => ({
      conversations: state.conversations.filter((c) => c.id !== id),
      activeConversation:
        state.activeConversation?.id === id ? null : state.activeConversation,
    })),

  setActiveConversation: (convo) =>
    set({ activeConversation: convo }),

  // --------------------------------------------------------------------------
  // Entity Actions
  // --------------------------------------------------------------------------

  setSelectedEntity: (entity) =>
    set({ selectedEntity: entity }),

  // --------------------------------------------------------------------------
  // UI Actions
  // --------------------------------------------------------------------------

  toggleSidebar: () =>
    set((state) => ({ isSidebarCollapsed: !state.isSidebarCollapsed })),
}));

export default useStore;

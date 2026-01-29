/**
 * Chat Page
 * =========
 *
 * Interactive chat interface for conversing with the AI about code:
 *   - Create and manage conversations
 *   - Ask questions about the codebase
 *   - Get explanations and suggestions
 *   - View related code entities
 *
 * VISUAL LAYOUT:
 *   ┌───────────────┬─────────────────────────────────────────┐
 *   │ Conversations │  Chat Messages                          │
 *   │               │  ┌─────────────────────────────────────┐│
 *   │ [+ New Chat]  │  │ User: How does X work?             ││
 *   │               │  └─────────────────────────────────────┘│
 *   │ [Conv 1]      │  ┌─────────────────────────────────────┐│
 *   │ [Conv 2]      │  │ AI: X works by...                  ││
 *   │ [Conv 3]      │  │ Related: [Entity1] [Entity2]       ││
 *   │               │  └─────────────────────────────────────┘│
 *   │               │                                         │
 *   │               │  ┌─────────────────────────────────────┐│
 *   │               │  │ Type your message...      [Send]   ││
 *   │               │  └─────────────────────────────────────┘│
 *   └───────────────┴─────────────────────────────────────────┘
 *
 * DATA FLOW:
 *   1. User types message
 *   2. POST to /api/chat with message + conversation_id
 *   3. Backend queries knowledge graph and vector DB
 *   4. LLM generates response with context
 *   5. Response stored in Cosmos DB
 *   6. UI displays message + related entities
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from 'react-query';
import {
  PlusIcon,
  PaperAirplaneIcon,
  TrashIcon,
  ChatBubbleLeftRightIcon,
  ArrowPathIcon,
  UserIcon,
  CpuChipIcon,
  CodeBracketIcon,
  FolderIcon,
} from '@heroicons/react/24/outline';
import toast from 'react-hot-toast';
import { api, Conversation, Message, ChatRequest, Repository } from '../services/api';
import { useStore } from '../store/useStore';

/**
 * Message Bubble Component
 */
function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === 'user';

  return (
    <div className={`flex gap-4 ${isUser ? 'flex-row-reverse' : ''}`}>
      {/* Avatar */}
      <div
        className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
          isUser
            ? 'bg-primary-100 dark:bg-primary-900/30'
            : 'bg-gray-100 dark:bg-dark-bg'
        }`}
      >
        {isUser ? (
          <UserIcon className="w-5 h-5 text-primary-600 dark:text-primary-400" />
        ) : (
          <CpuChipIcon className="w-5 h-5 text-gray-600 dark:text-gray-400" />
        )}
      </div>

      {/* Message Content */}
      <div
        className={`max-w-[80%] ${
          isUser ? 'text-right' : ''
        }`}
      >
        <div
          className={`inline-block p-4 rounded-2xl ${
            isUser
              ? 'bg-primary-600 text-white rounded-br-md'
              : 'bg-gray-100 dark:bg-dark-bg text-gray-900 dark:text-white rounded-bl-md'
          }`}
        >
          <p className="whitespace-pre-wrap">{message.content}</p>
        </div>
        <p className="text-xs text-gray-400 mt-1">
          {new Date(message.timestamp).toLocaleTimeString()}
        </p>
      </div>
    </div>
  );
}

/**
 * Conversation List Item
 */
function ConversationItem({
  conversation,
  isActive,
  onClick,
  onDelete,
}: {
  conversation: Conversation;
  isActive: boolean;
  onClick: () => void;
  onDelete: () => void;
}) {
  return (
    <div
      className={`group flex items-center justify-between px-3 py-2 rounded-lg cursor-pointer transition-colors ${
        isActive
          ? 'bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300'
          : 'hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-700 dark:text-gray-300'
      }`}
      onClick={onClick}
    >
      <div className="flex items-center gap-2 min-w-0 flex-1">
        <ChatBubbleLeftRightIcon className="w-4 h-4 flex-shrink-0" />
        <span className="truncate text-sm">{conversation.title}</span>
      </div>
      <button
        onClick={(e) => {
          e.stopPropagation();
          onDelete();
        }}
        className="opacity-0 group-hover:opacity-100 p-1 hover:bg-red-100 dark:hover:bg-red-900/30 rounded transition-opacity"
      >
        <TrashIcon className="w-4 h-4 text-red-500" />
      </button>
    </div>
  );
}

/**
 * New Conversation Modal
 */
function NewConversationModal({
  isOpen,
  onClose,
  onSubmit,
  repositories,
}: {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (title: string, repoId?: string) => void;
  repositories?: Repository[];
}) {
  const [title, setTitle] = useState('');
  const [repoId, setRepoId] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit(title || 'New Conversation', repoId || undefined);
    setTitle('');
    setRepoId('');
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />
      <div className="relative bg-white dark:bg-dark-card rounded-xl shadow-xl w-full max-w-md mx-4 p-6 animate-fadeIn">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
          New Conversation
        </h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Title
            </label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="What would you like to discuss?"
              className="input"
              autoFocus
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Repository Context (optional)
            </label>
            <select
              value={repoId}
              onChange={(e) => setRepoId(e.target.value)}
              className="input"
            >
              <option value="">No repository</option>
              {repositories?.filter(r => r.status === 'ready').map((repo) => (
                <option key={repo.id} value={repo.id}>
                  {repo.name}
                </option>
              ))}
            </select>
          </div>
          <div className="flex gap-3">
            <button type="button" onClick={onClose} className="btn-secondary flex-1">
              Cancel
            </button>
            <button type="submit" className="btn-primary flex-1">
              Create
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

/**
 * Main Chat Page Component
 */
function ChatPage() {
  // URL params and navigation
  const { conversationId } = useParams<{ conversationId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  // Local state
  const [message, setMessage] = useState('');
  const [isNewConvoModalOpen, setIsNewConvoModalOpen] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Global state
  const {
    conversations,
    setConversations,
    activeConversation,
    setActiveConversation,
    addConversation,
    removeConversation,
  } = useStore();

  // Fetch repositories
  const { data: repositories } = useQuery('repositories', () =>
    api.repositories.list()
  );

  // Fetch conversations
  const { isLoading: isLoadingConversations } = useQuery(
    'conversations',
    () => api.chat.listConversations(),
    {
      onSuccess: (data) => setConversations(data),
    }
  );

  // Fetch current conversation
  const { isLoading: isLoadingConversation } = useQuery(
    ['conversation', conversationId],
    () => api.chat.getConversation(conversationId!),
    {
      enabled: !!conversationId,
      onSuccess: (data) => setActiveConversation(data),
    }
  );

  // Create conversation mutation
  const createMutation = useMutation(
    ({ title, repoId }: { title: string; repoId?: string }) =>
      api.chat.createConversation(title, repoId),
    {
      onSuccess: (newConvo) => {
        addConversation(newConvo);
        navigate(`/chat/${newConvo.id}`);
        toast.success('Conversation created');
      },
    }
  );

  // Delete conversation mutation
  const deleteMutation = useMutation(
    (id: string) => api.chat.deleteConversation(id),
    {
      onSuccess: (_, id) => {
        removeConversation(id);
        if (conversationId === id) {
          navigate('/chat');
        }
        toast.success('Conversation deleted');
      },
    }
  );

  // Send message mutation
  const sendMutation = useMutation(
    (request: ChatRequest) => api.chat.send(request),
    {
      onSuccess: (response) => {
        // If this was a new conversation, navigate to it
        if (!conversationId && response.conversation_id) {
          navigate(`/chat/${response.conversation_id}`);
        }
        // Refresh conversation
        queryClient.invalidateQueries(['conversation', conversationId || response.conversation_id]);
        queryClient.invalidateQueries('conversations');
      },
      onError: (error: { message: string }) => {
        toast.error(error.message || 'Failed to send message');
      },
    }
  );

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [activeConversation?.messages]);

  // Clear active conversation when leaving
  useEffect(() => {
    if (!conversationId) {
      setActiveConversation(null);
    }
  }, [conversationId, setActiveConversation]);

  // Handle send message
  const handleSend = useCallback((e: React.FormEvent) => {
    e.preventDefault();
    if (!message.trim() || sendMutation.isLoading) return;

    const request: ChatRequest = {
      message: message.trim(),
      conversation_id: conversationId,
      repository_id: activeConversation?.repository_id,
    };

    // Optimistically add user message to UI
    if (activeConversation) {
      const optimisticMessage: Message = {
        id: `temp-${Date.now()}`,
        role: 'user',
        content: message.trim(),
        timestamp: new Date().toISOString(),
      };
      setActiveConversation({
        ...activeConversation,
        messages: [...activeConversation.messages, optimisticMessage],
      });
    }

    setMessage('');
    sendMutation.mutate(request);
  }, [message, conversationId, activeConversation, sendMutation, setActiveConversation]);

  // Handle conversation selection
  const handleSelectConversation = (convo: Conversation) => {
    navigate(`/chat/${convo.id}`);
  };

  // Handle new conversation
  const handleNewConversation = (title: string, repoId?: string) => {
    createMutation.mutate({ title, repoId });
  };

  // Handle delete conversation
  const handleDeleteConversation = (id: string) => {
    if (window.confirm('Delete this conversation?')) {
      deleteMutation.mutate(id);
    }
  };

  return (
    <div className="flex h-[calc(100vh-8rem)] animate-fadeIn">
      {/* Sidebar - Conversations List */}
      <div className="w-64 flex-shrink-0 border-r border-gray-200 dark:border-dark-border flex flex-col">
        {/* New Conversation Button */}
        <div className="p-4 border-b border-gray-200 dark:border-dark-border">
          <button
            onClick={() => setIsNewConvoModalOpen(true)}
            className="w-full btn-primary flex items-center justify-center gap-2"
          >
            <PlusIcon className="w-5 h-5" />
            New Chat
          </button>
        </div>

        {/* Conversations List */}
        <div className="flex-1 overflow-y-auto p-2">
          {isLoadingConversations ? (
            <div className="flex items-center justify-center py-8">
              <ArrowPathIcon className="w-6 h-6 text-gray-400 animate-spin" />
            </div>
          ) : conversations.length > 0 ? (
            <div className="space-y-1">
              {conversations.map((convo) => (
                <ConversationItem
                  key={convo.id}
                  conversation={convo}
                  isActive={convo.id === conversationId}
                  onClick={() => handleSelectConversation(convo)}
                  onDelete={() => handleDeleteConversation(convo.id)}
                />
              ))}
            </div>
          ) : (
            <p className="text-center text-gray-500 dark:text-gray-400 text-sm py-4">
              No conversations yet
            </p>
          )}
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col">
        {conversationId && activeConversation ? (
          <>
            {/* Chat Header */}
            <div className="px-6 py-4 border-b border-gray-200 dark:border-dark-border">
              <h2 className="font-semibold text-gray-900 dark:text-white">
                {activeConversation.title}
              </h2>
              {activeConversation.repository_id && (
                <p className="text-sm text-gray-500 dark:text-gray-400 flex items-center gap-1 mt-1">
                  <FolderIcon className="w-4 h-4" />
                  Repository context attached
                </p>
              )}
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-6 space-y-6">
              {isLoadingConversation ? (
                <div className="flex items-center justify-center h-full">
                  <ArrowPathIcon className="w-8 h-8 text-primary-500 animate-spin" />
                </div>
              ) : activeConversation.messages.length > 0 ? (
                activeConversation.messages.map((msg) => (
                  <MessageBubble key={msg.id} message={msg} />
                ))
              ) : (
                <div className="text-center text-gray-500 dark:text-gray-400 py-12">
                  <ChatBubbleLeftRightIcon className="w-12 h-12 mx-auto mb-4 opacity-50" />
                  <p>Start the conversation by sending a message</p>
                </div>
              )}
              {sendMutation.isLoading && (
                <div className="flex gap-4">
                  <div className="w-8 h-8 rounded-full bg-gray-100 dark:bg-dark-bg flex items-center justify-center">
                    <CpuChipIcon className="w-5 h-5 text-gray-600 dark:text-gray-400" />
                  </div>
                  <div className="bg-gray-100 dark:bg-dark-bg rounded-2xl rounded-bl-md p-4">
                    <div className="flex gap-1">
                      <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                      <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                      <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                    </div>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* Message Input */}
            <form onSubmit={handleSend} className="p-4 border-t border-gray-200 dark:border-dark-border">
              <div className="flex gap-3">
                <input
                  type="text"
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  placeholder="Type your message..."
                  className="input flex-1"
                  disabled={sendMutation.isLoading}
                />
                <button
                  type="submit"
                  disabled={!message.trim() || sendMutation.isLoading}
                  className="btn-primary px-4"
                >
                  <PaperAirplaneIcon className="w-5 h-5" />
                </button>
              </div>
            </form>
          </>
        ) : (
          /* Empty State */
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center max-w-md">
              <ChatBubbleLeftRightIcon className="w-16 h-16 text-gray-300 dark:text-gray-600 mx-auto mb-6" />
              <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
                Chat with Your Codebase
              </h2>
              <p className="text-gray-500 dark:text-gray-400 mb-6">
                Start a new conversation to ask questions about your code, get explanations,
                or explore your repository using natural language.
              </p>
              <button
                onClick={() => setIsNewConvoModalOpen(true)}
                className="btn-primary inline-flex items-center gap-2"
              >
                <PlusIcon className="w-5 h-5" />
                Start New Conversation
              </button>
            </div>
          </div>
        )}
      </div>

      {/* New Conversation Modal */}
      <NewConversationModal
        isOpen={isNewConvoModalOpen}
        onClose={() => setIsNewConvoModalOpen(false)}
        onSubmit={handleNewConversation}
        repositories={repositories}
      />
    </div>
  );
}

export default ChatPage;

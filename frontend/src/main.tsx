/**
 * Main Entry Point
 * =================
 *
 * This is where the React application starts.
 *
 * HOW IT WORKS:
 *   1. Import React and ReactDOM
 *   2. Import the root App component
 *   3. Import global styles
 *   4. Render the App into the DOM
 *
 * DATA FLOW:
 *   index.html
 *       ↓
 *   main.tsx (this file)
 *       ↓
 *   App.tsx (router setup)
 *       ↓
 *   Pages (Repository, Search, etc.)
 */

import React from 'react';
import ReactDOM from 'react-dom/client';
import { QueryClient, QueryClientProvider } from 'react-query';
import { Toaster } from 'react-hot-toast';
import App from './App';
import './styles/globals.css';

// Create a React Query client for data fetching
// React Query handles caching, refetching, and loading states
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // Refetch on window focus
      refetchOnWindowFocus: false,
      // Retry failed requests 3 times
      retry: 3,
      // Cache data for 5 minutes
      staleTime: 5 * 60 * 1000,
    },
  },
});

// Get the root element from index.html
const rootElement = document.getElementById('root')!;

// Create a React root and render the app
ReactDOM.createRoot(rootElement).render(
  <React.StrictMode>
    {/* QueryClientProvider makes React Query available throughout the app */}
    <QueryClientProvider client={queryClient}>
      {/* Main App component with routing */}
      <App />
      {/* Toast notifications container */}
      <Toaster
        position="top-right"
        toastOptions={{
          duration: 4000,
          style: {
            background: '#1e293b',
            color: '#f1f5f9',
          },
        }}
      />
    </QueryClientProvider>
  </React.StrictMode>
);

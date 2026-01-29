/**
 * App Component - Main Application Router
 * ========================================
 *
 * This component sets up the routing for the entire application.
 *
 * HOW ROUTING WORKS:
 *   React Router uses URL paths to determine which page to show.
 *
 *   URL: /repositories  -->  RepositoriesPage
 *   URL: /search        -->  SearchPage
 *   URL: /impact        -->  ImpactPage
 *   URL: /generate      -->  GeneratePage
 *   URL: /chat          -->  ChatPage
 *
 * LAYOUT STRUCTURE:
 *   ┌─────────────────────────────────────────────────┐
 *   │                    Header                        │
 *   ├──────────┬──────────────────────────────────────┤
 *   │          │                                      │
 *   │ Sidebar  │           Main Content               │
 *   │  (nav)   │           (page)                     │
 *   │          │                                      │
 *   └──────────┴──────────────────────────────────────┘
 */

import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import DashboardPage from './pages/DashboardPage';
import RepositoriesPage from './pages/RepositoriesPage';
import SearchPage from './pages/SearchPage';
import ImpactPage from './pages/ImpactPage';
import GeneratePage from './pages/GeneratePage';
import ChatPage from './pages/ChatPage';

/**
 * Main App component with routing configuration.
 */
function App() {
  return (
    // BrowserRouter enables client-side routing
    <BrowserRouter>
      {/* Layout wraps all pages with header and sidebar */}
      <Layout>
        {/* Routes define which component to render for each URL */}
        <Routes>
          {/* Dashboard - home page */}
          <Route path="/" element={<DashboardPage />} />

          {/* Repository management */}
          <Route path="/repositories" element={<RepositoriesPage />} />

          {/* Semantic search */}
          <Route path="/search" element={<SearchPage />} />

          {/* Impact analysis */}
          <Route path="/impact" element={<ImpactPage />} />

          {/* Code generation */}
          <Route path="/generate" element={<GeneratePage />} />

          {/* Chat conversations */}
          <Route path="/chat" element={<ChatPage />} />
          <Route path="/chat/:conversationId" element={<ChatPage />} />

          {/* Redirect unknown routes to dashboard */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
}

export default App;

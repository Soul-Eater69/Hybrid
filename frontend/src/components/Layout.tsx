/**
 * Layout Component
 * ================
 *
 * This component provides the main application layout structure:
 * - Header at the top (with logo and dark mode toggle)
 * - Sidebar on the left (navigation menu)
 * - Main content area (where pages render)
 *
 * VISUAL STRUCTURE:
 *   ┌─────────────────────────────────────────────────────────┐
 *   │                      Header                              │
 *   │  [Logo]                              [Dark Mode Toggle]  │
 *   ├──────────────┬──────────────────────────────────────────┤
 *   │              │                                          │
 *   │   Sidebar    │            Main Content                  │
 *   │              │            (children)                    │
 *   │  - Dashboard │                                          │
 *   │  - Repos     │                                          │
 *   │  - Search    │                                          │
 *   │  - Impact    │                                          │
 *   │  - Generate  │                                          │
 *   │  - Chat      │                                          │
 *   │              │                                          │
 *   └──────────────┴──────────────────────────────────────────┘
 */

import { ReactNode, useState, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import {
  HomeIcon,
  FolderIcon,
  MagnifyingGlassIcon,
  BoltIcon,
  CodeBracketIcon,
  ChatBubbleLeftRightIcon,
  SunIcon,
  MoonIcon,
  Bars3Icon,
  XMarkIcon,
} from '@heroicons/react/24/outline';

// Type for Layout props - children is the page content
interface LayoutProps {
  children: ReactNode;
}

// Navigation items configuration
// Each item has: name (display text), path (URL), icon (component)
const navigationItems = [
  { name: 'Dashboard', path: '/', icon: HomeIcon },
  { name: 'Repositories', path: '/repositories', icon: FolderIcon },
  { name: 'Search', path: '/search', icon: MagnifyingGlassIcon },
  { name: 'Impact Analysis', path: '/impact', icon: BoltIcon },
  { name: 'Code Generation', path: '/generate', icon: CodeBracketIcon },
  { name: 'Chat', path: '/chat', icon: ChatBubbleLeftRightIcon },
];

/**
 * Main Layout Component
 * Wraps all pages with consistent header and sidebar navigation.
 */
function Layout({ children }: LayoutProps) {
  // Track dark mode state (stored in localStorage for persistence)
  const [isDarkMode, setIsDarkMode] = useState(() => {
    // Check localStorage first, then system preference
    const saved = localStorage.getItem('darkMode');
    if (saved !== null) {
      return JSON.parse(saved);
    }
    return window.matchMedia('(prefers-color-scheme: dark)').matches;
  });

  // Track mobile sidebar open state
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  // Get current URL path to highlight active nav item
  const location = useLocation();

  // Apply dark mode class to HTML element
  useEffect(() => {
    if (isDarkMode) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
    localStorage.setItem('darkMode', JSON.stringify(isDarkMode));
  }, [isDarkMode]);

  // Toggle dark mode
  const toggleDarkMode = () => {
    setIsDarkMode(!isDarkMode);
  };

  // Close sidebar when navigating (mobile)
  useEffect(() => {
    setIsSidebarOpen(false);
  }, [location.pathname]);

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-dark-bg">
      {/* ================================================================
          HEADER
          Fixed at top, spans full width
          ================================================================ */}
      <header className="fixed top-0 left-0 right-0 z-50 h-16 bg-white dark:bg-dark-card border-b border-gray-200 dark:border-dark-border">
        <div className="flex items-center justify-between h-full px-4">
          {/* Left side: Mobile menu button + Logo */}
          <div className="flex items-center gap-4">
            {/* Mobile menu button - only visible on small screens */}
            <button
              onClick={() => setIsSidebarOpen(!isSidebarOpen)}
              className="lg:hidden p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700"
              aria-label="Toggle menu"
            >
              {isSidebarOpen ? (
                <XMarkIcon className="w-6 h-6 text-gray-600 dark:text-gray-300" />
              ) : (
                <Bars3Icon className="w-6 h-6 text-gray-600 dark:text-gray-300" />
              )}
            </button>

            {/* Logo and App Name */}
            <Link to="/" className="flex items-center gap-3">
              <div className="w-8 h-8 bg-primary-600 rounded-lg flex items-center justify-center">
                <CodeBracketIcon className="w-5 h-5 text-white" />
              </div>
              <span className="text-xl font-bold text-gray-900 dark:text-white">
                Hybrid
              </span>
            </Link>
          </div>

          {/* Right side: Dark mode toggle */}
          <button
            onClick={toggleDarkMode}
            className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
            aria-label="Toggle dark mode"
          >
            {isDarkMode ? (
              <SunIcon className="w-6 h-6 text-yellow-500" />
            ) : (
              <MoonIcon className="w-6 h-6 text-gray-600" />
            )}
          </button>
        </div>
      </header>

      {/* ================================================================
          SIDEBAR
          Fixed on left side, below header
          On mobile: slides in/out based on isSidebarOpen
          ================================================================ */}

      {/* Mobile overlay - darkens background when sidebar is open */}
      {isSidebarOpen && (
        <div
          className="fixed inset-0 z-30 bg-black/50 lg:hidden"
          onClick={() => setIsSidebarOpen(false)}
        />
      )}

      {/* Sidebar navigation */}
      <aside
        className={`
          fixed top-16 left-0 z-40 w-64 h-[calc(100vh-4rem)]
          bg-white dark:bg-dark-card
          border-r border-gray-200 dark:border-dark-border
          transform transition-transform duration-200 ease-in-out
          ${isSidebarOpen ? 'translate-x-0' : '-translate-x-full'}
          lg:translate-x-0
        `}
      >
        <nav className="p-4 space-y-1">
          {navigationItems.map((item) => {
            // Check if this nav item is the current page
            const isActive = location.pathname === item.path ||
              (item.path === '/chat' && location.pathname.startsWith('/chat'));

            return (
              <Link
                key={item.path}
                to={item.path}
                className={`
                  flex items-center gap-3 px-4 py-3 rounded-lg
                  transition-colors duration-150
                  ${isActive
                    ? 'bg-primary-50 dark:bg-primary-900/20 text-primary-600 dark:text-primary-400'
                    : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'
                  }
                `}
              >
                <item.icon className={`w-5 h-5 ${isActive ? 'text-primary-600 dark:text-primary-400' : ''}`} />
                <span className="font-medium">{item.name}</span>
              </Link>
            );
          })}
        </nav>

        {/* Sidebar footer with version info */}
        <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-gray-200 dark:border-dark-border">
          <p className="text-xs text-gray-500 dark:text-gray-400 text-center">
            Hybrid Code Analysis v1.0
          </p>
        </div>
      </aside>

      {/* ================================================================
          MAIN CONTENT AREA
          Offset by header height (top) and sidebar width (left)
          ================================================================ */}
      <main className="pt-16 lg:pl-64 min-h-screen">
        <div className="p-6">
          {children}
        </div>
      </main>
    </div>
  );
}

export default Layout;

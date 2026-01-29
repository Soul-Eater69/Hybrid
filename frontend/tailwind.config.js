/**
 * Tailwind CSS Configuration
 * ==========================
 *
 * Configures Tailwind CSS for the frontend.
 *
 * WHAT IS TAILWIND?
 *   Tailwind is a utility-first CSS framework.
 *   Instead of writing CSS, you use utility classes:
 *
 *   <div class="flex items-center p-4 bg-blue-500 text-white">
 *
 * CUSTOMIZATION:
 *   - colors: Custom color palette
 *   - fontFamily: Custom fonts
 *   - extend: Add new utilities
 */

/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Custom brand colors
        primary: {
          50: '#f0f9ff',
          100: '#e0f2fe',
          200: '#bae6fd',
          300: '#7dd3fc',
          400: '#38bdf8',
          500: '#0ea5e9',
          600: '#0284c7',
          700: '#0369a1',
          800: '#075985',
          900: '#0c4a6e',
        },
        // Dark mode colors
        dark: {
          bg: '#0f172a',
          card: '#1e293b',
          border: '#334155',
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
    },
  },
  plugins: [],
  darkMode: 'class',
}

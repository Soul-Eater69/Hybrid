# Hybrid Code Analysis - Frontend

A React-based frontend for the Hybrid Code Analysis platform. This provides a user interface for analyzing code repositories, semantic search, impact analysis, code generation, and AI-powered chat.

## Quick Start

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build
```

## Project Structure

```
frontend/
├── src/
│   ├── components/          # Reusable UI components
│   │   └── Layout.tsx       # Main layout with header & sidebar
│   ├── pages/               # Page components (one per route)
│   │   ├── DashboardPage.tsx
│   │   ├── RepositoriesPage.tsx
│   │   ├── SearchPage.tsx
│   │   ├── ImpactPage.tsx
│   │   ├── GeneratePage.tsx
│   │   └── ChatPage.tsx
│   ├── services/            # API communication layer
│   │   └── api.ts           # Axios-based API client
│   ├── store/               # Global state management
│   │   └── useStore.ts      # Zustand store
│   ├── styles/              # Global styles
│   │   └── globals.css      # Tailwind + custom CSS
│   ├── App.tsx              # Router configuration
│   └── main.tsx             # Entry point
├── package.json
├── vite.config.ts           # Vite configuration
├── tailwind.config.js       # Tailwind CSS configuration
└── tsconfig.json            # TypeScript configuration
```

## How It Works

### Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                         FRONTEND                                 │
│                                                                  │
│  ┌──────────┐    ┌─────────────┐    ┌──────────────────────┐   │
│  │  React   │───▶│   Zustand   │───▶│   React Query        │   │
│  │  Pages   │    │   Store     │    │   (Data Fetching)    │   │
│  └──────────┘    └─────────────┘    └──────────────────────┘   │
│       ▲                                        │                 │
│       │                                        ▼                 │
│       │                              ┌──────────────────────┐   │
│       └──────────────────────────────│   API Service        │   │
│                                      │   (Axios)            │   │
│                                      └──────────────────────┘   │
└────────────────────────────────────────────────│────────────────┘
                                                 │
                                                 ▼
                                    ┌─────────────────────────┐
                                    │   FastAPI Backend       │
                                    │   /api/...              │
                                    └─────────────────────────┘
```

### Technologies Used

| Technology | Purpose |
|------------|---------|
| React 18 | UI framework |
| TypeScript | Type safety |
| Vite | Build tool & dev server |
| TailwindCSS | Styling |
| React Router | Client-side routing |
| React Query | Server state management |
| Zustand | Client state management |
| Axios | HTTP client |
| Heroicons | Icon library |

## Pages Overview

### 1. Dashboard (`/`)
The home page showing:
- Quick statistics (repos, entities, etc.)
- Quick action buttons
- Recent repositories
- System health status

### 2. Repositories (`/repositories`)
Manage analyzed repositories:
- View all repositories
- Add new repository (URL or local path)
- Monitor analysis progress
- Delete repositories

### 3. Search (`/search`)
Semantic code search:
- Natural language queries
- Filter by repository, entity type
- Choose search mode (semantic/structural/hybrid)
- View matching code entities

### 4. Impact Analysis (`/impact`)
Understand code change effects:
- Search and select an entity
- View impacted entities with severity levels
- See dependency paths
- Understand risk levels

### 5. Code Generation (`/generate`)
AI-powered code generation:
- Natural language prompts
- Repository context selection
- View generated code with explanations
- See similar examples used as context

### 6. Chat (`/chat`)
Interactive AI conversations:
- Create conversation threads
- Ask questions about code
- Get explanations and suggestions
- Persist conversations in Cosmos DB

## API Integration

The frontend communicates with the FastAPI backend through the API service (`src/services/api.ts`).

### Key Endpoints

```typescript
// Repositories
api.repositories.list()
api.repositories.analyze({ url: "..." })
api.repositories.delete(id)

// Search
api.search.query({ query: "...", use_semantic: true })

// Impact Analysis
api.impact.analyze({ entity_id: "...", max_depth: 5 })

// Code Generation
api.generate.code({ prompt: "...", repository_id: "..." })

// Chat
api.chat.send({ message: "...", conversation_id: "..." })
api.chat.listConversations()
```

### Error Handling

All API errors are normalized to a consistent format:

```typescript
interface ApiError {
  message: string;
  status: number;
  details?: Record<string, unknown>;
}
```

## State Management

### Zustand Store

Global state is managed with Zustand (`src/store/useStore.ts`):

```typescript
// Access state in components
const { repositories, setRepositories } = useStore();

// Or select specific values
const repos = useStore(state => state.repositories);
```

### React Query

Server state is managed with React Query:
- Automatic caching (5 minutes)
- Background refetching
- Optimistic updates
- Loading/error states

## Styling

### Tailwind CSS

Using Tailwind for utility-first styling:

```tsx
<div className="bg-white dark:bg-dark-card p-4 rounded-lg shadow">
  <h1 className="text-xl font-bold text-gray-900 dark:text-white">
    Hello World
  </h1>
</div>
```

### Custom Components

Reusable component classes in `globals.css`:

```css
.btn-primary { @apply ... }
.card { @apply ... }
.input { @apply ... }
.badge { @apply ... }
```

### Dark Mode

Dark mode is:
- Toggled via header button
- Persisted in localStorage
- Uses `dark:` prefix for dark variants

## Development

### Environment Setup

The frontend uses Vite's proxy to forward API requests during development:

```typescript
// vite.config.ts
proxy: {
  '/api': {
    target: 'http://localhost:8000',
    changeOrigin: true,
  },
},
```

### Running the App

1. Start the backend:
```bash
cd /path/to/backend
uvicorn src.main:app --reload
```

2. Start the frontend:
```bash
cd frontend
npm run dev
```

3. Open http://localhost:5173

### Building for Production

```bash
npm run build
# Output in dist/ directory
```

## Component Architecture

### Layout Component
```
Layout
├── Header (logo, dark mode toggle)
├── Sidebar (navigation menu)
└── Main Content (children/pages)
```

### Page Component Pattern
```typescript
function SomePage() {
  // 1. Local state
  const [value, setValue] = useState('');

  // 2. Global state
  const { data, setData } = useStore();

  // 3. Data fetching
  const { data: apiData } = useQuery('key', fetchFn);

  // 4. Mutations
  const mutation = useMutation(mutationFn);

  // 5. Handlers
  const handleSubmit = () => { ... };

  // 6. Render
  return ( ... );
}
```

## Browser Support

- Chrome (latest)
- Firefox (latest)
- Safari (latest)
- Edge (latest)

## License

MIT License

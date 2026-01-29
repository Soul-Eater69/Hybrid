# Code Intelligence Backend

A production-ready backend for intelligent code analysis and generation using **Vector DB**, **Neo4j Knowledge Graph**, **Cosmos DB**, **CodeQL**, and **LangChain**.

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Quick Start](#quick-start)
4. [API Reference](#api-reference)
5. [How It Works](#how-it-works)
6. [Configuration](#configuration)
7. [Development](#development)

---

## Overview

This backend provides intelligent code analysis capabilities:

| Feature | Description |
|---------|-------------|
| **Repository Analysis** | Parse and index code repositories using CodeQL and AST |
| **Semantic Search** | Find code by meaning using vector embeddings |
| **Impact Analysis** | Understand what code would be affected by changes |
| **Code Generation** | Generate code following existing codebase patterns |
| **Chat Conversations** | Interactive AI chat with full code context and history |

### Technology Stack

- **FastAPI** - Modern async web framework
- **Neo4j** - Graph database for code relationships
- **ChromaDB** - Vector database for semantic search
- **Cosmos DB** - Conversation persistence for chat
- **CodeQL** - Semantic code analysis (with AST fallback)
- **LangChain** - LLM orchestration for code generation
- **OpenAI** - Embeddings and code generation

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         API Layer                                │
│                     (FastAPI + REST)                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Repository   │  │   Search     │  │   Impact     │          │
│  │  Endpoints   │  │  Endpoints   │  │  Endpoints   │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐                             │
│  │  Generate    │  │    Chat      │                             │
│  │  Endpoints   │  │  Endpoints   │                             │
│  └──────────────┘  └──────────────┘                             │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│                      Service Layer                               │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Repository   │  │   Search     │  │   Impact     │          │
│  │  Service     │  │  Service     │  │  Analyzer    │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │    Code      │  │    Chat      │  │   Cosmos     │          │
│  │  Generator   │  │  Service     │  │  Service     │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   Neo4j      │  │   Vector     │  │   CodeQL     │          │
│  │  Service     │  │  Service     │  │   Parser     │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│                      Storage Layer                               │
│                                                                  │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐    │
│  │     Neo4j      │  │   ChromaDB     │  │   Cosmos DB    │    │
│  │ (Knowledge     │  │   (Vector      │  │ (Conversations)│    │
│  │    Graph)      │  │  Embeddings)   │  │                │    │
│  └────────────────┘  └────────────────┘  └────────────────┘    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Quick Start

### Prerequisites

- Python 3.10+
- Neo4j (local or cloud)
- OpenAI API key

### Installation

```bash
# Clone the repository
git clone <repo-url>
cd code-intel-backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Copy environment file and configure
cp .env.example .env
# Edit .env with your settings
```

### Configuration

Edit `.env` with your settings:

```env
# OpenAI
OPENAI_API_KEY=sk-your-key-here

# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-password

# Cosmos DB (for chat conversations)
COSMOS_ENDPOINT=https://your-account.documents.azure.com:443/
COSMOS_KEY=your-cosmos-key

# Optional: GitHub token for private repos
GITHUB_TOKEN=ghp_your-token
```

### Running

```bash
# Development mode (with auto-reload)
uvicorn src.main:app --reload

# Production mode
uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### API Documentation

Once running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## API Reference

### Analyze a Repository

```bash
# Analyze a GitHub repository
curl -X POST http://localhost:8000/api/v1/repositories \
     -H "Content-Type: application/json" \
     -d '{
         "url": "https://github.com/fastapi/fastapi",
         "branch": "main"
     }'
```

### Semantic Search

```bash
# Search for code by meaning
curl -X POST http://localhost:8000/api/v1/search/semantic \
     -H "Content-Type: application/json" \
     -d '{
         "repository_id": "YOUR_REPO_ID",
         "query": "function that validates email addresses"
     }'
```

### Impact Analysis

```bash
# Analyze change impact
curl -X POST http://localhost:8000/api/v1/impact/analyze \
     -H "Content-Type: application/json" \
     -d '{
         "repository_id": "YOUR_REPO_ID",
         "entity_name": "validate_email",
         "change_description": "Changing return type"
     }'
```

### Code Generation

```bash
# Generate code
curl -X POST http://localhost:8000/api/v1/generate \
     -H "Content-Type: application/json" \
     -d '{
         "repository_id": "YOUR_REPO_ID",
         "prompt": "Create a function to validate phone numbers",
         "include_tests": true
     }'
```

### Chat Conversations

```bash
# Create a new conversation
curl -X POST http://localhost:8000/api/v1/chat/conversations \
     -H "Content-Type: application/json" \
     -d '{
         "user_id": "user-123",
         "repository_id": "YOUR_REPO_ID",
         "initial_message": "How do I validate emails in this codebase?"
     }'

# Send a follow-up message
curl -X POST http://localhost:8000/api/v1/chat/conversations/{CONV_ID}/messages \
     -H "Content-Type: application/json" \
     -d '{
         "user_id": "user-123",
         "content": "Can you show me how to improve the error handling?"
     }'

# List your conversations
curl "http://localhost:8000/api/v1/chat/conversations?user_id=user-123"
```

---

## How It Works

### 1. Repository Analysis Pipeline

When you analyze a repository, here's what happens:

```
GitHub URL / Local Path
        │
        ▼
┌───────────────────┐
│  Clone Repository │  (if remote)
│    (git clone)    │
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│ Detect Language   │
│ (file extensions) │
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│   Parse Code      │
│ (CodeQL or AST)   │
│                   │
│ Extracts:         │
│ - Functions       │
│ - Classes         │
│ - Modules         │
│ - Relationships   │
└─────────┬─────────┘
          │
          ▼
┌───────────────────────────────────────┐
│           Index in Parallel           │
│                                       │
│  ┌─────────────┐    ┌─────────────┐  │
│  │   Neo4j     │    │  ChromaDB   │  │
│  │   (graph)   │    │ (vectors)   │  │
│  └─────────────┘    └─────────────┘  │
└───────────────────────────────────────┘
          │
          ▼
    Repository READY
```

### 2. Knowledge Graph (Neo4j)

Code relationships are stored as a graph:

```
Nodes (Code Entities):
┌──────────────┐
│   :Module    │  Python files
├──────────────┤
│   :Class     │  Class definitions
├──────────────┤
│  :Function   │  Functions/methods
├──────────────┤
│  :Variable   │  Variables/constants
└──────────────┘

Relationships (Edges):
  -[:CALLS]->      Function A calls Function B
  -[:IMPORTS]->    Module A imports Module B
  -[:INHERITS]->   Class A inherits from Class B
  -[:CONTAINS]->   Module contains Function
  -[:USES]->       Entity A uses Entity B
```

### 3. Vector Embeddings (ChromaDB)

Code is converted to embeddings for semantic search:

```
Code Entity
     │
     ▼
┌─────────────────────────────────────┐
│  to_embedding_document()            │
│                                     │
│  "# FUNCTION: validate_email        │
│   File: validators.py               │
│   Documentation: Validates email    │
│   Code: def validate_email(...)..." │
└─────────────────┬───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│      OpenAI Embedding API           │
│    (text-embedding-3-small)         │
└─────────────────┬───────────────────┘
                  │
                  ▼
         [0.23, -0.15, 0.87, ...]
              (1536 dimensions)
                  │
                  ▼
         Stored in ChromaDB
```

### 4. Semantic Search

How semantic search finds code by meaning:

```
User Query: "function to check if email is valid"
                    │
                    ▼
            ┌───────────────┐
            │   Embed Query │
            └───────┬───────┘
                    │
                    ▼
            Query Vector: [0.21, -0.17, 0.89, ...]
                    │
                    ▼
            ┌───────────────┐
            │   ChromaDB    │
            │  Similarity   │
            │    Search     │
            └───────┬───────┘
                    │
                    ▼
        Top matching code entities
        (even if they use different words!)
```

### 5. Impact Analysis

How we find what would be affected by a change:

```
Changed: validate_email()
              │
              ▼
┌─────────────────────────────────────────────┐
│         Neo4j Graph Traversal               │
│                                             │
│  Find all paths TO this entity:             │
│    (caller)-[:CALLS]->(validate_email)      │
│    (user)-[:USES]->(validate_email)         │
│    (child)-[:INHERITS]->(parent)            │
└─────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────┐
│            Score Each Impact                │
│                                             │
│  Score = Base × Distance_Decay × Rel_Weight │
│                                             │
│  Distance Decay:                            │
│    1 hop = 1.0, 2 hops = 0.7, 3 hops = 0.5  │
│                                             │
│  Relationship Weight:                       │
│    INHERITS = 1.0, CALLS = 0.9, USES = 0.7  │
└─────────────────────────────────────────────┘
              │
              ▼
        Ranked Impact Results
        + Recommendations
```

### 6. Code Generation (RAG)

How we generate code that matches your codebase:

```
User Prompt: "Create a function to validate phone numbers"
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                   RETRIEVAL STEP                         │
│                                                          │
│  Vector DB: Find similar code                            │
│    → validate_email(), validate_username()               │
│                                                          │
│  Neo4j: Find related entities                            │
│    → ValidationError, re module, phonenumbers lib        │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                  CONTEXT BUILDING                        │
│                                                          │
│  Combine:                                                │
│  - User's prompt                                         │
│  - Similar code examples                                 │
│  - Related entities                                      │
│  - Style guidelines                                      │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                   LLM GENERATION                         │
│                                                          │
│  System: "You are an expert software engineer..."        │
│  User: [Full context + prompt]                           │
│                                                          │
│  → GPT-4 generates code following existing patterns      │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
                 Generated Code
                 + Explanation
                 + Tests (optional)
```

---

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key | Required |
| `OPENAI_MODEL` | Model for generation | gpt-4-turbo-preview |
| `OPENAI_EMBEDDING_MODEL` | Model for embeddings | text-embedding-3-small |
| `NEO4J_URI` | Neo4j connection URI | bolt://localhost:7687 |
| `NEO4J_USER` | Neo4j username | neo4j |
| `NEO4J_PASSWORD` | Neo4j password | Required |
| `CHROMA_PERSIST_DIRECTORY` | ChromaDB storage | ./data/chroma |
| `CODEQL_PATH` | Path to CodeQL CLI | /usr/local/bin/codeql |
| `GITHUB_TOKEN` | GitHub PAT for private repos | Optional |
| `DEBUG` | Enable debug mode | false |

---

## Development

### Project Structure

```
code-intel-backend/
├── src/
│   ├── api/                 # FastAPI routes
│   │   ├── endpoints/       # Individual endpoints
│   │   ├── dependencies.py  # Dependency injection
│   │   └── router.py        # Route configuration
│   ├── core/                # Core utilities
│   │   ├── config.py        # Settings management
│   │   ├── logging.py       # Logging setup
│   │   └── exceptions.py    # Custom exceptions
│   ├── models/              # Data models
│   │   ├── code_entity.py   # Code entity models
│   │   ├── relationship.py  # Relationship models
│   │   ├── repository.py    # Repository models
│   │   └── impact.py        # Impact analysis models
│   ├── schemas/             # API schemas
│   │   ├── requests.py      # Request schemas
│   │   └── responses.py     # Response schemas
│   ├── services/            # Business logic
│   │   ├── codeql_parser.py # Code parsing
│   │   ├── neo4j_service.py # Graph operations
│   │   ├── vector_service.py# Embedding operations
│   │   ├── repository_service.py
│   │   ├── search_service.py
│   │   ├── impact_analyzer.py
│   │   └── code_generator.py
│   └── main.py              # Application entry
├── tests/                   # Test files
├── docs/                    # Documentation
├── requirements.txt
├── pyproject.toml
└── README.md
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_parser.py
```

### Code Quality

```bash
# Format code
black src tests

# Lint code
ruff check src tests

# Type checking
mypy src
```

---

## License

MIT License - see LICENSE file for details.

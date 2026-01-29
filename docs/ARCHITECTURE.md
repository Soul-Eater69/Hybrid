# Architecture Documentation

This document explains the architecture of the Code Intelligence Backend in detail.

## Table of Contents

1. [System Overview](#system-overview)
2. [Data Flow](#data-flow)
3. [Components](#components)
4. [Service Layer](#service-layer)
5. [Data Models](#data-models)
6. [API Design](#api-design)

---

## System Overview

The Code Intelligence Backend is designed with a **layered architecture** that separates concerns:

```
┌─────────────────────────────────────────────────────────────┐
│                    PRESENTATION LAYER                        │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │                    FastAPI                              │ │
│  │  - REST endpoints                                       │ │
│  │  - Request validation (Pydantic)                        │ │
│  │  - OpenAPI documentation                                │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     SERVICE LAYER                            │
│                                                              │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────────┐│
│  │ Repository  │ │   Search    │ │     Impact              ││
│  │  Service    │ │  Service    │ │    Analyzer             ││
│  └─────────────┘ └─────────────┘ └─────────────────────────┘│
│                                                              │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────────┐│
│  │    Code     │ │   Neo4j     │ │     Vector              ││
│  │  Generator  │ │  Service    │ │    Service              ││
│  └─────────────┘ └─────────────┘ └─────────────────────────┘│
│                                                              │
│  ┌─────────────────────────────────────────────────────────┐│
│  │                   CodeQL Parser                          ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     DATA LAYER                               │
│                                                              │
│  ┌──────────────────────┐  ┌──────────────────────────────┐ │
│  │       Neo4j          │  │         ChromaDB             │ │
│  │   Knowledge Graph    │  │     Vector Embeddings        │ │
│  │                      │  │                              │ │
│  │  - Code entities     │  │  - Semantic embeddings       │ │
│  │  - Relationships     │  │  - Similarity search         │ │
│  │  - Graph traversal   │  │                              │ │
│  └──────────────────────┘  └──────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

---

## Data Flow

### Repository Analysis Flow

```
1. USER REQUEST
   ┌─────────────────────────────────────┐
   │  POST /api/v1/repositories          │
   │  {                                  │
   │    "url": "https://github.com/..."  │
   │  }                                  │
   └─────────────────┬───────────────────┘
                     │
                     ▼
2. REPOSITORY SERVICE
   ┌─────────────────────────────────────┐
   │  a. Validate request                │
   │  b. Clone repository (if remote)    │
   │  c. Detect programming language     │
   │  d. Update status: CLONING          │
   └─────────────────┬───────────────────┘
                     │
                     ▼
3. CODEQL PARSER
   ┌─────────────────────────────────────┐
   │  a. Check CodeQL availability       │
   │     - If available: use CodeQL      │
   │     - If not: fall back to AST      │
   │  b. Parse all source files          │
   │  c. Extract entities:               │
   │     - Modules                       │
   │     - Classes                       │
   │     - Functions                     │
   │     - Variables                     │
   │  d. Extract relationships:          │
   │     - CALLS                         │
   │     - IMPORTS                       │
   │     - INHERITS                      │
   │     - CONTAINS                      │
   │  e. Update status: ANALYZING        │
   └─────────────────┬───────────────────┘
                     │
                     ▼
4. INDEXING (PARALLEL)
   ┌─────────────────────────────────────┐
   │           ┌──────────────────┐      │
   │           │    Neo4j         │      │
   │           │  Store entities  │      │
   │           │  Store relations │      │
   │           └──────────────────┘      │
   │                                     │
   │           ┌──────────────────┐      │
   │           │   ChromaDB       │      │
   │           │  Create embeds   │      │
   │           │  Store vectors   │      │
   │           └──────────────────┘      │
   │                                     │
   │  Update status: INDEXING            │
   └─────────────────┬───────────────────┘
                     │
                     ▼
5. COMPLETE
   ┌─────────────────────────────────────┐
   │  Update status: READY               │
   │  Return repository details          │
   └─────────────────────────────────────┘
```

### Semantic Search Flow

```
1. SEARCH REQUEST
   ┌───────────────────────────────────────┐
   │  POST /api/v1/search/semantic         │
   │  {                                    │
   │    "query": "validate user input",    │
   │    "repository_id": "..."             │
   │  }                                    │
   └─────────────────┬─────────────────────┘
                     │
                     ▼
2. VECTOR SERVICE
   ┌───────────────────────────────────────┐
   │  a. Send query to OpenAI Embeddings   │
   │     "validate user input"             │
   │              ↓                        │
   │     [0.21, -0.17, 0.89, ...]          │
   │                                       │
   │  b. Search ChromaDB for similar       │
   │     vectors using cosine similarity   │
   │                                       │
   │  c. Return top K matches with scores  │
   └─────────────────┬─────────────────────┘
                     │
                     ▼
3. NEO4J SERVICE
   ┌───────────────────────────────────────┐
   │  Enhance results with full entity     │
   │  information from the graph           │
   └─────────────────┬─────────────────────┘
                     │
                     ▼
4. RESPONSE
   ┌───────────────────────────────────────┐
   │  {                                    │
   │    "results": [                       │
   │      {                                │
   │        "entity": {                    │
   │          "name": "validate_email",    │
   │          "file_path": "validators.py",│
   │          ...                          │
   │        },                             │
   │        "score": 0.92                  │
   │      },                               │
   │      ...                              │
   │    ]                                  │
   │  }                                    │
   └───────────────────────────────────────┘
```

### Impact Analysis Flow

```
1. IMPACT REQUEST
   ┌───────────────────────────────────────┐
   │  POST /api/v1/impact/analyze          │
   │  {                                    │
   │    "entity_name": "validate_email",   │
   │    "change_type": "signature_change"  │
   │  }                                    │
   └─────────────────┬─────────────────────┘
                     │
                     ▼
2. FIND SOURCE ENTITY
   ┌───────────────────────────────────────┐
   │  Query Neo4j to find the entity       │
   │  MATCH (e:Entity {name: $name})       │
   │  RETURN e                             │
   └─────────────────┬─────────────────────┘
                     │
                     ▼
3. TRAVERSE GRAPH
   ┌───────────────────────────────────────┐
   │  Find all dependents up to max_depth  │
   │                                       │
   │  MATCH path = (dep)-[*1..3]->(target) │
   │  WHERE target.id = $entity_id         │
   │  RETURN dep, path                     │
   │                                       │
   │  Result: All entities that depend     │
   │  on the changed entity                │
   └─────────────────┬─────────────────────┘
                     │
                     ▼
4. CALCULATE IMPACT SCORES
   ┌───────────────────────────────────────┐
   │  For each dependent entity:           │
   │                                       │
   │  Score = Base × Decay × Weight        │
   │                                       │
   │  Where:                               │
   │  - Base = 10                          │
   │  - Decay = 1.0/0.7/0.5 by distance    │
   │  - Weight = rel type weight           │
   │                                       │
   │  Determine impact level:              │
   │  - CRITICAL: score >= 8, distance = 1 │
   │  - DIRECT: distance = 1               │
   │  - INDIRECT: distance = 2-3           │
   │  - POTENTIAL: distance > 3            │
   └─────────────────┬─────────────────────┘
                     │
                     ▼
5. GENERATE RECOMMENDATIONS
   ┌───────────────────────────────────────┐
   │  Based on impact analysis:            │
   │  - Critical impacts need attention    │
   │  - Tests to update                    │
   │  - API changes to document            │
   └─────────────────┬─────────────────────┘
                     │
                     ▼
6. RESPONSE
   ┌───────────────────────────────────────┐
   │  {                                    │
   │    "impacted_entities": [...],        │
   │    "summary": {...},                  │
   │    "recommendations": [...]           │
   │  }                                    │
   └───────────────────────────────────────┘
```

---

## Components

### CodeQL Parser

The CodeQL Parser extracts code structure using either CodeQL or AST.

**With CodeQL:**
```
Source Code → CodeQL Database → Queries → Structured Results
```

**With AST (fallback):**
```
Source Code → Python ast.parse() → AST Visitor → Entities
```

**Extracted Entities:**

| Entity Type | Attributes |
|-------------|------------|
| Module | name, imports, exports, classes, functions |
| Class | name, bases, methods, attributes, decorators |
| Function | name, parameters, return_type, decorators, complexity |
| Variable | name, type, value, scope |

**Extracted Relationships:**

| Relationship | Description |
|--------------|-------------|
| CALLS | Function A calls Function B |
| IMPORTS | Module A imports Module B |
| INHERITS | Class A extends Class B |
| CONTAINS | Module/Class contains Function |
| USES | Entity A uses Entity B |

### Neo4j Service

Manages the knowledge graph with Cypher queries.

**Key Operations:**

```cypher
-- Store entity
MERGE (e:Entity:Function {id: $id})
SET e += $properties

-- Store relationship
MATCH (source:Entity {id: $source_id})
MATCH (target:Entity {id: $target_id})
MERGE (source)-[r:CALLS]->(target)

-- Find callers
MATCH (caller)-[:CALLS*1..3]->(target {id: $id})
RETURN caller

-- Find dependents (for impact analysis)
MATCH path = (dep)-[:CALLS|USES|IMPORTS*1..3]->(target {id: $id})
RETURN dep, path
```

### Vector Service

Manages embeddings using ChromaDB and OpenAI.

**Embedding Process:**
```python
# 1. Create document from entity
document = entity.to_embedding_document()
# "# FUNCTION: validate_email
#  File: validators.py
#  Documentation: Validates email format
#  Code: def validate_email(email)..."

# 2. Generate embedding
embedding = openai.embed(document)
# [0.23, -0.15, 0.87, ...] (1536 dimensions)

# 3. Store in ChromaDB
collection.add(
    ids=[entity_id],
    embeddings=[embedding],
    documents=[document],
    metadatas=[{...}]
)
```

**Search Process:**
```python
# 1. Embed query
query_embedding = openai.embed(query)

# 2. Find similar
results = collection.query(
    query_embeddings=[query_embedding],
    n_results=10
)

# 3. Return with scores
# Score = 1 / (1 + distance)
```

---

## Data Models

### Code Entity Hierarchy

```
CodeEntity (Base)
├── ModuleEntity
│   └── Additional: imports, exports, classes, functions
├── ClassEntity
│   └── Additional: bases, methods, attributes, is_abstract
├── FunctionEntity
│   └── Additional: signature, parameters, return_type, is_async
└── VariableEntity
    └── Additional: type_annotation, value, is_constant
```

### Relationship Model

```python
class Relationship:
    id: UUID
    source_id: UUID      # Entity that has the relationship
    target_id: UUID      # Entity being referenced
    relationship_type: RelationshipType
    weight: float        # Importance (0-10)
    file_path: str       # Where the relationship was found
    line_number: int     # Line number in source
```

### Impact Model

```python
class ImpactedEntity:
    entity_id: UUID
    entity_name: str
    entity_type: CodeEntityType
    file_path: str
    impact_level: ImpactLevel  # CRITICAL, DIRECT, INDIRECT, POTENTIAL
    impact_score: float        # 0-10
    distance: int              # Hops from source
    relationship_path: list[str]  # ["CALLS", "USES"]
    reason: str                # Human-readable explanation
    suggested_action: str      # What to do
```

---

## API Design

### Endpoint Structure

```
/api/v1
├── /health
│   ├── GET /              Health check
│   ├── GET /ready         Readiness check (dependencies)
│   └── GET /live          Liveness check
│
├── /repositories
│   ├── POST /             Analyze repository
│   ├── GET /              List repositories
│   ├── GET /{id}          Get repository details
│   └── DELETE /{id}       Delete repository
│
├── /search
│   ├── POST /semantic     Semantic code search
│   ├── POST /callers      Find function callers
│   ├── POST /callees      Find function callees
│   ├── POST /dependencies Find entity dependencies
│   ├── POST /similar      Find similar code
│   └── GET /overview/{id} Repository overview
│
├── /impact
│   ├── POST /analyze      Analyze change impact
│   └── POST /summary      Get impact summary
│
└── /generate
    ├── POST /             Generate code
    └── POST /improve      Suggest improvements
```

### Request/Response Examples

**Analyze Repository:**
```json
// Request
POST /api/v1/repositories
{
    "url": "https://github.com/fastapi/fastapi",
    "branch": "main",
    "language": "python"
}

// Response
{
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "fastapi",
    "status": "ready",
    "entity_count": 1250,
    "relationship_count": 3800,
    "language": "python"
}
```

**Semantic Search:**
```json
// Request
POST /api/v1/search/semantic
{
    "repository_id": "550e8400-...",
    "query": "function that validates email",
    "limit": 5
}

// Response
{
    "query": "function that validates email",
    "results": [
        {
            "entity": {
                "id": "...",
                "name": "validate_email",
                "entity_type": "function",
                "file_path": "src/validators.py",
                "start_line": 42
            },
            "score": 0.92
        }
    ],
    "total_count": 5
}
```

**Impact Analysis:**
```json
// Request
POST /api/v1/impact/analyze
{
    "repository_id": "550e8400-...",
    "entity_name": "validate_email",
    "change_type": "signature_change",
    "max_depth": 3
}

// Response
{
    "source_entity": {
        "name": "validate_email",
        "file_path": "src/validators.py"
    },
    "impacted_entities": [
        {
            "entity_name": "register_user",
            "impact_level": "critical",
            "impact_score": 9.0,
            "distance": 1,
            "reason": "Directly calls validate_email"
        }
    ],
    "summary": {
        "total_count": 15,
        "critical_count": 2,
        "direct_count": 5
    },
    "recommendations": [
        "2 critical impacts require immediate attention",
        "Update 5 affected tests before merging"
    ]
}
```

---

## Error Handling

### Custom Exceptions

```python
CodeIntelError (Base)
├── RepositoryError
│   ├── RepositoryNotFoundError
│   ├── RepositoryCloneError
│   └── InvalidRepositoryURLError
├── AnalysisError
│   ├── CodeQLError
│   └── ParsingError
├── StorageError
│   ├── Neo4jError
│   └── VectorDBError
└── GenerationError
    └── LLMError
```

### Error Response Format

```json
{
    "error": "REPOSITORY_NOT_FOUND",
    "message": "Repository not found: invalid-url",
    "details": {
        "repository_url": "invalid-url"
    }
}
```

---

## Performance Considerations

1. **Batch Processing**: Entities are stored in batches to avoid overwhelming Neo4j and ChromaDB

2. **Parallel Indexing**: Neo4j and ChromaDB indexing happens in parallel

3. **Caching**:
   - Settings are cached with lru_cache
   - Vector DB uses persistent storage

4. **Retry Logic**: Network operations use tenacity for automatic retries

5. **Connection Pooling**: Neo4j driver handles connection pooling automatically

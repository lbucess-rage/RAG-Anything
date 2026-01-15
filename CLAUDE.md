# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

RAG-Anything is an all-in-one multimodal RAG (Retrieval-Augmented Generation) framework built on LightRAG. It processes diverse document content—text, images, tables, equations—and builds a multimodal knowledge graph for intelligent retrieval.

## Common Commands

### Installation
```bash
# Using uv (recommended)
uv sync                          # Install dependencies
uv sync --all-extras             # Install with all optional features

# Using pip
pip install raganything
pip install 'raganything[all]'   # With all optional features
```

### Running the Core Library
```bash
# Run examples
uv run python examples/raganything_example.py path/to/document.pdf --api-key YOUR_API_KEY --parser mineru
uv run python examples/modalprocessors_example.py --api-key YOUR_API_KEY
```

### Running the Backend API Server
```bash
cd server/backend

# Add .venv/bin to PATH for MinerU commands
export PATH="/path/to/RAG-Anything/.venv/bin:$PATH"

# Start server
python -m uvicorn app.main:app --host 0.0.0.0 --port 15001 --reload
```

### Linting and Formatting
```bash
# Ruff (used by pre-commit)
ruff format .                    # Format code
ruff check --fix --ignore=E402 . # Lint and auto-fix

# Pre-commit hooks
pre-commit run --all-files
```

## Architecture

### Core Library (`raganything/`)

The main class `RAGAnything` uses a mixin pattern for modularity:

```
RAGAnything (raganything.py)
├── QueryMixin (query.py)         # Query methods: aquery(), aquery_with_multimodal()
├── ProcessorMixin (processor.py) # Document processing: process_document_complete(), insert_content_list()
└── BatchMixin (batch.py)         # Batch operations: process_folder_complete()
```

**Key Components:**
- **Parsers** (`parser.py`): MineruParser, DoclingParser - extract content from PDFs/Office docs
- **Modal Processors** (`modalprocessors.py`): Specialized handlers for each content type
  - `ImageModalProcessor`: VLM-based image analysis
  - `TableModalProcessor`: Table interpretation
  - `EquationModalProcessor`: LaTeX formula processing
  - `GenericModalProcessor`: Custom content types
- **ContextExtractor** (`modalprocessors.py`): Provides surrounding context to modal processors
- **Config** (`config.py`): `RAGAnythingConfig` dataclass for all configuration options

**Processing Flow:**
1. Document → Parser (MinerU/Docling) → Content List
2. Content List → Text goes to LightRAG, Multimodal content to Modal Processors
3. Modal Processors → VLM/LLM analysis → Entity extraction → Knowledge Graph

### Backend API Server (`server/backend/`)

FastAPI server that wraps RAG-Anything for HTTP access:

```
server/backend/
├── app/
│   ├── main.py                   # FastAPI app entry point
│   ├── config.py                 # Server configuration (endpoints, credentials)
│   ├── api/v1/
│   │   ├── documents.py          # POST /api/v1/documents/upload
│   │   ├── query.py              # Query API (LightRAG proxy)
│   │   └── graph.py              # Knowledge graph API (LightRAG proxy)
│   └── services/
│       ├── raganything_service.py # Multimodal document processing
│       ├── lightrag_client.py     # HTTP client for LightRAG API (9621)
│       └── document_service.py    # Document storage & version management
```

**Architecture Pattern:**
- Document upload → RAG-Anything (multimodal processing)
- Query/Graph → Proxy to LightRAG API (port 9621)
- Storage: PostgreSQL (vectors/KV) + Neo4j (graph)

## Configuration

Environment variables are loaded from `.env` (see `env.example`):

**Required External Services:**
- LLM API (OpenAI-compatible): `LLM_BINDING_HOST`, `LLM_BINDING_API_KEY`
- VLM API: For image processing (GPT-4o or compatible)
- Embedding API: `EMBEDDING_BINDING_HOST`
- PostgreSQL: Vector and KV storage
- Neo4j: Knowledge graph storage

**Parser Selection:**
- `PARSER=mineru` (default) - GPU recommended, supports PDF/images/Office
- `PARSER=docling` - Alternative parser

## Key Patterns

**Async-First Design:** All main methods are async (`aquery`, `process_document_complete`). Sync wrappers available (`query`).

**LightRAG Integration:** RAGAnything wraps LightRAG. You can pass an existing LightRAG instance or let RAGAnything create one via `lightrag_kwargs`.

**Content List Format:** Standardized format for document content:
```python
{"type": "text", "text": "...", "page_idx": 0}
{"type": "image", "img_path": "/absolute/path.jpg", "image_caption": [...], "page_idx": 1}
{"type": "table", "table_body": "| ... |", "table_caption": [...], "page_idx": 2}
{"type": "equation", "latex": "E=mc^2", "text": "...", "page_idx": 3}
```

## Dependencies

- **MinerU**: Document parsing (requires GPU for reasonable performance)
- **LibreOffice**: Required for Office document formats (.doc, .docx, .ppt, .pptx, .xls, .xlsx)
- **lightrag-hku**: Core RAG engine

# Prompt: Build the CadSentinel DWG ETL & Embedding Pipeline in Python

You are a senior Python backend engineer, FastAPI expert, CAD/engineering tooling integrator, and vector-search/LLM systems architect. You will help me build a production-grade **DWG → JSON → embeddings** pipeline for a project called **CadSentinel**.

CadSentinel’s goal is to:
- Ingest **AutoCAD DWG** files.
- Normalize them through a **C++ DWG → JSON** tool (`dwg_to_json`) that uses LibreDWG and a fixed JSON schema.
- Produce **DXF**, **PDF**, **PNG**, and **thumbnail** derivatives for each drawing.
- Compute a **stable SHA256-based document ID** (same pattern used in my “Aura” project) and store all artifacts in a **PostgreSQL + pgvector** database.
- Expose **FastAPI** endpoints so a **Vercel v0.app** frontend can support:
  - File ingestion
  - Search & retrieval
  - “Chat with the drawing”
  - Semantic / “synaptic” search
  - Later: “Spell checking” drawings against engineering standards (e.g., ASTM).

The C++ program `dwg_to_json` is already implemented and emits a stable **CadSentinel DWG JSON Format v1.1** (header, layers, entities, blocks, summary, title_block, etc.). Treat its JSON output as **authoritative**; do not propose changes to the C++ code unless absolutely necessary. :contentReference[oaicite:0]{index=0}

---

## High-Level Requirements

Build a **single cohesive Python project** (with modular structure) that performs this pipeline:

1. **Load the source DWG file** from disk (path provided as argument or input).
2. **Compute a unique SHA256 document ID** from the DWG file bytes (as in my Aura project):
   - Read the DWG file bytes.
   - Compute `sha256` hex digest.
   - Use this hex string as the canonical **document_id**.
3. **Copy the original DWG** into an “ingested documents” folder:
   - Save as:  
     `ingested/<document_id>.dwg`
4. **All derived outputs must use this same `<document_id>`** as their base filename.
5. **Convert DWG → DXF**:
   - Call the external CLI **`dwg2dxf`** (from LibreDWG) on the ingested DWG:
     - Input: `ingested/<document_id>.dwg`
     - Output: a DXF file (you may use a temp folder or persist as `derived/<document_id>.dxf`).
6. **Generate drawing exports from DXF using a Python library**:
   - Use an appropriate Python DXF/CAD library (e.g., `ezdxf` + a rendering backend or another open-source renderer) to:
     a. Produce a **high-resolution PDF**  
        `derived/<document_id>.pdf`
     b. Produce a **high-resolution PNG**  
        `derived/<document_id>.png`
     c. Produce a **thumbnail PNG** derived from the high-res PNG  
        `derived/<document_id>_thumbnail.png`
   - Choose sensible DPI (e.g., 300+ for PDF/PNG) and thumbnail size (e.g., 256–512 px on the long edge).
   - Handle model space / paper space so the exported views match a typical printed drawing.
7. **Call the C++ `dwg_to_json` program**:
   - Input: `ingested/<document_id>.dwg`
   - Capture its JSON output (stdout or file).
   - Save it as:  
     `derived/<document_id>.json`
   - Ensure the JSON is valid UTF-8 and conforms to the **CadSentinel DWG JSON schema**.
8. **Build embeddings for the DWG JSON**:
   - Use the OpenAI API’s embeddings endpoint (e.g., `text-embedding-3-large` or similar) **for now**.
   - Later we will support a local model via **Ollama**, so design the code with a thin `EmbeddingProvider` abstraction that can swap backends.
   - Decide what text to embed. At minimum:
     - Entire JSON text as a single “document embedding”.
     - Optionally, finer-grained chunks: layers, entities with text, title-block attributes, etc.
   - Return embeddings as lists of floats ready for pgvector storage.
9. **Persist all metadata and embeddings in PostgreSQL + pgvector**:
   - Use **SQLAlchemy** ORM + **Alembic** migrations.
   - Define a clean schema, for example (you may improve this):

   - `drawings` table:
     - `id` (PK, UUID or bigserial)
     - `document_id` (text, unique) – the SHA256 hex
     - `original_filename` (text)
     - `ingested_path` (text) – path to `<document_id>.dwg`
     - `pdf_path` (text)
     - `png_path` (text)
     - `thumbnail_path` (text)
     - `json_path` (text)
     - `dwg_version` (int or text) – from JSON header
     - `schema_version` (text) – from JSON (e.g., "1.1.0")
     - `created_at`, `updated_at` (timestamps)

   - `drawing_chunks` table (for granular embeddings):
     - `id` (PK)
     - `drawing_id` (FK → drawings.id)
     - `chunk_type` (e.g., "entity", "layer", "title_block", "summary", "full_json")
     - `label` (e.g., entity type & index, layer name, etc.)
     - `source_ref` (e.g., JSON path or entity index)
     - `text` (text) – the text content used for embedding
     - `embedding` (pgvector) – the embedding vector
     - `metadata` (JSONB) – optional extra info (layer name, category, etc.)

   - (Optional) `standards_docs` and `standards_chunks` tables for later ASTM / standards spell-checking:
     - Similar structure: `text`, `embedding`, `metadata` (e.g., standard name, clause number).

   - Configure **pgvector** extension and appropriate vector column types (e.g., `VECTOR(1536)` depending on model dimensions).
10. **Implement robust error handling and logging**:
    - Log each step (hashing, copying, dwg2dxf, PDF/PNG export, `dwg_to_json`, embeddings, DB writes).
    - Provide clear error messages and fail-safe behavior (e.g., if rendering fails but JSON/embeddings succeed, still index, and mark export status flags in DB).

---

## Step-by-Step Development Tasks

Please proceed in **phases**, and at each phase provide:

- Python code
- Configuration / env variable notes
- CLI usage examples
- Any tests / sanity checks (even simple ones)

### Phase 1 – Project Scaffolding

1. Create a **modern Python project layout**, including:
   - `pyproject.toml` or `requirements.txt`
   - `src/` or `app/` package (choose one layout and stick to it)
   - `.env.example` for configuration:
     - `DATABASE_URL`
     - `OPENAI_API_KEY`
     - Paths: `INGESTED_DIR`, `DERIVED_DIR`, etc.
     - Paths/command names for `dwg2dxf` and `dwg_to_json`.
   - `.gitignore`
2. Set up **virtual environment** instructions.
3. Add **basic logging** configuration (e.g., `logging` module, log level via env).
4. Add `README` notes for installing system dependencies:
   - LibreDWG tools (`dwg2dxf`)
   - The compiled `dwg_to_json` binary
   - Any DXF rendering library requirements (e.g., Cairo, Pillow, etc.).

### Phase 2 – Core DWG Ingestion & Hashing

1. Implement a Python function `compute_document_id(path: Path) -> str`:
   - Read DWG bytes in chunks.
   - Compute SHA256 hex digest.
2. Implement a function `ingest_dwg_file(src_path: Path) -> IngestionResult` that:
   - Computes `document_id`.
   - Copies the file into `INGESTED_DIR` as `<document_id>.dwg`.
   - Returns a dataclass/object with:
     - `document_id`
     - `ingested_path`
     - `original_filename`
3. Provide a minimal **CLI entrypoint** (`python -m app.ingest <path_to_dwg>` or similar) that:
   - Runs ingestion.
   - Prints the `document_id` and ingested path.

### Phase 3 – DWG → DXF via `dwg2dxf`

1. Implement a wrapper function `convert_dwg_to_dxf(ingested_path: Path, document_id: str) -> Path` that:
   - Calls external `dwg2dxf` via `subprocess.run`.
   - Writes DXF either:
     - To `DERIVED_DIR/<document_id>.dxf`, or
     - To a temp directory; but if temp, clearly explain your choice.
   - Properly captures and checks exit codes, logs stderr, and raises clear Python exceptions on failure.
2. Update the CLI to run DWG ingestion **and** DWG → DXF conversion in one command.

### Phase 4 – DXF Rendering to PDF/PNG/Thumbnail

1. Choose a Python approach to load DXF and create:
   - **High-res PDF**
   - **High-res PNG**
   - **Thumbnail PNG**
2. Implement functions like:
   - `render_dxf_to_pdf(dxf_path: Path, output_pdf: Path) -> None`
   - `render_dxf_to_png(dxf_path: Path, output_png: Path) -> None`
   - `generate_thumbnail_from_png(png_path: Path, thumb_path: Path, max_size: int = 512) -> None`
3. Ensure:
   - Good DPI (e.g., 300+).
   - Full drawing extents are visible.
   - Transparent or white background as appropriate.
4. Integrate these into the main ingestion pipeline so we end up with:
   - `<document_id>.pdf`
   - `<document_id>.png`
   - `<document_id>_thumbnail.png`

### Phase 5 – Calling `dwg_to_json` (C++ Tool)

1. Implement `run_dwg_to_json(ingested_path: Path, document_id: str) -> Path` that:
   - Calls the `dwg_to_json` CLI with the DWG file.
   - Captures output into `DERIVED_DIR/<document_id>.json`.
   - Optionally also prints to stdout for debugging.
2. Validate that the JSON conforms to expected structure (lightweight checks):
   - Required top-level keys: `file`, `schema_version`, `header`, `layers`, `entities`, `blocks`, `summary`, `title_block`.
   - Confirm `schema_version` is `"1.1.0"`.
3. Add error handling if `dwg_to_json` fails or emits invalid JSON.

### Phase 6 – Database Schema & pgvector Setup

1. Initialize SQLAlchemy + Alembic:
   - Create engine from `DATABASE_URL`.
   - Set up Alembic migration environment.
2. Define ORM models for:
   - `Drawing`
   - `DrawingChunk`
   - (Optional) `StandardsDoc`, `StandardsChunk` (for future phases)
3. Ensure your migrations:
   - Enable the `pgvector` extension.
   - Create vector columns with appropriate dimension.
4. Implement CRUD helpers:
   - `create_drawing(...)`
   - `create_drawing_chunk(...)`
   - `get_drawing_by_document_id(...)`
   - Basic listing/search helpers.

### Phase 7 – Embedding Provider & Embedding Ingestion

1. Design a small abstraction, e.g.:

   ```python
   class EmbeddingProvider(Protocol):
       def embed_texts(self, texts: list[str]) -> list[list[float]]:
           ...

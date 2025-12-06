# Prompt: Build the CadSentinel DWG ETL & Embedding Pipeline in Python

You are a senior Python backend engineer, FastAPI expert, CAD/engineering tooling integrator, and vector-search/LLM systems architect. You will help me build a production-grade **DWG → JSON → embeddings** pipeline for a project called **CadSentinel**.

CadSentinel’s goal is to:

- Ingest **AutoCAD DWG** files.
- Normalize them through a **C++ DWG → JSON** tool (`dwg_to_json`) that uses LibreDWG and a fixed JSON schema (the schema and behavior are documented in a separate file that I will provide in this chat).
- Produce **DXF**, **PDF**, **PNG**, and **thumbnail** derivatives for each drawing.
- Compute a **stable SHA256-based document ID** (same pattern used in my “Aura” project) and store all artifacts in a **PostgreSQL + pgvector** database.
- Expose **FastAPI** endpoints so a **Vercel v0.app** frontend can support:
  - File ingestion
  - Search and retrieval
  - “Chat with the drawing”
  - Semantic / “synaptic” search
  - Later: “Spell checking” drawings against engineering standards (e.g., ASTM and similar documents).

The **C++ program `dwg_to_json` is already implemented and finalized** and emits a stable **CadSentinel DWG JSON Format** (header, layers, entities, blocks, summary, title_block, and other fields). Treat its JSON output as **authoritative**; do **not** propose changes to the C++ code or the JSON schema unless there is a clear, critical missing feature that prevents the Python pipeline from functioning.

I am now asking you to write Python code and system design in a phased, step-by-step way, following the detailed instructions below.

---

## Overall Functional Requirements

The Python program and surrounding system must do the following:

1. **Load an AutoCAD DWG file** from disk or from an uploaded file via FastAPI.

2. **Create a unique SHA256 file ID**, using the same pattern that was used for my “Aura” project documents:
   - Read the entire DWG file as bytes.
   - Compute the SHA256 digest.
   - Represent the digest as a lowercase hex string.
   - Use this hex string as the canonical **`document_id`** for this DWG.

3. **Copy the AutoCAD DWG file into an “ingested documents” folder**, and save it with the **document ID** as the filename:
   - The ingested DWG path must be:
     - `ingested/<sha256_unique_ID>.dwg`
   - The original filename should still be trackable in the database as metadata.

4. **Ensure that all output files use this same document ID as their filename base**. Every derived artifact will use `<sha256_unique_ID>` as its base name.

5. **Call `dwg2dxf` to convert the DWG into a DXF file**:
   - Use the ingested DWG file `ingested/<sha256_unique_ID>.dwg` as input.
   - Call the **LibreDWG** command-line tool `dwg2dxf`.
   - The generated DXF file should be saved (for example) as:
     - `derived/<sha256_unique_ID>.dxf`

6. **Use a Python DXF-capable library to load the DXF and generate drawing outputs**:
   - The Python library should read the DXF and allow rendering to:
     1. A **high-resolution PDF file**:
        - Output filename: `derived/<sha256_unique_ID>.pdf`
     2. A **high-resolution PNG file**:
        - Output filename: `derived/<sha256_unique_ID>.png`
     3. A **thumbnail PNG file** generated from the high-resolution PNG:
        - Output filename: `derived/<sha256_unique_ID>_thumbnail.png`
   - The rendering should:
     - Use a reasonable high DPI (for example 300 DPI or higher).
     - Show the full drawing extents so all geometry is visible.
     - Use an appropriate background (typically white).

7. **At this point, for each DWG that has been successfully processed, the following files must exist**:

   - `ingested/<sha256_unique_ID>.dwg`
   - `derived/<sha256_unique_ID>.dxf`
   - `derived/<sha256_unique_ID>.pdf`
   - `derived/<sha256_unique_ID>.png`
   - `derived/<sha256_unique_ID>_thumbnail.png`

8. **Call the C++ `dwg_to_json` program** to extract structured data from the DWG:
   - Input: `ingested/<sha256_unique_ID>.dwg`
   - Capture the JSON output from `dwg_to_json` (either via stdout or a file argument).
   - Save the output JSON file as:
     - `derived/<sha256_unique_ID>.json`

9. **The JSON output file is saved alongside the other derived documents**:
   - `derived/<sha256_unique_ID>.json`

10. **The Python program will then use ChatGPT (via the OpenAI API) to build embeddings for the JSON data**:
    - Later, support must be added for a **local Ollama model**, so the design must be abstracted enough to allow swapping the embedding backend.
    - The embedding process must:
      - Decide how to chunk the JSON into multiple logical pieces (full JSON, per-layer summaries, entity-level text, title-block text, summary text, or other items).
      - Generate embeddings for each chunk.
      - Generate at least one “document-level embedding” for the entire JSON representation of the drawing.

11. **The Python program must save all filename locations, JSON data references, and embedding vectors into a PostgreSQL database with pgvector enabled**:
    - The database must store:
      - The `document_id` (the SHA256 hex).
      - Paths (or URLs) for:
        - The ingested DWG.
        - The DXF.
        - The PDF.
        - The PNG.
        - The thumbnail PNG.
        - The JSON file.
      - Additional metadata extracted from the JSON (e.g., DWG version, title block info).
    - The database must also store:
      - The embedding vectors as pgvector columns.
      - The text content that was embedded, for later retrieval and inspection.

12. **Describe and design the additional functionality that will allow LLMs to use this information to**:
    - Perform natural language “chat” about the drawing.
    - Perform “synaptic” semantic searches across drawings and their content.
    - Later, “spell-check” the drawing against given standards (such as ASTM documents), including:
      - Checking thread sizes, fits, tolerances, and notes.
      - Identifying missing or inconsistent information relative to the standard.
      - Producing a structured “compliance” or “findings” report for each drawing.

13. **All interaction between the backend and user interface will be via FastAPI**:
    - Implement FastAPI endpoints for:
      - Ingesting files.
      - Querying documents.
      - Search and chat.
      - Standards-based spell-check and analysis.
    - The design must be clean and well-documented so that a frontend built with Vercel v0.app can consume these APIs.

14. **The frontend UI will be built with Vercel v0.app**:
    - You do not need to write frontend code in this prompt.
    - You must, however, design the FastAPI endpoints and response payloads with the frontend’s needs in mind.

15. **Write all of this as a step-by-step process**:
    - Organize the work into clearly labeled phases (Phase 1, Phase 2, etc.).
    - Each phase should include:
      - Objectives.
      - The specific Python modules and functions that should be implemented.
      - Any necessary configuration and environment variables.
      - Example usage (CLI calls or API examples).
      - Notes on error handling and logging where appropriate.

16. **We will not modify the `dwg_to_json` program unless absolutely necessary**:
    - Assume that its current behavior and JSON schema are correct and sufficient.
    - Only suggest modifications if a critical piece of functionality is missing.

17. **Output everything as a Markdown document**:
    - This entire response must be a well-structured Markdown file.
    - I will copy and paste this Markdown directly into a new chat to guide implementation.
    - Do not truncate any sections or phases.
    - Do not use placeholders like “etc.” to represent omitted important steps; instead, explicitly describe what needs to happen.

---

## Phase 0 – Assumptions and Inputs

In this phase, clearly state your assumptions and the external tools the Python system depends on.

1. **Assume the following are installed and available on the system path**:
   - `dwg2dxf` from **LibreDWG**.
   - The compiled C++ tool `dwg_to_json`.

2. **Assume we have access to the following**:
   - A running **PostgreSQL** instance.
   - The **pgvector** extension installed and enabled in the database.
   - An **OpenAI API key** for calling ChatGPT and the embeddings API.
   - Later, a running **Ollama** instance or similar local embedding model endpoint.

3. **Assume the following directory structure (or something similar that you define clearly)**:
   - `ingested/` – for ingested DWG files.
   - `derived/` – for DXF, PDF, PNG, thumbnail PNG, and JSON files.
   - `logs/` – for log files if you choose to log to disk in addition to stdout.

4. **Assume we will configure the system using environment variables**, including:
   - `DATABASE_URL`
   - `OPENAI_API_KEY`
   - `INGESTED_DIR`
   - `DERIVED_DIR`
   - `DWG2DXF_PATH` (or assume it is on PATH)
   - `DWG_TO_JSON_PATH` (or assume it is on PATH)
   - Any additional configuration keys needed for embeddings or external tools.

State these assumptions explicitly in the code comments and README during implementation.

---

## Phase 1 – Project Scaffolding and Configuration

In this phase, set up the Python project structure and basic configuration.

1. **Create a modern Python project layout**, for example:

   ```text
   cadsentinel_dwg_pipeline/
     ├─ pyproject.toml  (or requirements.txt)
     ├─ .env.example
     ├─ .gitignore
     ├─ README.md
     ├─ alembic.ini
     ├─ alembic/
     └─ app/
        ├─ __init__.py
        ├─ config.py
        ├─ logging_config.py
        ├─ db/
        │  ├─ __init__.py
        │  ├─ base.py
        │  ├─ models.py
        │  ├─ session.py
        ├─ ingestion/
        │  ├─ __init__.py
        │  ├─ hashing.py
        │  ├─ files.py
        │  ├─ dwg_to_dxf.py
        │  ├─ dxf_render.py
        │  ├─ dwg_json.py
        ├─ embeddings/
        │  ├─ __init__.py
        │  ├─ provider_base.py
        │  ├─ provider_openai.py
        │  ├─ chunking.py
        ├─ services/
        │  ├─ __init__.py
        │  ├─ drawing_indexer.py
        │  ├─ search_service.py
        │  ├─ chat_service.py
        │  ├─ standards_service.py
        ├─ api/
        │  ├─ __init__.py
        │  ├─ main.py
        │  ├─ routers/
        │  │  ├─ __init__.py
        │  │  ├─ ingest.py
        │  │  ├─ drawings.py
        │  │  ├─ search.py
        │  │  ├─ chat.py
        │  │  ├─ standards.py
        └─ cli/
           ├─ __init__.py
           ├─ ingest_cli.py
   ```

2. **Create `pyproject.toml` or `requirements.txt`** with dependencies such as:
   - `fastapi`
   - `uvicorn`
   - `sqlalchemy`
   - `alembic`
   - `psycopg[binary]` or `psycopg2-binary`
   - `python-dotenv`
   - `pydantic`
   - `openai` (or the latest official OpenAI client)
   - `pgvector` Python client or equivalent integration
   - DXF/PDF/PNG-related libraries (e.g., `ezdxf`, `Pillow`, a rendering backend such as `matplotlib` or `cairo` bindings, depending on your chosen solution)

3. **Create `.env.example`** with keys:
   - `DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/cadsentinel`
   - `OPENAI_API_KEY=your_api_key_here`
   - `INGESTED_DIR=./ingested`
   - `DERIVED_DIR=./derived`
   - `DWG2DXF_PATH=dwg2dxf`
   - `DWG_TO_JSON_PATH=./dwg_to_json`
   - Any other keys you introduce later.

4. **Create `config.py`**:
   - Use `pydantic` or standard environment parsing to create a `Settings` class.
   - Load environment variables and expose them to the rest of the project.

5. **Create `logging_config.py`**:
   - Configure standard Python logging with:
     - Log level controlled by an environment variable.
     - Console logging with timestamps and log levels.
   - Optionally configure log file output.

6. **Document the setup in `README.md`**:
   - How to create and activate a virtual environment.
   - How to install dependencies.
   - How to configure environment variables.
   - How to run Alembic migrations.
   - How to start the FastAPI app with `uvicorn`.

---

## Phase 2 – DWG Ingestion and SHA256 Document ID

Implement the ingestion logic that reads a DWG file, hashes it, and copies it to the ingested folder.

1. **Implement `hashing.py`**:
   - Write a function:

     ```python
     def compute_document_id(dwg_path: Path) -> str:
         """Read the DWG file in binary mode and return a SHA256 hex string."""
     ```

   - Ensure:
     - The file is read in chunks to handle large files.
     - The hex digest is lowercase.
     - Errors (missing file, permission issues) are logged and raised.

2. **Implement `files.py`** with a function to copy ingested files:

   ```python
   @dataclass
   class IngestionResult:
       document_id: str
       ingested_path: Path
       original_filename: str
   ```

   ```python
   def ingest_dwg_file(src_path: Path, ingested_dir: Path) -> IngestionResult:
       """Compute document_id, copy the DWG to ingested_dir/<document_id>.dwg, and return metadata."""
   ```

   - Steps:
     - Confirm `src_path` exists and is a DWG.
     - Compute `document_id` via `compute_document_id`.
     - Create `ingested_dir` if it does not exist.
     - Copy the file to `ingested_dir / f"{document_id}.dwg"`.
     - Return an `IngestionResult` instance.

3. **Create a minimal CLI entrypoint in `cli/ingest_cli.py`**:
   - Use `argparse` or `click` to accept a DWG path.
   - Call `ingest_dwg_file`.
   - Print:
     - The `document_id`.
     - The location of the ingested DWG file.

4. **Add unit tests (if test framework is configured)**:
   - Test hashing on a known small file.
   - Test ingestion copies the file and uses the correct filename.

---

## Phase 3 – DWG → DXF Conversion via `dwg2dxf`

Use the LibreDWG `dwg2dxf` CLI to convert DWG into DXF.

1. **Implement `dwg_to_dxf.py`** with a function:

   ```python
   def convert_dwg_to_dxf(
       ingested_dwg_path: Path,
       derived_dir: Path,
       dwg2dxf_path: str
   ) -> Path:
       """Run dwg2dxf to convert the DWG file to DXF, returning the path to the DXF file."""
   ```

2. **Function behavior**:
   - Ensure `derived_dir` exists, create if needed.
   - Construct the DXF output path:
     - Use the document ID from the DWG filename to create:
       - `derived_dir / f"{document_id}.dxf"`
   - Call `subprocess.run`:
     - Pass in the input DWG and output DXF.
     - Capture stdout and stderr.
     - Check the return code.
     - On error, log stderr and raise an exception with a clear message.

3. **Integrate with the CLI**:
   - Extend the CLI so that after ingestion, it calls `convert_dwg_to_dxf`.
   - Print the DXF output path.

4. **Document required system dependencies** in `README.md`:
   - How to install LibreDWG and ensure `dwg2dxf` is available.

---

## Phase 4 – DXF Rendering to PDF, PNG, and Thumbnail

Use a Python DXF library and image tools to render the drawing into viewable formats.

1. **Choose DXF rendering approach**:
   - For example, you may:
     - Use `ezdxf` to load the DXF.
     - Use a rendering backend (such as `ezdxf.addons.drawing` with Matplotlib or a Cairo backend).
     - Produce a PDF and PNG at a chosen DPI.

2. **Implement `dxf_render.py`** with functions:

   ```python
   def render_dxf_to_pdf(dxf_path: Path, pdf_path: Path, dpi: int = 300) -> None:
       """Render the DXF file to a high-resolution PDF."""
   ```

   ```python
   def render_dxf_to_png(dxf_path: Path, png_path: Path, dpi: int = 300) -> None:
       """Render the DXF file to a high-resolution PNG."""
   ```

   ```python
   def generate_thumbnail_from_png(
       png_path: Path,
       thumbnail_path: Path,
       max_size: int = 512
   ) -> None:
       """Generate a thumbnail PNG from the high-resolution PNG."""
   ```

3. **Rendering details**:
   - For both PDF and PNG:
     - Use drawing extents such that all visible entities are included.
     - Use an appropriate page size or image size that shows the complete drawing clearly.
   - For the thumbnail:
     - Use `Pillow` to open the PNG.
     - Resize while preserving aspect ratio.
     - Ensure the maximum dimension (width or height) is `max_size`.

4. **Integrate rendering into the pipeline**:
   - After `convert_dwg_to_dxf`, call:
     - `render_dxf_to_pdf(dxf_path, derived_dir / f"{document_id}.pdf")`
     - `render_dxf_to_png(dxf_path, derived_dir / f"{document_id}.png")`
     - `generate_thumbnail_from_png(derived_dir / f"{document_id}.png", derived_dir / f"{document_id}_thumbnail.png")`

5. **Add logging**:
   - Log the start and end of each rendering step.
   - Log the output paths.

---

## Phase 5 – Calling `dwg_to_json` (C++ Tool) and Saving JSON

Use the existing C++ program to produce standardized JSON for each DWG.

1. **Implement `dwg_json.py`** with a function:

   ```python
   def run_dwg_to_json(
       ingested_dwg_path: Path,
       derived_dir: Path,
       dwg_to_json_path: str
   ) -> Path:
       """Call the C++ dwg_to_json tool and save its JSON output to derived_dir/<document_id>.json."""
   ```

2. **Function behavior**:
   - Infer `document_id` from the DWG filename.
   - Construct JSON output path:
     - `derived_dir / f"{document_id}.json"`
   - Call `subprocess.run` on `dwg_to_json_path`:
     - Pass in the DWG path as argument.
     - Capture stdout and stderr.
   - Write stdout to the JSON output file.
   - Parse the JSON in memory to ensure it is valid.
   - Optionally validate presence of keys like:
     - `file`
     - `schema_version`
     - `header`
     - `layers`
     - `entities`
     - `blocks`
     - `summary`
     - `title_block`
   - Log schema_version and any basic stats (number of layers, entities, etc.).

3. **Error handling**:
   - On non-zero return code:
     - Log stderr.
     - Raise an exception.
   - On invalid JSON:
     - Log the error.
     - Raise an exception.

4. **Integrate into the pipeline**:
   - After rendering, call `run_dwg_to_json`.
   - Ensure that at the end of the pipeline, we have:
     - DWG
     - DXF
     - PDF
     - PNG
     - Thumbnail PNG
     - JSON

---

## Phase 6 – Database Schema and pgvector Integration

Define the database schema and integrate `pgvector` for storing embeddings.

1. **Set up SQLAlchemy and Alembic**:
   - In `db/session.py`, create a database engine from `DATABASE_URL`.
   - Create a `SessionLocal` or similar session factory.
   - In `db/base.py`, configure the Base class for models.

2. **Enable pgvector**:
   - Create an initial Alembic migration that:
     - Ensures the `pgvector` extension is created:
       - `CREATE EXTENSION IF NOT EXISTS vector;`

3. **Design and implement models in `db/models.py`**:

   - `Drawing` model:
     - `id` – primary key (UUID or integer).
     - `document_id` – text, unique.
     - `original_filename` – text.
     - `ingested_path` – text.
     - `dxf_path` – text.
     - `pdf_path` – text.
     - `png_path` – text.
     - `thumbnail_path` – text.
     - `json_path` – text.
     - `dwg_version` – optional text or integer.
     - `schema_version` – text (from JSON, e.g., "1.1.0").
     - `created_at` – timestamp with time zone.
     - `updated_at` – timestamp with time zone.

   - `DrawingChunk` model:
     - `id` – primary key.
     - `drawing_id` – foreign key to `Drawing`.
     - `chunk_type` – text (e.g., "full_json", "layer", "entity", "title_block", "summary").
     - `label` – text (e.g., layer name, entity type + index).
     - `source_ref` – text (e.g., JSON pointer, entity index).
     - `text` – the text content used to build the embedding.
     - `embedding` – pgvector column, with dimension matching the embedding model.
     - `metadata` – JSONB for additional info (layer name, entity category, etc.).

   - Future standards-related models (to be fully designed later in Phase 9):
     - `StandardsDoc` – for the original standard document.
     - `StandardsChunk` – for chunked embeddings of standards content.

4. **Create Alembic migrations**:
   - Auto-generate or hand-write migrations to create the tables.
   - Ensure `embedding` columns use the `vector` type.
   - Apply migrations to the database.

5. **Implement basic CRUD functions**:
   - In a `db/crud.py` or equivalent module, implement functions to:
     - Create a `Drawing`.
     - Create many `DrawingChunk` records.
     - Fetch a `Drawing` by `document_id`.
     - Search for `DrawingChunk` records by drawing or by criteria.

---

## Phase 7 – Embedding Provider and JSON Chunking

Add the ability to generate embeddings for the DWG JSON and store them in the database.

1. **Create `embeddings/provider_base.py`**:
   - Define a protocol or base class:

     ```python
     class EmbeddingProvider(Protocol):
         def embed_texts(self, texts: list[str]) -> list[list[float]]:
             """Return one embedding vector per input text."""
     ```

2. **Create `embeddings/provider_openai.py`**:
   - Implement `OpenAIEmbeddingProvider`:
     - Constructor accepts:
       - Model name (e.g., "text-embedding-3-large").
       - API key from settings.
     - Implement `embed_texts` by calling the official OpenAI embeddings API.
     - Handle batching, rate limiting, and retries.
     - Return embeddings as lists of floats.

3. **Create `embeddings/chunking.py`**:
   - Functions for turning DWG JSON into chunks:

     ```python
     def load_drawing_json(json_path: Path) -> dict:
         ...
     ```

     ```python
     def generate_chunks_from_drawing_json(data: dict) -> list[dict]:
         """Return a list of chunk dicts with fields:
         {
             "chunk_type": str,
             "label": str,
             "source_ref": str,
             "text": str,
             "metadata": dict
         }
         """
     ```

   - Chunk types might include:
     - `"full_json"` – the entire JSON string representation.
     - `"summary"` – summary field from JSON.
     - `"title_block"` – title-block text and attributes.
     - `"layer"` – per-layer aggregated info (layer name, number of entities, text snippets).
     - `"entity"` – per-text-bearing entity (e.g., TEXT, MTEXT, ATTRIB).

4. **Implement `services/drawing_indexer.py`**:
   - A function:

     ```python
     def index_drawing(
         document_id: str,
         json_path: Path,
         db_session: Session,
         embedding_provider: EmbeddingProvider
     ) -> None:
         """Load the JSON, generate chunks, embed them, and persist to the database."""
     ```

   - Steps:
     - Load JSON from file.
     - Either create or update a `Drawing` record with metadata:
       - `document_id`, `json_path`, etc.
     - Generate chunks with `generate_chunks_from_drawing_json`.
     - Extract the `text` fields.
     - Call `embedding_provider.embed_texts`.
     - For each chunk:
       - Insert a `DrawingChunk` record into the database with the text, embedding, and metadata.

5. **Add logging and simple tests**:
   - Log how many chunks were created.
   - Log summary statistics (e.g., how many entity-level chunks).

---

## Phase 8 – FastAPI Application and Core Endpoints

Expose the pipeline and search capabilities via FastAPI.

1. **Create `api/main.py`** to initialize the FastAPI app:

   - Initialize settings and database.
   - Include routers from:
     - `api/routers/ingest.py`
     - `api/routers/drawings.py`
     - `api/routers/search.py`
     - `api/routers/chat.py`
     - `api/routers/standards.py`
   - Configure CORS to allow requests from the future Vercel v0.app domain.

2. **Router: `ingest.py`**:
   - Endpoint: `POST /ingest/dwg`
   - Request:
     - Multipart form data with:
       - `file`: DWG file upload.
   - Behavior:
     - Save the uploaded DWG to a temporary path.
     - Call `ingest_dwg_file` to hash and copy it into `ingested/` with document ID.
     - Call `convert_dwg_to_dxf`.
     - Call `render_dxf_to_pdf`, `render_dxf_to_png`, `generate_thumbnail_from_png`.
     - Call `run_dwg_to_json`.
     - Call `index_drawing` with:
       - `document_id`
       - JSON path
       - DB session
       - Embedding provider
     - Create or update a `Drawing` record with all artifact paths.
   - Response:
     - JSON with:
       - `document_id`
       - Paths or URLs for:
         - DWG, DXF, PDF, PNG, thumbnail PNG, JSON
       - Basic metadata, such as:
         - Title-block info
         - Number of layers and entities

3. **Router: `drawings.py`**:
   - Endpoint: `GET /drawings`
     - Query parameters for pagination and optional filters.
     - Returns a list of drawings with basic metadata and preview URLs.
   - Endpoint: `GET /drawings/{document_id}`
     - Returns detailed metadata and links for a single drawing.

4. **Router: `search.py`**:
   - Endpoint: `POST /search/vector`
   - Request body:
     - `query`: text string.
     - Optional filters:
       - `document_id`
       - `chunk_type`
   - Behavior:
     - Use `embedding_provider` to embed the query.
     - Perform a pgvector similarity search against `DrawingChunk.embedding`.
     - Return the top-k matching chunks with:
       - Score or similarity.
       - `document_id`, `chunk_type`, `label`, `text`, and minimal metadata.

5. **Router: `chat.py`**:
   - Endpoint: `POST /chat/{document_id}`
   - Request body:
     - `message`: user question or request.
   - Behavior:
     - Embed the message.
     - Run a similarity search for chunks in that specific drawing.
     - Select the top-k chunks as context.
     - Build a prompt for ChatGPT that includes:
       - The user’s question.
       - A summary of the drawing (from JSON).
       - The retrieved chunks with clear labeling.
       - Instructions to answer strictly based on the provided information.
     - Call OpenAI Chat Completion API.
     - Return:
       - The model’s answer.
       - The chunks and references used for context.

6. **Router: `standards.py` (initial design)**:
   - Design endpoints but full implementation can appear in Phase 9:
     - `POST /ingest/standard`
       - For uploading standards documents (PDF or text).
     - `POST /analyze/{document_id}/standards`
       - For running a “spell-check” or compliance analysis against selected standards.

7. **Document the API**:
   - Use pydantic models for request/response schemas.
   - Ensure the OpenAPI schema is complete.
   - Provide example requests and responses in docstrings where useful.

---

## Phase 9 – Synaptic Search and Standards-Based Spell-Check Design

Design and partially implement functionality that allows richer semantics and standards checking.

1. **Synaptic (Semantic Graph-Style) Search**:
   - Goal:
     - Move beyond simple nearest-neighbor search to semantic navigation of a drawing and its components.
   - Design ideas:
     - Use `DrawingChunk.metadata` to store relationships between entities, layers, and title-block fields.
     - For example:
       - Entities include metadata like:
         - `{"layer": "DIMENSIONS", "entity_type": "DIMENSION", "index": 123}`
       - Layers include metadata like:
         - `{"color": 7, "linetype": "CONTINUOUS"}`
       - Title block chunks include metadata like:
         - `{"field": "DRAWING_NUMBER", "value": "ABC-123"}`
     - Allow the search endpoint to:
       - Filter by metadata before applying vector similarity.
       - Combine embedding similarity with explicit filters like “only dimension entities on layer DIMENSIONS.”

   - Extend `search_service.py`:
     - Implement functions that:
       - Accept query text and a dict of filters.
       - Build SQL queries that:
         - Restrict by metadata JSONB fields (using appropriate operators).
         - Order by cosine distance or inner product via pgvector.

2. **Standards Ingestion (`StandardsDoc` and `StandardsChunk`)**:
   - Design `StandardsDoc` fields:
     - `id`
     - `name`
     - `source_path`
     - `created_at`
   - Design `StandardsChunk` fields:
     - `id`
     - `standards_doc_id`
     - `section_id` or `clause_number`
     - `text`
     - `embedding` (pgvector)
     - `metadata` (JSONB) – e.g., `{ "standard": "ASTM A123", "clause": "4.3" }`

   - Implement a service `standards_service.py`:
     - Ingest a PDF or text file.
     - Extract plain text (for PDF, you may call an external tool or assume text has already been extracted).
     - Chunk the text into logical sections (per paragraph, per clause, or by headings).
     - Embed each chunk and store in `StandardsChunk`.

3. **Standards-Based Spell-Check and Compliance Analysis**:
   - Design a pipeline in `standards_service.py` (or a new service) that, for a given `document_id`:
     - Iterates over relevant `DrawingChunk` entries, especially:
       - Dimension entities.
       - GD&T or tolerance notes.
       - Thread callouts.
       - Material and finish notes.
     - For each such chunk:
       - Perform a vector similarity search against `StandardsChunk`.
       - Retrieve the most relevant standard clauses.
       - Use an LLM (ChatGPT initially) in a structured prompt that:
         - Shows the drawing text chunk.
         - Shows the candidate standard clauses.
         - Asks the model to:
           - Determine if the drawing text is compliant or non-compliant.
           - Suggest corrections if needed.
           - Explain its reasoning.
     - Aggregate results into a **compliance report** that includes:
       - A list of issues by severity.
       - References to specific drawing entities or layers.
       - References to specific standards and clauses.

   - Expose this via `POST /analyze/{document_id}/standards`:
     - Request body:
       - Standards selection (e.g., list of `StandardsDoc` IDs).
     - Response:
       - A structured report with:
         - Issues.
         - Suggested fixes.
         - Linked standards references.

---

## Phase 10 – End-to-End Pipeline and Testing

Tie everything together and describe how to test the system from ingestion to chat and spell-check.

1. **Define an end-to-end ingestion function**:
   - In `services/drawing_indexer.py` or a new module, create:

     ```python
     def process_dwg_file(
         src_path: Path,
         settings: Settings,
         db_session: Session,
         embedding_provider: EmbeddingProvider
     ) -> str:
         """End-to-end processing: ingestion, DWG→DXF, rendering, JSON, embedding, DB insert. Returns document_id."""
     ```

   - Steps:
     - Ingest DWG and compute `document_id`.
     - Convert to DXF.
     - Render PDF, PNG, thumbnail.
     - Run `dwg_to_json`.
     - Index drawing (JSON chunking + embeddings).
     - Insert or update `Drawing` record with all artifact paths.

2. **Connect this to FastAPI**:
   - Ensure `/ingest/dwg` calls `process_dwg_file`.

3. **Testing**:
   - Manual tests:
     - Use `curl` or HTTP clients to:
       - Upload a DWG via `/ingest/dwg`.
       - Confirm returned `document_id`.
       - Call `/drawings/{document_id}` to inspect metadata.
       - Call `/search/vector` with some queries.
       - Call `/chat/{document_id}` with simple questions (“What is the overall size of this part?”).
   - Automated tests:
     - If possible, add basic integration tests with a small sample DWG and a temporary database.

4. **Logging and observability**:
   - Ensure each major step logs:
     - The `document_id`.
     - Start and end of operations.
     - Any failures, with clear error messages.

---

## Phase 11 – Future Enhancements and Local Models (Ollama)

Prepare the architecture so we can later plug in local models.

1. **Embedding provider abstraction**:
   - Add an `OllamaEmbeddingProvider` implementation (even if only sketched for now) that:
     - Calls a local HTTP endpoint for embedding generation.
     - Reads configuration from env (`OLLAMA_BASE_URL`, `OLLAMA_MODEL_NAME`).

2. **Chat model abstraction**:
   - Introduce a `ChatProvider` abstraction, similar to `EmbeddingProvider`, so you can swap between:
     - OpenAI ChatGPT models.
     - Local chat models via Ollama or other backends.

3. **Configuration switching**:
   - In `config.py`, add settings indicating:
     - Which embedding provider to use (`"openai"`, `"ollama"`, or similar).
     - Which chat provider to use.
   - In `api/main.py` or an app initialization module, initialize the chosen providers based on configuration.

4. **Performance and scaling considerations**:
   - Note that for large numbers of drawings, ingestion should:
     - Be idempotent (reprocessing the same DWG should not create duplicate records).
     - Possibly be queued for background processing (e.g., Celery, RQ, or built-in background tasks) instead of blocking API calls.

---

## Final Instructions for You (the Assistant in the New Chat)

When I paste this entire Markdown prompt into a new chat, you must:

1. Treat this document as the **complete specification** for the Python-based CadSentinel DWG pipeline.
2. Implement the system **phase by phase**, starting at Phase 1 and moving forward in order.
3. For each phase:
   - Provide concrete Python code for the described modules and functions.
   - Provide configuration snippets, Alembic migration examples, and FastAPI route implementations.
   - Provide example commands for running and testing the code.
4. Keep the code modular, production-minded, and well-structured.
5. Do not modify the C++ `dwg_to_json` program or its JSON schema unless I explicitly tell you to do so later due to missing functionality.

This Markdown prompt is complete and untruncated and is intended to fully define the behavior and structure of the CadSentinel DWG ETL & Embedding Pipeline in Python.


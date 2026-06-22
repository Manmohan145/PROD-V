# VisionAI Edge Production Audit

Date: 2026-06-22

## Outcome

VisionAI Edge has been migrated from the legacy Grok image-generation implementation to a backend-only Hugging Face FLUX integration without changing the application architecture or removing working AI features.

Model: `black-forest-labs/FLUX.1-schnell`

Provider: Hugging Face Inference API through the official `huggingface_hub` client.

## Files Removed

- `backend/services/grok_service.py`
- `frontend/lib/index.js` (unused template placeholder)
- Tracked compiled artifacts:
  - `backend/__pycache__/detector.cpython-314.pyc`
  - `backend/__pycache__/gemini_service.cpython-314.pyc`
  - `backend/__pycache__/history_db.cpython-314.pyc`
  - `backend/__pycache__/image_utils.cpython-314.pyc`
  - `backend/__pycache__/local_llm_service.cpython-314.pyc`
  - `backend/__pycache__/ocr_service.cpython-314.pyc`
  - `backend/__pycache__/tts_service.cpython-314.pyc`
- Runtime `__pycache__` directories created by local execution.

## Files Added

- `backend/services/flux_image_service.py`
- `CLEANUP_REPORT.md`
- `PRODUCTION_AUDIT.md`

## Files Refactored

- `backend/main.py`
  - Loads `backend/.env` before service initialization.
  - Preserves only legacy root Ollama settings; it does not load a Hugging Face key from the root environment file.
  - Initializes SQLite during FastAPI lifespan.
  - Serves generated images from `/generated-images`.
  - Restricts credentialed CORS to the local SvelteKit origins.
- `backend/routes/api_routes.py`
  - Replaces all `/api/grok/*` routes with `/api/image/*`.
  - Runs blocking image generation in a worker thread.
  - Validates empty and oversized prompts.
  - Returns safe provider errors without exposing credentials.
- `backend/database/history_db.py`
  - Adds idempotent schema initialization and indexing.
  - Migrates valid legacy base64 image records to local PNG files.
  - Separates scan-history clearing from generated-image clearing.
  - Deletes generated files with path-boundary protection.
- `backend/services/local_llm_service.py`
  - Loads backend-local configuration explicitly.
- `frontend/routes/+page.svelte`
  - Replaces Grok UI copy, endpoints, handlers, and fields.
  - Adds FLUX templates, responsive history, download, regenerate, delete, clear, and loading behavior.
  - Adds the required object-aware tiger, laptop, and plant prompts.
- `frontend/components/HistoryPanel.svelte`
  - Uses centralized API configuration.
- `frontend/lib/api.js`
  - Centralizes API URLs and generated-asset URL resolution.
- `.env.example`
  - Documents secure `backend/.env` configuration.
- `.gitignore`
  - Adds recursive Python cache, generated-image, and backend secret exclusions.
- `requirements.txt`
  - Adds `huggingface_hub>=1.0.0`.
- `README.md`
  - Documents AI Image Studio, secure setup, architecture, and endpoints.

## API Endpoints

### `POST /api/image/generate`

Request:

```json
{
  "prompt": "Create a detailed scientific botanical diagram with labels."
}
```

Response:

```json
{
  "success": true,
  "id": 1,
  "image": "/generated-images/flux-<generated-id>.png",
  "prompt": "Create a detailed scientific botanical diagram with labels.",
  "generation_time": "3.42s"
}
```

### History

- `GET /api/image/history`
- `DELETE /api/image/history/{id}`
- `POST /api/image/history/clear`

Regeneration uses the stored prompt through `POST /api/image/generate`.

## Database Schema

```sql
CREATE TABLE image_generations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prompt TEXT NOT NULL,
    image_path TEXT NOT NULL,
    created_at TEXT NOT NULL,
    generation_time REAL NOT NULL
);

CREATE INDEX idx_image_generations_created_at
ON image_generations(created_at DESC);
```

Retained table: `scan_history`

Removed legacy tables: `image_history`, `image_generation_history`

## Object-Aware Generation

- Tiger — Generate Learning Illustration:
  `Create an educational wildlife illustration of a Bengal Tiger showing habitat, anatomy, conservation status, and scientific labels.`
- Laptop — Generate Future Version:
  `Create a futuristic AI-powered laptop from the year 2050 with advanced holographic interfaces and modern industrial design.`
- Plant / Potted Plant — Generate Scientific Diagram:
  `Create a detailed scientific botanical diagram with labels and educational annotations.`

## Security Review

- `HUGGINGFACE_API_KEY` is read only from `backend/.env`.
- No secret is present in frontend source, generated bundles, API payloads, or logs.
- The frontend communicates only with FastAPI.
- `.env`, `.env.*`, and `backend/.env` are gitignored; `.env.example` remains publishable.
- Generated files are isolated under `uploads/generated/`, which is gitignored.
- File deletion resolves and validates paths against the generated-image directory.
- Provider exceptions are converted to sanitized user-facing messages.
- Prompt length is limited to 1,000 characters.
- The FLUX model requires the Hugging Face access conditions to be accepted and the token to have Inference Providers permission.
- The obsolete root `.env` still contains a `GROK_API_KEY`. It is ignored and no longer loaded or referenced. Revoke that xAI key and remove the obsolete file when no longer needed.

## Dependency Audit

### Python

Kept because actively imported:

- FastAPI
- Uvicorn
- python-multipart
- OpenCV
- NumPy
- Ollama
- Pillow
- PyTesseract
- python-dotenv

Added:

- `huggingface_hub`

No Gemini, xAI, Stable Diffusion, Diffusers, Torch, or experimental image-generation package remains.

### Frontend

Kept because actively used:

- Svelte
- SvelteKit
- Vite
- Svelte adapter and Vite plugin
- `marked`

No package removal is recommended. `package.json` and `package-lock.json` remain valid and unchanged.

## Performance Audit

- Generated images moved from full base64 SQLite values to local files, reducing database size and history response payloads.
- A database index supports newest-first generated-image history reads.
- Schema migration no longer destructively drops a table on every database call.
- Image generation is moved off the FastAPI event loop with `asyncio.to_thread`.
- Frontend API base URLs are centralized, eliminating duplicated endpoint configuration.
- No unbounded timer, webcam stream, or speech-synthesis leak was introduced.
- The Svelte page client chunk remains below 130 kB before gzip and below 40 kB after gzip.
- The main page is large, but splitting it during this migration would be an architecture rewrite and is not required for current production performance.

## Validation Results

| Capability | Result |
|---|---|
| SvelteKit production build | Passed |
| FastAPI import and lifespan | Passed |
| Uvicorn startup and `/api/status` | Passed |
| MobileNetV2 inference | Passed |
| YOLOv8 ONNX inference | Passed |
| Tesseract OCR | Passed |
| Ollama status integration | Passed; live availability depends on local Ollama process |
| Analyze API contract | Passed |
| Scan history view/delete | Passed |
| Learning API contract | Passed |
| Chat API contract | Passed |
| Comparison API contract | Passed |
| OCR API contract | Passed |
| ReadingHighlighter Svelte compilation | Passed |
| SQLite migration and schema | Passed |
| FLUX route/storage/history/delete flow | Passed with an isolated mocked provider image |
| Missing-secret failure behavior | Passed |
| Live Hugging Face generation | Not executed: `backend/.env` has no Hugging Face token |

The only remaining validation dependency is a user-supplied Hugging Face token. Once configured, generate one image from AI Image Studio to verify account access, accepted model terms, provider availability, and billing/rate limits.

## Final Architecture Verification

The application remains a single SvelteKit frontend backed by one FastAPI service. Existing OpenCV vision, YOLOv8, MobileNetV2, OCR, Ollama, SQLite history, learning mode, comparison mode, webcam capture, and ReadingHighlighter flows retain their existing contracts. FLUX is implemented as one backend service and one SQLite history table; no duplicate image-generation system remains.

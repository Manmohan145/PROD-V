# VisionAI Edge Cleanup Report

Date: 2026-06-22

## Scope

This report records the repository audit completed before the Hugging Face FLUX migration. The cleanup policy is conservative: remove only confirmed legacy or generated artifacts, refactor active integration points in place, and preserve all working vision, OCR, Ollama, learning, comparison, history, and accessibility features.

## Baseline Verification

- SvelteKit production build: passing.
- Active backend routes: status, analyze, search, learn, chat, OCR, compare, scan history, and Grok image generation/history.
- Active vision engines: MobileNetV2 classification and YOLOv8 detection through OpenCV DNN.
- Active OCR: Tesseract through `pytesseract`.
- Active local LLM: Ollama through the `ollama` package.
- Active storage: SQLite scan history plus the current Grok `image_history` table.
- ReadingHighlighter, quiz, flashcard, archive history, learning, and comparison components are referenced by the live Svelte page.

## Legacy Image Generation Findings

### Confirmed active legacy system to replace

- `backend/services/grok_service.py`
- `/api/grok/generate`
- `/api/grok/history`
- `/api/grok/history/{id}`
- `/api/grok/history/clear`
- Grok-specific state, handlers, labels, prompts, and UI copy in `frontend/routes/+page.svelte`
- `GROK_API_KEY` example configuration
- Grok database helpers and the `image_history` table

### Confirmed dead legacy artifacts

The repository tracks compiled Python bytecode whose source modules no longer exist:

- `backend/__pycache__/gemini_service.cpython-314.pyc`
- `backend/__pycache__/tts_service.cpython-314.pyc`
- Other tracked `backend/__pycache__/*.pyc` files generated from older module locations

These files are build artifacts, can be stale or incompatible across Python versions, and must not be versioned.

### Not found as live source systems

- Stable Diffusion
- Educational Poster Generator
- Infographic Generator
- Concept Art Generator
- Experimental Image Generator
- A live Gemini image-generation route or service

The only Gemini evidence is stale compiled bytecode.

## Files To Delete

- `backend/services/grok_service.py` after its functionality is replaced by the FLUX service.
- All tracked `backend/__pycache__/*.pyc` legacy/generated artifacts.
- Runtime `__pycache__` directories generated during local validation.

No working AI feature source files are deletion candidates.

## Files To Refactor

- `backend/main.py`
  - Load backend-only environment configuration.
  - Tighten local-development CORS configuration.
  - Initialize SQLite schema at application startup.
- `backend/routes/api_routes.py`
  - Replace Grok routes with `/api/image/*` FLUX routes.
  - Preserve all existing non-image endpoints.
- `backend/database/history_db.py`
  - Replace `image_history` with the required `image_generations` schema.
  - Add safe migration, file cleanup, generation-time persistence, and indexed history access.
  - Keep scan history behavior intact.
- `frontend/routes/+page.svelte`
  - Replace Grok-specific API calls and copy with AI Image Studio.
  - Add FLUX history, regenerate, download, templates, and exact object-aware actions.
  - Preserve the current design system and all existing tabs.
- `frontend/lib/api.js`
  - Use the existing centralized API base instead of repeated hard-coded URLs.
- `frontend/components/HistoryPanel.svelte`
  - Use centralized API configuration.
- `.env.example`
  - Replace Grok configuration with `HUGGINGFACE_API_KEY` guidance for `backend/.env`.
- `requirements.txt`
  - Add the official Hugging Face inference client dependency.
- `.gitignore`
  - Verify required runtime, database, cache, upload, and secret exclusions.
- `README.md`
  - Document secure FLUX setup and the new endpoints if needed.

## Files To Keep

- `backend/services/detector.py`
- `backend/services/ocr_service.py`
- `backend/services/local_llm_service.py`
- `backend/utils/image_utils.py`
- `backend/models/domain_models.py`
- `frontend/components/FlashcardDeck.svelte`
- `frontend/components/QuizComponent.svelte`
- `frontend/components/ReadingHighlighter.svelte`
- `frontend/components/HistoryPanel.svelte`
- MobileNetV2 and YOLOv8 ONNX assets
- SvelteKit, FastAPI, OpenCV, OCR, Ollama, and SQLite configuration

## Database Findings

- `scan_history` is active and must be retained.
- `image_history` is tied only to the Grok implementation and will be migrated to:

  `image_generations(id, prompt, image_path, created_at, generation_time)`

- `image_generation_history` is referenced only by an unconditional drop statement and is not an active table. The destructive drop-on-every-init behavior must be removed.
- Image history clearing must not clear scan history, and scan history clearing must not clear image generation history.

## Performance Findings

- The main Svelte page is large and produces a relatively large page chunk, but splitting it wholesale would be an architecture rewrite and is outside this safe migration.
- Backend status polling every ten seconds is intentional and bounded.
- Generated image history currently stores full base64 images in SQLite, inflating the database and API payloads. FLUX images should be stored as files with paths in SQLite.
- API URLs are duplicated across the frontend despite an existing `API_BASE` module.
- Database initialization currently runs on every operation and executes schema work repeatedly.
- The existing generated-image implementation performs blocking network calls in a synchronous route; the replacement should isolate this work from the event loop.

## Dependency Findings

- Frontend packages are all referenced by the SvelteKit application.
- `marked` is actively used.
- Python packages in `requirements.txt` support active features.
- `python-dotenv` is required for backend-only key loading.
- No Stable Diffusion, Diffusers, Gemini, or xAI package is declared.
- Add `huggingface_hub`; avoid adding heavyweight local diffusion dependencies.

## Safety Constraints For Migration

- Preserve all modified user work unrelated to Grok.
- Do not change detector, OCR, Ollama, learning, comparison, or ReadingHighlighter contracts.
- Do not expose `HUGGINGFACE_API_KEY` through frontend code, API responses, logs, or committed environment files.
- Store generated images under a gitignored runtime directory and expose them through a controlled FastAPI static mount.
- Keep migrations idempotent and preserve any existing generation records where feasible.

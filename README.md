# VisionAI Edge — Real-Time Intelligent Object Recognition & Learning Suite

VisionAI Edge is a production-quality, modern full-stack application built for academic presentation and edge AI deployment. It features a fully decoupled architecture:

1. **Frontend**: A **SvelteKit** single-page application (Svelte 5 Runes) with a premium glassmorphism dark theme, animated scanner effects, and instant client-side interactivity.
2. **Backend**: A **FastAPI (Python)** REST server integrating OpenCV DNN (MobileNetV2 / YOLOv8 ONNX), local SQLite3 scan history, PyTesseract OCR, and a local Ollama LLM with persistent JSON caching.

---

## Key Features

1. **Dual-Engine Vision Pipeline**:
   - **Classification Mode (MobileNetV2)**: Contour-based ROI extraction + 1,000-class ONNX classification via OpenCV DNN.
   - **Detection Mode (YOLOv8 Nano)**: Multi-object bounding box overlays with NMS post-processing.
2. **Local AI Knowledge Engine (Ollama)**:
   - Uses a local Llama 3.2 model to generate educational fact sheets, revision guides, comparison reports, and document study guides.
   - Supports contextual Q&A chat with detected objects.
   - Persistent JSON cache (`llm_cache.json`) for instant offline responses.
3. **Interactive Study Workspace**:
   - Dynamic 5-question MCQ quizzes with live score tracking.
   - Interactive 3D flip-card flashcard carousel (fully client-side).
   - Full explanations, revision bullet points, and viva Q&A lists.
4. **Document OCR & Summarizer**:
   - Extracts printed text from uploaded documents using PyTesseract (offline).
   - Generates structured study guides with summaries, key terms, and exam questions.
5. **SQLite Scan History Archive**:
   - Persists all past scans with base64 thumbnail previews and inspection options.
6. **Real-Time Webcam Scanner**:
   - Captures frames from webcam and runs full inference pipeline.
7. **AI Image Studio**:
   - Generates VisionAI-connected learning illustrations through the backend-only Hugging Face Inference API.
   - Uses `black-forest-labs/FLUX.1-schnell` with local file storage and SQLite generation history.
   - Supports templates, object-aware actions, downloads, regeneration, deletion, and history clearing.

---

## Repository Structure

```text
VisionAI/
├── backend/
│   ├── main.py                    # FastAPI app entry point + CORS/static config
│   ├── routes/
│   │   └── api_routes.py          # All REST API endpoints
│   ├── services/
│   │   ├── detector.py            # MobileNetV2 & YOLOv8 ONNX inference (OpenCV DNN)
│   │   ├── flux_image_service.py  # Backend-only Hugging Face FLUX integration
│   │   ├── local_llm_service.py   # Local Ollama Client SDK + persistent JSON cache
│   │   └── ocr_service.py         # PyTesseract OCR document extraction service
│   ├── database/
│   │   └── history_db.py          # SQLite history manager + base64 thumbnail builder
│   ├── models/
│   │   └── domain_models.py       # Pydantic request/response models
│   └── utils/
│       └── image_utils.py         # Image loading, validation, Wikipedia API helpers
├── frontend/
│   ├── routes/
│   │   ├── +layout.svelte         # App metadata, icon, global CSS import
│   │   └── +page.svelte           # Main dashboard (all tabs + state machine)
│   ├── components/
│   │   ├── FlashcardDeck.svelte   # 3D interactive flip-card carousel
│   │   ├── QuizComponent.svelte   # MCQ quiz evaluator with scoring
│   │   ├── HistoryPanel.svelte    # Scan history records with thumbnails
│   │   └── ReadingHighlighter.svelte # Animated markdown fact reader
│   ├── lib/
│   │   ├── app.css                # Global CSS tokens (glassmorphism design system)
│   │   ├── api.js                 # Centralized API base URL constant
│   │   └── assets/
│   │       └── favicon.svg        # Application icon
│   ├── stores/                    # (Reserved for future Svelte stores)
│   └── app.html                   # SvelteKit HTML shell
├── assets/
│   ├── mobilenetv2-7.onnx         # MobileNetV2 classification model (13.6 MB)
│   ├── yolov8n.onnx               # YOLOv8 Nano detection model (12.2 MB)
│   └── synset.txt                 # ImageNet 1,000-class label file
├── static/
│   └── robots.txt                 # Web crawler directives
├── .env.example                   # Environment template (copy to backend/.env)
├── .gitignore                     # Production-grade git exclusion rules
├── requirements.txt               # Python dependencies
├── package.json                   # Node.js dependencies (SvelteKit + Vite)
├── svelte.config.js               # SvelteKit configuration (custom folder paths)
├── vite.config.js                 # Vite bundler configuration
└── run.bat                        # Unified Windows launcher (backend + frontend)
```

---

## Prerequisites

- **Python 3.9+** and **Node.js v20+** installed and in PATH
- **Tesseract OCR Engine** (required for Document Digest tab):
  - Windows: Download from [UB-Mannheim Tesseract](https://github.com/UB-Mannheim/tesseract/wiki) and add to `C:\Program Files\Tesseract-OCR` to System PATH
- **Ollama** (required for AI knowledge engine):
  - Download from [https://ollama.com](https://ollama.com) and run: `ollama pull llama3.2:3b`

---

## Setup & Running

### Option 1 — One-Click Launch (Recommended)
Double-click **`run.bat`**. It will automatically:
1. Create and activate the Python virtual environment (`venv/`)
2. Install Python dependencies from `requirements.txt`
3. Install Node.js packages if `node_modules/` is missing
4. Start the **FastAPI backend** on `http://localhost:8000`
5. Start the **SvelteKit frontend** on `http://localhost:5173`
6. Open your browser to the dashboard

### Option 2 — Manual Launch
```bash
# Terminal 1 — Backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000

# Terminal 2 — Frontend
npm install
npm run dev
```

### Environment Configuration
Copy `.env.example` to `backend/.env` and add a Hugging Face token with Inference Providers permission:
```bash
copy .env.example backend\.env
```

Accept the access conditions on the `black-forest-labs/FLUX.1-schnell`
Hugging Face model page before using AI Image Studio. The token is read only by
FastAPI and is never sent to SvelteKit.

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/status` | Ollama status, model name, vision engine |
| `POST` | `/api/analyze` | Image upload → object detection → annotated result |
| `GET` | `/api/search?q=<query>` | Wikipedia + LLM fact profile for an object |
| `POST` | `/api/learn` | Generate MCQs, flashcards, notes, viva for an object |
| `POST` | `/api/chat` | Contextual LLM Q&A dialog about a detected object |
| `POST` | `/api/ocr` | Extract text from image + generate study guide |
| `POST` | `/api/compare` | Compare two objects with a structured markdown report |
| `GET` | `/api/history` | Retrieve all scan history records |
| `DELETE` | `/api/history/{id}` | Delete a specific history record |
| `POST` | `/api/history/clear` | Clear all history records and uploaded images |
| `POST` | `/api/image/generate` | Generate and locally store a FLUX image |
| `GET` | `/api/image/history` | Retrieve generated-image history |
| `DELETE` | `/api/image/history/{id}` | Delete a generated image and its record |
| `POST` | `/api/image/history/clear` | Clear generated-image history and files |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | SvelteKit 2 (Svelte 5 Runes), Vite 8 |
| Backend | FastAPI, Uvicorn, Python 3.9+ |
| Vision AI | OpenCV DNN, MobileNetV2 ONNX, YOLOv8 ONNX |
| Language AI | Ollama (local LLaMA 3.2 3B) |
| OCR | PyTesseract + Tesseract Engine |
| Image Generation | Hugging Face Inference API + FLUX.1-schnell |
| Database | SQLite3 (via Python stdlib) |
| Styling | Vanilla CSS (glassmorphism design system) |

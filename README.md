# VisionAI – Real-Time Intelligent Object Recognition & Learning Suite

VisionAI is a production-quality, modern full-stack application. It features a decoupled architecture:
1. **Frontend**: A highly responsive **SvelteKit** single-page application built on Svelte 5 with sleek glassmorphism themes, floating background bubble animations, and instant client-side card flipping.
2. **Backend**: A robust **FastAPI (Python)** server that integrates OpenCV DNN (MobileNetV2 / YOLOv8), local SQLite3 logs, PyTesseract OCR, and a local Ollama LLM.

---

## Key Features

1. **Dual-Engine Vision Pipeline**:
   - **Classification Mode (MobileNetV2)**: Runs edge segmentation and crops regions of interest to run classification via a 1,000-class ONNX model.
   - **Detection Mode (YOLOv8)**: Leverages YOLOv8 Nano to overlay bounding boxes around multiple objects concurrently.
2. **Local AI Knowledge Engine (Ollama)**:
   - Uses local Llama 3.2 model to compile educational facts, revision guides, comparative profiles, and document analyses.
   - Supports contextual conversations with detected objects.
   - Uses local persistent caching (`llm_cache.json`) for instant responses.
3. **Interactive Study Dashboard**:
   - Compiles dynamic 5-question multiple choice quizzes with instant results tracking.
   - Interactive 3D flip card carousel running fully client-side.
4. **Document OCR & Summarizer**:
   - Extracts printed text from documents offline using PyTesseract OCR.
5. **SQLite Scan History Explorer**:
   - Persists all past scans in a local database, displaying visual base64 thumbnails and inspection options.
6. **Voice Synthesis**:
   - Client-side text-to-speech reading fact sheets or OCR summary notes with browser native synthesizers.

---

## Folder Structure

```text
VisionAI/
├── backend/
│   ├── detector.py          # MobileNetV2 & YOLOv8 ONNX inference via OpenCV DNN
│   ├── local_llm_service.py # Local Ollama Client SDK integration with persistent JSON cache
│   ├── image_utils.py       # Helper functions for image loading, validation, and Wikipedia fetches
│   ├── history_db.py        # SQLite history database manager and base64 thumbnail builder
│   ├── ocr_service.py       # PyTesseract OCR document service
│   └── tts_service.py       # Offline pyttsx3 text-to-speech audio player generator
├── src/                     # SvelteKit Application Source
│   ├── lib/
│   │   └── components/
│   │       ├── FloatingBubbles.svelte # Slow rising bubble particles background
│   │       ├── FlashcardDeck.svelte   # 3D interactive flip-cards
│   │       ├── QuizComponent.svelte   # Interactive quiz evaluator
│   │       └── HistoryPanel.svelte    # SQLite scan history records loader
│   ├── routes/
│   │   ├── +layout.svelte   # Main page metadata & global CSS overrides
│   │   └── +page.svelte     # Main dashboard interface
│   └── app.css              # Theme CSS tokens (glassmorphism variables)
├── static/                  # Static assets
├── assets/                  # Precompiled ONNX weights and model assets
├── uploads/                 # Dynamically generated directory for storing uploaded images
├── api.py                   # FastAPI application endpoint routers
├── requirements.txt         # Python dependencies list
├── package.json             # Node.js dependencies list
└── run.bat                  # Unified Windows launcher
```

---

## Setup & Running the Application

### Prerequisites
- **Python 3.9+** and **Node.js v20+** installed.
- **Tesseract OCR Engine** installed locally (required for Text Reader mode).
  - *Windows*: Download from [UB-Mannheim Tesseract](https://github.com/UB-Mannheim/tesseract/wiki) and add `C:\Program Files\Tesseract-OCR` to your System Environment variables.
- **Ollama** installed locally (required for AI assistants).
  - Download and run Ollama from [https://ollama.com](https://ollama.com).
  - Pull the model: `ollama run llama3.2:3b`.

### Launching the Application (Recommended)
Simply double-click the **[run.bat](file:///c:/Users/Manmohan/Documents/VisionAI/run.bat)** file. It will automatically:
1. Set up/activate the Python virtual environment and update dependencies.
2. Install npm dependencies if `node_modules` is missing.
3. Start the FastAPI backend on `http://localhost:8000`.
4. Start the SvelteKit frontend server on `http://localhost:5173`.
5. Open your default web browser to the SvelteKit dashboard page.

To stop the servers, simply close the command prompt window.

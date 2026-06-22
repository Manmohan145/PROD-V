import os
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from dotenv import dotenv_values, load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles


BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent
GENERATED_IMAGE_DIR = PROJECT_ROOT / "uploads" / "generated"

load_dotenv(BACKEND_DIR / ".env", override=False)
legacy_env = dotenv_values(PROJECT_ROOT / ".env")
for legacy_key in ("OLLAMA_MODEL", "OLLAMA_HOST"):
    legacy_value = legacy_env.get(legacy_key)
    if legacy_value:
        os.environ.setdefault(legacy_key, legacy_value)

from backend.database.history_db import init_db
from backend.routes.api_routes import router


@asynccontextmanager
async def lifespan(_: FastAPI):
    GENERATED_IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    init_db()
    yield


app = FastAPI(
    title="VisionAI REST Backend",
    description="Exposes AI Vision and Generative LLM services to the SvelteKit frontend.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
GENERATED_IMAGE_DIR.mkdir(parents=True, exist_ok=True)
app.mount(
    "/generated-images",
    StaticFiles(directory=GENERATED_IMAGE_DIR),
    name="generated-images",
)


if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)

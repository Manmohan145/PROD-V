from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.config import settings
from backend.database.history_db import init_db
from backend.routes.api_routes import router


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings.generated_image_dir.mkdir(parents=True, exist_ok=True)
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
settings.generated_image_dir.mkdir(parents=True, exist_ok=True)
app.mount(
    "/generated-images",
    StaticFiles(directory=settings.generated_image_dir),
    name="generated-images",
)


if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.routes.api_routes import router

app = FastAPI(
    title="VisionAI REST Backend",
    description="Exposes AI Vision and Generative LLM services to the SvelteKit frontend."
)

# Configure CORS for local SvelteKit dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register endpoints router
app.include_router(router)

if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)

import time
import base64
from asyncio import to_thread
import cv2
from fastapi import APIRouter, File, UploadFile, Form, HTTPException
from pydantic import BaseModel

# Import backend modules
from backend.services.vision.detector import ObjectDetector
from backend.services.llm.local_llm_service import LocalLLMService
from backend.services.ocr.ocr_service import OCRService
from backend.services.image_generation.flux_image_service import (
    FluxImageService,
    ImageGenerationError,
)
from backend.utils.image_utils import (
    validate_image_file,
    load_image_from_bytes,
    save_uploaded_image,
    get_wikipedia_image
)
from backend.database.history_db import (
    save_scan,
    get_history,
    delete_record,
    clear_history,
    save_image_generation,
    get_image_generations,
    delete_image_generation,
    clear_image_generations
)
from backend.models.domain_models import CompareRequest, LearnRequest, ChatRequest

class ImageGenerationRequest(BaseModel):
    prompt: str

router = APIRouter()

# Pre-load/instantiate services
detector = ObjectDetector(mode="classification")
detector.load_model()
llm_service = LocalLLMService()
ocr_service = OCRService()
image_service = FluxImageService()

@router.get("/api/status")
def get_status():
    """Returns Ollama status, current model, and active engine configuration."""
    ollama_active = llm_service.check_connection()
    return {
        "ollama_active": ollama_active,
        "ollama_model": llm_service.model_name,
        "vision_engine": detector.mode
    }

@router.post("/api/analyze")
async def analyze_image(
    file: UploadFile = File(...),
    engine_mode: str = Form("classification"),
    confidence_threshold: float = Form(0.25)
):
    """Processes uploaded image, draws bounding boxes, saves to DB, returns results."""
    try:
        file_bytes = await file.read()

        # Validate image file
        is_valid, err_msg = validate_image_file(file.filename, len(file_bytes))
        if not is_valid:
            raise HTTPException(status_code=400, detail=err_msg)

        # Switch mode dynamically if requested
        if detector.mode != engine_mode:
            detector.set_mode(engine_mode)

        # Process BGR image
        bgr_image = load_image_from_bytes(file_bytes)
        save_path = save_uploaded_image(file_bytes, file.filename)

        # Run inference
        start_time = time.perf_counter()
        detections = detector.detect_and_classify(bgr_image, min_confidence=confidence_threshold)
        latency_ms = (time.perf_counter() - start_time) * 1000

        if not detections:
            # Return original image in base64 if no detections
            _, buffer = cv2.imencode('.png', bgr_image)
            base64_str = base64.b64encode(buffer).decode('utf-8')
            return {
                "detections": [],
                "latency_ms": latency_ms,
                "resolution": f"{bgr_image.shape[1]}x{bgr_image.shape[0]}",
                "annotated_image": f"data:image/png;base64,{base64_str}",
                "top_label": None
            }

        # Save highest confidence detection to scan history
        top_det = detections[0]
        save_scan(top_det['label'], top_det['confidence'], save_path)

        # Draw bounding boxes
        annotated_bgr = detector.draw_detections(bgr_image, detections)
        _, buffer = cv2.imencode('.png', annotated_bgr)
        base64_str = base64.b64encode(buffer).decode('utf-8')

        return {
            "detections": detections,
            "latency_ms": latency_ms,
            "resolution": f"{bgr_image.shape[1]}x{bgr_image.shape[0]}",
            "annotated_image": f"data:image/png;base64,{base64_str}",
            "top_label": top_det['label']
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Inference error: {str(e)}")

@router.get("/api/search")
def search_object(q: str):
    """Searches Wikipedia and queries local LLM for object information."""
    if not q:
        raise HTTPException(status_code=400, detail="Search query is required")

    try:
        img_url, wiki_summary = get_wikipedia_image(q)

        llm_info = None
        llm_latency_s = 0.0
        if llm_service.check_connection():
            llm_start = time.perf_counter()
            llm_info = llm_service.generate_educational_info(q)
            llm_latency_s = time.perf_counter() - llm_start

        return {
            "query": q.title(),
            "image_url": img_url,
            "wikipedia_summary": wiki_summary,
            "llm_info": llm_info,
            "llm_latency_s": llm_latency_s
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/learn")
def learn_curriculum(req: LearnRequest):
    """Generates MCQs, flashcards, revision notes, and viva list for a concept."""
    try:
        if not llm_service.check_connection():
            raise HTTPException(status_code=503, detail="Ollama is currently offline")

        start_time = time.perf_counter()
        data = llm_service.generate_educational_data(req.target_object)
        latency = time.perf_counter() - start_time

        return {
            "data": data,
            "latency_s": latency
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/chat")
def chat_with_object(req: ChatRequest):
    """Contextual interactive dialogue with local Ollama regarding an object."""
    try:
        if not llm_service.check_connection():
            raise HTTPException(status_code=503, detail="Ollama is currently offline")

        # Format dialog history
        history_lines = []
        for msg in req.messages[:-1]:
            history_lines.append(f"{msg.role.capitalize()}: {msg.content}")

        chat_context = f"""You are an educational tutor answering questions about the object: "{req.selected_label}".

        Conversation history:
        {"\n".join(history_lines)}

        User's new question: {req.messages[-1].content}

        Provide a clear, engaging, and scientifically accurate answer in 2-3 sentences. Do not use markdown headers."""

        start_time = time.perf_counter()
        reply = llm_service.generate_educational_info(chat_context)
        latency = time.perf_counter() - start_time

        return {
            "reply": reply,
            "latency_s": latency
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/ocr")
async def ocr_document(file: UploadFile = File(...)):
    """Extracts text via pytesseract and compiles structured summaries via Ollama."""
    try:
        file_bytes = await file.read()
        text, method = ocr_service.extract_text(file_bytes)

        # Check LLM summary analysis
        analysis = None
        if llm_service.check_connection():
            analysis = ocr_service.analyze_document(text)

        return {
            "text": text,
            "method": method,
            "analysis": analysis
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/compare")
def compare_concepts(req: CompareRequest):
    """Compares structural, ecological, or technical differences between concepts."""
    try:
        if not llm_service.check_connection():
            raise HTTPException(status_code=503, detail="Ollama is currently offline")

        start_time = time.perf_counter()
        comparison = llm_service.generate_comparison_data(req.object_a, req.object_b)
        latency = time.perf_counter() - start_time

        return {
            "comparison": comparison,
            "latency_s": latency
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/history")
def scan_history():
    """Retrieves SQLite scan records."""
    try:
        return get_history()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/api/history/{record_id}")
def delete_history_record(record_id: int):
    """Deletes a specific history record."""
    try:
        delete_record(record_id)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/history/clear")
def clear_all_history():
    """Clears all logs and uploads."""
    try:
        clear_history()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/image/generate")
async def generate_image(req: ImageGenerationRequest):
    """Generate an image with FLUX and persist its local history record."""
    prompt = req.prompt.strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt cannot be empty")
    if len(prompt) > 1000:
        raise HTTPException(status_code=400, detail="Prompt must be 1000 characters or fewer")
    try:
        start_time = time.perf_counter()
        image_path = await to_thread(image_service.generate, prompt)
        generation_time = round(time.perf_counter() - start_time, 2)
        record_id = save_image_generation(prompt, image_path, generation_time)
        return {
            "success": True,
            "id": record_id,
            "image": f"/generated-images/{image_path.rsplit('/', 1)[-1]}",
            "prompt": prompt,
            "generation_time": f"{generation_time:.2f}s"
        }
    except ImageGenerationError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

@router.get("/api/image/history")
def get_image_history():
    try:
        records = get_image_generations()
        for record in records:
            filename = record["image_path"].rsplit("/", 1)[-1]
            record["image"] = f"/generated-images/{filename}"
        return records
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/api/image/history/{record_id}")
def delete_image_history_record(record_id: int):
    try:
        if not delete_image_generation(record_id):
            raise HTTPException(status_code=404, detail="Image generation not found")
        return {"status": "success"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/image/history/clear")
def clear_image_history():
    try:
        clear_image_generations()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

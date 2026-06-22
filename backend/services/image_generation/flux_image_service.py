from pathlib import Path
from uuid import uuid4

from huggingface_hub import InferenceClient
from PIL import Image, ImageOps

from backend.config import settings

PROJECT_ROOT = settings.project_root
GENERATED_IMAGE_DIR = settings.generated_image_dir


class ImageGenerationError(RuntimeError):
    """Raised when the remote image provider cannot complete a generation."""


class FluxImageService:
    model_name = "black-forest-labs/FLUX.1-schnell"

    def __init__(self, output_dir: Path = GENERATED_IMAGE_DIR):
        self.output_dir = output_dir.resolve()

    def _get_api_key(self) -> str:
        api_key = settings.huggingface_api_key
        if not api_key or api_key == "hf_your_token_here":
            raise ImageGenerationError(
                "HUGGINGFACE_API_KEY is not configured in backend/.env"
            )
        return api_key

    def generate(self, prompt: str) -> str:
        """Generate a FLUX image and return its project-relative file path."""
        client = InferenceClient(
            provider="auto",
            api_key=self._get_api_key(),
            timeout=120,
        )

        try:
            image = client.text_to_image(
                prompt,
                model=self.model_name,
                width=1024,
                height=1024,
                num_inference_steps=4,
                guidance_scale=0.0,
            )
        except Exception as exc:
            message = str(exc).lower()
            if "401" in message or "unauthorized" in message:
                detail = "Hugging Face authentication failed. Check backend/.env."
            elif "403" in message or "gated" in message or "access" in message:
                detail = (
                    "FLUX access was denied. Accept the model terms on Hugging Face "
                    "and grant the token Inference Providers permission."
                )
            elif "429" in message or "rate limit" in message:
                detail = "Hugging Face rate limit reached. Please retry shortly."
            elif "timeout" in message or "timed out" in message:
                detail = "Hugging Face image generation timed out. Please retry."
            else:
                detail = "Hugging Face could not generate the image."
            raise ImageGenerationError(detail) from exc

        if not isinstance(image, Image.Image):
            raise ImageGenerationError("Hugging Face returned an invalid image response.")

        self.output_dir.mkdir(parents=True, exist_ok=True)
        output_path = self.output_dir / f"flux-{uuid4().hex}.png"
        normalized = ImageOps.exif_transpose(image).convert("RGB")
        normalized.save(output_path, format="PNG", optimize=True)
        return output_path.relative_to(PROJECT_ROOT).as_posix()

import os
from PIL import Image
import io
from backend.services.llm.local_llm_service import LocalLLMService


class OCRService:
    def __init__(self):
        """Initializes the OCR service and checks Ollama connectivity."""
        self.llm = LocalLLMService()
        self.is_configured = self.llm.is_configured

        # Configure Tesseract binary path on Windows if not in PATH
        import shutil
        if not shutil.which("tesseract"):
            common_paths = [
                r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
                os.path.expandvars(r"%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe"),
            ]
            for path in common_paths:
                if os.path.exists(path):
                    import pytesseract
                    pytesseract.pytesseract.tesseract_cmd = path
                    print(f"VisionAI: Configured Tesseract binary path to {path}")
                    break

    def extract_text(self, image_bytes: bytes) -> tuple[str, str]:
        """
        Attempts to extract text using pytesseract. If Tesseract is missing,
        raises a clean offline warning.
        
        Args:
            image_bytes (bytes): Raw image bytes of the document.
            
        Returns:
            tuple[str, str]: (extracted_text, method_used)
        """
        try:
            import pytesseract
            # Convert bytes to PIL Image
            image = Image.open(io.BytesIO(image_bytes))
            # Test if Tesseract is installed and reachable
            text = pytesseract.image_to_string(image)
            if text.strip():
                return text.strip(), "Tesseract OCR (Offline)"
            else:
                return "[No text detected in the image]", "Tesseract OCR (Offline)"
        except Exception as e:
            print(f"Pytesseract extraction failed: {e}")
            raise Exception(
                "Tesseract OCR is not installed or not in your system PATH.\n"
                "Please download and install Tesseract OCR on your local machine to extract text offline:\n"
                "  https://github.com/UB-Mannheim/tesseract/wiki"
            )

    def analyze_document(self, text: str) -> str:
        """
        Queries the local Ollama LLM service to generate summaries, key points, terms, and questions.
        
        Args:
            text (str): The extracted text from the document.
            
        Returns:
            str: Markdown formatted analysis study guide.
        """
        # Re-check connectivity
        if not self.llm.check_connection():
            raise Exception(
                "Ollama is offline. Please make sure the Ollama application is running to compile study guides."
            )
        try:
            return self.llm.generate_document_analysis(text)
        except Exception as e:
            raise Exception(f"Failed to compile document analysis offline: {str(e)}")

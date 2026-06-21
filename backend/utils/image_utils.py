import os
import cv2
import numpy as np
from PIL import Image
from datetime import datetime

# Maximum file size allowed: 10 MB
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024
ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png'}

def validate_image_file(file_name: str, file_size: int) -> tuple[bool, str]:
    """
    Validates the uploaded file based on its extension and file size.
    
    Args:
        file_name (str): The original name of the file.
        file_size (int): The size of the file in bytes.
        
    Returns:
        tuple[bool, str]: (is_valid, error_message)
    """
    # Check extension
    _, ext = os.path.splitext(file_name.lower())
    if ext not in ALLOWED_EXTENSIONS:
        return False, f"Unsupported file type '{ext}'. Allowed extensions are: JPG, JPEG, PNG."
    
    # Check size
    if file_size > MAX_FILE_SIZE_BYTES:
        max_mb = MAX_FILE_SIZE_BYTES / (1024 * 1024)
        return False, f"File size exceeds the limit of {max_mb:.1f} MB (got {file_size / (1024 * 1024):.1f} MB)."
        
    return True, ""

def load_image_from_bytes(image_bytes: bytes) -> np.ndarray:
    """
    Converts raw image bytes to an OpenCV BGR image.
    
    Args:
        image_bytes (bytes): The raw image bytes.
        
    Returns:
        np.ndarray: OpenCV BGR image array.
        
    Raises:
        ValueError: If the image cannot be decoded.
    """
    np_arr = np.frombuffer(image_bytes, np.uint8)
    image = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("Failed to decode image. The file may be corrupted or in an unsupported format.")
    return image

def convert_cv2_to_pil(cv2_image: np.ndarray) -> Image.Image:
    """
    Converts an OpenCV BGR image array to a PIL Image (RGB).
    
    Args:
        cv2_image (np.ndarray): The OpenCV image in BGR format.
        
    Returns:
        Image.Image: The converted PIL Image in RGB format.
    """
    rgb_image = cv2.cvtColor(cv2_image, cv2.COLOR_BGR2RGB)
    return Image.fromarray(rgb_image)



def save_uploaded_image(image_bytes: bytes, original_filename: str, upload_dir: str = "uploads") -> str:
    """
    Saves the image bytes to a file in the upload directory with a unique timestamped name.
    
    Args:
        image_bytes (bytes): Raw image bytes.
        original_filename (str): Original name of the uploaded file.
        upload_dir (str): Directory where the image should be saved.
        
    Returns:
        str: Absolute path to the saved file.
    """
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir, exist_ok=True)
        
    _, ext = os.path.splitext(original_filename.lower())
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # Clean file name or generate a safe unique name
    safe_filename = f"upload_{timestamp}{ext}"
    dest_path = os.path.join(upload_dir, safe_filename)
    
    with open(dest_path, "wb") as f:
        f.write(image_bytes)
        
    return os.path.abspath(dest_path)

def get_wikipedia_image(query: str) -> tuple[str | None, str | None]:
    """
    Searches Wikipedia for the query and retrieves the main page image URL and short summary.
    
    Args:
        query (str): The search query (e.g. "Tiger").
        
    Returns:
        tuple[str | None, str | None]: (image_url, summary)
    """
    import urllib.parse
    import urllib.request
    import json
    
    search_url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={urllib.parse.quote(query)}&format=json"
    req = urllib.request.Request(search_url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
    
    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))
            search_results = data.get('query', {}).get('search', [])
            if not search_results:
                return None, None
            
            best_title = search_results[0]['title']
            
        info_url = f"https://en.wikipedia.org/w/api.php?action=query&prop=pageimages|extracts&exintro&explaintext&exchars=300&piprop=original&titles={urllib.parse.quote(best_title)}&format=json"
        req_info = urllib.request.Request(info_url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        
        with urllib.request.urlopen(req_info) as response:
            data = json.loads(response.read().decode('utf-8'))
            pages = data.get('query', {}).get('pages', {})
            for page_id, page_data in pages.items():
                image_url = page_data.get('original', {}).get('source')
                summary = page_data.get('extract')
                return image_url, summary
                
    except Exception:
        return None, None
    return None, None

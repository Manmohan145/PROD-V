import sqlite3
import os
import cv2
import base64
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "scan_history.db")

def init_db():
    """Initializes the SQLite database and creates the scan_history table if it doesn't exist."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scan_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            object_name TEXT NOT NULL,
            confidence REAL NOT NULL,
            timestamp TEXT NOT NULL,
            image_path TEXT,
            thumbnail TEXT
        )
    """)
    conn.commit()
    conn.close()

def generate_thumbnail(image_path: str, max_size: int = 150) -> str:
    """
    Reads an image from disk, resizes it keeping aspect ratio,
    and returns its JPEG representation as a base64 string.
    
    Args:
        image_path (str): Path to the image file.
        max_size (int): Max width/height dimension.
        
    Returns:
        str: Base64 encoded JPEG thumbnail string, or empty string on failure.
    """
    if not image_path or not os.path.exists(image_path):
        return ""
    try:
        img = cv2.imread(image_path)
        if img is None:
            return ""
            
        h, w = img.shape[:2]
        # Calculate scale ratio to fit max_size
        scale = max_size / max(h, w)
        if scale < 1.0:
            new_w = int(w * scale)
            new_h = int(h * scale)
            img_resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
        else:
            img_resized = img
            
        # Encode to JPEG
        _, buffer = cv2.imencode('.jpg', img_resized, [cv2.IMWRITE_JPEG_QUALITY, 70])
        b64_str = base64.b64encode(buffer).decode('utf-8')
        return f"data:image/jpeg;base64,{b64_str}"
    except Exception as e:
        print(f"Error generating thumbnail: {e}")
        return ""

def save_scan(object_name: str, confidence: float, image_path: str) -> int:
    """
    Saves a scan record to the database.
    
    Args:
        object_name (str): Label of the identified object.
        confidence (float): Confidence score (0.0 to 1.0).
        image_path (str): File path of the stored image.
        
    Returns:
        int: The database ID of the inserted record.
    """
    init_db()
    thumbnail_b64 = generate_thumbnail(image_path)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO scan_history (object_name, confidence, timestamp, image_path, thumbnail)
        VALUES (?, ?, ?, ?, ?)
    """, (object_name, confidence, timestamp, image_path, thumbnail_b64))
    
    record_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return record_id

def get_history() -> list[dict]:
    """
    Retrieves all scan records from the database sorted by date and time descending.
    
    Returns:
        list[dict]: List of scan records as dictionaries.
    """
    init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM scan_history ORDER BY id DESC")
    rows = cursor.fetchall()
    
    history = []
    for row in rows:
        history.append({
            'id': row['id'],
            'object_name': row['object_name'],
            'confidence': row['confidence'],
            'timestamp': row['timestamp'],
            'image_path': row['image_path'],
            'thumbnail': row['thumbnail']
        })
    conn.close()
    return history

def delete_record(record_id: int):
    """Deletes a specific record from the scan history."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Optional: Delete corresponding physical image file
    cursor.execute("SELECT image_path FROM scan_history WHERE id = ?", (record_id,))
    row = cursor.fetchone()
    if row and row[0] and os.path.exists(row[0]):
        try:
            os.remove(row[0])
        except Exception:
            pass
            
    cursor.execute("DELETE FROM scan_history WHERE id = ?", (record_id,))
    conn.commit()
    conn.close()

def clear_history():
    """Deletes all records from the database and removes all cached upload images."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Remove all physical files mentioned in DB
    cursor.execute("SELECT image_path FROM scan_history")
    rows = cursor.fetchall()
    for row in rows:
        if row[0] and os.path.exists(row[0]):
            try:
                os.remove(row[0])
            except Exception:
                pass
                
    cursor.execute("DELETE FROM scan_history")
    conn.commit()
    conn.close()

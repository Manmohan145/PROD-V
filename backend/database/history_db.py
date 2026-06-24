import base64
import binascii
import sqlite3
from datetime import datetime
from io import BytesIO
from pathlib import Path

import cv2
from PIL import Image


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = Path(__file__).resolve().with_name("scan_history.db")
GENERATED_IMAGE_DIR = (PROJECT_ROOT / "uploads" / "generated").resolve()


def init_db():
    """Create current tables and migrate legacy image history once."""
    with sqlite3.connect(DB_PATH) as conn:
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
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS image_generations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prompt TEXT NOT NULL,
                image_path TEXT NOT NULL,
                created_at TEXT NOT NULL,
                generation_time REAL NOT NULL
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_image_generations_created_at
            ON image_generations(created_at DESC)
        """)
        _migrate_legacy_image_history(cursor)
        cursor.execute("DROP TABLE IF EXISTS image_generation_history")


def _migrate_legacy_image_history(cursor: sqlite3.Cursor):
    legacy_exists = cursor.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'image_history'"
    ).fetchone()
    if not legacy_exists:
        return

    GENERATED_IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    rows = cursor.execute(
        "SELECT id, prompt, image_url, created_at FROM image_history ORDER BY id"
    ).fetchall()
    for legacy_id, prompt, image_url, created_at in rows:
        image_path = _persist_legacy_data_url(legacy_id, image_url)
        if image_path:
            cursor.execute(
                """
                INSERT INTO image_generations
                    (prompt, image_path, created_at, generation_time)
                VALUES (?, ?, ?, ?)
                """,
                (prompt, image_path, created_at, 0.0),
            )
    cursor.execute("DROP TABLE image_history")


def _persist_legacy_data_url(legacy_id: int, image_url: str) -> str | None:
    if not image_url or not image_url.startswith("data:image/"):
        return None
    try:
        _, encoded = image_url.split(",", 1)
        image_bytes = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error):
        return None

    output_path = GENERATED_IMAGE_DIR / f"legacy-{legacy_id}.png"
    try:
        with Image.open(BytesIO(image_bytes)) as image:
            image.convert("RGB").save(output_path, format="PNG", optimize=True)
    except (OSError, ValueError):
        return None
    return output_path.relative_to(PROJECT_ROOT).as_posix()


def _resolve_image_path(image_path: str) -> Path:
    """Resolves a stored image path (relative or legacy absolute) to an existing file."""
    candidate = Path(image_path)
    if candidate.is_absolute():
        return candidate
    return (PROJECT_ROOT / candidate).resolve()


def generate_thumbnail(image_path: str, max_size: int = 150) -> str:
    """Return a compact JPEG data URL for a saved scan image."""
    resolved_path = _resolve_image_path(image_path) if image_path else None
    if not resolved_path or not resolved_path.exists():
        return ""
    try:
        image = cv2.imread(str(resolved_path))
        if image is None:
            return ""

        height, width = image.shape[:2]
        scale = max_size / max(height, width)
        if scale < 1.0:
            image = cv2.resize(
                image,
                (int(width * scale), int(height * scale)),
                interpolation=cv2.INTER_AREA,
            )

        success, buffer = cv2.imencode(
            ".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, 70]
        )
        if not success:
            return ""
        encoded = base64.b64encode(buffer).decode("utf-8")
        return f"data:image/jpeg;base64,{encoded}"
    except (OSError, cv2.error):
        return ""


def save_scan(object_name: str, confidence: float, image_path: str) -> int:
    init_db()
    thumbnail = generate_thumbnail(image_path)
    timestamp = datetime.now().astimezone().isoformat(timespec="seconds")
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO scan_history
                (object_name, confidence, timestamp, image_path, thumbnail)
            VALUES (?, ?, ?, ?, ?)
            """,
            (object_name, confidence, timestamp, image_path, thumbnail),
        )
        return cursor.lastrowid


def get_history() -> list[dict]:
    init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM scan_history ORDER BY id DESC").fetchall()
    conn.close()
    return [dict(row) for row in rows]


def delete_record(record_id: int):
    init_db()
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        row = cursor.execute(
            "SELECT image_path FROM scan_history WHERE id = ?", (record_id,)
        ).fetchone()
        if row and row[0]:
            resolved_path = _resolve_image_path(row[0])
            if resolved_path.exists():
                try:
                    resolved_path.unlink()
                except OSError:
                    pass
        cursor.execute("DELETE FROM scan_history WHERE id = ?", (record_id,))


def clear_history():
    """Clear scan history without affecting generated-image history."""
    init_db()
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        rows = cursor.execute("SELECT image_path FROM scan_history").fetchall()
        for row in rows:
            if row[0]:
                resolved_path = _resolve_image_path(row[0])
                if resolved_path.exists():
                    try:
                        resolved_path.unlink()
                    except OSError:
                        pass
        cursor.execute("DELETE FROM scan_history")


def save_image_generation(
    prompt: str, image_path: str, generation_time: float
) -> int:
    init_db()
    created_at = datetime.now().astimezone().isoformat(timespec="seconds")
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO image_generations
                (prompt, image_path, created_at, generation_time)
            VALUES (?, ?, ?, ?)
            """,
            (prompt, image_path, created_at, generation_time),
        )
        return cursor.lastrowid


def get_image_generations() -> list[dict]:
    init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """
        SELECT id, prompt, image_path, created_at, generation_time
        FROM image_generations
        ORDER BY id DESC
        """
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def delete_image_generation(record_id: int) -> bool:
    init_db()
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        row = cursor.execute(
            "SELECT image_path FROM image_generations WHERE id = ?", (record_id,)
        ).fetchone()
        if not row:
            return False
        _delete_generated_file(row[0])
        cursor.execute("DELETE FROM image_generations WHERE id = ?", (record_id,))
        return True


def clear_image_generations():
    init_db()
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        rows = cursor.execute("SELECT image_path FROM image_generations").fetchall()
        for row in rows:
            _delete_generated_file(row[0])
        cursor.execute("DELETE FROM image_generations")


def _delete_generated_file(image_path: str):
    candidate = (PROJECT_ROOT / image_path).resolve()
    if GENERATED_IMAGE_DIR not in candidate.parents:
        return
    try:
        candidate.unlink(missing_ok=True)
    except OSError:
        pass

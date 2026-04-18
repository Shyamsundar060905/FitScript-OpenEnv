"""
Progress photo management.

Handles uploading, storing, and retrieving progress photos. Each photo is:
  - Saved to data/photos/<user_id>/<date>_<uuid>.<ext>
  - Registered in the progress_photos table (see memory/episodic.py)
  - Validated for file type and size before writing to disk

The Streamlit app uses these helpers via st.file_uploader.
"""

from __future__ import annotations

import hashlib
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import BinaryIO, Optional

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import config
from memory.episodic import save_photo_metadata, get_photos, delete_photo


# Accepted image MIME types / extensions
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".heic"}
MAX_FILE_SIZE_MB = 10
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024


class PhotoUploadError(Exception):
    """Raised when a photo upload fails validation or writing."""


def _photo_dir(user_id: str) -> Path:
    """Return the directory where this user's photos live, creating if needed."""
    d = config.PHOTOS_DIR / user_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def _validate_upload(filename: str, size_bytes: int):
    """Raise PhotoUploadError if the upload is unacceptable."""
    if not filename:
        raise PhotoUploadError("No filename provided")

    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise PhotoUploadError(
            f"File type '{ext}' not supported. "
            f"Accepted: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )

    if size_bytes > MAX_FILE_SIZE_BYTES:
        raise PhotoUploadError(
            f"File too large ({size_bytes / 1024 / 1024:.1f}MB). "
            f"Max is {MAX_FILE_SIZE_MB}MB."
        )

    if size_bytes == 0:
        raise PhotoUploadError("File is empty")


def save_photo(
    user_id: str,
    file_bytes: bytes,
    original_filename: str,
    date: Optional[str] = None,
    weight_kg: Optional[float] = None,
    note: str = "",
) -> dict:
    """
    Save a photo upload. Returns a dict with the saved path and DB row id.

    Args:
        user_id: the user identifier
        file_bytes: raw bytes of the uploaded file
        original_filename: source filename (used only for extension detection)
        date: ISO date string (defaults to today)
        weight_kg: optional weight to associate with the photo
        note: optional freeform note

    Raises:
        PhotoUploadError if validation fails.
    """
    _validate_upload(original_filename, len(file_bytes))

    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")

    ext = Path(original_filename).suffix.lower()
    # Use a short UUID to prevent collisions; include date prefix for human
    # readability when browsing the filesystem.
    unique = uuid.uuid4().hex[:8]
    filename = f"{date}_{unique}{ext}"
    target = _photo_dir(user_id) / filename

    target.write_bytes(file_bytes)

    photo_id = save_photo_metadata(
        user_id=user_id,
        photo_path=str(target),
        date=date,
        weight_kg=weight_kg,
        note=note,
    )

    return {
        "photo_id": photo_id,
        "path": str(target),
        "filename": filename,
        "size_bytes": len(file_bytes),
        "date": date,
    }


def list_photos(user_id: str, limit: int = 20) -> list[dict]:
    """Return photo metadata for the user, most recent first."""
    return get_photos(user_id, limit=limit)


def remove_photo(user_id: str, photo_id: int) -> bool:
    """Delete a photo (both file and DB row). Returns True if removed."""
    return delete_photo(user_id, photo_id)


def get_photo_bytes(photo_path: str) -> Optional[bytes]:
    """Read bytes for a photo. Returns None if missing."""
    p = Path(photo_path)
    if not p.exists():
        return None
    return p.read_bytes()


# Self-test with a tiny fake PNG
if __name__ == "__main__":
    import tempfile

    # Override paths for isolated testing
    config.PHOTOS_DIR = Path(tempfile.mkdtemp()) / "photos"
    config.EPISODIC_DB = Path(tempfile.mkdtemp()) / "test.db"

    print("── Photo upload tests ──\n")

    # Minimal valid PNG (1x1 black pixel)
    tiny_png = bytes([
        0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,
        0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,
        0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,
        0x08, 0x02, 0x00, 0x00, 0x00, 0x90, 0x77, 0x53,
        0xDE, 0x00, 0x00, 0x00, 0x0C, 0x49, 0x44, 0x41,
        0x54, 0x08, 0x99, 0x63, 0x00, 0x01, 0x00, 0x00,
        0x05, 0x00, 0x01, 0x0D, 0x0A, 0x2D, 0xB4, 0x00,
        0x00, 0x00, 0x00, 0x49, 0x45, 0x4E, 0x44, 0xAE,
        0x42, 0x60, 0x82,
    ])

    # Valid upload
    result = save_photo("test_user", tiny_png, "progress.png",
                         weight_kg=78.5, note="Week 1 front")
    print(f"  ✓ Saved: {result['filename']} (photo_id={result['photo_id']})")

    # List
    photos = list_photos("test_user")
    print(f"  ✓ Listed: {len(photos)} photo(s)")
    assert len(photos) == 1

    # Bad extension
    try:
        save_photo("test_user", b"hello", "malicious.exe")
        print("  ✗ Should reject .exe")
    except PhotoUploadError as e:
        print(f"  ✓ Rejects bad extension: {e}")

    # Too large
    try:
        save_photo("test_user", b"x" * (MAX_FILE_SIZE_BYTES + 1), "big.png")
        print("  ✗ Should reject oversized file")
    except PhotoUploadError as e:
        print(f"  ✓ Rejects oversized: {e}")

    # Empty
    try:
        save_photo("test_user", b"", "empty.png")
        print("  ✗ Should reject empty file")
    except PhotoUploadError as e:
        print(f"  ✓ Rejects empty file: {e}")

    # Delete
    removed = remove_photo("test_user", result["photo_id"])
    assert removed
    print(f"  ✓ Deleted photo_id={result['photo_id']}")
    assert len(list_photos("test_user")) == 0

    print("\n  [Photos] Tests passed")
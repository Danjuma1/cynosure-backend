"""
Image processing utilities for cause list photos.

Workflow on upload:
  1. Validate format (JPEG, PNG, WEBP, HEIC accepted).
  2. Auto-orient based on EXIF rotation tag.
  3. Resize to max 1800 × 2400 px (preserving aspect ratio) — keeps the doc
     legible while cutting file size dramatically.
  4. Save as JPEG at quality=82 (visually lossless for document photos).
  5. Generate a thumbnail (450 px wide) for the page-strip/grid UI.

Returns (image_io, thumb_io, width, height, file_size) as BytesIO objects
ready to be written to Django ImageFields.
"""
import io
from PIL import Image, ImageOps

MAX_WIDTH = 1800
MAX_HEIGHT = 2400
JPEG_QUALITY = 82
THUMB_WIDTH = 450


def _open_and_orient(file_obj) -> Image.Image:
    """Open an image and apply EXIF orientation correction."""
    img = Image.open(file_obj)
    img = ImageOps.exif_transpose(img)   # fix rotation from phone cameras
    if img.mode not in ('RGB', 'L'):
        img = img.convert('RGB')
    return img


def _resize_down(img: Image.Image, max_w: int, max_h: int) -> Image.Image:
    """Downscale *only* — never upscale."""
    w, h = img.size
    if w <= max_w and h <= max_h:
        return img
    ratio = min(max_w / w, max_h / h)
    new_w = int(w * ratio)
    new_h = int(h * ratio)
    return img.resize((new_w, new_h), Image.LANCZOS)


def process_cause_list_image(file_obj) -> dict:
    """
    Process an uploaded cause list image.

    Returns a dict with keys:
        image_io   – BytesIO of the compressed main image
        thumb_io   – BytesIO of the compressed thumbnail
        width      – pixel width of the main image
        height     – pixel height of the main image
        file_size  – byte length of the compressed main image
    """
    img = _open_and_orient(file_obj)

    # ── Main image ────────────────────────────────────────────────────────────
    main = _resize_down(img, MAX_WIDTH, MAX_HEIGHT)
    width, height = main.size

    image_io = io.BytesIO()
    main.save(image_io, format='JPEG', quality=JPEG_QUALITY, optimize=True)
    image_io.seek(0)
    file_size = image_io.getbuffer().nbytes

    # ── Thumbnail ─────────────────────────────────────────────────────────────
    thumb = img.copy()
    ratio = THUMB_WIDTH / thumb.width
    thumb_h = int(thumb.height * ratio)
    thumb = thumb.resize((THUMB_WIDTH, thumb_h), Image.LANCZOS)

    thumb_io = io.BytesIO()
    thumb.save(thumb_io, format='JPEG', quality=75, optimize=True)
    thumb_io.seek(0)

    return {
        'image_io': image_io,
        'thumb_io': thumb_io,
        'width': width,
        'height': height,
        'file_size': file_size,
    }

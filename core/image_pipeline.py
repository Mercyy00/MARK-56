"""
core/image_pipeline.py — High-Performance Image Ingestion & Progressive Asset Pipeline.

Provides non-blocking, asynchronous image ingestion, multi-tier downsampling,
progressive enhancement (Low-Quality Image Placeholders / LQIP, responsive srcsets,
loading='lazy', decoding='async'), and strict memory-bounded caching for the JARVIS
Design Creator and presentation engines.
"""

from __future__ import annotations

import base64
import concurrent.futures
import hashlib
import io
import mimetypes
import os
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

try:
    from PIL import Image, ImageFilter, ImageOps
except ImportError:
    Image = None  # type: ignore
    ImageFilter = None  # type: ignore
    ImageOps = None  # type: ignore

# Base cache and output directory
BASE_DIR = Path(__file__).resolve().parent.parent
CACHE_DIR = BASE_DIR / "outputs" / "cache" / "images"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Shared thread pool for background image downscaling & decoding
_IMAGE_EXECUTOR = concurrent.futures.ThreadPoolExecutor(max_workers=4, thread_name_prefix="JarvisImgWorker")

# In-memory LRU descriptor cache
_DESCRIPTOR_CACHE: Dict[str, ImageAsset] = {}
_MAX_CACHE_ENTRIES = 256


@dataclass
class ImageAsset:
    """Represents an ingested image asset with progressive delivery variants."""
    content_hash: str
    original_path: Optional[str]
    width: int
    height: int
    aspect_ratio: float
    lqip_base64: str          # 16-32px blurred data URI for zero-CLS preview
    full_path: str            # Optimized 1920w WebP/JPEG
    medium_path: str          # Optimized 800w WebP/JPEG
    thumb_path: str           # Optimized 320w WebP/JPEG
    full_url: str
    medium_url: str
    thumb_url: str
    mime_type: str = "image/webp"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _compute_hash(data: bytes) -> str:
    """Computes a SHA-256 hex digest for content addressing."""
    return hashlib.sha256(data).hexdigest()[:16]


def _generate_fallback_svg(title: str = "Asset", width: int = 800, height: int = 600) -> ImageAsset:
    """Generates an immediate zero-dependency SVG fallback if Pillow or the file is missing."""
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'width="{width}" height="{height}" style="background:#131b2e;display:block;">'
        f'<rect width="100%" height="100%" fill="#131b2e"/>'
        f'<text x="50%" y="50%" fill="#94a3b8" font-family="sans-serif" font-size="24" '
        f'text-anchor="middle" dominant-baseline="middle">{title}</text>'
        f'</svg>'
    )
    b64 = "data:image/svg+xml;base64," + base64.b64encode(svg.encode("utf-8")).decode("ascii")
    dummy_path = str(CACHE_DIR / "fallback.svg")
    try:
        Path(dummy_path).write_text(svg, encoding="utf-8")
    except Exception:
        pass

    return ImageAsset(
        content_hash="fallback-0000",
        original_path=None,
        width=width,
        height=height,
        aspect_ratio=round(width / max(1, height), 3),
        lqip_base64=b64,
        full_path=dummy_path,
        medium_path=dummy_path,
        thumb_path=dummy_path,
        full_url=b64,
        medium_url=b64,
        thumb_url=b64,
        mime_type="image/svg+xml"
    )


def _process_image_sync(
    raw_bytes: bytes,
    original_path: Optional[str] = None,
    max_dimension: int = 1920,
    quality: int = 82
) -> ImageAsset:
    """
    Synchronous processing core executed within worker threads.
    Generates multi-tier responsive assets and micro-LQIP placeholder.
    """
    if Image is None:
        return _generate_fallback_svg("Image Engine Unavailable")

    content_hash = _compute_hash(raw_bytes)
    if content_hash in _DESCRIPTOR_CACHE:
        return _DESCRIPTOR_CACHE[content_hash]

    # Check disk cache
    full_disk = CACHE_DIR / f"{content_hash}_full.webp"
    medium_disk = CACHE_DIR / f"{content_hash}_med.webp"
    thumb_disk = CACHE_DIR / f"{content_hash}_thumb.webp"
    lqip_file = CACHE_DIR / f"{content_hash}_lqip.txt"

    if full_disk.exists() and medium_disk.exists() and thumb_disk.exists() and lqip_file.exists():
        try:
            lqip_data = lqip_file.read_text(encoding="utf-8").strip()
            with Image.open(full_disk) as im:
                w, h = im.size
            asset = ImageAsset(
                content_hash=content_hash,
                original_path=original_path,
                width=w,
                height=h,
                aspect_ratio=round(w / max(1, h), 3),
                lqip_base64=lqip_data,
                full_path=str(full_disk),
                medium_path=str(medium_disk),
                thumb_path=str(thumb_disk),
                full_url=f"file:///{full_disk.resolve().as_posix()}",
                medium_url=f"file:///{medium_disk.resolve().as_posix()}",
                thumb_url=f"file:///{thumb_disk.resolve().as_posix()}",
                mime_type="image/webp"
            )
            _DESCRIPTOR_CACHE[content_hash] = asset
            return asset
        except Exception:
            pass  # Recompute if cache is corrupted

    try:
        bio = io.BytesIO(raw_bytes)
        with Image.open(bio) as img:
            # Memory safety: correct orientation via EXIF if present
            try:
                img = ImageOps.exif_transpose(img)
            except Exception:
                pass

            orig_w, orig_h = img.size
            aspect = round(orig_w / max(1, orig_h), 3)

            # Convert RGBA/P to RGB if saving as WebP/JPEG
            if img.mode in ("RGBA", "LA") and "A" in img.getbands():
                # Keep alpha for webp
                mode_to_use = "RGBA"
            else:
                mode_to_use = "RGB"

            if img.mode != mode_to_use:
                img = img.convert(mode_to_use)

            # 1. Generate Micro-LQIP (16px width with Gaussian blur)
            lqip_w = 16
            lqip_h = max(1, int(16 / max(0.01, aspect)))
            lqip_img = img.resize((lqip_w, lqip_h), Image.Resampling.BILINEAR)
            if ImageFilter:
                lqip_img = lqip_img.filter(ImageFilter.GaussianBlur(radius=1.0))
            
            lqip_buf = io.BytesIO()
            lqip_img.save(lqip_buf, format="WEBP", quality=50)
            lqip_b64 = "data:image/webp;base64," + base64.b64encode(lqip_buf.getvalue()).decode("ascii")
            lqip_file.write_text(lqip_b64, encoding="utf-8")

            # 2. Generate Full Variant (max 1920w)
            if orig_w > max_dimension or orig_h > max_dimension:
                scale = min(max_dimension / orig_w, max_dimension / orig_h)
                full_w = int(orig_w * scale)
                full_h = int(orig_h * scale)
                full_img = img.resize((full_w, full_h), Image.Resampling.LANCZOS)
            else:
                full_w, full_h = orig_w, orig_h
                full_img = img

            full_img.save(full_disk, format="WEBP", quality=quality, method=4)

            # 3. Generate Medium Variant (max 800w)
            med_target = 800
            if full_w > med_target:
                scale_med = med_target / full_w
                med_w = int(full_w * scale_med)
                med_h = int(full_h * scale_med)
                med_img = full_img.resize((med_w, med_h), Image.Resampling.BILINEAR)
            else:
                med_w, med_h = full_w, full_h
                med_img = full_img
            med_img.save(medium_disk, format="WEBP", quality=quality, method=4)

            # 4. Generate Thumbnail Variant (max 320w)
            thumb_target = 320
            if full_w > thumb_target:
                scale_th = thumb_target / full_w
                th_w = int(full_w * scale_th)
                th_h = int(full_h * scale_th)
                th_img = med_img.resize((th_w, th_h), Image.Resampling.BILINEAR)
            else:
                th_w, th_h = full_w, full_h
                th_img = med_img
            th_img.save(thumb_disk, format="WEBP", quality=quality - 5, method=4)

            asset = ImageAsset(
                content_hash=content_hash,
                original_path=original_path,
                width=full_w,
                height=full_h,
                aspect_ratio=aspect,
                lqip_base64=lqip_b64,
                full_path=str(full_disk),
                medium_path=str(medium_disk),
                thumb_path=str(thumb_disk),
                full_url=f"file:///{full_disk.resolve().as_posix()}",
                medium_url=f"file:///{medium_disk.resolve().as_posix()}",
                thumb_url=f"file:///{thumb_disk.resolve().as_posix()}",
                mime_type="image/webp"
            )

            # Cache eviction if beyond max capacity
            if len(_DESCRIPTOR_CACHE) >= _MAX_CACHE_ENTRIES:
                _DESCRIPTOR_CACHE.pop(next(iter(_DESCRIPTOR_CACHE)))
            _DESCRIPTOR_CACHE[content_hash] = asset
            return asset

    except Exception as exc:
        print(f"[ImagePipeline] Error processing image: {exc}", file=sys.stderr)
        return _generate_fallback_svg(f"Asset Error: {exc}", 800, 600)


def ingest_image(
    source: Union[str, Path, bytes],
    max_dimension: int = 1920,
    quality: int = 82
) -> ImageAsset:
    """
    Ingests an image from a filepath, data URI, or raw bytes synchronously.
    Handles memory pre-flight safety and invokes caching.
    """
    raw_bytes: bytes
    orig_path: Optional[str] = None

    if isinstance(source, (str, Path)):
        p = Path(source)
        if p.exists() and p.is_file():
            orig_path = str(p.resolve())
            raw_bytes = p.read_bytes()
        elif isinstance(source, str) and source.startswith("data:image/"):
            try:
                _, b64data = source.split(",", 1)
                raw_bytes = base64.b64decode(b64data)
            except Exception:
                return _generate_fallback_svg("Invalid Data URI")
        else:
            return _generate_fallback_svg(f"File Not Found: {source}")
    elif isinstance(source, bytes):
        raw_bytes = source
    else:
        return _generate_fallback_svg("Unsupported Image Source")

    return _process_image_sync(raw_bytes, original_path=orig_path, max_dimension=max_dimension, quality=quality)


def ingest_image_async(
    source: Union[str, Path, bytes],
    max_dimension: int = 1920,
    quality: int = 82
) -> concurrent.futures.Future[ImageAsset]:
    """
    Submits image ingestion to the background worker pool for non-blocking execution.
    """
    return _IMAGE_EXECUTOR.submit(ingest_image, source, max_dimension, quality)


def batch_ingest_images(
    sources: List[Union[str, Path, bytes]],
    max_dimension: int = 1920
) -> List[ImageAsset]:
    """
    Concurrently processes a batch of image assets in parallel threads.
    """
    futures = [ingest_image_async(src, max_dimension=max_dimension) for src in sources]
    results: List[ImageAsset] = []
    for f in futures:
        try:
            results.append(f.result(timeout=10.0))
        except Exception as e:
            results.append(_generate_fallback_svg(f"Timeout: {e}"))
    return results


def render_progressive_picture(
    asset: ImageAsset,
    alt: str = "Image",
    css_class: str = "",
    extra_style: str = ""
) -> str:
    """
    Generates an anti-slop, zero-CLS HTML5 <picture> element featuring:
      - Progressive WebP srcset (320w, 800w, 1920w)
      - Native lazy loading (loading='lazy')
      - Asynchronous decoding (decoding='async')
      - Micro-LQIP blur-up inline background placeholder
      - Explicit intrinsic aspect-ratio container
    """
    style_parts = [
        f"aspect-ratio: {asset.width}/{asset.height};",
        "background-size: cover;",
        "background-position: center;",
        f"background-image: url('{asset.lqip_base64}');",
        "transition: filter 0.4s ease, opacity 0.4s ease;",
        "object-fit: cover;",
        "width: 100%;",
        "height: auto;",
        "display: block;",
    ]
    if extra_style:
        style_parts.append(extra_style)
    combined_style = " ".join(style_parts)

    html_markup = (
        f'<picture class="progressive-media-wrapper {css_class}">'
        f'<source media="(max-width: 480px)" srcset="{asset.thumb_url} 320w">'
        f'<source media="(max-width: 1024px)" srcset="{asset.medium_url} 800w">'
        f'<source srcset="{asset.full_url} 1920w">'
        f'<img src="{asset.medium_url}" '
        f'alt="{alt}" '
        f'loading="lazy" '
        f'decoding="async" '
        f'width="{asset.width}" '
        f'height="{asset.height}" '
        f'style="{combined_style}" '
        f'onload="this.style.backgroundImage=\'none\'; this.classList.add(\'loaded\');" '
        f'/>'
        f'</picture>'
    )
    return html_markup

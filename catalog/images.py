"""Same-origin image cache helpers for categories with slow remote images."""

import hashlib
import os
import shutil
import subprocess
import urllib.request
import uuid
from urllib.parse import urlparse

from flask import abort, redirect, send_file

from .config import (
    INNO_IMAGE_CACHE_DIR,
    INNO_IMAGE_HOST,
    INNO_IMAGE_PATH_PREFIX,
    TOPSPEED_IMAGE_HOST,
    TOPSPEED_IMAGE_PATH_PREFIX,
    TOPSPEED_THUMB_DIR,
)


def is_safe_topspeed_image_url(src):
    parsed = urlparse(src)
    return (
        parsed.scheme == "https"
        and parsed.netloc == TOPSPEED_IMAGE_HOST
        and parsed.path.startswith(TOPSPEED_IMAGE_PATH_PREFIX)
    )


def is_safe_inno_image_url(src):
    parsed = urlparse(src)
    return (
        parsed.scheme == "https"
        and parsed.netloc == INNO_IMAGE_HOST
        and parsed.path.startswith(INNO_IMAGE_PATH_PREFIX)
    )


def image_mimetype_from_path(path):
    ext = os.path.splitext(path)[1].lower()
    return {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
    }.get(ext, "image/jpeg")


def download_inno_image(src, image_path):
    image_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = image_path.parent / f"{uuid.uuid4().hex}.download"

    try:
        req = urllib.request.Request(src, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Referer": "https://www.inno-models.com/",
        })
        with urllib.request.urlopen(req, timeout=30) as response, temp_path.open("wb") as f:
            shutil.copyfileobj(response, f)
        temp_path.replace(image_path)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def build_topspeed_thumbnail(src, thumb_path):
    thumb_path.parent.mkdir(parents=True, exist_ok=True)
    temp_id = uuid.uuid4().hex
    temp_original = thumb_path.parent / f"{temp_id}.download"
    temp_thumb = thumb_path.parent / f"{temp_id}.tmp.jpg"

    try:
        req = urllib.request.Request(src, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        })
        with urllib.request.urlopen(req, timeout=30) as response, temp_original.open("wb") as f:
            shutil.copyfileobj(response, f)

        result = subprocess.run(
            ["/usr/bin/sips", "-Z", "640", str(temp_original), "--out", str(temp_thumb)],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError((result.stderr or result.stdout or "sips failed").strip())
        temp_thumb.replace(thumb_path)
    finally:
        for path in (temp_original, temp_thumb):
            if path.exists():
                path.unlink()


def serve_topspeed_thumb(src):
    if not is_safe_topspeed_image_url(src):
        abort(400)

    cache_key = hashlib.sha256(src.encode("utf-8")).hexdigest()
    thumb_path = TOPSPEED_THUMB_DIR / f"{cache_key}.jpg"

    if not thumb_path.exists():
        try:
            build_topspeed_thumbnail(src, thumb_path)
        except Exception:
            return redirect(src, code=302)

    response = send_file(thumb_path, mimetype="image/jpeg", max_age=60 * 60 * 24 * 30)
    response.headers["Cache-Control"] = "public, max-age=2592000"
    return response


def serve_inno_image(src):
    if not is_safe_inno_image_url(src):
        abort(400)

    parsed = urlparse(src)
    ext = os.path.splitext(parsed.path)[1].lower()
    if ext not in (".jpg", ".jpeg", ".png", ".webp"):
        ext = ".jpg"

    cache_key = hashlib.sha256(src.encode("utf-8")).hexdigest()
    image_path = INNO_IMAGE_CACHE_DIR / f"{cache_key}{ext}"

    if not image_path.exists():
        try:
            download_inno_image(src, image_path)
        except Exception:
            return redirect(src, code=302)

    response = send_file(image_path, mimetype=image_mimetype_from_path(image_path), max_age=60 * 60 * 24 * 30)
    response.headers["Cache-Control"] = "public, max-age=2592000"
    return response

"""Shared paths and constants for the catalog app."""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
HTML_PATH = BASE_DIR / "MINI_GT_产品清单.html"
PRODUCTS_PATH = BASE_DIR / "minigt_products.json"

SUMMARY_PATHS = {
    "ar": BASE_DIR / "ar_update_summary.json",
    "minigt": BASE_DIR / "minigt_update_summary.json",
    "topspeed": BASE_DIR / "topspeed_update_summary.json",
    "spark": BASE_DIR / "spark_update_summary.json",
    "spark64": BASE_DIR / "spark64_update_summary.json",
    "inno": BASE_DIR / "inno_update_summary.json",
    "poprace": BASE_DIR / "poprace_update_summary.json",
}

TOPSPEED_THUMB_DIR = BASE_DIR / "static" / "topspeed_thumb_cache"
TOPSPEED_IMAGE_HOST = "topspeed.tsm-models.com"
TOPSPEED_IMAGE_PATH_PREFIX = "/upload/"

INNO_IMAGE_CACHE_DIR = BASE_DIR / "static" / "inno_image_cache"
INNO_IMAGE_HOST = "www.inno-models.com"
INNO_IMAGE_PATH_PREFIX = "/wp-content/uploads/"

#!/usr/bin/env python3
"""抓取 GreenLight WooCommerce Store API，输出 20 个样本产品。"""

import json
import re
from html import unescape
from pathlib import Path

import requests


BASE_DIR = Path(__file__).resolve().parent
OUTPUT_PATH = BASE_DIR / "greenlight_products_api.json"
SUMMARY_PATH = BASE_DIR / "greenlight_update_summary.json"
SOURCE_URL = "https://www.greenlighttoys.com/wp-json/wc/store/v1/products?per_page=20"
MAX_PRODUCTS = 20
MAX_IMAGES_PER_PRODUCT = 4
HEADERS = {
    "Accept": "application/json,text/plain,*/*",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X) AppleWebKit/537.36",
    "Referer": "https://www.greenlighttoys.com/",
}


def strip_html(value):
    text = re.sub(r"<[^>]+>", " ", str(value or ""))
    return re.sub(r"\s+", " ", unescape(text)).strip()


def clean_images(images):
    cleaned = []
    for image in images or []:
        src = image.get("src") or image.get("thumbnail") if isinstance(image, dict) else image
        if src and src not in cleaned:
            cleaned.append(src)
        if len(cleaned) >= MAX_IMAGES_PER_PRODUCT:
            break
    return cleaned


def status_from_product(product):
    if product.get("is_on_backorder"):
        return "Pre-Order"
    if product.get("is_in_stock") is False:
        return "Sold Out"
    return "Released"


def normalize_product(product, index):
    detail_id = str(product.get("id") or "").strip()
    sku = str(product.get("sku") or "").strip() or f"GL-{detail_id}"
    images = clean_images(product.get("images") or [])
    return {
        "detail_id": detail_id,
        "sku": sku,
        "name": strip_html(product.get("name")) or sku,
        "status": status_from_product(product),
        "image": images[0] if images else "",
        "images": images,
        "greenlight_url": product.get("permalink") or "https://www.greenlighttoys.com/shop/",
        "greenlight_slug": product.get("slug") or "",
        "greenlight_type": product.get("type") or "",
        "greenlight_categories": [item.get("name", "") for item in product.get("categories") or [] if item.get("name")],
        "greenlight_display_order": index,
        "greenlight_short_description": strip_html(product.get("short_description")),
        "greenlight_in_stock": bool(product.get("is_in_stock")),
        "greenlight_on_backorder": bool(product.get("is_on_backorder")),
    }


def main():
    response = requests.get(SOURCE_URL, headers=HEADERS, timeout=(8, 30))
    response.raise_for_status()
    raw_products = response.json()
    if not raw_products:
        raise RuntimeError("GreenLight 接口返回空产品列表，停止更新")
    products = [normalize_product(product, index) for index, product in enumerate(raw_products[:MAX_PRODUCTS], start=1)]
    summary = {
        "source": SOURCE_URL,
        "max_products": MAX_PRODUCTS,
        "max_images_per_product": MAX_IMAGES_PER_PRODUCT,
        "fetched_count": len(products),
        "image_success_count": sum(1 for product in products if product.get("images")),
        "image_failed_count": sum(1 for product in products if not product.get("images")),
        "api_total_count": int(response.headers.get("X-WP-Total") or 0),
        "page_count": int(response.headers.get("X-WP-TotalPages") or 0),
    }
    OUTPUT_PATH.write_text(json.dumps(products, ensure_ascii=False, indent=2), encoding="utf-8")
    SUMMARY_PATH.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ GreenLight 抓取完成：{len(products)} 个，接口总数 {summary['api_total_count']} 个")


if __name__ == "__main__":
    main()

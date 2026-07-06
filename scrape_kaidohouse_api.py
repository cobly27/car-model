#!/usr/bin/env python3
"""抓取 Kaido House Shopify diecast 集合，输出车模产品。"""

import json
import time
import urllib.request
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
OUTPUT_PATH = BASE_DIR / "kaidohouse_products_api.json"
SUMMARY_PATH = BASE_DIR / "kaidohouse_update_summary.json"
COLLECTION_URL = "https://www.kaidohouse.com/collections/diecast/products.json"
PRODUCT_BASE_URL = "https://www.kaidohouse.com/products/"
LIMIT = 250
MAX_IMAGES_PER_PRODUCT = 4


def fetch_json(url):
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0",
        },
    )
    with urllib.request.urlopen(request, timeout=45) as response:
        return json.load(response)


def clean_images(images):
    cleaned = []
    for image in images or []:
        src = image.get("src") if isinstance(image, dict) else image
        if src and src not in cleaned:
            cleaned.append(src)
        if len(cleaned) >= MAX_IMAGES_PER_PRODUCT:
            break
    return cleaned


def status_from_product(product):
    marker_text = f"{product.get('title') or ''} {' '.join(product.get('tags') or [])}".lower()
    if any(marker in marker_text for marker in ("pre-order", "preorder", "pre order", "coming soon")):
        return "Pre-Order"
    variants = product.get("variants") or []
    if variants and not any(bool(variant.get("available")) for variant in variants):
        return "Sold Out"
    return "Released"


def first_sku(product):
    for variant in product.get("variants") or []:
        sku = str(variant.get("sku") or "").strip()
        if sku:
            return sku
    return str(product.get("handle") or product.get("id") or "").strip()


def primary_variant(product):
    variants = product.get("variants") or []
    return variants[0] if variants else {}


def normalize_product(product, index):
    detail_id = str(product.get("id") or "").strip()
    handle = str(product.get("handle") or "").strip()
    images = clean_images(product.get("images") or [])
    variant = primary_variant(product)
    variants = product.get("variants") or []
    return {
        "detail_id": detail_id,
        "sku": first_sku(product),
        "name": str(product.get("title") or first_sku(product)).strip(),
        "status": status_from_product(product),
        "image": images[0] if images else "",
        "images": images,
        "kaidohouse_url": f"{PRODUCT_BASE_URL}{handle}" if handle else "https://www.kaidohouse.com/collections/diecast",
        "kaidohouse_handle": handle,
        "kaidohouse_vendor": str(product.get("vendor") or "").strip(),
        "kaidohouse_product_type": str(product.get("product_type") or "").strip(),
        "kaidohouse_tags": product.get("tags") or [],
        "kaidohouse_display_order": index,
        "kaidohouse_published_at": product.get("published_at") or "",
        "kaidohouse_updated_at": product.get("updated_at") or "",
        "kaidohouse_price": str(variant.get("price") or "").strip(),
        "kaidohouse_available": any(bool(item.get("available")) for item in variants),
        "kaidohouse_collection": "diecast",
    }


def fetch_all_products():
    products = []
    page = 1
    while True:
        url = f"{COLLECTION_URL}?limit={LIMIT}&page={page}"
        page_products = fetch_json(url).get("products") or []
        if not page_products:
            break
        products.extend(page_products)
        print(f"Kaido House diecast 第 {page} 页：{len(page_products)} 个")
        if len(page_products) < LIMIT:
            break
        page += 1
        time.sleep(0.3)
    return products, page


def main():
    raw_products, page_count = fetch_all_products()
    products = [normalize_product(product, index) for index, product in enumerate(raw_products, start=1)]
    products = [product for product in products if product.get("detail_id")]
    if not products:
        raise RuntimeError("Kaido House diecast 接口返回空产品列表，停止更新")

    summary = {
        "source": COLLECTION_URL,
        "collection": "diecast",
        "page_count": page_count,
        "max_images_per_product": MAX_IMAGES_PER_PRODUCT,
        "fetched_count": len(products),
        "image_success_count": sum(1 for product in products if product.get("images")),
        "image_failed_count": sum(1 for product in products if not product.get("images")),
    }
    OUTPUT_PATH.write_text(json.dumps(products, ensure_ascii=False, indent=2), encoding="utf-8")
    SUMMARY_PATH.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ Kaido House 抓取完成：{len(products)} 个 diecast 车模")


if __name__ == "__main__":
    main()

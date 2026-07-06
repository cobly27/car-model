#!/usr/bin/env python3
"""抓取 Tarmac Works Shopify 产品接口，输出 20 个样本产品。"""

import json
import urllib.request
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
OUTPUT_PATH = BASE_DIR / "tarmacworks_products_api.json"
SUMMARY_PATH = BASE_DIR / "tarmacworks_update_summary.json"
SOURCE_URL = "https://www.tarmacworks.com/products.json?limit=20"
PRODUCT_BASE_URL = "https://www.tarmacworks.com/products/"
MAX_PRODUCTS = 20
MAX_IMAGES_PER_PRODUCT = 4


def fetch_json(url):
    request = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "Mozilla/5.0"})
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


def normalize_product(product, index):
    detail_id = str(product.get("id") or "").strip()
    handle = str(product.get("handle") or "").strip()
    images = clean_images(product.get("images") or [])
    variants = product.get("variants") or []
    primary_variant = variants[0] if variants else {}
    return {
        "detail_id": detail_id,
        "sku": first_sku(product),
        "name": str(product.get("title") or first_sku(product)).strip(),
        "status": status_from_product(product),
        "image": images[0] if images else "",
        "images": images,
        "tarmacworks_url": f"{PRODUCT_BASE_URL}{handle}" if handle else "https://www.tarmacworks.com/collections/all",
        "tarmacworks_handle": handle,
        "tarmacworks_vendor": str(product.get("vendor") or "").strip(),
        "tarmacworks_product_type": str(product.get("product_type") or "").strip(),
        "tarmacworks_tags": product.get("tags") or [],
        "tarmacworks_display_order": index,
        "tarmacworks_published_at": product.get("published_at") or "",
        "tarmacworks_updated_at": product.get("updated_at") or "",
        "tarmacworks_price": str(primary_variant.get("price") or "").strip(),
        "tarmacworks_available": any(bool(variant.get("available")) for variant in variants),
    }


def main():
    raw_products = fetch_json(SOURCE_URL).get("products") or []
    products = [normalize_product(product, index) for index, product in enumerate(raw_products[:MAX_PRODUCTS], start=1)]
    products = [product for product in products if product.get("detail_id")]
    if not products:
        raise RuntimeError("Tarmac Works 接口返回空产品列表，停止更新")
    summary = {
        "source": SOURCE_URL,
        "max_products": MAX_PRODUCTS,
        "max_images_per_product": MAX_IMAGES_PER_PRODUCT,
        "fetched_count": len(products),
        "image_success_count": sum(1 for product in products if product.get("images")),
        "image_failed_count": sum(1 for product in products if not product.get("images")),
    }
    OUTPUT_PATH.write_text(json.dumps(products, ensure_ascii=False, indent=2), encoding="utf-8")
    SUMMARY_PATH.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ Tarmac Works 抓取完成：{len(products)} 个")


if __name__ == "__main__":
    main()

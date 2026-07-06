#!/usr/bin/env python3
"""将 GreenLight Store API 结果合并进 minigt_products.json。"""

from pathlib import Path

from catalog.merge import load_json, merge_incremental_products, merge_result_summary, save_json
from catalog.products import normalize_catalog_product, normalized_images


BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "minigt_products.json"
API_PRODUCTS_PATH = BASE_DIR / "greenlight_products_api.json"
SUMMARY_PATH = BASE_DIR / "greenlight_update_summary.json"
CATEGORY_ID = "greenlight"
CATEGORY_NAME = "GreenLight"
MAX_IMAGES_PER_PRODUCT = 4
CHANGED_KEYS = (
    "detail_id", "sku", "name", "status", "image", "images",
    "greenlight_url", "greenlight_slug", "greenlight_type", "greenlight_categories",
    "greenlight_display_order", "greenlight_short_description", "greenlight_in_stock", "greenlight_on_backorder",
)


def product_key(product):
    key = product.get("detail_id") or product.get("sku")
    return str(key).strip() if key else None


def normalize_product(product):
    normalized = dict(product)
    normalized["detail_id"] = str(normalized.get("detail_id") or normalized.get("sku") or "").strip()
    normalized["sku"] = str(normalized.get("sku") or f"GL-{normalized['detail_id']}").strip()
    normalized["images"] = normalized_images(normalized, MAX_IMAGES_PER_PRODUCT)
    return normalize_catalog_product(normalized, key_label="GreenLight 产品", max_images=MAX_IMAGES_PER_PRODUCT, stringify_key=True)


def merge_product(existing, incoming):
    return {**existing, **incoming}


def sort_product(product):
    return (int(product.get("greenlight_display_order") or 999999), str(product.get("sku") or ""))


def main():
    data = load_json(DATA_PATH)
    incoming = load_json(API_PRODUCTS_PATH)
    if not incoming:
        raise RuntimeError("greenlight_products_api.json 为空，停止合并")
    result = merge_incremental_products(
        data=data,
        incoming_products=incoming,
        category_id=CATEGORY_ID,
        category_name=CATEGORY_NAME,
        key_fn=product_key,
        normalize_fn=normalize_product,
        merge_fn=merge_product,
        changed_keys=CHANGED_KEYS,
        sort_key=sort_product,
    )
    save_json(DATA_PATH, data)
    scrape_summary = load_json(SUMMARY_PATH, {})
    save_json(SUMMARY_PATH, {
        **scrape_summary,
        **merge_result_summary(
            result,
            original_count_key="original_greenlight_count",
            final_count_key="final_greenlight_count",
            extra={"max_images_per_product": MAX_IMAGES_PER_PRODUCT},
        ),
    })
    print(f"✅ GreenLight 合并完成：新增 {result['added_count']}，更新 {result['updated_count']}，未变 {result['unchanged_count']}")


if __name__ == "__main__":
    main()

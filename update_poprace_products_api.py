#!/usr/bin/env python3
"""将 POP RACE OCR 抓取结果合并进 minigt_products.json。"""

from pathlib import Path

from catalog.merge import load_json, merge_incremental_products, merge_result_summary, save_json
from catalog.products import normalize_catalog_product, normalized_images

BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "minigt_products.json"
POPRACE_PATH = BASE_DIR / "poprace_products_api.json"
SUMMARY_PATH = BASE_DIR / "poprace_update_summary.json"
CATEGORY_ID = "poprace"
CATEGORY_NAME = "POP RACE"
MAX_IMAGES_PER_PRODUCT = 4
CHANGED_KEYS = (
    "detail_id",
    "sku",
    "name",
    "status",
    "image",
    "images",
    "poprace_display_order",
    "poprace_ocr_name",
    "poprace_picture_ids",
    "poprace_source_image_urls",
    "poprace_source_url",
    "poprace_title",
)


def product_key(product):
    key = product.get("detail_id") or product.get("sku")
    return str(key) if key else None


def normalize_product(product):
    sku = str(product.get("sku") or product.get("detail_id") or "").strip()
    detail_id = str(product.get("detail_id") or sku).strip()
    normalized = {
        **product,
        "detail_id": detail_id,
        "sku": sku or detail_id,
    }
    normalized["images"] = normalized_images(normalized, MAX_IMAGES_PER_PRODUCT)
    return normalize_catalog_product(
        normalized,
        key_label="POP RACE 产品",
        max_images=MAX_IMAGES_PER_PRODUCT,
        stringify_key=True,
    )


def merge_product(existing, incoming):
    return {**existing, **incoming}


def sort_product(product):
    return (
        int(product.get("poprace_display_order") or 999999),
        str(product.get("sku") or ""),
    )


def main():
    data = load_json(DATA_PATH)
    incoming = load_json(POPRACE_PATH)
    if not incoming:
        raise RuntimeError("poprace_products_api.json 为空，停止合并")

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
    summary = {
        **scrape_summary,
        **merge_result_summary(
            result,
            original_count_key="original_poprace_count",
            final_count_key="final_poprace_count",
            extra={"max_images_per_product": MAX_IMAGES_PER_PRODUCT},
        ),
    }
    save_json(SUMMARY_PATH, summary)
    print(
        f"✅ POP RACE 合并完成：新增 {result['added_count']}，更新 {result['updated_count']}，"
        f"未变 {result['unchanged_count']}，最终 {len(result['updated_products'])}，总数 {result['total_products']}"
    )


if __name__ == "__main__":
    main()

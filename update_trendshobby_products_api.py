#!/usr/bin/env python3
"""将 Trends Hobby / TH 渠道聚合结果合并进 minigt_products.json。"""

from pathlib import Path

from catalog.merge import load_json, merge_incremental_products, merge_result_summary, save_json
from catalog.products import normalize_catalog_product, normalized_images


BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "minigt_products.json"
API_PRODUCTS_PATH = BASE_DIR / "trendshobby_products_api.json"
SUMMARY_PATH = BASE_DIR / "trendshobby_update_summary.json"
CATEGORY_ID = "trendshobby"
CATEGORY_NAME = "TH / Trends Hobby"
MAX_IMAGES_PER_PRODUCT = 4
CHANGED_KEYS = (
    "detail_id",
    "sku",
    "name",
    "status",
    "image",
    "images",
    "trendshobby_url",
    "trendshobby_handle",
    "trendshobby_sources",
    "trendshobby_source_names",
    "trendshobby_model_code",
    "trendshobby_display_order",
    "trendshobby_price",
    "trendshobby_available",
)


def product_key(product):
    key = product.get("detail_id") or product.get("sku")
    return str(key).strip() if key else None


def normalize_product(product):
    normalized = dict(product)
    normalized["detail_id"] = str(normalized.get("detail_id") or normalized.get("sku") or "").strip()
    normalized["sku"] = str(normalized.get("sku") or normalized["detail_id"]).strip()
    normalized["images"] = normalized_images(normalized, MAX_IMAGES_PER_PRODUCT)
    return normalize_catalog_product(
        normalized,
        key_label="Trends Hobby 产品",
        max_images=MAX_IMAGES_PER_PRODUCT,
        stringify_key=True,
    )


def merge_product(existing, incoming):
    return {**existing, **incoming}


def sort_product(product):
    return (
        int(product.get("trendshobby_display_order") or 999999),
        str(product.get("sku") or ""),
    )


def main():
    data = load_json(DATA_PATH)
    incoming = load_json(API_PRODUCTS_PATH)
    if not incoming:
        raise RuntimeError("trendshobby_products_api.json 为空，停止合并")

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
            original_count_key="original_trendshobby_count",
            final_count_key="final_trendshobby_count",
            extra={"max_images_per_product": MAX_IMAGES_PER_PRODUCT},
        ),
    }
    save_json(SUMMARY_PATH, summary)
    print(
        f"✅ Trends Hobby 合并完成：新增 {result['added_count']}，更新 {result['updated_count']}，"
        f"未变 {result['unchanged_count']}，最终 {len(result['updated_products'])}，总数 {result['total_products']}"
    )


if __name__ == "__main__":
    main()

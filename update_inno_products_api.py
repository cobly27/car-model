#!/usr/bin/env python3
"""将 INNO 1:64 官网产品增量合并进 minigt_products.json。"""

import sys
from pathlib import Path

from catalog.merge import load_json, merge_incremental_products, merge_result_summary, save_json
from catalog.products import choose_merged_images, normalize_catalog_product

BASE_DIR = Path(__file__).resolve().parent
PRODUCTS_PATH = BASE_DIR / "minigt_products.json"
API_PRODUCTS_PATH = BASE_DIR / "inno_products_api.json"
SUMMARY_PATH = BASE_DIR / "inno_update_summary.json"
CATEGORY_ID = "inno"
CATEGORY_NAME = "INNO 1:64"
MAX_IMAGES_PER_PRODUCT = 3
CHANGED_KEYS = (
    "name",
    "sku",
    "status",
    "image",
    "images",
    "inno_url",
    "inno_scale",
    "inno_brand",
    "inno_status",
    "inno_type",
)


def product_key(product):
    return product.get("detail_id")


def normalize_product(product):
    return normalize_catalog_product(
        product,
        key_label="INNO 产品",
        sku_prefix="INNO",
        max_images=MAX_IMAGES_PER_PRODUCT,
    )


def merge_product(existing, incoming):
    merged = dict(existing)
    image, images = choose_merged_images(
        existing,
        incoming,
        limit=MAX_IMAGES_PER_PRODUCT,
    )

    merged.update({
        "detail_id": incoming.get("detail_id", existing.get("detail_id")),
        "name": incoming.get("name", existing.get("name", "")),
        "sku": incoming.get("sku", existing.get("sku", "")),
        "status": incoming.get("status") or existing.get("status", "Released"),
        "image": image,
        "images": images,
        "inno_url": incoming.get("inno_url", existing.get("inno_url", "")),
        "inno_scale": incoming.get("inno_scale", existing.get("inno_scale", "1/64")),
        "inno_brand": incoming.get("inno_brand", existing.get("inno_brand", "")),
        "inno_status": incoming.get("inno_status", existing.get("inno_status", "")),
        "inno_type": incoming.get("inno_type", existing.get("inno_type", "")),
    })
    return merged


def main():
    try:
        data = load_json(PRODUCTS_PATH)
        api_products = load_json(API_PRODUCTS_PATH)
        if not isinstance(api_products, list) or not api_products:
            raise RuntimeError("INNO 产品数据为空或格式错误")

        result = merge_incremental_products(
            data=data,
            incoming_products=api_products,
            category_id=CATEGORY_ID,
            category_name=CATEGORY_NAME,
            key_fn=product_key,
            normalize_fn=normalize_product,
            merge_fn=merge_product,
            changed_keys=CHANGED_KEYS,
            sort_key=lambda item: item.get("detail_id", 0),
            reverse=True,
        )

        save_json(PRODUCTS_PATH, data)

        scrape_summary = load_json(SUMMARY_PATH, {})
        summary = {
            **scrape_summary,
            **merge_result_summary(
                result,
                original_count_key="original_inno_count",
                final_count_key="final_inno_count",
                extra={"max_images_per_product": MAX_IMAGES_PER_PRODUCT},
            ),
        }
        save_json(SUMMARY_PATH, summary)

        print("INNO 1:64 产品清单合并完成")
        print(f"官网抓取：{result['fetched_count']} 个")
        print(f"新增：{result['added_count']}，更新：{result['updated_count']}，未变：{result['unchanged_count']}")
        print(f"官网未返回但已保留：{result['preserved_count']}")
        print(f"最终 INNO 1:64 数量：{len(result['updated_products'])}")
        print(f"总产品数：{result['total_products']}")
    except Exception as exc:
        print(f"错误：{exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()

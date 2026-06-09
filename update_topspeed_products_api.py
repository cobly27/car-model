#!/usr/bin/env python3
"""将 TOP SPEED 官网产品增量合并进 minigt_products.json。"""

import sys
from pathlib import Path

from catalog.merge import load_json, merge_incremental_products, merge_result_summary, save_json
from catalog.products import choose_merged_images, normalize_catalog_product

BASE_DIR = Path(__file__).resolve().parent
PRODUCTS_PATH = BASE_DIR / "minigt_products.json"
API_PRODUCTS_PATH = BASE_DIR / "topspeed_products_api.json"
SUMMARY_PATH = BASE_DIR / "topspeed_update_summary.json"
CATEGORY_ID = "topspeed"
CATEGORY_NAME = "TOP SPEED"
MAX_IMAGES_PER_PRODUCT = 4
CHANGED_KEYS = ("name", "sku", "status", "image", "images", "topspeed_categories")


def product_key(product):
    return product.get("detail_id")


def normalize_product(product):
    return normalize_catalog_product(
        product,
        key_label="TOP SPEED 产品",
        sku_prefix="TOPSPEED",
        max_images=MAX_IMAGES_PER_PRODUCT,
    )


def merge_product(existing, incoming):
    merged = dict(existing)
    image, images = choose_merged_images(
        existing,
        incoming,
        limit=MAX_IMAGES_PER_PRODUCT,
        min_incoming_images=2,
    )

    merged.update({
        "detail_id": incoming.get("detail_id", existing.get("detail_id")),
        "name": incoming.get("name", existing.get("name", "")),
        "sku": incoming.get("sku", existing.get("sku", "")),
        "status": incoming.get("status") or existing.get("status", "Released"),
        "image": image,
        "images": images,
        "topspeed_categories": incoming.get("topspeed_categories", existing.get("topspeed_categories", [])),
    })
    return merged


def main():
    try:
        data = load_json(PRODUCTS_PATH)
        api_products = load_json(API_PRODUCTS_PATH)
        if not isinstance(api_products, list) or not api_products:
            raise RuntimeError("TOP SPEED 产品数据为空或格式错误")

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
                original_count_key="original_topspeed_count",
                final_count_key="final_topspeed_count",
                extra={"max_images_per_product": MAX_IMAGES_PER_PRODUCT},
            ),
        }
        save_json(SUMMARY_PATH, summary)

        print("TOP SPEED 产品清单合并完成")
        print(f"官网抓取：{result['fetched_count']} 个")
        print(f"新增：{result['added_count']}，更新：{result['updated_count']}，未变：{result['unchanged_count']}")
        print(f"官网未返回但已保留：{result['preserved_count']}")
        print(f"最终 TOP SPEED 数量：{len(result['updated_products'])}")
        print(f"总产品数：{result['total_products']}")
    except Exception as exc:
        print(f"错误：{exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()

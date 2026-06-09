#!/usr/bin/env python3
"""将 MINI GT 官网列表增量合并进 minigt_products.json。"""

import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
PRODUCTS_PATH = BASE_DIR / "minigt_products.json"
API_PRODUCTS_PATH = BASE_DIR / "minigt_products_api.json"
DETAIL_TARGETS_PATH = BASE_DIR / "minigt_detail_targets.json"
SUMMARY_PATH = BASE_DIR / "minigt_update_summary.json"


def load_json(path, default=None):
    if not path.exists():
        if default is not None:
            return default
        raise FileNotFoundError(path.name)
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def clean_images(images):
    cleaned = []
    for image in images or []:
        if image and image not in cleaned:
            cleaned.append(image)
    return cleaned


def get_category(data, category_id):
    for idx, category in enumerate(data.get("categories", [])):
        if category.get("id") == category_id:
            return idx, category
    return -1, None


def update_total_products(data):
    total = sum(len(category.get("products", [])) for category in data.get("categories", []))
    data.setdefault("meta", {})["total_products"] = total
    return total


def needs_detail_images(product, changed):
    images = clean_images(product.get("images", []))
    return changed or len(images) == 0


def merge_product(existing, incoming):
    merged = dict(existing)
    old_images = clean_images(existing.get("images", []))
    incoming_images = clean_images(incoming.get("images", []))
    image = incoming.get("image") or existing.get("image", "")

    if old_images:
        images = old_images
    elif incoming_images:
        images = incoming_images
    elif image:
        images = [image]
    else:
        images = []

    merged.update({
        "detail_id": incoming.get("detail_id", existing.get("detail_id")),
        "name": incoming.get("name", existing.get("name", "")),
        "sku": incoming.get("sku", existing.get("sku", "")),
        "status": incoming.get("status") or existing.get("status", ""),
        "image": image,
        "images": images,
    })
    return merged


def main():
    try:
        data = load_json(PRODUCTS_PATH)
        api_products = load_json(API_PRODUCTS_PATH)
        if not isinstance(api_products, list) or not api_products:
            raise RuntimeError("MINI GT API 产品数据为空或格式错误")

        category_idx, mini_category = get_category(data, "mini-gt")
        if category_idx == -1:
            raise RuntimeError("未找到 MINI GT 分类")

        existing_products = mini_category.get("products", [])
        existing_by_detail = {
            product.get("detail_id"): product
            for product in existing_products
            if product.get("detail_id") is not None
        }
        existing_by_sku = {
            product.get("sku"): product
            for product in existing_products
            if product.get("sku")
        }

        updated_products = []
        detail_targets = []
        fetched_detail_ids = set()
        fetched_skus = set()
        added_count = 0
        updated_count = 0
        unchanged_count = 0
        duplicate_count = 0

        for incoming in api_products:
            detail_id = incoming.get("detail_id")
            sku = incoming.get("sku")
            if detail_id is None or not sku:
                raise RuntimeError(f"官网产品缺少 detail_id 或 sku：{incoming}")

            if detail_id in fetched_detail_ids or sku in fetched_skus:
                duplicate_count += 1
                continue
            fetched_detail_ids.add(detail_id)
            fetched_skus.add(sku)

            existing = existing_by_detail.get(detail_id) or existing_by_sku.get(sku)
            if existing:
                merged = merge_product(existing, incoming)
                changed = any(
                    merged.get(key) != existing.get(key)
                    for key in ("detail_id", "name", "sku", "status", "image")
                )
                if changed:
                    updated_count += 1
                else:
                    unchanged_count += 1
                if needs_detail_images(merged, changed):
                    detail_targets.append(merged)
                updated_products.append(merged)
            else:
                new_product = dict(incoming)
                new_product["images"] = clean_images(new_product.get("images", []))
                if new_product.get("image") and not new_product["images"]:
                    new_product["images"] = [new_product["image"]]
                added_count += 1
                detail_targets.append(new_product)
                updated_products.append(new_product)

        preserved_products = [
            product for product in existing_products
            if product.get("detail_id") not in fetched_detail_ids and product.get("sku") not in fetched_skus
        ]
        preserved_count = len(preserved_products)
        updated_products.extend(preserved_products)

        data["categories"][category_idx]["products"] = updated_products
        total_products = update_total_products(data)

        save_json(PRODUCTS_PATH, data)
        save_json(DETAIL_TARGETS_PATH, detail_targets)

        scrape_summary = load_json(SUMMARY_PATH, {})
        summary = {
            **scrape_summary,
            "fetched_count": len(fetched_detail_ids),
            "original_minigt_count": len(existing_products),
            "added_count": added_count,
            "updated_count": updated_count,
            "unchanged_count": unchanged_count,
            "preserved_count": preserved_count,
            "duplicate_count": duplicate_count,
            "detail_target_count": len(detail_targets),
            "final_minigt_count": len(updated_products),
            "total_products": total_products,
        }
        save_json(SUMMARY_PATH, summary)

        print("MINI GT 产品清单合并完成")
        print(f"官网抓取：{summary['fetched_count']} 个")
        print(f"新增：{added_count}，更新：{updated_count}，未变：{unchanged_count}")
        print(f"官网未返回但已保留：{preserved_count}")
        print(f"详情图待抓取：{len(detail_targets)} 个")
        print(f"最终 MINI GT 数量：{len(updated_products)}")
    except Exception as exc:
        print(f"错误：{exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""将 MINI GT 详情图抓取结果写回产品数据。"""

import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
PRODUCTS_PATH = BASE_DIR / "minigt_products.json"
DETAIL_PATH = BASE_DIR / "minigt_products_detail.json"
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


def update_total_products(data):
    total = sum(len(category.get("products", [])) for category in data.get("categories", []))
    data.setdefault("meta", {})["total_products"] = total
    return total


def main():
    try:
        data = load_json(PRODUCTS_PATH)
        detail_data = load_json(DETAIL_PATH)
        summary = load_json(SUMMARY_PATH, {})

        detail_products = detail_data.get("products", [])
        failed_ids = set(detail_data.get("failed_ids", []))
        detail_dict = {
            product.get("detail_id"): product
            for product in detail_products
            if product.get("detail_id") is not None
        }

        mini_category = None
        for category in data.get("categories", []):
            if category.get("id") == "mini-gt":
                mini_category = category
                break
        if mini_category is None:
            raise RuntimeError("未找到 MINI GT 分类")

        updated_count = 0
        skipped_failed_count = 0
        missing_detail_count = 0

        for product in mini_category.get("products", []):
            detail_id = product.get("detail_id")
            if detail_id in failed_ids:
                skipped_failed_count += 1
                continue
            detail = detail_dict.get(detail_id)
            if detail:
                product["image"] = detail.get("image", product.get("image", ""))
                product["images"] = detail.get("images", product.get("images", []))
                updated_count += 1

        target_count = summary.get("detail_target_count", detail_data.get("total", 0))
        missing_detail_count = max(0, target_count - updated_count - skipped_failed_count)

        total_products = update_total_products(data)
        save_json(PRODUCTS_PATH, data)

        summary.update({
            "detail_total": detail_data.get("total", len(detail_products)),
            "detail_success_count": detail_data.get("success_count", 0),
            "detail_failed_count": detail_data.get("failed_count", 0),
            "images_updated_count": updated_count,
            "images_skipped_failed_count": skipped_failed_count,
            "missing_detail_count": missing_detail_count,
            "final_minigt_count": len(mini_category.get("products", [])),
            "total_products": total_products,
        })
        save_json(SUMMARY_PATH, summary)

        print("MINI GT 产品图片数据更新完成")
        print(f"已写回详情图：{updated_count} 个")
        print(f"详情图失败保留原图：{skipped_failed_count} 个")
        print(f"缺少详情图数据：{missing_detail_count} 个")
    except Exception as exc:
        print(f"错误：{exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()

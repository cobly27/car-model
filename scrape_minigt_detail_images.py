#!/usr/bin/env python3
"""抓取 MINI GT 新增/变更产品的详情图。"""

import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from scrape_minigt_images import scrape_detail

BASE_DIR = Path(__file__).resolve().parent
TARGETS_PATH = BASE_DIR / "minigt_detail_targets.json"
OUTPUT_PATH = BASE_DIR / "minigt_products_detail.json"
MAX_WORKERS = 8


def save_result(products, failed_ids):
    failed_ids = list(dict.fromkeys(failed_ids))
    success_count = len([
        product for product in products
        if product.get("detail_id") not in failed_ids and product.get("images")
    ])
    with OUTPUT_PATH.open("w", encoding="utf-8") as f:
        json.dump({
            "products": products,
            "failed_ids": failed_ids,
            "total": len(products),
            "success_count": success_count,
            "failed_count": len(failed_ids),
        }, f, ensure_ascii=False, indent=2)


def main():
    try:
        if not TARGETS_PATH.exists():
            raise RuntimeError("未找到 minigt_detail_targets.json")

        with TARGETS_PATH.open("r", encoding="utf-8") as f:
            targets = json.load(f)

        if not isinstance(targets, list):
            raise RuntimeError("详情图目标文件格式错误")

        if not targets:
            save_result([], [])
            print("没有需要抓取详情图的 MINI GT 产品")
            return

        print(f"开始抓取 {len(targets)} 个 MINI GT 产品详情图...")
        start = time.time()
        products = []
        failed_ids = []

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {executor.submit(scrape_detail, product): product for product in targets}
            for index, future in enumerate(as_completed(futures), 1):
                product, images = future.result()
                product = dict(product)
                if images:
                    product["images"] = images
                    product["image"] = images[0]
                    print(f"  ✓ {product.get('sku', '')}: {len(images)} 图")
                else:
                    product["images"] = product.get("images") or ([product.get("image")] if product.get("image") else [])
                    failed_ids.append(product.get("detail_id"))
                    print(f"  ⚠️ {product.get('sku', '')}: 详情图抓取失败，保留原图")
                products.append(product)

                if index % 50 == 0 or index == len(targets):
                    print(f"  进度：{index}/{len(targets)}，耗时 {time.time() - start:.0f}s")

        products.sort(key=lambda item: item.get("detail_id", 0), reverse=True)
        save_result(products, failed_ids)

        print("MINI GT 详情图抓取完成")
        print(f"成功：{len(products) - len(failed_ids)}，失败：{len(failed_ids)}")
    except Exception as exc:
        print(f"错误：{exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()

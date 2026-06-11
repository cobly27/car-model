#!/usr/bin/env python3
"""抓取 GCD 官网产品文章分类，输出当前 GCD 产品清单。"""

import json
from pathlib import Path

from catalog.wordpress_category import build_wordpress_category_products


BASE_DIR = Path(__file__).resolve().parent
OUTPUT_PATH = BASE_DIR / "gcd_products_api.json"
SUMMARY_PATH = BASE_DIR / "gcd_update_summary.json"
GCD_CATEGORY_ID = 36
SOURCE_URL = "https://www.gcd-models.com/category/products/gcd/"
MAX_IMAGES_PER_PRODUCT = 4


def main():
    products, summary = build_wordpress_category_products(
        category_id=GCD_CATEGORY_ID,
        source_url=SOURCE_URL,
        field_prefix="gcd",
        max_images=MAX_IMAGES_PER_PRODUCT,
    )
    if not products:
        raise RuntimeError("GCD 抓取结果为空，停止更新")

    with OUTPUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(products, f, ensure_ascii=False, indent=2)
    with SUMMARY_PATH.open("w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f"✅ GCD 抓取完成：{len(products)} 个，分页 {summary['page_count']} 页")


if __name__ == "__main__":
    main()

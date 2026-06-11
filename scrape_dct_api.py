#!/usr/bin/env python3
"""抓取 GCD 官网 DCT 产品文章分类，输出当前 DCT 产品清单。"""

import json
from pathlib import Path

from catalog.wordpress_category import build_wordpress_category_products


BASE_DIR = Path(__file__).resolve().parent
OUTPUT_PATH = BASE_DIR / "dct_products_api.json"
SUMMARY_PATH = BASE_DIR / "dct_update_summary.json"
DCT_CATEGORY_ID = 37
SOURCE_URL = "https://www.gcd-models.com/category/products/dct/"
MAX_IMAGES_PER_PRODUCT = 4


def main():
    products, summary = build_wordpress_category_products(
        category_id=DCT_CATEGORY_ID,
        source_url=SOURCE_URL,
        field_prefix="dct",
        max_images=MAX_IMAGES_PER_PRODUCT,
    )
    if not products:
        raise RuntimeError("DCT 抓取结果为空，停止更新")

    with OUTPUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(products, f, ensure_ascii=False, indent=2)
    with SUMMARY_PATH.open("w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f"✅ DCT 抓取完成：{len(products)} 个，分页 {summary['page_count']} 页")


if __name__ == "__main__":
    main()

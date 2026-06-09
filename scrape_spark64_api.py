#!/usr/bin/env python3
"""抓取 Spark 1:64 MODEL 产品，复用 SPARK 1:43 的 API 逻辑。"""

import json
import sys

import scrape_spark_api as spark


spark.SCALE_NAME = "1:64"
spark.SCALE_FILTER = 'scale_name = "1:64"'
spark.OUTPUT_PATH = spark.BASE_DIR / "spark64_products_api.json"
spark.SUMMARY_PATH = spark.BASE_DIR / "spark64_update_summary.json"
spark.VALIDATE_IMAGE_URLS = True


def main():
    try:
        products, summary = spark.fetch_products()
        with spark.OUTPUT_PATH.open("w", encoding="utf-8") as f:
            json.dump(products, f, ensure_ascii=False, indent=2)

        with spark.SUMMARY_PATH.open("w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)

        print("Spark 1:64 产品抓取完成")
        print(f"官网估算：{summary['expected_total']} 个，实际去重：{summary['fetched_count']} 个")
        print(f"查询桶：{summary['query_bucket_count']} 个，跳过缺字段：{summary['skipped_count']} 个")
        print(f"图片 URL 成功：{summary['image_success_count']} 个，缺失：{summary['image_failed_count']} 个")
        print(f"已保存到：{spark.OUTPUT_PATH.name}")
    except Exception as exc:
        print(f"错误：{exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()

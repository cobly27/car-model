#!/usr/bin/env python3
"""将 Spark 1:64 产品增量合并进 minigt_products.json。"""

import update_spark_products_api as spark_update


spark_update.API_PRODUCTS_PATH = spark_update.BASE_DIR / "spark64_products_api.json"
spark_update.SUMMARY_PATH = spark_update.BASE_DIR / "spark64_update_summary.json"
spark_update.IMAGE_CACHE_PATH = spark_update.BASE_DIR / "spark64_image_cache.json"
spark_update.CATEGORY_ID = "spark64"
spark_update.CATEGORY_NAME = "SPARK 1:64"
spark_update.SPARK_SCALE_NAME = "1:64"
spark_update.CLEAR_IMAGES_WHEN_INCOMING_EMPTY = False


if __name__ == "__main__":
    spark_update.main()

#!/usr/bin/env python3
"""专项补齐 SPARK 缺图产品，不重抓完整产品清单。"""

import json
from pathlib import Path

import update_spark_products_api as spark_images


BASE_DIR = Path(__file__).resolve().parent
PRODUCTS_PATH = BASE_DIR / "minigt_products.json"
TARGETS = {
    "spark": {
        "name": "SPARK 1:43",
        "cache": BASE_DIR / "spark_image_cache.json",
    },
    "spark64": {
        "name": "SPARK 1:64",
        "cache": BASE_DIR / "spark64_image_cache.json",
    },
}


def load_json(path, default=None):
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def clean_images(images):
    return spark_images.clean_images(images, spark_images.MAX_IMAGES_PER_PRODUCT)


def product_needs_image(product):
    return not (product.get("image") or clean_images(product.get("images", [])))


def load_cache(path):
    cache = load_json(path, {})
    if not isinstance(cache, dict):
        return {}
    return {key: clean_images(value) for key, value in cache.items() if clean_images(value)}


def save_cache(path, cache):
    save_json(path, cache)


def find_category(data, category_id):
    for category in data.get("categories", []):
        if category.get("id") == category_id:
            return category
    return None


def repair_category(data, category_id, config):
    category = find_category(data, category_id)
    if not category:
        return {"category": category_id, "target_count": 0, "success_count": 0, "failed_count": 0}

    cache = load_cache(config["cache"])
    targets = [product for product in category.get("products", []) if product_needs_image(product)]
    success_count = 0

    fetch_targets = []
    for product in targets:
        detail_id = str(product.get("detail_id") or "")
        cached_images = clean_images(cache.get(detail_id, []))
        if cached_images:
            product["images"] = cached_images
            product["image"] = cached_images[0]
            success_count += 1
        else:
            fetch_targets.append(product)

    images_by_detail, failed_products = ({}, [])
    if fetch_targets:
        images_by_detail, failed_products = spark_images.run_image_fetch_phase(
            fetch_targets,
            workers=spark_images.IMAGE_RETRY_WORKERS,
            timeout=spark_images.IMAGE_RETRY_TIMEOUT,
            retries=spark_images.IMAGE_RETRY_RETRIES,
            label=f"{config['name']} 缺图补齐",
            cache=cache,
        )
        for product in fetch_targets:
            detail_id = str(product.get("detail_id") or "")
            images = clean_images(images_by_detail.get(detail_id, []))
            if images:
                product["images"] = images
                product["image"] = images[0]
                success_count += 1

    save_cache(config["cache"], cache)
    return {
        "category": category_id,
        "name": config["name"],
        "target_count": len(targets),
        "success_count": success_count,
        "failed_count": len(failed_products),
    }


def main():
    data = load_json(PRODUCTS_PATH)
    results = [
        repair_category(data, category_id, config)
        for category_id, config in TARGETS.items()
    ]
    save_json(PRODUCTS_PATH, data)

    for result in results:
        print(
            f"{result['name']} 缺图补齐：目标 {result['target_count']}，"
            f"成功 {result['success_count']}，失败 {result['failed_count']}"
        )


if __name__ == "__main__":
    main()

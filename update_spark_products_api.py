#!/usr/bin/env python3
"""将 Spark 1:43 产品增量合并进 minigt_products.json。"""

import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests

BASE_DIR = Path(__file__).resolve().parent
PRODUCTS_PATH = BASE_DIR / "minigt_products.json"
API_PRODUCTS_PATH = BASE_DIR / "spark_products_api.json"
SUMMARY_PATH = BASE_DIR / "spark_update_summary.json"
IMAGE_CACHE_PATH = BASE_DIR / "spark_image_cache.json"
CATEGORY_ID = "spark"
CATEGORY_NAME = "SPARK 1:43"
SPARK_SCALE_NAME = os.environ.get("SPARK_SCALE_NAME", "1:43")
API_URL = "https://rapi.sparkmodel.com/products"
CDN_URL = "https://minimax.fra1.cdn.digitaloceanspaces.com"
MAX_IMAGES_PER_PRODUCT = 3
IMAGE_FAST_WORKERS = 16
IMAGE_FAST_TIMEOUT = 12
IMAGE_FAST_RETRIES = 1
IMAGE_RETRY_WORKERS = 6
IMAGE_RETRY_TIMEOUT = 25
IMAGE_RETRY_RETRIES = 2
CLEAR_IMAGES_WHEN_INCOMING_EMPTY = False
DETAIL_IMAGE_TARGET_MODE = os.environ.get("SPARK_DETAIL_IMAGE_TARGET_MODE", "missing")
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Content-Language": "en",
    "Connection": "close",
}


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


def clean_images(images, limit=MAX_IMAGES_PER_PRODUCT):
    cleaned = []
    for image in images or []:
        if image and image not in cleaned:
            cleaned.append(image)
        if limit and len(cleaned) >= limit:
            break
    return cleaned


def get_or_create_category(data):
    categories = data.setdefault("categories", [])
    for index, category in enumerate(categories):
        if category.get("id") == CATEGORY_ID:
            category.setdefault("name", CATEGORY_NAME)
            category.setdefault("products", [])
            return index, category

    category = {"id": CATEGORY_ID, "name": CATEGORY_NAME, "products": []}
    categories.append(category)
    return len(categories) - 1, category


def update_total_products(data):
    total = sum(len(category.get("products", [])) for category in data.get("categories", []))
    data.setdefault("meta", {})["total_products"] = total
    return total


def normalize_product(product):
    normalized = dict(product)
    detail_id = normalized.get("detail_id")
    if not detail_id:
        raise RuntimeError(f"Spark 产品缺少 detail_id：{product}")
    normalized["sku"] = normalized.get("sku") or f"SPARK-{detail_id}"
    normalized["status"] = normalized.get("status") or "Released"
    normalized["images"] = clean_images(normalized.get("images", []))
    if normalized.get("image") and normalized["image"] not in normalized["images"]:
        normalized["images"].insert(0, normalized["image"])
    if not normalized.get("image") and normalized["images"]:
        normalized["image"] = normalized["images"][0]
    return normalized


def sized_image_url(image_id):
    if not image_id:
        return ""
    return f"{CDN_URL}/published/{image_id}-desktop-1x.webp"


def fetch_product_images(product, timeout, retries):
    detail_id = product.get("detail_id")
    if not detail_id:
        return product, []

    for attempt in range(retries + 1):
        try:
            resp = requests.get(
                f"{API_URL}/{detail_id}/images",
                params={"sort": "position"},
                headers=HEADERS,
                timeout=timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            image_ids = data.get("data", [])
            images = [
                sized_image_url(image_id)
                for image_id in image_ids[:MAX_IMAGES_PER_PRODUCT]
                if image_id
            ]
            return product, clean_images(images)
        except Exception:
            if attempt < retries:
                time.sleep(0.4 * (attempt + 1))
    return product, []


def load_image_cache():
    cache = load_json(IMAGE_CACHE_PATH, {})
    if not isinstance(cache, dict):
        return {}
    return {
        detail_id: clean_images(images)
        for detail_id, images in cache.items()
        if clean_images(images)
    }


def save_image_cache(cache):
    save_json(IMAGE_CACHE_PATH, cache)


def run_image_fetch_phase(targets, workers, timeout, retries, label, cache):
    images_by_detail = {}
    failed_products = []
    start = time.time()

    print(f"{label}：{len(targets)} 个目标，并发 {workers}，超时 {timeout}s", flush=True)
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(fetch_product_images, product, timeout, retries): product
            for product in targets
        }
        for index, future in enumerate(as_completed(futures), 1):
            product, images = future.result()
            detail_id = product.get("detail_id")
            if images:
                images_by_detail[detail_id] = images
                cache[detail_id] = images
            else:
                failed_products.append(product)

            if index % 250 == 0 or index == len(targets):
                save_image_cache(cache)
                print(
                    f"  {label}进度：{index}/{len(targets)}，成功 {len(images_by_detail)}，失败 {len(failed_products)}，耗时 {time.time() - start:.0f}s",
                    flush=True,
                )

    save_image_cache(cache)
    return images_by_detail, failed_products


def basic_fields_changed(existing, incoming):
    return any(
        incoming.get(key) != existing.get(key)
        for key in (
            "detail_id",
            "name",
            "sku",
            "status",
            "spark_state",
            "spark_brand",
            "spark_manufacturer",
            "spark_model",
            "spark_year",
        )
    )


def needs_detail_images(existing, incoming, changed):
    if existing is None:
        return True
    existing_images = clean_images(existing.get("images", []))
    if changed:
        return True
    if DETAIL_IMAGE_TARGET_MODE == "incomplete":
        return len(existing_images) < MAX_IMAGES_PER_PRODUCT
    return not existing.get("image") and not existing_images


def fetch_detail_images_for_targets(targets):
    if not targets:
        return {}, {
            "detail_image_target_count": 0,
            "detail_image_success_count": 0,
            "detail_image_failed_count": 0,
            "detail_image_cache_hit_count": 0,
        }

    cache = load_image_cache()
    images_by_detail = {}
    pending_targets = []
    cache_hit_count = 0

    for product in targets:
        detail_id = product.get("detail_id")
        cached_images = cache.get(detail_id)
        if cached_images:
            images_by_detail[detail_id] = cached_images
            cache_hit_count += 1
        else:
            pending_targets.append(product)

    print(
        f"开始抓取 {CATEGORY_NAME} 产品图：{len(targets)} 个目标，每个最多 {MAX_IMAGES_PER_PRODUCT} 张，缓存命中 {cache_hit_count} 个",
        flush=True,
    )

    fast_images, failed_products = run_image_fetch_phase(
        pending_targets,
        IMAGE_FAST_WORKERS,
        IMAGE_FAST_TIMEOUT,
        IMAGE_FAST_RETRIES,
        "第一阶段快速抓图",
        cache,
    )
    images_by_detail.update(fast_images)

    retry_images, retry_failed_products = run_image_fetch_phase(
        failed_products,
        IMAGE_RETRY_WORKERS,
        IMAGE_RETRY_TIMEOUT,
        IMAGE_RETRY_RETRIES,
        "第二阶段失败重试",
        cache,
    )
    images_by_detail.update(retry_images)

    return images_by_detail, {
        "detail_image_target_count": len(targets),
        "detail_image_success_count": len(images_by_detail),
        "detail_image_failed_count": len(retry_failed_products),
        "detail_image_cache_hit_count": cache_hit_count,
    }


def missing_image_summary(products, limit=12):
    missing = [
        product.get("sku") or product.get("detail_id") or product.get("name") or "未知产品"
        for product in products
        if not product.get("image") and not clean_images(product.get("images", []))
    ]
    return {
        "missing_image_count": len(missing),
        "missing_image_examples": missing[:limit],
    }


def merge_product(existing, incoming, detail_images=None):
    merged = dict(existing)
    detail_images = clean_images(detail_images or [])
    incoming_images = clean_images(incoming.get("images", []))
    existing_images = clean_images(existing.get("images", []))

    if CLEAR_IMAGES_WHEN_INCOMING_EMPTY and not detail_images and not incoming_images:
        images = []
    else:
        images = detail_images or existing_images or incoming_images
    image = images[0] if images else incoming.get("image") or existing.get("image", "")
    if image and image not in images:
        images.insert(0, image)
    images = clean_images(images)
    image = images[0] if images else image

    merged.update({
        "detail_id": incoming.get("detail_id", existing.get("detail_id")),
        "name": incoming.get("name", existing.get("name", "")),
        "sku": incoming.get("sku", existing.get("sku", "")),
        "status": incoming.get("status") or existing.get("status", "Released"),
        "image": image,
        "images": clean_images(images),
        "spark_scale": incoming.get("spark_scale", existing.get("spark_scale", SPARK_SCALE_NAME)),
        "spark_brand": incoming.get("spark_brand", existing.get("spark_brand", "")),
        "spark_manufacturer": incoming.get("spark_manufacturer", existing.get("spark_manufacturer", "")),
        "spark_model": incoming.get("spark_model", existing.get("spark_model", "")),
        "spark_state": incoming.get("spark_state", existing.get("spark_state", "")),
        "spark_year": incoming.get("spark_year", existing.get("spark_year")),
        "spark_primary_image_url": incoming.get("spark_primary_image_url", existing.get("spark_primary_image_url", "")),
    })
    return merged


def new_product_with_images(product, detail_images=None):
    new_product = dict(product)
    images = clean_images(detail_images or new_product.get("images", []))
    if new_product.get("image") and new_product["image"] not in images:
        images.insert(0, new_product["image"])
    images = clean_images(images)
    new_product["image"] = images[0] if images else new_product.get("image", "")
    new_product["images"] = images
    return new_product


def main():
    try:
        data = load_json(PRODUCTS_PATH)
        api_products = load_json(API_PRODUCTS_PATH)
        if not isinstance(api_products, list) or not api_products:
            raise RuntimeError("Spark 产品数据为空或格式错误")

        category_idx, spark_category = get_or_create_category(data)
        existing_products = spark_category.get("products", [])
        existing_by_detail = {
            product.get("detail_id"): product
            for product in existing_products
            if product.get("detail_id") is not None
        }

        updated_products = []
        fetched_detail_ids = set()
        added_count = 0
        updated_count = 0
        unchanged_count = 0
        duplicate_count = 0
        image_targets = []
        staged_products = []

        for incoming in api_products:
            normalized = normalize_product(incoming)
            detail_id = normalized["detail_id"]
            if detail_id in fetched_detail_ids:
                duplicate_count += 1
                continue
            fetched_detail_ids.add(detail_id)

            existing = existing_by_detail.get(detail_id)
            if existing:
                changed = basic_fields_changed(existing, normalized)
                if needs_detail_images(existing, normalized, changed):
                    image_targets.append(normalized)
                staged_products.append((existing, normalized, changed))
            else:
                image_targets.append(normalized)
                staged_products.append((None, normalized, True))

        images_by_detail, image_summary = fetch_detail_images_for_targets(image_targets)

        for existing, normalized, changed in staged_products:
            detail_id = normalized["detail_id"]
            detail_images = images_by_detail.get(detail_id, [])

            if existing:
                merged = merge_product(existing, normalized, detail_images)
                final_changed = changed or any(
                    merged.get(key) != existing.get(key)
                    for key in ("image", "images")
                )
                if final_changed:
                    updated_count += 1
                else:
                    unchanged_count += 1
                updated_products.append(merged)
            else:
                added_count += 1
                updated_products.append(new_product_with_images(normalized, detail_images))

        preserved_products = [
            new_product_with_images(product)
            for product in existing_products
            if product.get("detail_id") not in fetched_detail_ids
        ]
        preserved_count = len(preserved_products)
        updated_products.extend(preserved_products)

        data["categories"][category_idx]["products"] = updated_products
        total_products = update_total_products(data)
        save_json(PRODUCTS_PATH, data)

        scrape_summary = load_json(SUMMARY_PATH, {})
        summary = {
            **scrape_summary,
            "original_spark_count": len(existing_products),
            "added_count": added_count,
            "updated_count": updated_count,
            "unchanged_count": unchanged_count,
            "preserved_count": preserved_count,
            "duplicate_count": duplicate_count,
            **image_summary,
            "detail_image_skipped_count": max(0, len(fetched_detail_ids) - image_summary["detail_image_target_count"]),
            "detail_image_target_mode": DETAIL_IMAGE_TARGET_MODE,
            "max_images_per_product": MAX_IMAGES_PER_PRODUCT,
            **missing_image_summary(updated_products),
            "final_spark_count": len(updated_products),
            "total_products": total_products,
        }
        save_json(SUMMARY_PATH, summary)

        print(f"{CATEGORY_NAME} 产品合并完成")
        print(f"官网抓取：{len(fetched_detail_ids)} 个")
        print(f"新增：{added_count}，更新：{updated_count}，未变：{unchanged_count}")
        print(f"官网未返回但已保留：{preserved_count}")
        print(f"产品图目标：{image_summary['detail_image_target_count']}，成功：{image_summary['detail_image_success_count']}，失败保留原图：{image_summary['detail_image_failed_count']}")
        print(f"仍缺图：{summary['missing_image_count']} 个")
        print(f"最终 {CATEGORY_NAME} 数量：{len(updated_products)}")
        print(f"总产品数：{total_products}")
    except Exception as exc:
        print(f"错误：{exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()

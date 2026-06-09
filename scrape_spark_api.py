#!/usr/bin/env python3
"""抓取 Spark 1:43 MODEL 产品，输出给合并流程使用。"""

import json
import math
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests

API_URL = "https://rapi.sparkmodel.com/products"
BASE_DIR = Path(__file__).resolve().parent
OUTPUT_PATH = BASE_DIR / "spark_products_api.json"
SUMMARY_PATH = BASE_DIR / "spark_update_summary.json"
SCALE_NAME = os.environ.get("SPARK_SCALE_NAME", "1:43")
SCALE_FILTER = f'scale_name = "{SCALE_NAME}"'
PAGE_SIZE = 250
MAX_SAFE_HITS = 1000
SPLIT_FACETS = ("webcatalogue_state", "brand_name", "year")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Content-Language": "en",
    "Connection": "close",
}
VALIDATE_IMAGE_URLS = False
IMAGE_VALIDATE_TIMEOUT = 8
IMAGE_VALIDATE_WORKERS = 24
_image_validation_cache = {}


def normalize_status(webcatalogue_state):
    if webcatalogue_state in {"INDEVELOPMENT", "COMINGSOON"}:
        return "Pre-Order"
    return "Released"


def normalize_name(name):
    return " ".join((name or "").split())


def escape_filter_value(value):
    return str(value).replace("\\", "\\\\").replace('"', '\\"')


def equals_filter(field, value):
    if isinstance(value, int):
        return f"{field} = {value}"
    return f'{field} = "{escape_filter_value(value)}"'


def null_filter(field):
    return f"{field} IS NULL"


def fallback_sized_url(primary_image_url):
    if not primary_image_url:
        return ""
    base = primary_image_url.rsplit(".", 1)[0]
    return f"{base}-desktop-1x.webp"


def image_url_reachable(url):
    if not url:
        return False
    if url in _image_validation_cache:
        return _image_validation_cache[url]

    ok = False
    try:
        resp = requests.head(url, headers=HEADERS, timeout=IMAGE_VALIDATE_TIMEOUT, allow_redirects=True)
        content_type = resp.headers.get("content-type", "")
        ok = resp.status_code == 200 and content_type.startswith("image/")
        if not ok and resp.status_code in {403, 404, 405}:
            _image_validation_cache[url] = False
            return False
    except requests.RequestException:
        pass

    if not ok:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=IMAGE_VALIDATE_TIMEOUT, stream=True)
            content_type = resp.headers.get("content-type", "")
            ok = resp.status_code == 200 and content_type.startswith("image/")
        except requests.RequestException:
            ok = False

    _image_validation_cache[url] = ok
    return ok


def best_sized_image_url(primary_image_url):
    image = fallback_sized_url(primary_image_url)
    return image


def validate_product_image(product):
    image = product.get("image") or ""
    primary_image_url = product.get("spark_primary_image_url") or ""
    if image and image_url_reachable(image):
        return product
    if primary_image_url and primary_image_url != image and image_url_reachable(primary_image_url):
        product["image"] = primary_image_url
        product["images"] = [primary_image_url]
        return product
    product["image"] = ""
    product["images"] = []
    return product


def validate_product_images(products):
    if not VALIDATE_IMAGE_URLS:
        return products

    start = time.time()
    print(f"开始并发验证 Spark {SCALE_NAME} 图片 URL：{len(products)} 个产品，并发 {IMAGE_VALIDATE_WORKERS}", flush=True)
    with ThreadPoolExecutor(max_workers=IMAGE_VALIDATE_WORKERS) as executor:
        validated = []
        total = len(products)
        for index, product in enumerate(executor.map(validate_product_image, [dict(product) for product in products]), 1):
            validated.append(product)
            if index % 100 == 0 or index == total:
                print(f"  图片验证进度：{index}/{total}，耗时 {time.time() - start:.0f}s", flush=True)
    return validated


def request_products(filters, page_number=1, page_size=1, facets=None):
    params = {
        "q": "",
        "page_number": page_number,
        "page_size": page_size,
        "filters": json.dumps(filters),
        "facets": json.dumps(list(facets or [])),
    }
    resp = requests.get(API_URL, params=params, headers=HEADERS, timeout=45)
    resp.raise_for_status()
    return resp.json()


def get_meta(filters, facets):
    data = request_products(filters, facets=facets)
    return data.get("meta", {}) or {}


def facet_distribution(meta, facet):
    distribution = (meta.get("facet_distribution") or {}).get(facet) or {}
    if not isinstance(distribution, dict):
        return {}
    return distribution


def count_for(filters):
    meta = get_meta(filters, [])
    return int(meta.get("total_hits") or 0)


def field_already_filtered(filters, field):
    prefix = f"{field} "
    return any(item.startswith(prefix) for item in filters)


def split_filters(filters, count_hint, depth=0):
    if count_hint <= MAX_SAFE_HITS:
        return [(filters, count_hint)]

    for facet in SPLIT_FACETS:
        if field_already_filtered(filters, facet):
            continue

        meta = get_meta(filters, [facet])
        distribution = facet_distribution(meta, facet)
        if not distribution:
            continue

        null_count = count_for(filters + [null_filter(facet)])
        known_count = sum(int(count) for count in distribution.values()) + null_count
        if known_count != count_hint:
            # Spark 只返回部分高基数字段的 facet 值。遇到这种情况不能用它拆分，
            # 否则会漏掉未返回的长尾值。
            continue

        buckets = []
        for value, count in distribution.items():
            child_filters = filters + [equals_filter(facet, value)]
            buckets.extend(split_filters(child_filters, int(count), depth + 1))
        if null_count:
            child_filters = filters + [null_filter(facet)]
            buckets.extend(split_filters(child_filters, null_count, depth + 1))
        return buckets

    raise RuntimeError(f"无法将 Spark 查询拆到 {MAX_SAFE_HITS} 条以内：{filters}，估算 {count_hint} 条")


def build_query_buckets():
    base_filters = [SCALE_FILTER]
    meta = get_meta(base_filters, ["webcatalogue_state"])
    state_counts = facet_distribution(meta, "webcatalogue_state")
    total_count = sum(int(count) for count in state_counts.values())
    if not state_counts or total_count <= 0:
        raise RuntimeError(f"未识别到 Spark {SCALE_NAME} 产品状态分布")

    null_state_count = count_for(base_filters + [null_filter("webcatalogue_state")])
    if null_state_count:
        total_count += null_state_count

    buckets = []
    for state, count in state_counts.items():
        filters = base_filters + [equals_filter("webcatalogue_state", state)]
        buckets.extend(split_filters(filters, int(count)))
    if null_state_count:
        filters = base_filters + [null_filter("webcatalogue_state")]
        buckets.extend(split_filters(filters, null_state_count))

    return buckets, total_count


def normalize_product(product):
    detail_id = product.get("product_id")
    sku = product.get("code")
    name = normalize_name(product.get("name"))
    if not detail_id or not sku or not name:
        return None

    primary_image_url = product.get("primary_image_url") or ""
    image = best_sized_image_url(primary_image_url)
    images = [image] if image else []

    return {
        "detail_id": detail_id,
        "name": name,
        "sku": sku,
        "status": normalize_status(product.get("webcatalogue_state")),
        "image": image,
        "images": images,
        "spark_scale": product.get("scale_name", "1:43"),
        "spark_brand": product.get("brand_name") or "",
        "spark_manufacturer": product.get("manufacturer_name") or "",
        "spark_model": product.get("model_name") or "",
        "spark_state": product.get("webcatalogue_state") or "",
        "spark_year": product.get("year"),
        "spark_primary_image_url": primary_image_url,
    }


def fetch_bucket(filters, expected_count):
    pages = max(1, math.ceil(expected_count / PAGE_SIZE))
    products = []
    for page in range(1, pages + 1):
        data = request_products(filters, page_number=page, page_size=PAGE_SIZE)
        page_products = data.get("data", [])
        if not isinstance(page_products, list):
            raise RuntimeError(f"Spark 接口返回格式异常：{filters}")
        products.extend(page_products)
        if len(page_products) < PAGE_SIZE:
            break
    return products


def fetch_products():
    buckets, expected_total = build_query_buckets()
    products_by_id = {}
    duplicate_count = 0
    skipped_count = 0
    start = time.time()

    print(f"检测到 Spark {SCALE_NAME} 约 {expected_total} 个产品，拆分为 {len(buckets)} 个查询桶")
    for index, (filters, expected_count) in enumerate(buckets, 1):
        raw_products = fetch_bucket(filters, expected_count)
        print(f"  桶 {index}/{len(buckets)}：期望 {expected_count}，抓到 {len(raw_products)}")

        for raw_product in raw_products:
            normalized = normalize_product(raw_product)
            if not normalized:
                skipped_count += 1
                continue

            detail_id = normalized["detail_id"]
            if detail_id in products_by_id:
                duplicate_count += 1
                continue

            products_by_id[detail_id] = normalized

    products = list(products_by_id.values())
    products = validate_product_images(products)
    if not products:
        raise RuntimeError(f"未抓取到可用的 Spark {SCALE_NAME} 产品")

    image_success_count = sum(1 for product in products if product.get("image"))
    image_failed_count = len(products) - image_success_count

    summary = {
        "scale": SCALE_NAME,
        "fetched_count": len(products),
        "expected_total": expected_total,
        "query_bucket_count": len(buckets),
        "page_size": PAGE_SIZE,
        "duplicate_count": duplicate_count,
        "skipped_count": skipped_count,
        "image_success_count": image_success_count,
        "image_fallback_count": 0,
        "image_failed_count": image_failed_count,
        "elapsed_seconds": round(time.time() - start, 1),
    }
    return products, summary


def main():
    try:
        products, summary = fetch_products()
        with OUTPUT_PATH.open("w", encoding="utf-8") as f:
            json.dump(products, f, ensure_ascii=False, indent=2)

        with SUMMARY_PATH.open("w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)

        print(f"Spark {summary['scale']} 产品抓取完成")
        print(f"官网估算：{summary['expected_total']} 个，实际去重：{summary['fetched_count']} 个")
        print(f"查询桶：{summary['query_bucket_count']} 个，跳过缺字段：{summary['skipped_count']} 个")
        print(f"图片 URL 成功：{summary['image_success_count']} 个，缺失：{summary['image_failed_count']} 个")
        print(f"已保存到：{OUTPUT_PATH.name}")
    except Exception as exc:
        print(f"错误：{exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""抓取 TOP SPEED 官网全部分类产品，输出给增量合并流程使用。"""

import json
import re
import sys
import time
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import parse_qs, urljoin, urlparse

warnings.filterwarnings("ignore", message="urllib3 v2 only supports OpenSSL.*")

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://topspeed.tsm-models.com"
INDEX_URL = BASE_URL + "/index.php?action=product"
BASE_DIR = Path(__file__).resolve().parent
OUTPUT_PATH = BASE_DIR / "topspeed_products_api.json"
SUMMARY_PATH = BASE_DIR / "topspeed_update_summary.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Connection": "close",
}
TIMEOUT = (8, 18)
MAX_WORKERS = 3
DETAIL_WORKERS = 4
MAX_RETRIES = 3
VALID_STATUSES = {"Pre-Order", "Sold Out"}
MAX_IMAGES_PER_PRODUCT = 4


def fix_url(src):
    if not src:
        return ""
    src = src.strip()
    return src if src.startswith("http") else urljoin(BASE_URL + "/", src)


def get_page(url):
    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            resp.raise_for_status()
            return resp.text
        except requests.RequestException as exc:
            last_error = exc
            if attempt < MAX_RETRIES:
                time.sleep(min(1.5 * attempt, 5))
    raise RuntimeError(f"连续 {MAX_RETRIES} 次请求失败：{url}：{last_error}")


def parse_categories(html):
    soup = BeautifulSoup(html, "html.parser")
    categories = []
    seen = set()
    for link in soup.find_all("a", href=re.compile(r"product-list&b_id=\d+")):
        href = link.get("href", "")
        match = re.search(r"b_id=(\d+)", href)
        if not match:
            continue
        category_id = int(match.group(1))
        name = link.get_text(" ", strip=True)
        if not name or category_id in seen:
            continue
        seen.add(category_id)
        categories.append({
            "id": category_id,
            "name": name,
            "url": urljoin(BASE_URL + "/", href),
        })
    return categories


def get_total_pages(html):
    max_page = 1
    soup = BeautifulSoup(html, "html.parser")
    for link in soup.find_all("a", href=re.compile(r"p=\d+")):
        match = re.search(r"p=(\d+)", link.get("href", ""))
        if match:
            max_page = max(max_page, int(match.group(1)))
    return max_page


def parse_status(text):
    for status in VALID_STATUSES:
        if status in text:
            return status
    return "Released"


def parse_products(html, category):
    soup = BeautifulSoup(html, "html.parser")
    products = []
    detail_pattern = re.compile(r"product-detail&id=(\d+)")

    for card in soup.select("div.pro_wrap, div.pd-list-in"):
        detail_id = None
        detail_href = ""
        for link in card.find_all("a", href=detail_pattern):
            href = link.get("href", "")
            match = detail_pattern.search(href)
            if match:
                detail_id = int(match.group(1))
                detail_href = href
                break

        if detail_id is None:
            continue

        name_tag = card.find("a", class_=re.compile(r"h6|text-dark|font-weight-bold"))
        if not name_tag:
            name_tag = card.find("a", href=detail_pattern)
        img_tag = card.find("img")
        sku_tag = card.find("p", class_="m-0")

        name = name_tag.get_text(" ", strip=True) if name_tag else ""
        if not name and img_tag:
            name = img_tag.get("alt", "").strip()
        sku = sku_tag.get_text(" ", strip=True) if sku_tag else ""
        image = fix_url((img_tag.get("data-src") or img_tag.get("src", "")) if img_tag else "")
        status = parse_status(card.get_text(" ", strip=True))

        if not name:
            continue

        products.append({
            "detail_id": detail_id,
            "name": name,
            "sku": sku,
            "status": status,
            "image": image,
            "images": [image] if image else [],
            "detail_url": urljoin(BASE_URL + "/", detail_href) if detail_href else f"{BASE_URL}/index.php?action=product-detail&id={detail_id}",
            "topspeed_categories": [{
                "id": category["id"],
                "name": category["name"],
            }],
        })
    return products


def category_page_url(category, page):
    if page == 1:
        return category["url"]
    return f"{BASE_URL}/index.php?action=product-list&b_id={category['id']}&p={page}"


def fetch_category(category):
    first_html = get_page(category_page_url(category, 1))
    total_pages = get_total_pages(first_html)
    pages = [1] + list(range(2, total_pages + 1))

    products = parse_products(first_html, category)
    failed_pages = []
    for page in pages[1:]:
        try:
            html = get_page(category_page_url(category, page))
            products.extend(parse_products(html, category))
        except Exception as exc:
            failed_pages.append(page)
            print(f"  {category['name']} p={page}: 抓取失败 - {exc}", flush=True)

    if failed_pages:
        raise RuntimeError(f"{category['name']} 有分页抓取失败：{failed_pages}")

    print(f"  {category['name']}: {len(products)} 个列表项，分页 {len(pages)} 页", flush=True)
    return category, products


def merge_category_product(products_by_id, incoming):
    detail_id = incoming["detail_id"]
    existing = products_by_id.get(detail_id)
    if not existing:
        products_by_id[detail_id] = incoming
        return

    known_category_ids = {item.get("id") for item in existing.get("topspeed_categories", [])}
    for category in incoming.get("topspeed_categories", []):
        if category.get("id") not in known_category_ids:
            existing.setdefault("topspeed_categories", []).append(category)
            known_category_ids.add(category.get("id"))

    for key in ("name", "sku", "status", "image", "detail_url"):
        if incoming.get(key) and not existing.get(key):
            existing[key] = incoming[key]
    for image in incoming.get("images", []):
        if image and image not in existing.setdefault("images", []):
            existing["images"].append(image)


def text_after_label(lines, label):
    for index, line in enumerate(lines):
        if line == label and index + 1 < len(lines):
            return lines[index + 1]
    return ""


def parse_detail(product):
    html = get_page(f"{BASE_URL}/index.php?action=product-detail&id={product['detail_id']}")
    soup = BeautifulSoup(html, "html.parser")
    lines = [line.strip() for line in soup.get_text("\n", strip=True).splitlines() if line.strip()]

    detail_sku = text_after_label(lines, "Item No.")
    sku = detail_sku if re.match(r"^TS\d+", detail_sku or "") else product.get("sku", "")
    if not sku:
        sku = f"TOPSPEED-{product['detail_id']}"
    availability = text_after_label(lines, "Availability")
    status = parse_status(availability or product.get("status", ""))

    images = []
    for img in soup.find_all("img"):
        src = img.get("data-src") or img.get("src") or ""
        if "upload/picfile" not in src:
            continue
        full_src = fix_url(src)
        if full_src and full_src not in images:
            images.append(full_src)

    if not images and product.get("image"):
        images = [product["image"]]
    images = images[:MAX_IMAGES_PER_PRODUCT]

    updated = dict(product)
    updated["sku"] = sku
    updated["status"] = status
    updated["images"] = images
    if images:
        updated["image"] = images[0]
    updated.pop("detail_url", None)
    return updated


def enrich_details(products):
    enriched = []
    failed_ids = []
    start = time.time()

    with ThreadPoolExecutor(max_workers=DETAIL_WORKERS) as executor:
        futures = {executor.submit(parse_detail, product): product for product in products}
        for index, future in enumerate(as_completed(futures), 1):
            product = futures[future]
            try:
                enriched_product = future.result()
                enriched.append(enriched_product)
                print(f"  ✓ {enriched_product.get('sku', '') or enriched_product['detail_id']}: {len(enriched_product.get('images', []))} 图", flush=True)
            except Exception as exc:
                fallback = dict(product)
                fallback.pop("detail_url", None)
                enriched.append(fallback)
                failed_ids.append(product.get("detail_id"))
                print(f"  ⚠️ {product.get('detail_id')}: 详情抓取失败，保留列表图 - {exc}", flush=True)

            if index % 50 == 0 or index == len(products):
                print(f"  详情进度：{index}/{len(products)}，耗时 {time.time() - start:.0f}s", flush=True)

    return enriched, failed_ids


def main():
    try:
        print("开始抓取 TOP SPEED 分类...", flush=True)
        index_html = get_page(INDEX_URL)
        categories = parse_categories(index_html)
        if not categories:
            raise RuntimeError("未识别到 TOP SPEED 子分类")

        print(f"检测到 {len(categories)} 个子分类，开始抓取产品列表...", flush=True)
        products_by_id = {}
        category_counts = {}
        failed_categories = []

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {executor.submit(fetch_category, category): category for category in categories}
            for future in as_completed(futures):
                category = futures[future]
                try:
                    category, products = future.result()
                    category_counts[category["name"]] = len(products)
                    for product in products:
                        merge_category_product(products_by_id, product)
                except Exception as exc:
                    failed_categories.append(category)
                    print(f"  {category['name']}: 子分类抓取失败 - {exc}", flush=True)

        if failed_categories:
            print(f"开始串行补抓失败子分类：{[item['name'] for item in failed_categories]}", flush=True)
            retry_failed = []
            for category in failed_categories:
                try:
                    category, products = fetch_category(category)
                    category_counts[category["name"]] = len(products)
                    for product in products:
                        merge_category_product(products_by_id, product)
                except Exception as exc:
                    retry_failed.append(category["name"])
                    print(f"  {category['name']}: 补抓失败 - {exc}", flush=True)
            if retry_failed:
                raise RuntimeError(f"有 {len(retry_failed)} 个子分类抓取失败：{retry_failed[:8]}")

        products = sorted(products_by_id.values(), key=lambda item: item.get("detail_id", 0), reverse=True)
        if not products:
            raise RuntimeError("未抓取到任何 TOP SPEED 产品")

        print()
        print(f"列表去重后：{len(products)} 个 TOP SPEED 产品，开始抓取详情...")
        products, failed_ids = enrich_details(products)
        products.sort(key=lambda item: item.get("detail_id", 0), reverse=True)

        with OUTPUT_PATH.open("w", encoding="utf-8") as f:
            json.dump(products, f, ensure_ascii=False, indent=2)

        summary = {
            "category_count": len(categories),
            "category_counts": category_counts,
            "fetched_count": len(products),
            "detail_success_count": len(products) - len(failed_ids),
            "detail_failed_count": len(failed_ids),
            "detail_failed_ids": failed_ids,
            "max_images_per_product": MAX_IMAGES_PER_PRODUCT,
        }
        with SUMMARY_PATH.open("w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)

        print()
        print("TOP SPEED 抓取完成")
        print(f"官网子分类：{len(categories)} 个")
        print(f"唯一产品：{len(products)} 个")
        print(f"详情成功：{summary['detail_success_count']}，失败：{summary['detail_failed_count']}")
        print(f"已保存到：{OUTPUT_PATH.name}")
    except Exception as exc:
        print(f"错误：{exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()

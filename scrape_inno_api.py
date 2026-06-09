#!/usr/bin/env python3
"""抓取 INNO 1:64 官网产品，输出给增量合并流程使用。"""

import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.inno-models.com"
LIST_URL = BASE_URL + "/our-products/?jsf=jet-engine:shop-loop&tax=pa_scale:1-64"
BASE_DIR = Path(__file__).resolve().parent
OUTPUT_PATH = BASE_DIR / "inno_products_api.json"
SUMMARY_PATH = BASE_DIR / "inno_update_summary.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}
TIMEOUT = 30
RETRIES = 3
DETAIL_WORKERS = 8
MAX_IMAGES_PER_PRODUCT = 3


def get_page(url):
    last_error = None
    for attempt in range(RETRIES + 1):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            resp.raise_for_status()
            return resp.text
        except Exception as exc:
            last_error = exc
            if attempt < RETRIES:
                time.sleep(1.2 * (attempt + 1))
    raise last_error


def page_url(page):
    if page == 1:
        return LIST_URL
    return f"{BASE_URL}/our-products/page/{page}/?jsf=jet-engine:shop-loop&tax=pa_scale:1-64"


def get_total_pages(html):
    match = re.search(r'data-pages="(\d+)"', html)
    return int(match.group(1)) if match else 1


def normalize_text(value):
    return " ".join((value or "").split())


def normalize_status(value):
    text = normalize_text(value).lower()
    if "out of stock" in text or "sold out" in text:
        return "Sold Out"
    if "pre-order" in text or "pre order" in text or "preorder" in text or "coming soon" in text:
        return "Pre-Order"
    return "Released"


def pick_sized_image(src, srcset):
    candidates = []
    for part in (srcset or "").split(","):
        pieces = part.strip().split()
        if not pieces:
            continue
        url = pieces[0]
        width = 0
        if len(pieces) > 1 and pieces[1].endswith("w"):
            try:
                width = int(pieces[1][:-1])
            except ValueError:
                width = 0
        candidates.append((width, url))

    preferred = [item for item in candidates if 550 <= item[0] <= 700]
    if preferred:
        return min(preferred, key=lambda item: item[0])[1]
    smaller = [item for item in candidates if 250 <= item[0] < 550]
    if smaller:
        return max(smaller, key=lambda item: item[0])[1]
    return src or (candidates[0][1] if candidates else "")


def product_links(item):
    links = []
    for link in item.find_all("a", href=re.compile(r"/product/")):
        href = urljoin(BASE_URL + "/", link.get("href", ""))
        if href and href not in links:
            links.append(href)
    return links


def parse_list_products(html):
    soup = BeautifulSoup(html, "html.parser")
    products = []

    for item in soup.select(".jet-listing-grid__item"):
        post_id = item.get("data-post-id")
        if not post_id:
            continue

        links = product_links(item)
        if not links:
            continue
        detail_url = links[0]

        name = ""
        for link in item.find_all("a", href=re.compile(r"/product/")):
            text = normalize_text(link.get_text(" ", strip=True))
            if text:
                name = text
                break
        if not name:
            name = normalize_text(item.get_text(" ", strip=True))
        if not name:
            continue

        image = ""
        for img in item.find_all("img"):
            src = img.get("src") or ""
            if "wp-content/uploads" not in src:
                continue
            image = pick_sized_image(src, img.get("srcset"))
            break

        products.append({
            "detail_id": int(post_id),
            "name": name,
            "sku": "",
            "status": "Released",
            "image": image,
            "images": [image] if image else [],
            "detail_url": detail_url,
            "inno_scale": "1/64",
        })

    return products


def text_after_label(lines, label):
    for index, line in enumerate(lines):
        if line.lower() == label.lower() and index + 1 < len(lines):
            return lines[index + 1]
    return ""


def detail_images(soup, fallback_image):
    images = []
    selectors = [
        "img.iconic-woothumbs-images__image",
        "img.iconic-woothumbs-thumbnails__image",
    ]

    for selector in selectors:
        for img in soup.select(selector):
            src = img.get("src") or ""
            if "wp-content/uploads" not in src:
                continue
            image = pick_sized_image(src, img.get("srcset"))
            if image and image not in images:
                images.append(image)

    if not images and fallback_image:
        images = [fallback_image]
    return images[:MAX_IMAGES_PER_PRODUCT]


def parse_detail(product):
    html = get_page(product["detail_url"])
    soup = BeautifulSoup(html, "html.parser")
    lines = [line.strip() for line in soup.get_text("\n", strip=True).splitlines() if line.strip()]

    sku = text_after_label(lines, "SKU") or product.get("sku") or f"INNO-{product['detail_id']}"
    scale = text_after_label(lines, "Scale") or "1/64"
    brand = text_after_label(lines, "Brand")
    raw_status = text_after_label(lines, "Status")
    product_type = text_after_label(lines, "Type")
    status = normalize_status(raw_status or product.get("status"))
    images = detail_images(soup, product.get("image", ""))

    updated = dict(product)
    updated.update({
        "sku": sku,
        "status": status,
        "image": images[0] if images else product.get("image", ""),
        "images": images,
        "inno_url": product.get("detail_url", ""),
        "inno_scale": scale,
        "inno_brand": brand,
        "inno_status": raw_status,
        "inno_type": product_type,
    })
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
                print(f"  ✓ {enriched_product.get('sku', '')}: {len(enriched_product.get('images', []))} 图", flush=True)
            except Exception as exc:
                fallback = dict(product)
                fallback["sku"] = fallback.get("sku") or f"INNO-{fallback['detail_id']}"
                fallback["inno_url"] = fallback.get("detail_url", "")
                fallback.pop("detail_url", None)
                enriched.append(fallback)
                failed_ids.append(product.get("detail_id"))
                print(f"  ⚠️ {product.get('detail_id')}: 详情抓取失败，保留列表图 - {exc}", flush=True)

            if index % 50 == 0 or index == len(products):
                print(f"  详情进度：{index}/{len(products)}，耗时 {time.time() - start:.0f}s", flush=True)

    return enriched, failed_ids


def main():
    try:
        print("开始抓取 INNO 1:64 产品...")
        first_html = get_page(page_url(1))
        total_pages = get_total_pages(first_html)
        if total_pages < 1:
            raise RuntimeError("未识别到 INNO 分页")

        products_by_id = {}
        products = parse_list_products(first_html)
        for product in products:
            products_by_id[product["detail_id"]] = product
        print(f"  第 1/{total_pages} 页：{len(products)} 个")

        for page in range(2, total_pages + 1):
            html = get_page(page_url(page))
            page_products = parse_list_products(html)
            print(f"  第 {page}/{total_pages} 页：{len(page_products)} 个")
            for product in page_products:
                products_by_id[product["detail_id"]] = product

        products = sorted(products_by_id.values(), key=lambda item: item.get("detail_id", 0), reverse=True)
        if not products:
            raise RuntimeError("未抓取到任何 INNO 1:64 产品")

        print()
        print(f"列表去重后：{len(products)} 个 INNO 产品，开始抓取详情...")
        products, failed_ids = enrich_details(products)
        products.sort(key=lambda item: item.get("detail_id", 0), reverse=True)

        with OUTPUT_PATH.open("w", encoding="utf-8") as f:
            json.dump(products, f, ensure_ascii=False, indent=2)

        summary = {
            "scale": "1/64",
            "page_count": total_pages,
            "fetched_count": len(products),
            "detail_success_count": len(products) - len(failed_ids),
            "detail_failed_count": len(failed_ids),
            "detail_failed_ids": failed_ids,
            "max_images_per_product": MAX_IMAGES_PER_PRODUCT,
        }
        with SUMMARY_PATH.open("w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)

        print()
        print("INNO 1:64 抓取完成")
        print(f"官网分页：{total_pages} 页")
        print(f"唯一产品：{len(products)} 个")
        print(f"详情成功：{summary['detail_success_count']}，失败：{summary['detail_failed_count']}")
        print(f"已保存到：{OUTPUT_PATH.name}")
    except Exception as exc:
        print(f"错误：{exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()

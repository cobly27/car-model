#!/usr/bin/env python3
"""抓取 MINI GT 官网产品列表，输出给增量合并流程使用。"""

import json
import re
import sys
import time
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urljoin

warnings.filterwarnings("ignore", message="urllib3 v2 only supports OpenSSL.*")

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://minigt.tsm-models.com"
LIST_URL = BASE_URL + "/index.php?action=product-list&b_id=13&p={}"
BASE_DIR = Path(__file__).resolve().parent
OUTPUT_PATH = BASE_DIR / "minigt_products_api.json"
SUMMARY_PATH = BASE_DIR / "minigt_update_summary.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Connection": "close",
}
TIMEOUT = (8, 15)
MAX_WORKERS = 3
MAX_RETRIES = 3
VALID_STATUSES = {"Pre-Order", "Released", "Sold Out"}


def fix_url(src):
    if not src:
        return ""
    src = src.strip()
    return src if src.startswith("http") else urljoin(BASE_URL, src)


def get_total_pages():
    soup = BeautifulSoup(fetch_page_html(0), "html.parser")

    max_page = 0
    for link in soup.find_all("a", href=re.compile(r"p=\d+")):
        match = re.search(r"p=(\d+)", link.get("href", ""))
        if match:
            max_page = max(max_page, int(match.group(1)))
    return max_page + 1


def fetch_page_html(page):
    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(LIST_URL.format(page), headers=HEADERS, timeout=TIMEOUT)
            resp.raise_for_status()
            return resp.text
        except requests.RequestException as exc:
            last_error = exc
            if attempt < MAX_RETRIES:
                time.sleep(min(1.5 * attempt, 5))
    raise RuntimeError(f"p={page} 连续 {MAX_RETRIES} 次请求失败：{last_error}")


def parse_products(html):
    soup = BeautifulSoup(html, "html.parser")
    products = []
    detail_pattern = re.compile(r"product-detail&id=(\d+)")

    for card in soup.select("div.pro_wrap, div.pd-list-in"):
        detail_id = None
        for link in card.find_all("a", href=detail_pattern):
            match = detail_pattern.search(link.get("href", ""))
            if match:
                detail_id = int(match.group(1))
                break

        name_tag = card.find("a", class_=re.compile(r"h6|text-dark|font-weight-bold"))
        if not name_tag:
            name_tag = card.find("a", href=detail_pattern)
        img_tag = card.find("img")

        name = name_tag.get_text(strip=True) if name_tag else ""
        if not name and img_tag:
            name = img_tag.get("alt", "").strip()

        sku_tag = card.find("p", class_="m-0")
        sku = sku_tag.get_text(strip=True) if sku_tag else ""

        status = ""
        for link in card.find_all("a", href=detail_pattern):
            text = link.get_text(strip=True)
            if text in VALID_STATUSES:
                status = text
                break

        image = ""
        if img_tag:
            image = fix_url(img_tag.get("data-src") or img_tag.get("src", ""))

        if detail_id is None or not name or not sku:
            continue

        products.append({
            "detail_id": detail_id,
            "name": name,
            "sku": sku,
            "status": status,
            "image": image,
            "images": [image] if image else [],
        })

    return products


def fetch_page(page):
    products = parse_products(fetch_page_html(page))
    print(f"  p={page}: {len(products)} 个产品", flush=True)
    return page, products


def dedupe_products(products):
    seen_detail_ids = set()
    seen_skus = set()
    unique = []
    duplicate_count = 0

    for product in products:
        detail_id = product["detail_id"]
        sku = product["sku"]
        if detail_id in seen_detail_ids or sku in seen_skus:
            duplicate_count += 1
            continue
        seen_detail_ids.add(detail_id)
        seen_skus.add(sku)
        unique.append(product)

    unique.sort(key=lambda item: item.get("detail_id", 0), reverse=True)
    return unique, duplicate_count


def main():
    try:
        total_pages = get_total_pages()
        if total_pages <= 0:
            raise RuntimeError("未能识别 MINI GT 分页")

        print(f"检测到 {total_pages} 页，开始抓取 MINI GT 产品列表...", flush=True)
        all_products = []
        failed_pages = []

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {executor.submit(fetch_page, page): page for page in range(total_pages)}
            for future in as_completed(futures):
                page = futures[future]
                try:
                    _, products = future.result()
                    all_products.extend(products)
                except Exception as exc:
                    failed_pages.append(page)
                    print(f"  p={page}: 抓取失败 - {exc}", flush=True)

        if failed_pages:
            print(f"开始串行补抓失败页：{failed_pages}", flush=True)
            retry_failed_pages = []
            for page in failed_pages:
                try:
                    _, products = fetch_page(page)
                    all_products.extend(products)
                except Exception as exc:
                    retry_failed_pages.append(page)
                    print(f"  p={page}: 补抓失败 - {exc}", flush=True)
            if retry_failed_pages:
                raise RuntimeError(f"有 {len(retry_failed_pages)} 页抓取失败：{retry_failed_pages[:10]}")

        products, duplicate_count = dedupe_products(all_products)
        if not products:
            raise RuntimeError("未抓取到任何 MINI GT 产品")

        with OUTPUT_PATH.open("w", encoding="utf-8") as f:
            json.dump(products, f, ensure_ascii=False, indent=2)

        summary = {
            "source": BASE_URL,
            "fetched_count": len(products),
            "page_count": total_pages,
            "duplicate_count": duplicate_count,
        }
        with SUMMARY_PATH.open("w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)

        print(flush=True)
        print(f"官网抓取：{len(products)} 个产品", flush=True)
        print(f"跳过重复：{duplicate_count} 个", flush=True)
        print(f"已保存到：{OUTPUT_PATH.name}", flush=True)
    except Exception as exc:
        print(f"错误：{exc}", flush=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

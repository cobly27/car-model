#!/usr/bin/env python3
"""抓取 MINI GT 官网产品列表，输出给增量合并流程使用。"""

import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urljoin

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
}
TIMEOUT = 30
MAX_WORKERS = 8
VALID_STATUSES = {"Pre-Order", "Released", "Sold Out"}


def fix_url(src):
    if not src:
        return ""
    src = src.strip()
    return src if src.startswith("http") else urljoin(BASE_URL, src)


def get_total_pages():
    resp = requests.get(LIST_URL.format(0), headers=HEADERS, timeout=TIMEOUT)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    max_page = 0
    for link in soup.find_all("a", href=re.compile(r"p=\d+")):
        match = re.search(r"p=(\d+)", link.get("href", ""))
        if match:
            max_page = max(max_page, int(match.group(1)))
    return max_page + 1


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
    resp = requests.get(LIST_URL.format(page), headers=HEADERS, timeout=TIMEOUT)
    resp.raise_for_status()
    products = parse_products(resp.text)
    print(f"  p={page}: {len(products)} 个产品")
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

        print(f"检测到 {total_pages} 页，开始抓取 MINI GT 产品列表...")
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
                    print(f"  p={page}: 抓取失败 - {exc}")

        if failed_pages:
            raise RuntimeError(f"有 {len(failed_pages)} 页抓取失败：{failed_pages[:10]}")

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

        print()
        print(f"官网抓取：{len(products)} 个产品")
        print(f"跳过重复：{duplicate_count} 个")
        print(f"已保存到：{OUTPUT_PATH.name}")
    except Exception as exc:
        print(f"错误：{exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()

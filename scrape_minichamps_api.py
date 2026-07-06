#!/usr/bin/env python3
"""抓取 CK-Modelcars MINICHAMPS 产品索引，默认输出全量产品。"""

import os
import json
import re
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from bs4 import BeautifulSoup


BASE_DIR = Path(__file__).resolve().parent
OUTPUT_PATH = BASE_DIR / "minichamps_products_api.json"
SUMMARY_PATH = BASE_DIR / "minichamps_update_summary.json"
SEARCH_INDEX_URL = "https://ck-modelcars.de/includes/search/search-64a76aa6d2f6934009982c4666aae36f.json"
DETAIL_URL_TEMPLATE = "https://ck-modelcars.de/en/p-{product_id}/"
MAX_PRODUCTS = None
CONCURRENCY = 8
MAX_IMAGES_PER_PRODUCT = 4
HEADERS = {
    "Accept": "application/json,text/html,*/*",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X) AppleWebKit/537.36",
}


def fetch_bytes(url):
    request = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(request, timeout=45) as response:
        return response.read(), response.geturl()


def fetch_json(url):
    body, _ = fetch_bytes(url)
    return json.loads(body.decode("utf-8"))


def fetch_html(url):
    body, final_url = fetch_bytes(url)
    return body.decode("utf-8", "ignore"), final_url


def max_products_from_env():
    raw = os.environ.get("MINICHAMPS_MAX_PRODUCTS", "").strip()
    if not raw:
        return MAX_PRODUCTS
    try:
        value = int(raw)
    except ValueError:
        raise RuntimeError("MINICHAMPS_MAX_PRODUCTS 必须是数字")
    return value if value > 0 else None


def clean_text(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()


def scale_from_name(name):
    match = re.search(r"\b1\s*:\s*(\d+)\b", name or "")
    return f"1:{match.group(1)}" if match else ""


def keywords_to_codes(keywords):
    return re.findall(r"[A-Za-z0-9][A-Za-z0-9./-]{3,}", keywords or "")


def status_from_detail(soup, name):
    text = soup.get_text(" ", strip=True).lower()
    availability = soup.select_one('[itemprop="availability"]')
    availability_text = clean_text(availability.get_text(" ", strip=True)).lower() if availability else ""
    if "pre-order" in text or "pre order" in text or "preorder" in text:
        return "Pre-Order"
    if "outofstock" in availability_text or "sold out" in text:
        return "Sold Out"
    return "Released"


def detail_images(soup):
    images = []
    for image in soup.select('[itemprop="image"]'):
        src = image.get("src") or image.get("content") or image.get("data-src")
        if not src:
            continue
        if "/ck_img/zoom/" not in src and "/ck_img/zoom_ck/" not in src:
            continue
        src = src.replace("/ck_img/zoom_ck/", "/ck_img/zoom/")
        if src not in images:
            images.append(src)
        if len(images) >= MAX_IMAGES_PER_PRODUCT:
            break
    return images


def detail_price(soup):
    price = soup.select_one('[itemprop="price"]')
    return clean_text(price.get("content") if price else "")


def detail_currency(soup):
    currency = soup.select_one('[itemprop="priceCurrency"]')
    return clean_text(currency.get("content") if currency else "")


def detail_gtin(soup, fallback_keywords):
    gtin = soup.select_one('[itemprop="gtin13"]')
    if gtin:
        value = clean_text(gtin.get_text(" ", strip=True))
        if value:
            return value
    for code in keywords_to_codes(fallback_keywords):
        if re.fullmatch(r"\d{13}", code):
            return code
    return ""


def normalize_product(index_item, display_order):
    detail_id = str(index_item.get("id") or "").strip()
    keywords = str(index_item.get("keyords") or "").strip()
    search_name = clean_text(index_item.get("name"))
    html, final_url = fetch_html(DETAIL_URL_TEMPLATE.format(product_id=detail_id))
    soup = BeautifulSoup(html, "html.parser")

    title = soup.select_one('[itemprop="name"]') or soup.select_one("h1")
    name = clean_text(title.get_text(" ", strip=True) if title else search_name)
    images = detail_images(soup)
    codes = keywords_to_codes(keywords)
    sku = codes[0] if codes else f"MINICHAMPS-{detail_id}"
    scale = scale_from_name(search_name) or scale_from_name(name)
    price = detail_price(soup)
    currency = detail_currency(soup)
    availability = soup.select_one('[itemprop="availability"]')
    availability_text = clean_text(availability.get_text(" ", strip=True)) if availability else ""

    return {
        "detail_id": detail_id,
        "sku": sku,
        "name": name or search_name or sku,
        "status": status_from_detail(soup, search_name),
        "image": images[0] if images else "",
        "images": images,
        "minichamps_url": final_url,
        "minichamps_source": "CK-Modelcars",
        "minichamps_search_name": search_name,
        "minichamps_article_id": sku,
        "minichamps_ean": detail_gtin(soup, keywords),
        "minichamps_scale": scale,
        "minichamps_price": price,
        "minichamps_currency": currency,
        "minichamps_available": availability_text.lower() == "instock",
        "minichamps_availability": availability_text,
        "minichamps_display_order": display_order,
        "minichamps_image_id": str(index_item.get("bild") or ""),
        "minichamps_bonus": index_item.get("bonus", 0),
    }


def main():
    index = fetch_json(SEARCH_INDEX_URL)
    candidates = [
        item for item in index
        if "minichamps" in str(item.get("name", "")).lower()
    ]
    candidates.sort(key=lambda item: int(item.get("id") or 0), reverse=True)
    max_products = max_products_from_env()
    targets = candidates[:max_products] if max_products else candidates
    if not targets:
        raise RuntimeError("CK-Modelcars MINICHAMPS 索引未返回产品，停止更新")

    products = []
    failed = []
    indexed_targets = list(enumerate(targets, start=1))
    with ThreadPoolExecutor(max_workers=CONCURRENCY) as executor:
        futures = {
            executor.submit(normalize_product, item, display_order): (display_order, item)
            for display_order, item in indexed_targets
        }
        for future in as_completed(futures):
            display_order, item = futures[future]
            try:
                product = future.result()
                products.append(product)
                print(f"✅ {display_order}/{len(targets)} {product['sku']} {product['name']}")
            except Exception as exc:
                failed.append({"id": item.get("id"), "name": item.get("name"), "error": str(exc)})
                print(f"⚠️ 跳过 {display_order}/{len(targets)} {item.get('id')}: {exc}")

    if not products:
        raise RuntimeError("MINICHAMPS 详情页全部抓取失败，停止更新")
    products.sort(key=lambda product: int(product.get("minichamps_display_order") or 999999))

    summary = {
        "source": SEARCH_INDEX_URL,
        "detail_source": "https://ck-modelcars.de/en/p-{id}/",
        "index_count": len(index),
        "candidate_count": len(candidates),
        "max_products": max_products or "all",
        "target_count": len(targets),
        "concurrency": CONCURRENCY,
        "max_images_per_product": MAX_IMAGES_PER_PRODUCT,
        "fetched_count": len(products),
        "detail_failed_count": len(failed),
        "detail_failed_examples": failed[:5],
        "image_success_count": sum(1 for product in products if product.get("images")),
        "image_failed_count": sum(1 for product in products if not product.get("images")),
    }
    OUTPUT_PATH.write_text(json.dumps(products, ensure_ascii=False, indent=2), encoding="utf-8")
    SUMMARY_PATH.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ MINICHAMPS 抓取完成：{len(products)} 个，候选 {len(candidates)} 个")


if __name__ == "__main__":
    main()

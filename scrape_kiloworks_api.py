#!/usr/bin/env python3
"""抓取 3000toys Kilo Works 全部产品，输出产品 JSON。"""

import json
import re
import urllib.request
from pathlib import Path
from urllib.parse import urljoin

from bs4 import BeautifulSoup


BASE_DIR = Path(__file__).resolve().parent
OUTPUT_PATH = BASE_DIR / "kiloworks_products_api.json"
SUMMARY_PATH = BASE_DIR / "kiloworks_update_summary.json"
LIST_URL = "https://www.3000toys.com/cars/kilo-works"
MAX_IMAGES_PER_PRODUCT = 4
HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X) AppleWebKit/537.36",
}


def fetch_html(url):
    request = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(request, timeout=45) as response:
        return response.read().decode("utf-8", "ignore"), response.geturl()


def clean_text(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()


def load_json_ld(soup):
    items = []
    for script in soup.select('script[type="application/ld+json"]'):
        text = script.get_text(" ", strip=True)
        if not text:
            continue
        try:
            items.append(json.loads(text))
        except json.JSONDecodeError:
            continue
    return items


def list_urls():
    html, _ = fetch_html(LIST_URL)
    soup = BeautifulSoup(html, "html.parser")
    urls = []
    for item in load_json_ld(soup):
        if item.get("@type") != "ItemList":
            continue
        for element in item.get("itemListElement", []):
            url = element.get("url")
            if url and url not in urls:
                urls.append(url)
    if urls:
        return urls

    for link in soup.find_all("a", href=True):
        href = urljoin(LIST_URL, link["href"])
        if "/cars/scale-" in href and "/product/" in href and href not in urls:
            urls.append(href)
    return urls


def product_json_ld(soup):
    for item in load_json_ld(soup):
        if item.get("@type") == "Product":
            return item
    return {}


def offer_from(product):
    offer = product.get("offers") or {}
    return offer if isinstance(offer, dict) else {}


def properties_from(product):
    values = {}
    for prop in product.get("additionalProperty") or []:
        name = clean_text(prop.get("name")).lower()
        if name:
            values[name] = clean_text(prop.get("value"))
    return values


def status_from(product, soup):
    availability = clean_text(offer_from(product).get("availability")).lower()
    text = soup.get_text(" ", strip=True).lower()
    if "preorder" in availability or "pre-order" in text or "pre order" in text:
        return "Pre-Order"
    if "outofstock" in availability or "sold out" in text or "notify me" in text:
        return "Sold Out"
    return "Released"


def available_from(product, soup):
    availability = clean_text(offer_from(product).get("availability")).lower()
    text = soup.get_text(" ", strip=True).lower()
    if "instock" in availability or "add to cart" in text:
        return True
    if "preorder" in availability or "outofstock" in availability or "notify me" in text:
        return False
    return False


def images_from(product, detail_url):
    images = []
    for src in product.get("image") or []:
        src = urljoin(detail_url, src)
        if src not in images:
            images.append(src)
        if len(images) >= MAX_IMAGES_PER_PRODUCT:
            break
    return images


def arrival_from(soup):
    text = soup.get_text(" ", strip=True)
    match = re.search(r"(?:Expected|Please allow)\s+([^.;]+)", text, re.I)
    return clean_text(match.group(1)) if match else ""


def added_date_from(soup):
    text = soup.get_text(" ", strip=True)
    match = re.search(r"Added to catalog:\s*([0-9/]+)", text, re.I)
    return clean_text(match.group(1)) if match else ""


def normalize_detail(url, display_order):
    html, final_url = fetch_html(url)
    soup = BeautifulSoup(html, "html.parser")
    product = product_json_ld(soup)
    if not product:
        raise RuntimeError("详情页缺少 Product JSON-LD")

    offer = offer_from(product)
    props = properties_from(product)
    sku = clean_text(product.get("sku") or product.get("mpn"))
    name = clean_text(product.get("description") or product.get("name") or soup.select_one("h1").get_text(" ", strip=True))
    images = images_from(product, final_url)
    scale = props.get("scale") or ""
    brand = clean_text((product.get("brand") or {}).get("name") if isinstance(product.get("brand"), dict) else product.get("brand"))

    return {
        "detail_id": sku,
        "sku": sku,
        "name": name,
        "status": status_from(product, soup),
        "image": images[0] if images else "",
        "images": images,
        "kiloworks_url": final_url,
        "kiloworks_source": "3000toys",
        "kiloworks_brand": brand or "Kilo Works",
        "kiloworks_scale": scale,
        "kiloworks_price": clean_text(offer.get("price")),
        "kiloworks_currency": clean_text(offer.get("priceCurrency")),
        "kiloworks_available": available_from(product, soup),
        "kiloworks_availability": clean_text(offer.get("availability")),
        "kiloworks_arrival": arrival_from(soup),
        "kiloworks_added_date": added_date_from(soup),
        "kiloworks_display_order": display_order,
    }


def main():
    urls = list_urls()
    if not urls:
        raise RuntimeError("3000toys Kilo Works 列表未返回产品，停止更新")

    products = []
    failed = []
    for index, url in enumerate(urls, start=1):
        try:
            product = normalize_detail(url, index)
            products.append(product)
            print(f"✅ {index}/{len(urls)} {product['sku']} {product['name']}")
        except Exception as exc:
            failed.append({"url": url, "error": str(exc)})
            print(f"⚠️ 跳过 {url}: {exc}")

    if not products:
        raise RuntimeError("Kilo Works 详情页全部抓取失败，停止更新")

    summary = {
        "source": LIST_URL,
        "list_count": len(urls),
        "fetched_count": len(products),
        "detail_failed_count": len(failed),
        "detail_failed_examples": failed[:5],
        "image_success_count": sum(1 for product in products if product.get("images")),
        "image_failed_count": sum(1 for product in products if not product.get("images")),
        "max_images_per_product": MAX_IMAGES_PER_PRODUCT,
    }
    OUTPUT_PATH.write_text(json.dumps(products, ensure_ascii=False, indent=2), encoding="utf-8")
    SUMMARY_PATH.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ Kilo Works 抓取完成：{len(products)} 个")


if __name__ == "__main__":
    main()

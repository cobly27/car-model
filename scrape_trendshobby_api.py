#!/usr/bin/env python3
"""聚合渠道中的 Trends Hobby / TH 产品，输出去重后的全量清单。"""

import hashlib
import json
import re
import urllib.request
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
OUTPUT_PATH = BASE_DIR / "trendshobby_products_api.json"
SUMMARY_PATH = BASE_DIR / "trendshobby_update_summary.json"
MAX_IMAGES_PER_PRODUCT = 4

SOURCES = [
    {
        "id": "diecasttalk",
        "name": "DiecastTalk",
        "url": "https://shopdiecasttalk.com/collections/trends-hobby/products.json?limit=250",
        "product_base": "https://shopdiecasttalk.com/products/",
    },
    {
        "id": "mobilegarage",
        "name": "Mobile Garage HK",
        "url": "https://www.mobilegaragehk.com/collections/trends-hobby/products.json?limit=250",
        "product_base": "https://www.mobilegaragehk.com/products/",
    },
    {
        "id": "treasuredmodels",
        "name": "Treasured Models",
        "url": "https://treasuredmodels.com/collections/trends-hobby/products.json?limit=250",
        "product_base": "https://treasuredmodels.com/products/",
    },
]


def fetch_json(url):
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X) AppleWebKit/537.36",
        },
    )
    with urllib.request.urlopen(request, timeout=45) as response:
        return json.load(response)


def clean_images(images):
    cleaned = []
    for image in images or []:
        src = image.get("src") if isinstance(image, dict) else image
        if src and src not in cleaned:
            cleaned.append(src)
        if len(cleaned) >= MAX_IMAGES_PER_PRODUCT:
            break
    return cleaned


def first_variant(product):
    variants = product.get("variants") or []
    return variants[0] if variants else {}


def first_meaningful_sku(product):
    for variant in product.get("variants") or []:
        sku = str(variant.get("sku") or "").strip()
        if sku and not sku.upper().startswith("PRE-ORDER"):
            return sku
    return ""


def extract_model_code(title):
    match = re.search(r"\b\d{6}[A-Z]\b", title or "", re.IGNORECASE)
    return match.group(0).upper() if match else ""


def display_name(title):
    name = str(title or "").strip()
    name = re.sub(r"\[?\s*pre[- ]?order\s*\]?", "", name, flags=re.IGNORECASE)
    name = re.sub(r"^\s*Trends\s+Hobby\s+", "", name, flags=re.IGNORECASE)
    name = re.sub(r"^\s*TH\s+", "", name, flags=re.IGNORECASE)
    name = re.sub(r"\s+", " ", name)
    return name.strip(" -–")


def canonical_title(title):
    text = display_name(title).lower()
    text = re.sub(r"\btrends\s+hobby\b", "", text)
    text = re.sub(r"\bth\b", "", text)
    text = re.sub(r"\b1\s*[:/]\s*64\b", "", text)
    text = re.sub(r"\bscale\b|\bdie\s*cast\b|\bdiecast\b|\bmodel\b", "", text)
    text = re.sub(r"[^a-z0-9#]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def product_key(product):
    title = str(product.get("title") or "")
    code = extract_model_code(title)
    if code:
        return f"th-{code.lower()}"
    fingerprint = canonical_title(title)
    digest = hashlib.sha1(fingerprint.encode("utf-8")).hexdigest()[:12]
    return f"th-{digest}"


def status_from_product(product):
    title = str(product.get("title") or "").lower()
    variant = first_variant(product)
    sku = str(variant.get("sku") or "").lower()
    if any(marker in f"{title} {sku}" for marker in ("pre-order", "preorder", "pre order")):
        return "Pre-Order"

    variants = product.get("variants") or []
    if variants and not any(bool(variant.get("available")) for variant in variants):
        return "Sold Out"
    return "Released"


def status_rank(status):
    return {"Released": 3, "Pre-Order": 2, "Sold Out": 1}.get(status, 0)


def source_url(source, product):
    handle = str(product.get("handle") or "").strip()
    return f"{source['product_base']}{handle}" if handle else source["url"]


def normalize_product(source, product, order):
    key = product_key(product)
    title = str(product.get("title") or "").strip()
    code = extract_model_code(title)
    images = clean_images(product.get("images") or [])
    variant = first_variant(product)
    sku = code or first_meaningful_sku(product) or key.upper()
    url = source_url(source, product)
    return {
        "detail_id": key,
        "sku": sku,
        "name": display_name(title) or sku,
        "status": status_from_product(product),
        "image": images[0] if images else "",
        "images": images,
        "trendshobby_url": url,
        "trendshobby_handle": product.get("handle") or "",
        "trendshobby_sources": [{
            "id": source["id"],
            "name": source["name"],
            "url": url,
            "product_id": str(product.get("id") or ""),
        }],
        "trendshobby_source_names": [source["name"]],
        "trendshobby_model_code": code,
        "trendshobby_display_order": order,
        "trendshobby_price": str(variant.get("price") or "").strip(),
        "trendshobby_available": any(bool(item.get("available")) for item in product.get("variants") or []),
    }


def merge_duplicate(existing, incoming):
    images = list(existing.get("images") or [])
    for image in incoming.get("images") or []:
        if image and image not in images:
            images.append(image)
        if len(images) >= MAX_IMAGES_PER_PRODUCT:
            break
    existing["images"] = images
    existing["image"] = images[0] if images else existing.get("image", "")

    if status_rank(incoming.get("status")) > status_rank(existing.get("status")):
        existing["status"] = incoming.get("status")

    if incoming.get("trendshobby_model_code") and not existing.get("trendshobby_model_code"):
        existing["trendshobby_model_code"] = incoming.get("trendshobby_model_code")
        existing["sku"] = incoming.get("trendshobby_model_code")

    if len(incoming.get("name") or "") > len(existing.get("name") or ""):
        existing["name"] = incoming.get("name")

    source_names = list(existing.get("trendshobby_source_names") or [])
    sources = list(existing.get("trendshobby_sources") or [])
    for source in incoming.get("trendshobby_sources") or []:
        if source.get("name") not in source_names:
            source_names.append(source.get("name"))
            sources.append(source)
    existing["trendshobby_source_names"] = source_names
    existing["trendshobby_sources"] = sources
    return existing


def main():
    products_by_key = {}
    source_counts = {}
    raw_count = 0

    for source in SOURCES:
        payload = fetch_json(source["url"])
        raw_products = payload.get("products") or []
        source_counts[source["id"]] = len(raw_products)
        for raw_product in raw_products:
            raw_count += 1
            incoming = normalize_product(source, raw_product, raw_count)
            key = incoming["detail_id"]
            if key in products_by_key:
                merge_duplicate(products_by_key[key], incoming)
            else:
                products_by_key[key] = incoming

    products = sorted(
        products_by_key.values(),
        key=lambda item: (int(item.get("trendshobby_display_order") or 999999), str(item.get("sku") or "")),
    )
    if not products:
        raise RuntimeError("Trends Hobby 渠道抓取结果为空，停止更新")

    summary = {
        "sources": [{**source, "count": source_counts.get(source["id"], 0)} for source in SOURCES],
        "source_count": len(SOURCES),
        "raw_count": raw_count,
        "fetched_count": len(products),
        "duplicate_count": raw_count - len(products),
        "max_images_per_product": MAX_IMAGES_PER_PRODUCT,
        "image_success_count": sum(1 for product in products if product.get("images")),
        "image_failed_count": sum(1 for product in products if not product.get("images")),
    }

    with OUTPUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(products, f, ensure_ascii=False, indent=2)
    with SUMMARY_PATH.open("w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(
        f"✅ Trends Hobby 抓取完成：渠道原始 {raw_count} 个，去重后 {len(products)} 个，"
        f"重复合并 {summary['duplicate_count']} 个"
    )


if __name__ == "__main__":
    main()

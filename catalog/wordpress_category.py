"""Helpers for GCD/DCT WordPress product categories."""

import re
import time
from html import unescape

import requests
from bs4 import BeautifulSoup


BASE_URL = "https://www.gcd-models.com"
HEADERS = {
    "Accept": "application/json,text/html,*/*",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X) AppleWebKit/537.36",
}
TIMEOUT = (8, 18)
MAX_RETRIES = 3


def fetch_json(url):
    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            response.raise_for_status()
            return response.json(), response.headers
        except requests.RequestException as exc:
            last_error = exc
            if attempt < MAX_RETRIES:
                time.sleep(min(1.5 * attempt, 5))
    raise RuntimeError(f"请求失败：{url}：{last_error}")


def clean_text(value):
    text = BeautifulSoup(str(value or ""), "html.parser").get_text(" ", strip=True)
    return re.sub(r"\s+", " ", unescape(text)).strip()


def image_from_media(media):
    sizes = (media or {}).get("media_details", {}).get("sizes", {})
    for key in ("medium_large", "large", "full"):
        source = sizes.get(key, {}).get("source_url")
        if source:
            return source
    return (media or {}).get("source_url", "")


def images_from_post(post, max_images):
    images = []
    featured = (post.get("_embedded", {}).get("wp:featuredmedia") or [{}])[0]
    for image in (image_from_media(featured), featured.get("source_url", "")):
        if image and image not in images:
            images.append(image)
    return images[:max_images]


def category_names(post):
    names = []
    for term_group in post.get("_embedded", {}).get("wp:term", []) or []:
        for term in term_group:
            name = clean_text(term.get("name", ""))
            if name and name.lower() not in {"products", "gcd", "dct"} and name not in names:
                names.append(name)
    return names


def split_title(title, prefix):
    title = clean_text(title)
    match = re.match(r"^([A-Z0-9/]+(?:\s*-\s*[A-Z0-9]+){0,3})\s+(.+)$", title, re.IGNORECASE)
    if match:
        sku = re.sub(r"\s*-\s*", " -", match.group(1)).strip()
        name = match.group(2).strip()
    else:
        sku = f"{prefix}-{abs(hash(title)) % 1000000}"
        name = title
    return sku, name


def fetch_category_posts(category_id):
    first_url = f"{BASE_URL}/wp-json/wp/v2/posts?categories={category_id}&per_page=20&page=1&_embed=1"
    first_posts, headers = fetch_json(first_url)
    page_count = int(headers.get("X-WP-TotalPages") or 1)
    posts = list(first_posts)
    for page in range(2, page_count + 1):
        url = f"{BASE_URL}/wp-json/wp/v2/posts?categories={category_id}&per_page=20&page={page}&_embed=1"
        page_posts, _headers = fetch_json(url)
        posts.extend(page_posts)
    return posts, page_count


def build_wordpress_category_products(*, category_id, source_url, field_prefix, max_images=4):
    posts, page_count = fetch_category_posts(category_id)
    products = []
    for index, post in enumerate(posts, start=1):
        title = clean_text(post.get("title", {}).get("rendered", ""))
        sku, name = split_title(title, field_prefix.upper())
        images = images_from_post(post, max_images)
        products.append({
            "detail_id": str(post.get("id")),
            "sku": sku,
            "name": name,
            "status": "Released",
            "image": images[0] if images else "",
            "images": images,
            f"{field_prefix}_url": post.get("link") or source_url,
            f"{field_prefix}_title": title,
            f"{field_prefix}_categories": category_names(post),
            f"{field_prefix}_display_order": index,
            f"{field_prefix}_date": post.get("date") or "",
        })
    return products, {
        "category_id": category_id,
        "source": source_url,
        "page_count": page_count,
        "fetched_count": len(products),
        "detail_success_count": len(products),
        "detail_failed_count": 0,
        "max_images_per_product": max_images,
    }

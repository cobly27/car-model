"""Shared WordPress category scraper for GCD-family product pages."""

import html
import json
import re
import urllib.parse
import urllib.request


BASE_URL = "https://www.gcd-models.com"
POSTS_ENDPOINT = f"{BASE_URL}/wp-json/wp/v2/posts"
CATEGORIES_ENDPOINT = f"{BASE_URL}/wp-json/wp/v2/categories"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
}

IMAGE_RE = re.compile(r"<img[^>]+src=[\"']([^\"']+)[\"']", re.I)
TAG_RE = re.compile(r"<[^>]+>")
SKU_RE = re.compile(r"^\s*([A-Z0-9/]+(?:\s*[-–—]\s*[A-Z0-9]+)*(?:-[A-Z0-9]+)*)\s+(.*)$")
SKIP_IMAGE_MARKERS = (
    "banner",
    "logo",
    "微信图片_202xxc41105160401",
)


def fetch_url(url):
    request = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read(), response.headers


def fetch_json(url):
    body, headers = fetch_url(url)
    return json.loads(body.decode("utf-8")), headers


def clean_text(value):
    value = html.unescape(TAG_RE.sub("", value or ""))
    value = value.replace("\xa0", " ")
    value = re.sub(r"\s+", " ", value).strip()
    return value


def normalize_url(url):
    url = html.unescape(url or "").strip()
    if url.startswith("//"):
        return "https:" + url
    if url.startswith("/"):
        return BASE_URL + url
    return url


def split_title(title):
    title = clean_text(title)
    match = SKU_RE.match(title)
    if not match:
        return title, title
    sku = re.sub(r"\s*[-–—]\s*", " -", match.group(1)).strip()
    name = match.group(2).strip() or title
    return sku, name


def embedded_image(post):
    media = post.get("_embedded", {}).get("wp:featuredmedia", [{}])
    if not media:
        return ""
    item = media[0]
    sizes = item.get("media_details", {}).get("sizes", {})
    for size_name in ("medium_large", "large", "medium"):
        source = sizes.get(size_name, {}).get("source_url")
        if source:
            return normalize_url(source)
    return normalize_url(item.get("source_url", ""))


def should_skip_image(url):
    lower = urllib.parse.unquote(url).lower()
    return any(marker.lower() in lower for marker in SKIP_IMAGE_MARKERS)


def detail_images(url, primary_image, max_images):
    try:
        body, _headers = fetch_url(url)
    except Exception:
        return [primary_image] if primary_image else []

    text = body.decode("utf-8", "replace")
    images = []
    if primary_image:
        images.append(primary_image)

    for raw_url in IMAGE_RE.findall(text):
        image = normalize_url(raw_url)
        if "/wp-content/uploads/" not in image:
            continue
        if should_skip_image(image):
            continue
        if image not in images:
            images.append(image)
        if len(images) >= max_images:
            break
    return images[:max_images]


def category_names():
    categories, _headers = fetch_json(f"{CATEGORIES_ENDPOINT}?per_page=100")
    return {item.get("id"): item.get("name", "") for item in categories}


def fetch_posts(category_id):
    posts = []
    page = 1
    total_pages = 1
    while page <= total_pages:
        url = f"{POSTS_ENDPOINT}?categories={category_id}&per_page=20&page={page}&_embed=1"
        data, headers = fetch_json(url)
        total_pages = int(headers.get("X-WP-TotalPages", total_pages) or total_pages)
        posts.extend(data)
        page += 1
    return posts, total_pages


def build_wordpress_category_products(*, category_id, source_url, field_prefix, max_images):
    category_map = category_names()
    posts, page_count = fetch_posts(category_id)
    products = []
    detail_success_count = 0
    detail_failed_count = 0

    for index, post in enumerate(posts, 1):
        title = clean_text(post.get("title", {}).get("rendered", ""))
        sku, name = split_title(title)
        detail_url = post.get("link", "")
        primary_image = embedded_image(post)
        images = detail_images(detail_url, primary_image, max_images)
        if images:
            detail_success_count += 1
        else:
            detail_failed_count += 1

        post_categories = [
            category_map.get(post_category_id, str(post_category_id))
            for post_category_id in post.get("categories", [])
            if post_category_id != category_id
        ]

        products.append({
            "detail_id": str(post.get("id")),
            "sku": sku,
            "name": name,
            "status": "Released",
            "image": images[0] if images else primary_image,
            "images": images,
            f"{field_prefix}_url": detail_url,
            f"{field_prefix}_title": title,
            f"{field_prefix}_categories": post_categories,
            f"{field_prefix}_display_order": index,
            f"{field_prefix}_date": post.get("date", ""),
        })

    summary = {
        "source": source_url,
        "category_id": category_id,
        "page_count": page_count,
        "fetched_count": len(products),
        "detail_success_count": detail_success_count,
        "detail_failed_count": detail_failed_count,
        "max_images_per_product": max_images,
    }
    return products, summary

"""JSON catalog loading and derived statistics."""

import json

from .config import PRODUCTS_PATH
from .image_policy import image_policy_response


def load_catalog():
    with PRODUCTS_PATH.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, list):
        data = {
            "meta": {"total_products": len(data)},
            "categories": [{"id": "mini-gt", "name": "MINI GT", "products": data}],
        }

    data.setdefault("meta", {})
    data.setdefault("categories", [])
    return data


def category_stats(categories):
    stats = {}
    for category in categories:
        products = category.get("products", [])
        stats[category.get("id", "")] = {
            "total": len(products),
            "released": sum(1 for item in products if item.get("status") == "Released"),
            "preorder": sum(1 for item in products if item.get("status") == "Pre-Order"),
            "soldout": sum(1 for item in products if item.get("status") == "Sold Out"),
        }
    return stats


def total_products(categories):
    return sum(len(category.get("products", [])) for category in categories)


def load_catalog_response():
    data = load_catalog()
    categories = data.get("categories", [])
    computed_total = total_products(categories)
    data["meta"]["computed_total_products"] = computed_total
    data["category_stats"] = category_stats(categories)
    data["image_policies"] = image_policy_response()
    return data


def load_catalog_meta_response():
    """Return catalog metadata without embedding every product."""
    data = load_catalog()
    categories = data.get("categories", [])
    computed_total = total_products(categories)
    return {
        "meta": {
            **data.get("meta", {}),
            "computed_total_products": computed_total,
        },
        "categories": [
            {
                "id": category.get("id", ""),
                "name": category.get("name", category.get("id", "")),
                "count": len(category.get("products", [])),
            }
            for category in categories
        ],
        "category_stats": category_stats(categories),
        "image_policies": image_policy_response(),
    }


def product_key(product):
    return str(product.get("detail_id") or product.get("sku") or "").strip()


def product_matches_search(product, query):
    if not query:
        return True
    haystack = " ".join([
        str(product.get("sku") or ""),
        str(product.get("name") or ""),
        str(product.get("detail_id") or ""),
    ]).lower()
    return query.lower() in haystack


def product_matches_filter(product, filter_value, favorite_skus):
    if not filter_value:
        return True
    if filter_value == "fav":
        return str(product.get("sku") or "") in favorite_skus
    return product.get("status") == filter_value


def product_images(product):
    images = []
    for image in product.get("images", []) or []:
        if image and image not in images:
            images.append(image)
    primary = product.get("image")
    if primary and primary not in images:
        images.insert(0, primary)
    return images


def category_by_id(data, category_id):
    for category in data.get("categories", []):
        if category.get("id") == category_id:
            return category
    return None


def iter_products(data, category_id, favorite_mode=False):
    index = 1
    for category in data.get("categories", []):
        if category_id and not favorite_mode and category.get("id") != category_id:
            index += len(category.get("products", []))
            continue
        for product in category.get("products", []):
            enriched = dict(product)
            enriched["categoryId"] = category.get("id", "")
            enriched["index"] = index
            yield enriched
            index += 1


def query_products_response(
    *,
    category_id,
    query="",
    filter_value="",
    favorite_skus=None,
    health_keys=None,
    page=1,
    page_size=20,
):
    """Return one filtered page of products for the v2 UI."""
    data = load_catalog()
    favorite_skus = set(favorite_skus or [])
    health_keys = set(health_keys or [])
    favorite_mode = filter_value == "fav"
    page_size = page_size if page_size in {20, 50, 100} else 20

    source_category = category_by_id(data, category_id)
    category_total = len(source_category.get("products", [])) if source_category else 0

    products = []
    for product in iter_products(data, category_id, favorite_mode=favorite_mode):
        if not product_matches_search(product, query):
            continue
        if health_keys:
            key = product_key(product)
            sku = str(product.get("sku") or "")
            if key not in health_keys and sku not in health_keys:
                continue
        if not product_matches_filter(product, filter_value, favorite_skus):
            continue
        products.append(product)

    total = len(products)
    total_pages = max(1, (total + page_size - 1) // page_size)
    page = max(1, min(page, total_pages))
    start = (page - 1) * page_size
    page_products = products[start:start + page_size]
    stats = {
        "Released": sum(1 for item in products if item.get("status") == "Released"),
        "Pre-Order": sum(1 for item in products if item.get("status") == "Pre-Order"),
        "Sold Out": sum(1 for item in products if item.get("status") == "Sold Out"),
    }

    return {
        "products": page_products,
        "total": total,
        "page": page,
        "pageSize": page_size,
        "totalPages": total_pages,
        "categoryTotal": category_total,
        "stats": stats,
    }


def favorites_slideshow_response(skus):
    """Return lightweight products for the favorites slideshow."""
    requested_skus = []
    seen = set()
    for sku in skus or []:
        normalized = str(sku or "").strip()
        if normalized and normalized not in seen:
            requested_skus.append(normalized)
            seen.add(normalized)

    if not requested_skus:
        return {"products": [], "requested": 0, "returned": 0}

    sku_position = {sku: index for index, sku in enumerate(requested_skus)}
    products = []
    data = load_catalog()
    for product in iter_products(data, "", favorite_mode=True):
        sku = str(product.get("sku") or "").strip()
        if sku not in sku_position:
            continue
        images = product_images(product)
        if not images:
            continue
        products.append({
            "sku": sku,
            "name": product.get("name", ""),
            "status": product.get("status", "Released"),
            "categoryId": product.get("categoryId", ""),
            "detail_id": product.get("detail_id", ""),
            "image": images[0],
            "images": [images[0]],
        })

    products.sort(key=lambda item: sku_position.get(item["sku"], 999999))
    return {
        "products": products,
        "requested": len(requested_skus),
        "returned": len(products),
    }

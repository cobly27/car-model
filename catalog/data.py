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

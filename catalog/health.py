"""Read-only catalog health checks."""

from .data import load_catalog, total_products
from .image_policy import IMAGE_POLICIES

VALID_STATUSES = {"Released", "Pre-Order", "Sold Out"}


def product_key(product):
    key = product.get("detail_id") or product.get("sku")
    return str(key).strip() if key else ""


def product_label(product):
    return str(product.get("sku") or product.get("detail_id") or product.get("name") or "").strip()


def has_image(product):
    return bool(product.get("image") or product.get("images"))


def limited_append(items, value, limit=8):
    if len(items) < limit:
        items.append(value)


def check_category(category):
    category_id = category.get("id", "")
    products = category.get("products", [])
    policy = IMAGE_POLICIES.get(category_id, {})
    max_images = policy.get("maxImages")

    seen = set()
    duplicate_examples = []
    missing_key_examples = []
    missing_sku_examples = []
    missing_name_examples = []
    missing_image_examples = []
    invalid_status_examples = []
    over_image_limit_examples = []

    duplicate_count = 0
    missing_key_count = 0
    missing_sku_count = 0
    missing_name_count = 0
    missing_image_count = 0
    invalid_status_count = 0
    over_image_limit_count = 0

    for product in products:
        label = product_label(product)
        key = product_key(product)
        if not key:
            missing_key_count += 1
            limited_append(missing_key_examples, label or "(未命名产品)")
        elif key in seen:
            duplicate_count += 1
            limited_append(duplicate_examples, label or key)
        else:
            seen.add(key)

        if not product.get("sku"):
            missing_sku_count += 1
            limited_append(missing_sku_examples, label or key or "(未命名产品)")
        if not product.get("name"):
            missing_name_count += 1
            limited_append(missing_name_examples, label or key or "(未命名产品)")
        if not has_image(product):
            missing_image_count += 1
            limited_append(missing_image_examples, label or key or "(未命名产品)")
        if product.get("status") not in VALID_STATUSES:
            invalid_status_count += 1
            limited_append(invalid_status_examples, label or key or "(未命名产品)")

        images = product.get("images", [])
        if isinstance(max_images, int) and max_images > 0 and isinstance(images, list) and len(images) > max_images:
            over_image_limit_count += 1
            limited_append(over_image_limit_examples, f"{label or key}: {len(images)} 张")

    issue_count = (
        duplicate_count
        + missing_key_count
        + missing_sku_count
        + missing_name_count
        + missing_image_count
        + invalid_status_count
        + over_image_limit_count
    )

    return {
        "id": category_id,
        "name": category.get("name", category_id),
        "total": len(products),
        "issueCount": issue_count,
        "duplicateKeyCount": duplicate_count,
        "missingKeyCount": missing_key_count,
        "missingSkuCount": missing_sku_count,
        "missingNameCount": missing_name_count,
        "missingImageCount": missing_image_count,
        "invalidStatusCount": invalid_status_count,
        "overImageLimitCount": over_image_limit_count,
        "examples": {
            "duplicateKeys": duplicate_examples,
            "missingKeys": missing_key_examples,
            "missingSkus": missing_sku_examples,
            "missingNames": missing_name_examples,
            "missingImages": missing_image_examples,
            "invalidStatuses": invalid_status_examples,
            "overImageLimit": over_image_limit_examples,
        },
    }


def catalog_health_response():
    data = load_catalog()
    categories = data.get("categories", [])
    computed_total = total_products(categories)
    meta_total = data.get("meta", {}).get("total_products")
    category_reports = [check_category(category) for category in categories]
    category_issue_count = sum(report["issueCount"] for report in category_reports)
    total_ok = meta_total == computed_total
    issue_count = category_issue_count + (0 if total_ok else 1)

    return {
        "ok": issue_count == 0,
        "issueCount": issue_count,
        "totalOk": total_ok,
        "metaTotal": meta_total,
        "computedTotal": computed_total,
        "categoryCount": len(categories),
        "categories": category_reports,
    }

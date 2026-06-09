"""Read-only catalog health checks."""

import csv
from io import StringIO

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


def missing_image_reason(category_id, product):
    if category_id not in {"spark", "spark64"}:
        return "缺少图片字段"
    if not product.get("spark_primary_image_url"):
        return "官网列表无图"
    return "图片 URL 验证失败（常见 CDN 403）"


def add_missing_image_reason(reasons, reason, label):
    entry = reasons.setdefault(reason, {"count": 0, "examples": []})
    entry["count"] += 1
    limited_append(entry["examples"], label)


def product_issue_types(category_id, product, seen_keys):
    issues = []
    label = product_label(product)
    key = product_key(product)
    if not key:
        issues.append(("缺唯一键", ""))
    elif key in seen_keys:
        issues.append(("重复唯一键", ""))

    if not product.get("sku"):
        issues.append(("缺 SKU", ""))
    if not product.get("name"):
        issues.append(("缺名称", ""))
    if not has_image(product):
        issues.append(("缺图", missing_image_reason(category_id, product)))
    if product.get("status") not in VALID_STATUSES:
        issues.append(("异常状态", str(product.get("status", ""))))

    max_images = IMAGE_POLICIES.get(category_id, {}).get("maxImages")
    images = product.get("images", [])
    if isinstance(max_images, int) and max_images > 0 and isinstance(images, list) and len(images) > max_images:
        issues.append(("图片超限", f"{len(images)} 张，限制 {max_images} 张"))
    return label, key, issues


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
    missing_image_reasons = {}
    issue_keys = []
    issue_key_seen = set()

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
        product_has_issue = False
        if not key:
            missing_key_count += 1
            limited_append(missing_key_examples, label or "(未命名产品)")
            product_has_issue = True
        elif key in seen:
            duplicate_count += 1
            limited_append(duplicate_examples, label or key)
            product_has_issue = True
        else:
            seen.add(key)

        if not product.get("sku"):
            missing_sku_count += 1
            limited_append(missing_sku_examples, label or key or "(未命名产品)")
            product_has_issue = True
        if not product.get("name"):
            missing_name_count += 1
            limited_append(missing_name_examples, label or key or "(未命名产品)")
            product_has_issue = True
        if not has_image(product):
            missing_image_count += 1
            limited_append(missing_image_examples, label or key or "(未命名产品)")
            add_missing_image_reason(
                missing_image_reasons,
                missing_image_reason(category_id, product),
                label or key or "(未命名产品)",
            )
            product_has_issue = True
        if product.get("status") not in VALID_STATUSES:
            invalid_status_count += 1
            limited_append(invalid_status_examples, label or key or "(未命名产品)")
            product_has_issue = True

        images = product.get("images", [])
        if isinstance(max_images, int) and max_images > 0 and isinstance(images, list) and len(images) > max_images:
            over_image_limit_count += 1
            limited_append(over_image_limit_examples, f"{label or key}: {len(images)} 张")
            product_has_issue = True

        issue_key = key or label
        if product_has_issue and issue_key and issue_key not in issue_key_seen:
            issue_keys.append(issue_key)
            issue_key_seen.add(issue_key)

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
        "issueKeys": issue_keys,
        "missingImageReasons": missing_image_reasons,
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


def catalog_health_csv():
    data = load_catalog()
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["category_id", "category_name", "issue_type", "product_key", "product_label", "reason"])

    for category in data.get("categories", []):
        category_id = category.get("id", "")
        category_name = category.get("name", category_id)
        seen = set()
        for product in category.get("products", []):
            label, key, issues = product_issue_types(category_id, product, seen)
            if key:
                seen.add(key)
            for issue_type, reason in issues:
                writer.writerow([category_id, category_name, issue_type, key, label, reason])

    return output.getvalue()

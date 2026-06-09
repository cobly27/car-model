"""Shared helpers for incremental product merges."""

import json


def load_json(path, default=None):
    if not path.exists():
        if default is not None:
            return default
        raise FileNotFoundError(path.name)
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def clean_images(images, limit=None):
    cleaned = []
    for image in images or []:
        if image and image not in cleaned:
            cleaned.append(image)
        if limit and len(cleaned) >= limit:
            break
    return cleaned


def get_or_create_category(data, category_id, category_name):
    categories = data.setdefault("categories", [])
    for index, category in enumerate(categories):
        if category.get("id") == category_id:
            category.setdefault("name", category_name)
            category.setdefault("products", [])
            return index, category

    category = {"id": category_id, "name": category_name, "products": []}
    categories.append(category)
    return len(categories) - 1, category


def update_total_products(data):
    total = sum(len(category.get("products", [])) for category in data.get("categories", []))
    data.setdefault("meta", {})["total_products"] = total
    return total


def merge_result_summary(result, *, original_count_key, final_count_key, extra=None):
    summary = {
        original_count_key: result["original_count"],
        "fetched_count": result["fetched_count"],
        "added_count": result["added_count"],
        "updated_count": result["updated_count"],
        "unchanged_count": result["unchanged_count"],
        "preserved_count": result["preserved_count"],
        "duplicate_count": result["duplicate_count"],
        final_count_key: len(result["updated_products"]),
        "total_products": result["total_products"],
    }
    if extra:
        summary.update(extra)
    return summary


def merge_incremental_products(
    *,
    data,
    incoming_products,
    category_id,
    category_name,
    key_fn,
    normalize_fn,
    merge_fn,
    changed_keys,
    sort_key=None,
    reverse=False,
):
    category_idx, category = get_or_create_category(data, category_id, category_name)
    existing_products = category.get("products", [])
    existing_by_key = {
        key: product
        for product in existing_products
        if (key := key_fn(product)) is not None
    }

    updated_products = []
    fetched_keys = set()
    added_count = 0
    updated_count = 0
    unchanged_count = 0
    duplicate_count = 0

    for raw_product in incoming_products:
        normalized = normalize_fn(raw_product)
        key = key_fn(normalized)
        if key is None:
            raise RuntimeError(f"产品缺少唯一键：{normalized}")
        if key in fetched_keys:
            duplicate_count += 1
            continue
        fetched_keys.add(key)

        existing = existing_by_key.get(key)
        if existing:
            merged = merge_fn(existing, normalized)
            if any(merged.get(field) != existing.get(field) for field in changed_keys):
                updated_count += 1
            else:
                unchanged_count += 1
            updated_products.append(merged)
        else:
            added_count += 1
            updated_products.append(normalized)

    preserved_products = [
        product for product in existing_products
        if key_fn(product) not in fetched_keys
    ]
    updated_products.extend(preserved_products)

    if sort_key:
        updated_products.sort(key=sort_key, reverse=reverse)

    data["categories"][category_idx]["products"] = updated_products
    total_products = update_total_products(data)

    return {
        "category_idx": category_idx,
        "original_count": len(existing_products),
        "updated_products": updated_products,
        "fetched_count": len(fetched_keys),
        "added_count": added_count,
        "updated_count": updated_count,
        "unchanged_count": unchanged_count,
        "preserved_count": len(preserved_products),
        "duplicate_count": duplicate_count,
        "total_products": total_products,
    }

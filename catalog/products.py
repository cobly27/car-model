"""Product normalization helpers shared by brand merge scripts."""

from .merge import clean_images


def is_blank(value):
    return value is None or (isinstance(value, str) and not value.strip())


def normalized_images(product, limit=None):
    images = clean_images(product.get("images", []), limit)
    primary = product.get("image")
    if primary and primary not in images:
        images.insert(0, primary)
    return clean_images(images, limit)


def normalize_catalog_product(
    product,
    *,
    key_field="detail_id",
    key_label="产品",
    sku_prefix=None,
    default_status="Released",
    max_images=None,
    stringify_key=False,
):
    """Return a product with stable core catalog fields.

    Brand scrapers can keep their own metadata fields, but every item entering
    the merge layer should have a usable unique key, sku, name, status, image,
    and images list.
    """

    normalized = dict(product)
    key = normalized.get(key_field)
    if is_blank(key):
        raise RuntimeError(f"{key_label}缺少 {key_field}：{product}")

    if stringify_key:
        key = str(key).strip()
        normalized[key_field] = key

    sku = normalized.get("sku")
    if is_blank(sku):
        sku = f"{sku_prefix}-{key}" if sku_prefix else str(key)
    normalized["sku"] = str(sku).strip()

    name = normalized.get("name")
    normalized["name"] = str(name or normalized["sku"] or key).strip()
    normalized["status"] = normalized.get("status") or default_status

    images = normalized_images(normalized, max_images)
    normalized["images"] = images
    normalized["image"] = images[0] if images else normalized.get("image", "")
    return normalized


def choose_merged_images(existing, incoming, *, limit=None, min_incoming_images=1):
    incoming_images = normalized_images(incoming, limit)
    existing_images = normalized_images(existing, limit)

    if len(incoming_images) >= min_incoming_images:
        images = incoming_images
    elif existing_images:
        images = existing_images
    else:
        images = incoming_images

    image = images[0] if images else incoming.get("image") or existing.get("image", "")
    if image and image not in images:
        images.insert(0, image)
    return image, clean_images(images, limit)

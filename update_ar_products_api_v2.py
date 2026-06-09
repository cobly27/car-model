#!/usr/bin/env python3
"""使用API同步AR产品清单，保留官网本次未返回的历史产品。"""

import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
PRODUCTS_PATH = BASE_DIR / 'minigt_products.json'
API_PRODUCTS_PATH = BASE_DIR / 'ar_products_api.json'
SUMMARY_PATH = BASE_DIR / 'ar_update_summary.json'


def load_json(path, default=None):
    if not path.exists():
        if default is not None:
            return default
        raise FileNotFoundError(path.name)
    with path.open('r', encoding='utf-8') as f:
        return json.load(f)


def save_json(path, data):
    with path.open('w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_ar_category(data):
    for idx, cat in enumerate(data.get('categories', [])):
        if cat.get('id') == 'ar':
            return idx, cat
    return -1, None


def clean_images(images):
    if not images:
        return []

    cleaned = []
    for image in images:
        if image and image not in cleaned:
            cleaned.append(image)
    return cleaned


def choose_images(existing_product, api_product):
    """保留现有多图；否则使用API封面图。"""
    existing_images = clean_images(existing_product.get('images', []))
    api_images = clean_images(api_product.get('images', []))

    if len(existing_images) > 1:
        images = existing_images
    elif api_images:
        images = api_images
    elif existing_images:
        images = existing_images
    else:
        images = []

    image = images[0] if images else api_product.get('image') or existing_product.get('image', '')
    if image and not images:
        images = [image]
    return image, images


def update_total_products(data):
    total = sum(len(cat.get('products', [])) for cat in data.get('categories', []))
    data.setdefault('meta', {})['total_products'] = total
    return total

def main():
    # 读取现有数据
    print("读取现有产品数据...")
    data = load_json(PRODUCTS_PATH)

    # 找到AR分类
    ar_category_idx, ar_category = get_ar_category(data)

    if ar_category_idx == -1:
        print("错误：未找到AR分类！")
        sys.exit(1)

    existing_ar_products = ar_category.get('products', [])
    print(f"现有 {len(existing_ar_products)} 个AR产品")

    # 读取API抓取的数据
    print()
    print("读取API抓取的产品数据...")
    if not API_PRODUCTS_PATH.exists():
        print("错误：未找到 ar_products_api.json 文件")
        sys.exit(1)

    api_products = load_json(API_PRODUCTS_PATH)

    if not isinstance(api_products, list) or not api_products:
        print("错误：API产品数据为空或格式错误")
        sys.exit(1)

    print(f"API抓取了 {len(api_products)} 个产品")

    # 创建现有产品的字典
    existing_dict = {}
    for product in existing_ar_products:
        pid = product.get('detail_id')
        if pid is not None and pid not in existing_dict:
            existing_dict[pid] = product

    # 去重和更新
    updated_products = []
    fetched_ids = set()
    added_count = 0
    updated_count = 0
    unchanged_count = 0
    duplicate_count = 0

    for api_product in api_products:
        pid = api_product.get('detail_id')
        if pid is None:
            print(f"错误：API产品缺少 detail_id：{api_product}")
            sys.exit(1)

        if pid in fetched_ids:
            duplicate_count += 1
            print(f"  ⚠️ 跳过重复产品 detail_id={pid}")
            continue

        fetched_ids.add(pid)
        if pid in existing_dict:
            old_product = existing_dict[pid]
            image, images = choose_images(old_product, api_product)
            merged_product = dict(old_product)
            merged_product.update({
                'detail_id': pid,
                'name': api_product.get('name', old_product.get('name', '')),
                'sku': api_product.get('sku', old_product.get('sku', '')),
                'status': api_product.get('status', old_product.get('status', 'Released')),
                'image': image,
                'images': images,
            })

            changed = any(
                merged_product.get(key) != old_product.get(key)
                for key in ('name', 'sku', 'status', 'image', 'images')
            )
            if changed:
                updated_count += 1
                print(f"  ⚡ 更新: {old_product.get('name', pid)} → {merged_product.get('name', '')}")
            else:
                unchanged_count += 1
            updated_products.append(merged_product)
        else:
            added_count += 1
            new_product = dict(api_product)
            new_product['images'] = clean_images(new_product.get('images', []))
            if new_product.get('image') and not new_product['images']:
                new_product['images'] = [new_product['image']]
            print(f"  + 新增: {new_product.get('name', '')} ({new_product.get('sku', '')})")
            updated_products.append(new_product)

    preserved_products = [p for p in existing_ar_products if p.get('detail_id') not in fetched_ids]
    preserved_count = len(preserved_products)
    if preserved_count:
        print(f"  ⏸ 保留官网本次未返回的旧产品：{preserved_count} 个")
        updated_products.extend(preserved_products)

    print()
    print(f"统计:")
    print(f"  - 新增: {added_count}")
    print(f"  - 更新: {updated_count}")
    print(f"  - 未变: {unchanged_count}")
    print(f"  - 保留旧产品: {preserved_count}")
    print(f"  - 跳过重复API产品: {duplicate_count}")

    # 更新数据
    data['categories'][ar_category_idx]['products'] = updated_products
    total_products = update_total_products(data)

    # 保存更新后的数据
    print()
    print("保存更新后的数据...")
    save_json(PRODUCTS_PATH, data)

    scrape_summary = load_json(SUMMARY_PATH, {})
    summary = {
        **scrape_summary,
        'fetched_count': len(fetched_ids),
        'original_ar_count': len(existing_ar_products),
        'added_count': added_count,
        'updated_count': updated_count,
        'unchanged_count': unchanged_count,
        'preserved_count': preserved_count,
        'duplicate_count': duplicate_count,
        'final_ar_count': len(updated_products),
        'total_products': total_products,
    }
    save_json(SUMMARY_PATH, summary)

    print()
    print("="*60)
    print("完成！")
    print("="*60)
    print(f"AR 分类现在有 {len(updated_products)} 款产品")

if __name__ == '__main__':
    main()

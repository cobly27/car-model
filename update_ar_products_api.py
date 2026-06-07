#!/usr/bin/env python3
"""使用API更新AR产品"""

import json
import os

def main():
    # 读取现有数据
    print("读取现有产品数据...")
    with open('minigt_products.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 找到AR分类
    ar_category_idx = -1
    for idx, cat in enumerate(data['categories']):
        if cat['id'] == 'ar':
            ar_category_idx = idx
            break

    if ar_category_idx == -1:
        print("错误：未找到AR分类！")
        return

    existing_ar_products = data['categories'][ar_category_idx].get('products', [])
    existing_ids = set(p['detail_id'] for p in existing_ar_products)
    print(f"现有 {len(existing_ar_products)} 个AR产品")

    # 读取API抓取的数据
    print()
    print("读取API抓取的产品数据...")
    if not os.path.exists('ar_products_api.json'):
        print("错误：未找到 ar_products_api.json 文件")
        return

    with open('ar_products_api.json', 'r', encoding='utf-8') as f:
        new_products = json.load(f)

    print(f"API抓取了 {len(new_products)} 个产品")

    # 去重 - 只添加新产品
    products_to_add = []
    for p in new_products:
        if p['detail_id'] not in existing_ids:
            products_to_add.append(p)
            print(f"  + 新增: {p['name']} ({p['sku']})")

    print()
    print(f"准备添加 {len(products_to_add)} 个新产品")

    # 合并产品
    updated_ar_products = existing_ar_products + products_to_add

    # 更新数据
    data['categories'][ar_category_idx]['products'] = updated_ar_products

    # 保存更新后的数据
    print()
    print("保存更新后的数据...")
    with open('minigt_products.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print()
    print("="*60)
    print("完成！")
    print("="*60)
    print(f"AR 分类现在有 {len(updated_ar_products)} 款产品")
    print(f"  - 原有: {len(existing_ar_products)}")
    print(f"  - 新增: {len(products_to_add)}")

if __name__ == '__main__':
    main()

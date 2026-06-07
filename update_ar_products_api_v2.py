#!/usr/bin/env python3
"""使用API更新AR产品，替换错误数据"""

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

    # 创建现有产品的字典
    existing_dict = {p['detail_id']: p for p in existing_ar_products}

    # 去重和更新
    products_to_add = []
    products_updated = []
    products_unchanged = []

    for p in new_products:
        pid = p['detail_id']
        if pid in existing_dict:
            # 检查是否相同
            old_p = existing_dict[pid]
            # 比较关键字段
            if (p.get('name') != old_p.get('name') or
                p.get('sku') != old_p.get('sku') or
                p.get('image') != old_p.get('image')):
                # 数据不同，需要更新
                products_updated.append((old_p, p))
                print(f"  ⚡ 更新: {old_p['name']} → {p['name']}")
            else:
                # 数据相同，保持不变
                products_unchanged.append(pid)
        else:
            # 新产品，添加
            products_to_add.append(p)
            print(f"  + 新增: {p['name']} ({p['sku']})")

    print()
    print(f"统计:")
    print(f"  - 新增: {len(products_to_add)}")
    print(f"  - 更新: {len(products_updated)}")
    print(f"  - 未变: {len(products_unchanged)}")

    # 构建新的产品列表
    # 保留未变化的和新的产品
    updated_products = []

    for p in new_products:
        pid = p['detail_id']
        if pid in existing_dict:
            # 在现有数据中找
            old_p = existing_dict[pid]
            # 检查是否需要更新
            need_update = False
            for old_prod, new_prod in products_updated:
                if old_prod['detail_id'] == pid:
                    updated_products.append(new_prod)  # 使用新数据
                    need_update = True
                    break
            if not need_update:
                updated_products.append(old_p)  # 使用旧数据
        else:
            updated_products.append(p)  # 新产品

    # 更新数据
    data['categories'][ar_category_idx]['products'] = updated_products

    # 保存更新后的数据
    print()
    print("保存更新后的数据...")
    with open('minigt_products.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print()
    print("="*60)
    print("完成！")
    print("="*60)
    print(f"AR 分类现在有 {len(updated_products)} 款产品")

if __name__ == '__main__':
    main()

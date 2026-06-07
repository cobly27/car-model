
#!/usr/bin/env python3
"""Update AR products with incremental updates"""

import json
import sys
import os

# Add current directory to path so we can import scrape_ar
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scrape_ar import scrape_ar_products


def main():
    # 读取现有数据
    print("Reading existing product data...")
    with open('minigt_products.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 获取现有 AR 产品
    existing_ar_products = []
    ar_category_idx = -1
    
    for idx, cat in enumerate(data['categories']):
        if cat['id'] == 'ar':
            ar_category_idx = idx
            existing_ar_products = cat.get('products', [])
            break
    
    if ar_category_idx == -1:
        print("Error: AR category not found!")
        return
    
    print(f"Found {len(existing_ar_products)} existing AR products")
    
    # 抓取所有产品
    print("\n--- Start scraping new products ---")
    new_products = scrape_ar_products(limit=None)  # None = all products
    print(f"\nScraped {len(new_products)} products")
    
    # 去重 - 基于 detail_id
    existing_ids = set(p['detail_id'] for p in existing_ar_products)
    
    # 分离新产品和已有产品
    products_to_add = []
    for p in new_products:
        if p['detail_id'] not in existing_ids:
            products_to_add.append(p)
            print(f"  + 新产品: {p['name']} ({p['sku']})")
    
    print(f"\n准备添加 {len(products_to_add)} 个新产品")
    
    # 合并现有产品和新产品
    updated_ar_products = existing_ar_products + products_to_add
    
    # 更新数据
    data['categories'][ar_category_idx]['products'] = updated_ar_products
    
    # 保存更新后的数据
    print("\nSaving updated data...")
    with open('minigt_products.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print("\n--- 完成 ---")
    print(f"AR 分类现在有 {len(updated_ar_products)} 款产品")
    print(f"  - 原有: {len(existing_ar_products)}")
    print(f"  - 新增: {len(products_to_add)}")


if __name__ == '__main__':
    main()


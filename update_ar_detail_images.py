#!/usr/bin/env python3
"""更新AR产品的图片数据"""

import json
import os

def main():
    print("开始更新AR产品图片数据...")
    print()

    # 读取详情页抓取的数据
    print("读取详情页抓取的数据...")
    if not os.path.exists('ar_products_detail.json'):
        print("错误：未找到 ar_products_detail.json 文件")
        print("请先运行 scrape_ar_detail_images.py 抓取图片")
        return

    with open('ar_products_detail.json', 'r', encoding='utf-8') as f:
        detail_data = json.load(f)

    detail_products = detail_data.get('products', [])
    print(f"详情页数据：{len(detail_products)} 个产品")
    print(f"成功获取图片：{detail_data.get('success_count', 0)} 个")
    print(f"获取失败：{detail_data.get('failed_count', 0)} 个")
    print()

    # 创建详情数据字典
    detail_dict = {p['detail_id']: p for p in detail_products}
    print(f"已构建 {len(detail_dict)} 个产品的详情数据字典")

    # 读取现有的minigt_products.json
    print()
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

    ar_products = data['categories'][ar_category_idx].get('products', [])
    print(f"AR分类现有 {len(ar_products)} 个产品")

    # 更新每个产品的图片数据
    updated_count = 0
    for product in ar_products:
        pid = product['detail_id']
        if pid in detail_dict:
            detail = detail_dict[pid]
            # 更新图片数据
            product['image'] = detail.get('image', product.get('image', ''))
            product['images'] = detail.get('images', [product.get('image', '')])
            updated_count += 1

    print()
    print(f"已更新 {updated_count} 个产品的图片数据")

    # 保存更新后的数据
    print()
    print("保存更新后的数据...")
    with open('minigt_products.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print()
    print("="*60)
    print("完成！")
    print("="*60)
    print(f"AR 分类现在有 {len(ar_products)} 款产品")
    print(f"更新了 {updated_count} 个产品的图片数据")

if __name__ == '__main__':
    main()

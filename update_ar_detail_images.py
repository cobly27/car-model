#!/usr/bin/env python3
"""更新AR产品的图片数据"""

import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DETAIL_PATH = BASE_DIR / 'ar_products_detail.json'
PRODUCTS_PATH = BASE_DIR / 'minigt_products.json'
SUMMARY_PATH = BASE_DIR / 'ar_update_summary.json'


def load_summary():
    if not SUMMARY_PATH.exists():
        return {}

    with SUMMARY_PATH.open('r', encoding='utf-8') as f:
        return json.load(f)


def save_summary(summary):
    with SUMMARY_PATH.open('w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)


def update_total_products(data):
    total = sum(len(cat.get('products', [])) for cat in data.get('categories', []))
    data.setdefault('meta', {})['total_products'] = total
    return total

def main():
    print("开始更新AR产品图片数据...")
    print()

    # 读取详情页抓取的数据
    print("读取详情页抓取的数据...")
    if not DETAIL_PATH.exists():
        print("错误：未找到 ar_products_detail.json 文件")
        print("请先运行 scrape_ar_detail_images.py 抓取图片")
        sys.exit(1)

    with DETAIL_PATH.open('r', encoding='utf-8') as f:
        detail_data = json.load(f)

    detail_products = detail_data.get('products', [])
    print(f"详情页数据：{len(detail_products)} 个产品")
    print(f"成功获取图片：{detail_data.get('success_count', 0)} 个")
    print(f"获取失败：{detail_data.get('failed_count', 0)} 个")
    print()

    if not detail_products:
        print("错误：详情页产品数据为空")
        sys.exit(1)

    # 创建详情数据字典
    detail_dict = {p['detail_id']: p for p in detail_products}
    print(f"已构建 {len(detail_dict)} 个产品的详情数据字典")
    failed_ids = set(detail_data.get('failed_ids', []))

    # 读取现有的minigt_products.json
    print()
    print("读取现有产品数据...")
    with PRODUCTS_PATH.open('r', encoding='utf-8') as f:
        data = json.load(f)

    # 找到AR分类
    ar_category_idx = -1
    for idx, cat in enumerate(data['categories']):
        if cat['id'] == 'ar':
            ar_category_idx = idx
            break

    if ar_category_idx == -1:
        print("错误：未找到AR分类！")
        sys.exit(1)

    ar_products = data['categories'][ar_category_idx].get('products', [])
    print(f"AR分类现有 {len(ar_products)} 个产品")

    # 更新每个产品的图片数据
    updated_count = 0
    skipped_failed_count = 0
    missing_detail_count = 0
    for product in ar_products:
        pid = product['detail_id']
        if pid in failed_ids:
            skipped_failed_count += 1
            continue

        if pid in detail_dict:
            detail = detail_dict[pid]
            # 更新图片数据
            product['image'] = detail.get('image', product.get('image', ''))
            product['images'] = detail.get('images', [product.get('image', '')])
            updated_count += 1
        else:
            missing_detail_count += 1

    print()
    print(f"已更新 {updated_count} 个产品的图片数据")
    print(f"详情图失败保留原图 {skipped_failed_count} 个")
    print(f"缺少详情图数据 {missing_detail_count} 个")

    if updated_count == 0 and detail_data.get('success_count', 0):
        print("错误：详情图数据与AR分类产品无法匹配")
        sys.exit(1)

    # 保存更新后的数据
    print()
    print("保存更新后的数据...")
    total_products = update_total_products(data)
    with PRODUCTS_PATH.open('w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    summary = load_summary()
    summary.update({
        'detail_total': detail_data.get('total', len(detail_products)),
        'detail_success_count': detail_data.get('success_count', 0),
        'detail_failed_count': detail_data.get('failed_count', 0),
        'images_updated_count': updated_count,
        'images_skipped_failed_count': skipped_failed_count,
        'missing_detail_count': missing_detail_count,
        'final_ar_count': len(ar_products),
        'total_products': total_products,
    })
    save_summary(summary)

    print()
    print("="*60)
    print("完成！")
    print("="*60)
    print(f"AR 分类现在有 {len(ar_products)} 款产品")
    print(f"更新了 {updated_count} 个产品的图片数据")

if __name__ == '__main__':
    main()

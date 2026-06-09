#!/usr/bin/env python3
"""使用API抓取AR产品"""

import requests
import json
import sys
from pathlib import Path

BASE_URL = "https://www.armodel.com.cn"
API_URL = f"{BASE_URL}/api/product/list"
BASE_DIR = Path(__file__).resolve().parent
OUTPUT_PATH = BASE_DIR / 'ar_products_api.json'
SUMMARY_PATH = BASE_DIR / 'ar_update_summary.json'

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "X-Requested-With": "XMLHttpRequest",
}

def fetch_all_products():
    """获取所有产品"""
    all_products = []
    page = 1
    limit = 100
    total_count = 0

    print("开始抓取AR产品...")
    print()

    while True:
        url = f"{API_URL}?page={page}&limit={limit}"
        print(f"获取第 {page} 页...")

        try:
            resp = requests.get(url, headers=HEADERS, timeout=30)
            resp.raise_for_status()

            data = resp.json()

            if data.get('code') in [1, '1', 'success']:
                products = data.get('data', {}).get('list', [])
                raw_total_count = data.get('data', {}).get('count', len(products))
                try:
                    total_count = int(raw_total_count)
                except (TypeError, ValueError):
                    total_count = len(products)

                if not products:
                    print(f"第 {page} 页没有产品，停止抓取")
                    break

                print(f"  获取到 {len(products)} 个产品")

                for p in products:
                    # 解析param_content获取更多信息
                    param_content = p.get('param_content', '[]')
                    try:
                        params = json.loads(param_content)
                        product_no = ''
                        for param in params:
                            if param.get('key') == '款号':
                                product_no = param.get('value', '')
                                break
                    except:
                        product_no = p.get('product_no', '')

                    product_info = {
                        'detail_id': p.get('id'),
                        'name': p.get('name', ''),
                        'sku': product_no or p.get('product_no', ''),
                        'status': 'Released',  # 默认值
                        'image': p.get('cover_pic', ''),
                        'images': [p.get('cover_pic', '')] if p.get('cover_pic') else [],
                    }
                    all_products.append(product_info)

                # 检查是否获取完毕
                if len(all_products) >= total_count:
                    print(f"已获取全部 {total_count} 个产品")
                    break

                page += 1

            else:
                raise RuntimeError(f"API返回错误: {data.get('info', '未知错误')}")

        except Exception as e:
            raise RuntimeError(f"请求失败: {e}") from e

    print()
    print(f"共抓取 {len(all_products)} 个产品")
    summary = {
        'source': BASE_URL,
        'fetched_count': len(all_products),
        'api_total_count': total_count,
        'page_count': page,
        'page_size': limit,
    }
    with SUMMARY_PATH.open('w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    return all_products

def fetch_product_details(product_id):
    """获取产品详情"""
    # 可以根据需要实现
    return {}

if __name__ == '__main__':
    try:
        products = fetch_all_products()
    except Exception as e:
        print(f"错误：{e}")
        sys.exit(1)

    if not products:
        print("错误：未抓取到任何 AR 产品")
        sys.exit(1)

    print()
    print("产品列表:")
    for i, p in enumerate(products[:20], 1):
        print(f"{i}. [{p['sku']}] {p['name']}")

    if len(products) > 20:
        print(f"... 还有 {len(products) - 20} 个产品")

    # 保存为JSON
    with OUTPUT_PATH.open('w', encoding='utf-8') as f:
        json.dump(products, f, ensure_ascii=False, indent=2)
    print()
    print(f"已保存到 {OUTPUT_PATH.name}")

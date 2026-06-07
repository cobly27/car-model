#!/usr/bin/env python3
"""使用API抓取AR产品"""

import requests
import json

BASE_URL = "https://www.armodel.com.cn"
API_URL = f"{BASE_URL}/api/product/list"

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
                total_count = data.get('data', {}).get('count', len(products))

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
                print(f"API返回错误: {data.get('info', '未知错误')}")
                break

        except Exception as e:
            print(f"请求失败: {e}")
            break

    print()
    print(f"共抓取 {len(all_products)} 个产品")
    return all_products

def fetch_product_details(product_id):
    """获取产品详情"""
    # 可以根据需要实现
    return {}

if __name__ == '__main__':
    products = fetch_all_products()
    print()
    print("产品列表:")
    for i, p in enumerate(products[:20], 1):
        print(f"{i}. [{p['sku']}] {p['name']}")

    if len(products) > 20:
        print(f"... 还有 {len(products) - 20} 个产品")

    # 保存为JSON
    with open('ar_products_api.json', 'w', encoding='utf-8') as f:
        json.dump(products, f, ensure_ascii=False, indent=2)
    print()
    print(f"已保存到 ar_products_api.json")

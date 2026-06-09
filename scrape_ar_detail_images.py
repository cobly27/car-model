#!/usr/bin/env python3
"""抓取AR产品详情页的所有图片 - 精确抓取轮播图区域"""

import requests
from bs4 import BeautifulSoup
import json
import time
import sys
from pathlib import Path

BASE_URL = "https://www.armodel.com.cn"
BASE_DIR = Path(__file__).resolve().parent
INPUT_PATH = BASE_DIR / 'ar_products_api.json'
OUTPUT_PATH = BASE_DIR / 'ar_products_detail.json'

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

REQUEST_DELAY = 1  # 每次请求间隔秒数
OUTPUT_FILE = OUTPUT_PATH.name

def scrape_detail_images(product_id):
    """抓取详情页的所有图片 - 精确抓取轮播图区域的图片"""
    url = f"{BASE_URL}/product/detail.html?id={product_id}"

    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, 'html.parser')

        # 精确查找产品轮播图区域：details-img-owl 容器内的 slide-item
        product_images = []
        
        # 1. 找到主轮播图容器
        carousel = soup.find('div', class_=['details-img-owl', 'owl-carousel'])
        if carousel:
            # 2. 找到所有 slide-item
            slide_items = carousel.find_all('div', class_='slide-item')
            for item in slide_items:
                # 3. 从 slide-item 内的 a 标签 href 获取图片（这个是大图）
                a_tag = item.find('a')
                if a_tag and a_tag.get('href'):
                    img_url = a_tag['href']
                    if img_url and img_url not in product_images:
                        product_images.append(img_url)
        
        # 如果轮播图没找到，回退到原方案
        if not product_images:
            # 查找所有图片
            all_imgs = soup.find_all('img')

            # 提取产品相关图片URL
            for img in all_imgs:
                src = img.get('src', '') or img.get('data-src', '')
                # 筛选AR官网的图片
                if src and ('armodel' in src or 'doubao' in src or 'uc.' in src):
                    if src not in product_images:  # 去重
                        product_images.append(src)

        return product_images

    except Exception as e:
        print(f"  ⚠️ 抓取失败: {e}")
        return []

def load_existing_products():
    """加载已存在的产品列表"""
    if INPUT_PATH.exists():
        with INPUT_PATH.open('r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_progress(products, failed_ids):
    """保存抓取进度"""
    failed_ids = list(dict.fromkeys(failed_ids))
    success_count = len([p for p in products if p.get('detail_id') not in failed_ids and p.get('images')])
    with OUTPUT_PATH.open('w', encoding='utf-8') as f:
        json.dump({
            'products': products,
            'failed_ids': failed_ids,
            'total': len(products),
            'success_count': success_count,
            'failed_count': len(failed_ids)
        }, f, ensure_ascii=False, indent=2)

def main():
    print("开始抓取AR产品详情页图片（精确抓取轮播图区域）")
    print()

    # 加载产品列表
    products = load_existing_products()
    if not products:
        print("错误：未找到 ar_products_api.json 文件")
        sys.exit(1)

    print(f"共有 {len(products)} 个产品需要抓取")
    print()

    # 旧结果只用于提示；本次更新需要重新按 detail_id 抓取当前API列表。
    if OUTPUT_PATH.exists():
        try:
            with OUTPUT_PATH.open('r', encoding='utf-8') as f:
                existing_data = json.load(f)
                existing_products = existing_data.get('products', [])
                print(f"找到旧详情图结果：{len(existing_products)} 个产品；本次将重新抓取当前列表")
        except:
            pass

    # 初始化失败ID列表
    failed_ids = []

    # 统计
    total_images = 0

    print("从第 1 个产品开始抓取")
    print()

    # 抓取每个产品的详情页图片
    for i, product in enumerate(products, 1):
        product_id = product['detail_id']
        product_name = product.get('name', '未知产品')

        print(f"[{i}/{len(products)}] 抓取 ID={product_id}: {product_name[:40]}...")

        # 抓取图片
        images = scrape_detail_images(product_id)

        if images:
            product['images'] = images
            product['image'] = images[0] if images else ''
            total_images += len(images)
            print(f"  ✓ 获取到 {len(images)} 张图片")
        else:
            product['images'] = [product.get('image', '')]
            product['image'] = product.get('image', '')
            failed_ids.append(product_id)
            print(f"  ⚠️ 未获取到图片")

        # 保存进度（每10个产品保存一次）
        if i % 10 == 0:
            save_progress(products[:i], failed_ids)
            print(f"  💾 已保存进度")

        # 延迟
        time.sleep(REQUEST_DELAY)

    # 最终保存
    save_progress(products, failed_ids)

    print()
    print("=" * 60)
    print("抓取完成！")
    print("=" * 60)
    print(f"总共处理：{len(products)} 个产品")
    print(f"成功获取图片：{len(products) - len(failed_ids)} 个")
    print(f"获取图片失败：{len(failed_ids)} 个")
    print(f"总图片数：{total_images} 张")
    print()
    print(f"结果已保存到：{OUTPUT_FILE}")

if __name__ == '__main__':
    main()

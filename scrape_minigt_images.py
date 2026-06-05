#!/usr/bin/env python3
"""
MINI GT 产品图片抓取 — 按轮播位置提取，避免大图/缩略图重复。
策略：data-hash="d" = 位置1主图 → 跳过第一个非d数据块(重复) → 取后续数据块作为位置2、3
"""

import requests, json, re, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urljoin

BASE = "https://minigt.tsm-models.com"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
}
WORKERS = 10
REQUEST_TIMEOUT = 45
MAX_RETRIES = 2


def fix_url(src):
    if not src:
        return ""
    src = src.strip()
    if src.startswith("http"):
        return src
    return urljoin(BASE, src)


def extract_images_by_position(html):
    """
    核心算法：
    - 所有产品详情页的图片轮播区都有 data-hash 属性标记每个位置
    - data-hash="d" 始终是位置1的主图
    - 后续 data-hash 块中，第一个是位置1的缩略图（重复！），跳过
    - 再后面的 data-hash 块才是位置2、位置3的图片
    """
    # Step 1: 定位轮播区域
    carousel_start = -1
    for marker in ['owl-carousel-5', 'products_gif', 'product_box']:
        carousel_start = html.find(marker)
        if carousel_start > 0:
            break

    if carousel_start <= 0:
        return []

    # 轮播区域截止于"產品 輪播圖 (小圖)"或 owl-carousel-1（小图轮播）
    carousel_end = html.find('產品 輪播圖 (小圖)', carousel_start)
    if carousel_end < 0:
        carousel_end = html.find('owl-carousel-1', carousel_start)
    if carousel_end < 0:
        carousel_end = len(html)

    segment = html[carousel_start:carousel_end]

    # Step 2: 提取所有 pro_wrap-d 数据块（含 HTML 注释中的）
    wrap_pattern = re.compile(
        r'<div\s+class="[^"]*pro_wrap-d[^"]*"\s+data-hash="([^"]*)"'
        r'[^>]*>(.*?)</div>\s*</div>',
        re.DOTALL
    )
    blocks = wrap_pattern.findall(segment)

    if not blocks:
        # 无 data-hash 块时，回退到全局提取（排除关联产品区）
        related = html.find('related_pro')
        body = html[:related] if related > 0 else html
        body = re.sub(r'<!--.*?-->', '', body, flags=re.DOTALL)
        all_imgs = re.findall(r'<img[^>]*src="([^"]*(?:picfile|product_pic|upload)/[^"]*)"', body)
        seen = set()
        result = []
        for img in all_imgs:
            full = fix_url(img)
            if full and full not in seen:
                seen.add(full)
                result.append(full)
            if len(result) >= 3:
                break
        return result

    # Step 3: 按位置提取
    images = []

    # 位置1: data-hash="d"
    for hash_val, block in blocks:
        if hash_val == 'd':
            # 优先非缩略图（picfile/、product_pic_big/）
            img = re.search(
                r'<img[^>]*src="([^"]*(?:/picfile/|/product_pic_big/)[^"]*)"',
                block
            )
            if not img:
                # 回退到任意图片
                img = re.search(r'<img[^>]*src="([^"]*(?:upload|picfile|product_pic)[^"]*)"', block)
            if img:
                images.append(fix_url(img.group(1)))
            break

    # 位置2、3: 跳过第一个非d数据块（它是位置1的缩略图重复），取接下来2个
    skipped_first = False
    for hash_val, block in blocks:
        if hash_val == 'd':
            continue
        if not skipped_first:
            skipped_first = True
            continue

        # 优先取大图
        img = re.search(
            r'<img[^>]*src="([^"]*(?:/picfile/|/product_pic_big/)[^"]*)"',
            block
        )
        if not img:
            img = re.search(r'<img[^>]*src="([^"]*(?:upload|picfile|product_pic)[^"]*)"', block)
        if img:
            full_url = fix_url(img.group(1))
            # 避免与位置1主图重复（某些边缘情况）
            if full_url and full_url not in images:
                images.append(full_url)

        if len(images) >= 3:
            break

    return images[:3]


def scrape_detail(product):
    """抓取单个产品详情页的图片"""
    did = product.get('detail_id')
    if not did:
        return product, []

    url = f"{BASE}/index.php?action=product-detail&id={did}"

    for attempt in range(MAX_RETRIES + 1):
        try:
            r = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            r.encoding = 'utf-8'
            if r.status_code != 200:
                raise Exception(f"HTTP {r.status_code}")
            images = extract_images_by_position(r.text)
            return product, images
        except Exception as e:
            if attempt < MAX_RETRIES:
                time.sleep(1.5 * (attempt + 1))
            else:
                return product, []


def main():
    with open('/Users/cobly/Desktop/AI编程/minigt_products.json', encoding='utf-8') as f:
        products = json.load(f)

    print(f"共 {len(products)} 款产品，正在按轮播位置抓取图片（{WORKERS} 并发）...")

    results = []
    start = time.time()
    with ThreadPoolExecutor(max_workers=WORKERS) as executor:
        futures = {executor.submit(scrape_detail, p): p for p in products}
        for i, future in enumerate(as_completed(futures)):
            product, images = future.result()
            product['images'] = images
            results.append(product)
            if (i + 1) % 100 == 0 or (i + 1) == len(products):
                elapsed = time.time() - start
                print(f"  进度: {i+1}/{len(products)} ({elapsed:.0f}s)")

    results.sort(key=lambda p: p.get('detail_id', 0), reverse=True)

    with open('/Users/cobly/Desktop/AI编程/minigt_products.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    elapsed = time.time() - start
    total = len(results)
    with_3 = sum(1 for p in results if len(p.get('images', [])) >= 3)
    with_2 = sum(1 for p in results if len(p.get('images', [])) == 2)
    with_1 = sum(1 for p in results if len(p.get('images', [])) == 1)
    with_0 = sum(1 for p in results if len(p.get('images', [])) == 0)

    print(f"\n完成！耗时 {elapsed:.0f}s")
    print(f"  3张: {with_3} | 2张: {with_2} | 1张: {with_1} | 0张: {with_0}")

    # 抽查 MGT01311
    for p in results:
        if p.get('sku') == 'MGT01311':
            print(f"\n=== 抽查 MGT01311 ===")
            imgs = p.get('images', [])
            print(f"图片数: {len(imgs)}")
            for i, img in enumerate(imgs):
                # 标记是否重复
                is_dup = imgs.count(img) > 1
                dup_tag = '⚠️ 重复!' if is_dup else '✅'
                print(f"  [{i}] {dup_tag} {img}")
            break


if __name__ == '__main__':
    main()

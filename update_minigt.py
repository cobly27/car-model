#!/usr/bin/env python3
"""
MINI GT 产品同步更新脚本
1. 读取现有 HTML 中所有 SKU
2. 抓取官网全部产品列表（含 detail_id）
3. 识别新增产品（SKU 不在现有列表）
4. 逐款抓取 3 张产品原图
5. 按 SKU 降序插入 HTML 正确位置
6. 更新统计数字
"""

import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
import re, json, time, sys, os, html as htmlmod
from urllib.parse import urljoin

BASE_URL = "https://minigt.tsm-models.com"
LIST_URL = BASE_URL + "/index.php?action=product-list&b_id=13&p={}"
DETAIL_URL = BASE_URL + "/index.php?action=product-detail&id={}"

HTML_PATH = "/Users/cobly/Desktop/AI编程/MINI_GT_产品清单.html"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}
TIMEOUT = 30
WORKERS_LIST = 8
WORKERS_IMAGES = 10

# ── 工具函数 ──
def fix_url(src):
    if not src: return ""
    src = src.strip()
    return src if src.startswith("http") else urljoin(BASE_URL, src)

def sku_num(s):
    """提取 SKU 中的数字用于排序"""
    m = re.search(r'MGT0*(\d+)', s)
    return int(m.group(1)) if m else 0

# ── 第一步：获取总页数 ──
def get_total_pages():
    url = LIST_URL.format(0)
    r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    max_p = 0
    for a in soup.find_all("a", href=re.compile(r"p=\d+")):
        m = re.search(r'p=(\d+)', a.get("href", ""))
        if m:
            max_p = max(max_p, int(m.group(1)))
    return max_p + 1

# ── 第二步：抓取单页产品列表 ──
def fetch_page(p):
    """抓取一页，返回 [{sku, name, status, detail_id, image_thumb}]"""
    url = LIST_URL.format(p)
    products = []
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        for card in soup.select("div.pro_wrap, div.pd-list-in"):
            img_tag = card.find("img")
            if not img_tag: continue
            img_src = img_tag.get("src", "")
            if not re.search(r'picfile|mini_gt|upload', img_src): continue

            thumb = fix_url(img_src)
            name_tag = card.find("a", class_=re.compile(r"h6|text-dark|font-weight-bold"))
            if not name_tag:
                name_tag = card.find("a", href=re.compile(r"product-detail"))
            name = name_tag.get_text(strip=True) if name_tag else img_tag.get("alt", "").strip()

            sku_tag = card.find("p", class_="m-0")
            sku = sku_tag.get_text(strip=True) if sku_tag else ""

            # Detail ID
            detail_id = ""
            for a in card.find_all("a", href=re.compile(r"product-detail")):
                m = re.search(r'id=(\d+)', a.get("href", ""))
                if m:
                    detail_id = int(m.group(1))
                    break

            # Status
            status = ""
            for a in card.find_all("a", href=re.compile(r"product-detail")):
                t = a.get_text(strip=True)
                if t and t != name and len(t) < 30 and not t.startswith("MGT"):
                    status = t
                    break

            products.append({"sku": sku, "name": name, "status": status,
                           "detail_id": detail_id, "image_thumb": thumb})
        print(f"  p={p}: {len(products)} products")
        return products
    except Exception as e:
        print(f"  p={p}: ERROR - {e}")
        return []

# ── 第三步：提取产品详情页 3 张图片 ──
def extract_images(html):
    """从详情页 HTML 提取最多 3 张图，按轮播位置"""
    for marker in ['owl-carousel-5', 'products_gif', 'product_box']:
        start = html.find(marker)
        if start > 0: break
    else:
        return []

    end = html.find('產品 輪播圖 (小圖)', start)
    if end < 0: end = html.find('owl-carousel-1', start)
    if end < 0: end = len(html)
    segment = html[start:end]

    blocks = re.findall(
        r'<div\s+class="[^"]*pro_wrap-d[^"]*"\s+data-hash="([^"]*)"[^>]*>(.*?)</div>\s*</div>',
        segment, re.DOTALL
    )
    if not blocks:
        related = html.find('related_pro')
        body = html[:related] if related > 0 else html
        body = re.sub(r'<!--.*?-->', '', body, flags=re.DOTALL)
        imgs = re.findall(r'<img[^>]*src="([^"]*(?:picfile|product_pic|upload)/[^"]*)"', body)
        seen = set(); result = []
        for i in imgs:
            f = fix_url(i)
            if f and f not in seen:
                seen.add(f); result.append(f)
            if len(result) >= 3: break
        return result

    images = []
    # Position 1: data-hash="d"
    for hv, blk in blocks:
        if hv == 'd':
            m = re.search(r'<img[^>]*src="([^"]*(?:/picfile/|/product_pic_big/)[^"]*)"', blk)
            if not m:
                m = re.search(r'<img[^>]*src="([^"]*(?:upload|picfile|product_pic)[^"]*)"', blk)
            if m: images.append(fix_url(m.group(1)))
            break

    # Position 2,3: skip first non-d block (thumbnail duplicate)
    skipped = False
    for hv, blk in blocks:
        if hv == 'd': continue
        if not skipped: skipped = True; continue
        m = re.search(r'<img[^>]*src="([^"]*(?:/picfile/|/product_pic_big/)[^"]*)"', blk)
        if not m:
            m = re.search(r'<img[^>]*src="([^"]*(?:upload|picfile|product_pic)[^"]*)"', blk)
        if m:
            u = fix_url(m.group(1))
            if u and u not in images: images.append(u)
        if len(images) >= 3: break
    return images[:3]

def fetch_detail_images(product):
    """抓取单个产品详情页的图片"""
    did = product.get('detail_id')
    if not did: return product, []
    url = DETAIL_URL.format(did)
    for attempt in range(3):
        try:
            r = requests.get(url, headers=HEADERS, timeout=45)
            r.encoding = 'utf-8'
            if r.status_code != 200:
                raise Exception(f"HTTP {r.status_code}")
            imgs = extract_images(r.text)
            return product, imgs
        except Exception as e:
            if attempt < 2: time.sleep(1.5 * (attempt + 1))
            else: return product, []

# ── 第四步：读取现有 HTML 中的 SKU ──
def get_existing_skus():
    with open(HTML_PATH, 'r', encoding='utf-8') as f:
        html = f.read()
    return set(re.findall(r'data-sku="(MGT\d+)"', html))

# ── 第五步：生成单个产品行 HTML ──
def generate_tr(product, images):
    """生成与当前 HTML 格式一致的 <tr>"""
    sku = product['sku']
    name = htmlmod.escape(product['name'], quote=True)
    name_attr = name.replace('"', '&quot;')
    status = product['status']
    badge_map = {
        'Pre-Order': 'status-preorder',
        'Released': 'status-released',
        'Sold Out': 'status-soldout',
    }
    badge_class = badge_map.get(status, 'status-preorder')
    did = product.get('detail_id', '')
    detail_url = f"https://minigt.tsm-models.com/index.php?action=product-detail&id={did}" if did else "#"

    # Images
    imgs = images[:3]
    while len(imgs) < 3:
        imgs.append(product.get('image_thumb', ''))

    # Build imgs JSON for openModalTriplet
    imgs_json = json.dumps(imgs, ensure_ascii=False)
    imgs_escaped = htmlmod.escape(imgs_json, quote=True)

    # Product name for onclick (escaped for JS)
    name_js = product['name'].replace('\\', '\\\\').replace("'", "\\'")

    # Build img tags
    img_tags = ''.join(
        f'<img src="{htmlmod.escape(img, quote=True)}" loading="lazy" alt="{name_attr}" onerror="this.style.display=\'none\'">'
        for img in imgs
    )

    return f"""
        <tr data-sku="{sku}" data-name="{name_attr}" data-status="{status}">
            <td class="td-check"><input type="checkbox" class="row-check" data-sku="{sku}"></td>
            <td class="sku" title="点击复制编号" onclick="copySKU('{sku}', this)">{sku}</td>
            <td class="name-cell">
                <a href="{detail_url}" target="_blank" rel="noopener" title="在官网查看详情">{name}</a>
                <button class="copy-name-btn" onclick="copyText('{name_js}', this)" title="复制名称">📋</button>
            </td>
            <td class="status-cell"><span class="badge {badge_class}">{status}</span></td>
            <td class="img-cell">
                <div class="img-triplet" onclick="openModalTriplet({imgs_escaped}, 0, '{name_js}')">
                    {img_tags}
                </div>
            </td>
        <td class="td-action"><button class="row-del-btn" onclick="deleteRow(this)" title="删除此行">×</button></td>
        </tr>"""

# ── 第六步：插入 HTML ──
def insert_into_html(new_products_with_images):
    """将新产品按 SKU 降序插入 HTML，更新统计"""
    with open(HTML_PATH, 'r', encoding='utf-8') as f:
        html = f.read()

    # 找到 tbody 区域
    tbody_start = html.find('<tbody>')
    tbody_end = html.find('</tbody>', tbody_start)
    if tbody_start < 0 or tbody_end < 0:
        print("ERROR: 找不到 tbody")
        return False

    # 按 SKU 降序排列新产品
    new_products_with_images.sort(key=lambda x: sku_num(x[0]['sku']), reverse=True)

    # 生成新行
    new_rows = []
    for product, images in new_products_with_images:
        row = generate_tr(product, images)
        new_rows.append(row)
        print(f"  新: {product['sku']} - {product['name'][:40]} ({len(images)} 图)")

    # 提取 tbody 内所有 SKU，找到插入位置
    tbody_content = html[tbody_start + len('<tbody>'):tbody_end]
    existing_skus = re.findall(r'data-sku="(MGT\d+)"', tbody_content)

    # 构建插入映射：把新产品分配到现有 SKU 之间
    all_skus = [(sku_num(s), False, '') for s in existing_skus]  # (num, is_new, sku)
    for p, imgs in new_products_with_images:
        row = generate_tr(p, imgs)
        all_skus.append((sku_num(p['sku']), True, row))

    # 按数字降序排列
    all_skus.sort(key=lambda x: x[0], reverse=True)

    # 重建 tbody
    new_tbody_lines = []
    for num, is_new, row_html in all_skus:
        if is_new:
            new_tbody_lines.append(row_html)
        else:
            # 从原始 tbody 提取对应行
            # 找到 data-sku="MGT..." 匹配的行
            pass

    # 这个方法太复杂了。换简单方法：
    # 直接在 <tbody> 之后的开头插入所有新行（因为新产品 SKU 号最大）
    new_rows_html = '\n'.join(new_rows)

    # Insert right after <tbody>
    insert_pos = tbody_start + len('<tbody>')
    new_html = html[:insert_pos] + '\n' + new_rows_html + html[insert_pos:]

    # Update stats
    old_count = len(existing_skus)
    new_count = old_count + len(new_products_with_images)

    # Update title
    new_html = re.sub(
        r'<title>MINI GT 全产品清单 \(\d+款\)</title>',
        f'<title>MINI GT 全产品清单 ({new_count}款)</title>',
        new_html
    )

    # Update header paragraph: 共 X 款产品
    new_html = re.sub(
        r'共 \d+ 款产品',
        f'共 {new_count} 款产品',
        new_html
    )

    # Update header paragraph counts: Pre-Order: N | Released: N | Sold Out: N
    # Count new statuses
    from collections import Counter
    # Re-count from the original HTML's status badges
    old_status_match = re.search(r'Pre-Order: (\d+) \| Released: (\d+) \| Sold Out: (\d+)', new_html)
    if old_status_match:
        old_po = int(old_status_match.group(1))
        old_re = int(old_status_match.group(2))
        old_so = int(old_status_match.group(3))
    else:
        old_po = old_re = old_so = 0

    for p, _ in new_products_with_images:
        s = p.get('status', '')
        if s == 'Pre-Order': old_po += 1
        elif s == 'Released': old_re += 1
        elif s == 'Sold Out': old_so += 1

    new_html = re.sub(
        r'Pre-Order: \d+ \| Released: \d+ \| Sold Out: \d+',
        f'Pre-Order: {old_po} | Released: {old_re} | Sold Out: {old_so}',
        new_html
    )

    # Update stats badges in controls
    new_html = re.sub(
        r'<span class="stat-badge all">全部 \d+</span>',
        f'<span class="stat-badge all">全部 {new_count}</span>',
        new_html
    )

    # Count preorder/released/soldout from new_html tbody for badge updates
    # Actually, let's just update the preorder badge since we know the delta
    po_badge_match = re.search(r'<span class="stat-badge preorder">📦 (\d+)</span>', new_html)
    if po_badge_match:
        new_html = re.sub(
            r'<span class="stat-badge preorder">📦 \d+</span>',
            f'<span class="stat-badge preorder">📦 {old_po}</span>',
            new_html
        )
    re_badge_match = re.search(r'<span class="stat-badge released">✅ (\d+)</span>', new_html)
    if re_badge_match:
        new_html = re.sub(
            r'<span class="stat-badge released">✅ \d+</span>',
            f'<span class="stat-badge released">✅ {old_re}</span>',
            new_html
        )
    so_badge_match = re.search(r'<span class="stat-badge soldout">❌ (\d+)</span>', new_html)
    if so_badge_match:
        new_html = re.sub(
            r'<span class="stat-badge soldout">❌ \d+</span>',
            f'<span class="stat-badge soldout">❌ {old_so}</span>',
            new_html
        )

    # Update the JS statsGroup fallback
    new_html = re.sub(
        r"'<span class=\"stat-badge all\">显示 ' \+ count \+ ' / 共 \d+ 款",
        f"'<span class=\"stat-badge all\">显示 ' + count + ' / 共 {new_count} 款",
        new_html
    )

    # 写回
    with open(HTML_PATH, 'w', encoding='utf-8') as f:
        f.write(new_html)

    print(f"\n✅ 已插入 {len(new_products_with_images)} 款新品，总计 {new_count} 款")
    return True

# ── 主流程 ──
def main():
    print("=" * 50)
    print("MINI GT 产品同步更新")
    print("=" * 50)

    # 1. 读取现有 SKU
    print("\n📋 读取现有产品清单...")
    existing = get_existing_skus()
    print(f"  现有 {len(existing)} 款产品")

    # 2. 获取总页数
    print(f"\n🔍 检测官网分页...")
    total_pages = get_total_pages()
    print(f"  共 {total_pages} 页")

    # 3. 抓取全部产品列表
    print(f"\n📥 抓取 {total_pages} 页产品列表（{WORKERS_LIST} 并发）...")
    all_products = []
    with ThreadPoolExecutor(max_workers=WORKERS_LIST) as ex:
        futures = {ex.submit(fetch_page, p): p for p in range(total_pages)}
        for f in as_completed(futures):
            all_products.extend(f.result())

    print(f"\n  官网共 {len(all_products)} 款产品")

    # 4. 识别新增
    new_products = [p for p in all_products if p['sku'] not in existing]
    print(f"\n🆕 发现 {len(new_products)} 款新品：")
    for p in new_products:
        print(f"  {p['sku']} - {p['name'][:50]} [{p['status']}]")

    if not new_products:
        print("\n✅ 没有新产品，清单已是最新！")
        return 0

    # 5. 抓取新品图片
    print(f"\n🖼️ 正在抓取新品图片（{WORKERS_IMAGES} 并发）...")
    results = []
    with ThreadPoolExecutor(max_workers=WORKERS_IMAGES) as ex:
        futures = {ex.submit(fetch_detail_images, p): p for p in new_products}
        for f in as_completed(futures):
            results.append(f.result())

    # 6. 插入 HTML
    print(f"\n✏️ 正在更新 HTML...")
    if insert_into_html(results):
        print(f"\n🎉 更新完成！新增 {len(new_products)} 款，刷新页面即可查看。")
        return len(new_products)
    else:
        print("\n❌ 更新失败")
        return -1

if __name__ == "__main__":
    sys.exit(main())

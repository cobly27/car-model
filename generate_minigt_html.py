#!/usr/bin/env python3
"""生成 MINI GT 全产品清单 HTML（优化版）"""
import json
import re
from pathlib import Path
from urllib.parse import quote

BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / 'minigt_products.json'
HTML_PATH = BASE_DIR / 'MINI_GT_产品清单.html'
PLACEHOLDER_IMAGE = "data:image/svg+xml,%3Csvg%20xmlns='http://www.w3.org/2000/svg'%20viewBox='0%200%20400%20300'%3E%3Crect%20width='400'%20height='300'%20fill='%23f2f4f8'/%3E%3Ctext%20x='200'%20y='158'%20font-family='Arial'%20font-size='24'%20fill='%23909aaa'%20text-anchor='middle'%3ENo%20image%3C/text%3E%3C/svg%3E"

# ── 读取数据 ──
with DATA_PATH.open('r', encoding='utf-8') as f:
    data = json.load(f)

# 支持新旧两种数据格式
if isinstance(data, dict) and "categories" in data:
    # 新格式：从分类中获取产品
    categories = data.get("categories", [])
else:
    # 旧格式：直接使用数组
    categories = [{"id": "mini-gt", "name": "MINI GT", "products": data if isinstance(data, list) else []}]

# 构建带分类信息的产品列表
all_products_with_category = []
for cat in categories:
    cat_id = cat.get('id', '')
    for p in cat.get('products', []):
        p_copy = p.copy()
        p_copy['categoryId'] = cat_id
        all_products_with_category.append(p_copy)

# 去重（基于 sku, name, image）
seen = set()
unique = []
for p in all_products_with_category:
    key = (p.get('sku', ''), p.get('name', ''), p.get('image', ''))
    if key not in seen:
        seen.add(key)
        unique.append(p)

# 分别提取产品列表和全局产品列表（兼容旧逻辑）
products = unique
categories_products = {}
for p in products:
    cat_id = p.get('categoryId', 'mini-gt')  # 保留 categoryId 字段
    if cat_id not in categories_products:
        categories_products[cat_id] = []
    categories_products[cat_id].append(p)

count_preorder = sum(1 for p in products if p.get('status') == 'Pre-Order')
count_released = sum(1 for p in products if p.get('status') == 'Released')
count_soldout = sum(1 for p in products if p.get('status') == 'Sold Out')

def esc(s):
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')

# ── 生成大类切换选项 ──
category_tabs_html = ''
category_options_html = ''
for cat in categories:
    cat_id = esc(cat.get('id', ''))
    cat_name = esc(cat.get('name', ''))
    cat_count = len(cat.get('products', []))
    active_class = 'active' if cat == categories[0] else ''
    category_tabs_html += f'<button class="category-tab {active_class}" data-category="{cat_id}" onclick="switchCategory(\'{cat_id}\')">{cat_name} ({cat_count})</button>\n        '
    selected_attr = ' selected' if cat == categories[0] else ''
    category_options_html += f'<option value="{cat_id}"{selected_attr}>全部 · {cat_name} ({cat_count})</option>\n        '

# ── 生成分类统计数据 ──
category_stats = {}
for cat in categories:
    cat_id = cat.get('id', '')
    cat_name = cat.get('name', '')
    cat_products = cat.get('products', [])
    category_stats[cat_id] = {
        "name": cat_name,
        "total": len(cat_products),
        "preorder": sum(1 for p in cat_products if p.get('status') == 'Pre-Order'),
        "released": sum(1 for p in cat_products if p.get('status') == 'Released'),
        "soldout": sum(1 for p in cat_products if p.get('status') == 'Sold Out')
    }

# 转换为 JSON
category_stats_json = json.dumps(category_stats, ensure_ascii=False)

# ── 生成表格行和卡片 ──
def esc(s):
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')

def status_class(s):
    m = {'Pre-Order': 'status-preorder', 'Released': 'status-released', 'Sold Out': 'status-soldout'}
    return m.get(s, '')

def product_url(detail_id, category_id='mini-gt'):
    """生成官网产品详情链接，根据分类返回不同URL"""
    if category_id == 'ar':
        return f'http://www.armodel.com.cn/product/detail.html?id={detail_id}'
    if category_id == 'topspeed':
        return f'https://topspeed.tsm-models.com/index.php?action=product-detail&id={detail_id}'
    if category_id in ('spark', 'spark64'):
        return f'https://www.sparkmodel.com/en/products/{detail_id}'
    if category_id == 'inno':
        product = next((item for item in products if item.get('detail_id') == detail_id and item.get('categoryId') == 'inno'), None)
        if product and product.get('inno_url'):
            return product.get('inno_url')
        return 'https://www.inno-models.com/our-products/?jsf=jet-engine:shop-loop&tax=pa_scale:1-64'
    if category_id == 'poprace':
        return 'https://www.xcartoys.com/S_series'
<<<<<<< Updated upstream
=======
    if category_id == 'gcd':
        product = next((item for item in products if item.get('detail_id') == detail_id and item.get('categoryId') == 'gcd'), None)
        if product and product.get('gcd_url'):
            return product.get('gcd_url')
        return 'https://www.gcd-models.com/category/products/gcd/'
    if category_id == 'dct':
        product = next((item for item in products if item.get('detail_id') == detail_id and item.get('categoryId') == 'dct'), None)
        if product and product.get('dct_url'):
            return product.get('dct_url')
        return 'https://www.gcd-models.com/category/products/dct/'
    if category_id == 'tarmacworks':
        product = next((item for item in products if item.get('detail_id') == detail_id and item.get('categoryId') == 'tarmacworks'), None)
        if product and product.get('tarmacworks_url'):
            return product.get('tarmacworks_url')
        if product and product.get('tarmacworks_handle'):
            return f"https://www.tarmacworks.com/products/{product.get('tarmacworks_handle')}"
        return 'https://www.tarmacworks.com/collections/all'
    if category_id == 'greenlight':
        product = next((item for item in products if item.get('detail_id') == detail_id and item.get('categoryId') == 'greenlight'), None)
        if product and product.get('greenlight_url'):
            return product.get('greenlight_url')
        return 'https://www.greenlighttoys.com/shop/'
    if category_id == 'trendshobby':
        product = next((item for item in products if item.get('detail_id') == detail_id and item.get('categoryId') == 'trendshobby'), None)
        if product and product.get('trendshobby_url'):
            return product.get('trendshobby_url')
        return 'https://www.instagram.com/trends.hobby/'
>>>>>>> Stashed changes
    return f'https://minigt.tsm-models.com/index.php?action=product-detail&id={detail_id}'

def preview_image_url(image, category_id='mini-gt'):
    if category_id == 'topspeed' and image.startswith('https://topspeed.tsm-models.com/upload/'):
        return f'/api/topspeed-thumb?src={quote(image, safe="")}'
    if category_id == 'inno' and image.startswith('https://www.inno-models.com/wp-content/uploads/'):
        return f'/api/inno-image?src={quote(image, safe="")}'
    return image

def modal_image_url(image, category_id='mini-gt'):
    if category_id == 'inno' and image.startswith('https://www.inno-models.com/wp-content/uploads/'):
        return f'/api/inno-image?src={quote(image, safe="")}'
    return image

def get_images(p):
    """获取产品图片列表，对 MINI GT 按封面图、实物图排序，其他分类保留原顺序"""
    images = []
    product_images = [img for img in p.get('images', []) if img]
    if product_images:
        # 只对含 picfile 路径进行排序，AR 等其他分类保留原顺序
        has_picfile = any('picfile' in img or 'picfile_list' in img for img in product_images)
        if has_picfile:
            # 分离 picfile_list 和 picfile 的图片
            list_images = [img for img in product_images if 'picfile_list' in img]
            main_images = [img for img in product_images if 'picfile/' in img and 'picfile_list' not in img]
            # 按顺序：封面图（主图）、实物图 1、实物图 2
            images = main_images + list_images
            if not images:
                images = product_images
        else:
            # 非 MINI GT 图片保持原顺序
            images = product_images
    elif p.get('image'):
        images = [p['image']]
    return images or [PLACEHOLDER_IMAGE]

table_rows = ''
card_items = ''
for i, p in enumerate(products):
    name = esc(p['name'])
    sku = esc(p['sku'])
    pid = p.get('detail_id', '')
    st = p.get('status', '')
    sc = status_class(st)
    category_id = p.get('categoryId', 'mini-gt')
    images = get_images(p)
    preview_limit = 1 if category_id == 'topspeed' else 3
    preview_images = images[:preview_limit]
    modal_images = [modal_image_url(img, category_id) for img in images]
    remaining_image_count = max(0, len(images) - preview_limit)
    
    # 生成图片 HTML - 每张图单独绑定点击事件（添加懒加载）
    img_html = ''
    for idx, img in enumerate(preview_images):
        preview_img = preview_image_url(img, category_id)
        img_html += f'<img src="{esc(preview_img)}" data-src="{esc(preview_img)}" alt="{name}" class="thumb-img img-lazy" loading="lazy" onclick="event.stopPropagation();openMultiModalFromElement(this.closest(\'tr\') || this.closest(\'.card-item\'), {idx})" onerror="handleImageError(this, {idx})">'
    
    # 生成图片数据的 JSON 字符串，用于 data 属性
    images_json_data = json.dumps(modal_images, ensure_ascii=False)
    images_json_escaped = esc(images_json_data)
    
    # 表格行 - 使用索引从 JS 数组获取数据
    safe_name = name.replace("'", "&apos;")
    safe_name_data_attr = name.replace('"', '&quot;')
    table_rows += '''
<tr data-sku="{0}" data-name="{9}" data-status="{2}" data-index="{4}" data-category="{11}" data-images="{10}">
    <td class="num">{4}</td>
    <td class="sku" title="点击复制编号" onclick="copySKU(\'{0}\', this)">{0}</td>
    <td class="name-cell">
        <a href="{5}" target="_blank" rel="noopener" title="在官网查看详情">{1}</a>
        <button class="copy-name-btn" onclick="copyText(\'{1}\', this)" title="复制名称">📋</button>
    </td>
    <td class="status-cell"><span class="badge {6}">{2}</span></td>
    <td class="img-cell">
        <div class="img-triplet" onclick="openMultiModalFromElement(this.closest(\'tr\'), 0)">
            {7}
            {8}
        </div>
    </td>
    <td class="fav-cell">
        <button class="fav-btn" onclick="toggleFavorite(\'{0}\', this)" title="收藏">☆</button>
    </td>
</tr>'''.format(
        sku, safe_name, st, '', i + 1,
        product_url(pid, p.get('categoryId', 'mini-gt')), sc,
        img_html,
        f'<span class="img-count" onclick="event.stopPropagation();openMultiModalFromElement(this.closest(\'tr\'), 0)">+{remaining_image_count}</span>' if remaining_image_count > 0 else '',
        safe_name_data_attr,
        images_json_escaped,
        category_id,
        product_url(pid, category_id)
    )
    
    # 卡片项
    no_image_class = 'is-placeholder' if images[0] == PLACEHOLDER_IMAGE else ''
    card_items += '''
<div class="card-item" data-sku="{0}" data-name="{9}" data-status="{2}" data-index="{4}" data-category="{11}" data-images="{10}">
    <div class="card-img {13}" onclick="openMultiModalFromElement(this.closest(\'.card-item\'), 0)">
        <img src="{5}" data-src="{5}" alt="{1}" loading="lazy" onload="this.classList.add('loaded')" onerror="handleImageError(this, 0)">
        <div class="card-img-overlay">
            <span class="card-img-count">{6} 图</span>
        </div>
    </div>
    <div class="card-body">
        <div class="card-sku" onclick="copySKU(\'{0}\', this)">{0}</div>
        <a href="{12}" target="_blank" rel="noopener" class="card-name" title="在官网查看详情">{1}</a>
        <div class="card-footer">
            <span class="badge {7}">{2}</span>
            <button class="fav-btn" onclick="toggleFavorite(\'{0}\', this)" title="收藏">☆</button>
        </div>
    </div>
</div>'''.format(
        sku, safe_name, st, '', i + 1,
        esc(preview_image_url(images[0], category_id)), len(images), sc,
        '',
        safe_name_data_attr,
        images_json_escaped,
        category_id,
        product_url(pid, category_id),
        no_image_class
    )

# 模板使用单大括号，避免处理问题
html = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Car Model-产品清单 ({len_products} 款)</title>
<link rel="icon" type="image/svg+xml" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Crect width='64' height='64' rx='14' fill='%23e63946'/%3E%3Cpath d='M12 38h5l5-12h20l6 12h4c2.2 0 4 1.8 4 4v4h-6a7 7 0 0 1-14 0H28a7 7 0 0 1-14 0H8v-4c0-2.2 1.8-4 4-4Z' fill='white'/%3E%3Cpath d='M24 30h16l3.5 8h-23L24 30Z' fill='%231a1a2e' opacity='.9'/%3E%3Ccircle cx='21' cy='46' r='4' fill='%231a1a2e'/%3E%3Ccircle cx='43' cy='46' r='4' fill='%231a1a2e'/%3E%3C/svg%3E">
<style>
* { margin:0; padding:0; box-sizing: border-box; }
:root {
    --red: #e63946;
    --dark: #1a1a2e;
    --bg: #f0f2f5;
    --card: #fff;
    --border: #e8e8e8;
    --text: #1a1a2e;
    --text-secondary: #666;
    --shadow: rgba(0,0,0,0.1);
}
body.dark {
    --bg: #0f0f1a;
    --card: #1a1a2e;
    --border: #2a2a4e;
    --text: #e0e0e0;
    --text-secondary: #999;
    --shadow: rgba(0,0,0,0.3);
}
body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", sans-serif;
    background: var(--bg);
    color: var(--text);
    transition: background 0.3s, color 0.3s;
}

/* Header */
.header {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
    color: #fff;
    padding: 24px 30px;
}
.header h1 { font-size: 22px; font-weight: 700; margin-bottom: 4px; letter-spacing: .5px; }
.header p { font-size: 13px; opacity: .75; }

/* Controls */
.controls {
    padding: 14px 30px 12px;
    background: var(--card);
    border-bottom: 1px solid var(--border);
    display: flex;
    flex-direction: column;
    gap: 12px;
    align-items: stretch;
    position: sticky;
    top: 0;
    z-index: 40;
    transition: background 0.3s;
    box-shadow: 0 1px 0 rgba(0,0,0,0.02);
}
.control-row {
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
    align-items: center;
    width: 100%;
}
.control-main {
    justify-content: space-between;
}
.control-main .search-wrap {
    flex: 1 1 420px;
    max-width: 720px;
}
.control-actions {
    justify-content: space-between;
    padding-top: 2px;
}
.action-group {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
    align-items: center;
}
.controls input, .controls select, .controls button {
    padding: 8px 14px;
    border: 1px solid var(--border);
    border-radius: 8px;
    font-size: 13px;
    background: var(--card);
    color: var(--text);
    font-family: inherit;
    transition: border-color 0.2s, box-shadow 0.2s;
}
.controls input:focus, .controls select:focus {
    outline: none;
    border-color: var(--red);
    box-shadow: 0 0 0 2px rgba(230,57,70,.1);
}
.controls input { min-width: 260px; }
.search-wrap {
    position: relative;
    display: flex;
    flex: 0 1 360px;
    min-width: 260px;
}
.search-wrap input {
    width: 100%;
    min-width: 0;
    padding-right: 38px;
}
.search-clear {
    position: absolute;
    right: 6px;
    top: 50%;
    transform: translateY(-50%);
    width: 28px;
    height: 28px;
    padding: 0;
    border: none;
    border-radius: 50%;
    background: transparent;
    color: var(--text-secondary);
    cursor: pointer;
    font-size: 18px;
    line-height: 1;
    display: none;
    align-items: center;
    justify-content: center;
}
.search-clear.visible {
    display: flex;
}
.search-clear:hover {
    background: var(--border);
    color: var(--text);
}
.control-hidden {
    display: none !important;
}

/* Quick filters */
.quick-filters {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
    align-items: center;
}
.quick-filter {
    min-height: 36px;
    padding: 7px 13px;
    border-radius: 10px;
    font-size: 12px;
    cursor: pointer;
    border: 1px solid var(--border);
    background: var(--card);
    color: var(--text);
    transition: all 0.2s;
}
.quick-filter:hover { border-color: var(--red); }
.quick-filter.active {
    background: var(--red);
    color: #fff;
    border-color: var(--red);
}
.quick-filter.fav-only {
    background: linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%);
    color: #d63031;
    border: none;
}
.quick-filter.fav-only.active {
    background: linear-gradient(135deg, #ff6b6b 0%, #ee5a5a 100%);
    color: #fff;
}

/* View toggle */
.view-toggle {
    display: flex;
    background: var(--border);
    border-radius: 8px;
    overflow: hidden;
}
.view-btn {
    width: 38px;
    height: 36px;
    padding: 0;
    border: none;
    background: transparent;
    cursor: pointer;
    font-size: 14px;
    color: var(--text-secondary);
    transition: all 0.2s;
}
.view-btn.active {
    background: var(--card);
    color: var(--red);
    font-weight: 600;
}

/* Theme toggle */
.theme-btn {
    background: var(--dark) !important;
    color: #fff !important;
    border: none !important;
    cursor: pointer;
    min-width: 42px;
}
body.dark .theme-btn {
    background: #f1c40f !important;
    color: #1a1a2e !important;
}

/* Update Button */
.update-btn {
    background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%) !important;
    color: #fff !important;
    border: none !important;
    cursor: pointer;
    font-weight: 600;
    min-height: 36px;
    transition: opacity 0.2s, transform 0.2s;
}
.update-btn:hover {
    opacity: 0.9;
    transform: translateY(-1px);
}
.update-btn:disabled {
    opacity: 0.5 !important;
    cursor: not-allowed !important;
    transform: none !important;
}

/* Status Panel */
.status-panel {
    display: none;
    position: relative;
    padding: 12px 20px;
    padding-right: 48px;
    background: #fff3cd;
    color: #856404;
    font-size: 14px;
    border-bottom: 1px solid #ffeaa7;
    white-space: pre-line;
    animation: slideDown 0.3s ease;
}
@keyframes slideDown {
    from { max-height: 0; padding-top: 0; padding-bottom: 0; }
    to { max-height: 200px; }
}
.status-panel.visible {
    display: block;
}
.status-panel.success {
    background: #d4edda;
    color: #155724;
    border-color: #c3e6cb;
}
.status-panel.error {
    background: #f8d7da;
    color: #721c24;
    border-color: #f5c6cb;
}
.status-panel .status-message {
    display: block;
}
.status-close {
    position: absolute;
    top: 8px;
    right: 12px;
    width: 28px;
    height: 28px;
    border: none;
    border-radius: 50%;
    background: rgba(0,0,0,0.08);
    color: inherit;
    cursor: pointer;
    font-size: 18px;
    line-height: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    opacity: 0.75;
}
.status-close:hover {
    opacity: 1;
    background: rgba(0,0,0,0.14);
}
body.dark .status-close {
    background: rgba(255,255,255,0.12);
}
body.dark .status-close:hover {
    background: rgba(255,255,255,0.2);
}

/* Stats */
.stats-group {
    display: flex;
    gap: 8px;
    align-items: center;
    flex-wrap: wrap;
    justify-content: flex-end;
}
.stat-badge {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 4px 10px;
    border-radius: 14px;
    font-size: 12px;
    font-weight: 600;
    white-space: nowrap;
    background: var(--border);
    color: var(--text-secondary);
}
.stat-badge.released { background: #d4edda; color: #155724; }
.stat-badge.preorder { background: #fff3cd; color: #856404; }
.stat-badge.soldout { background: #f8d7da; color: #721c24; }
body.dark .stat-badge { filter: brightness(0.9); }

/* Table view */
.table-wrap { display: block; overflow-x: auto; }
.table-wrap.hidden { display: none; }
table { width: 100%; border-collapse: collapse; background: var(--card); min-width: 800px; transition: background 0.3s; }
th {
    background: var(--border);
    padding: 10px 14px;
    text-align: left;
    font-size: 12px;
    font-weight: 600;
    color: var(--text-secondary);
    border-bottom: 2px solid var(--border);
    text-transform: uppercase;
    letter-spacing: .5px;
    cursor: pointer;
    user-select: none;
    position: relative;
    transition: background .15s;
}
th:hover { background: var(--bg); }
th .sort-arrow { font-size: 10px; margin-left: 4px; opacity: .3; }
th.sorted .sort-arrow { opacity: 1; color: var(--red); }
td { padding: 10px 14px; border-bottom: 1px solid var(--border); font-size: 13px; vertical-align: middle; transition: background .15s; }
tr:hover td { background: var(--bg); }
.hidden { display: none !important; }

/* Table columns */
.num { width: 50px; color: var(--text-secondary); text-align: center; }
.sku {
    font-family: "SF Mono", "Fira Code", Monaco, monospace;
    font-size: 12px;
    color: var(--red);
    font-weight: 700;
    white-space: nowrap;
    cursor: pointer;
    transition: background .15s;
    padding: 4px 8px;
    border-radius: 4px;
}
.sku:hover { background: rgba(230,57,70,0.1); }
.sku.copied { animation: flash-green .5s ease; }
@keyframes flash-green {
    0% { background: #d4edda; color: #155724; }
    100% { background: transparent; color: var(--red); }
}
.name-cell {
    line-height: 1.45;
    font-size: 13px;
    max-width: 400px;
}
.name-cell a {
    color: var(--text);
    text-decoration: none;
    transition: color .15s;
}
.name-cell a:hover { color: var(--red); text-decoration: underline; }
.copy-name-btn {
    opacity:0;
    background: none;
    border: none;
    cursor: pointer;
    font-size: 13px;
    padding: 0 4px;
    transition: opacity .15s;
    vertical-align: middle;
}
tr:hover .copy-name-btn { opacity: .6; }
.copy-name-btn:hover { opacity: 1 !important; }

/* Status badges */
.status-cell { width: 110px; text-align: center; }
.badge {
    display: inline-flex;
    padding: 3px 10px;
    border-radius: 12px;
    font-size: 11px;
    font-weight: 600;
}
.status-preorder { background: #fff3cd; color: #856404; }
.status-released { background: #d4edda; color: #155724; }
.status-soldout { background: #f8d7da; color: #721c24; }

/* Image triplet */
.img-cell { width: 160px; text-align: center; }
.img-triplet {
    display: flex;
    gap: 4px;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    padding: 4px;
    border-radius: 8px;
    transition: all 0.2s;
    position: relative;
}
.img-triplet:hover {
    background: var(--bg);
    transform: scale(1.02);
}
.img-triplet .thumb-img {
    width: 45px;
    height: 45px;
    object-fit: cover;
    border-radius: 6px;
    background: var(--border);
}
.img-count {
    position: absolute;
    right: 4px;
    bottom: 4px;
    background: var(--red);
    color: #fff;
    font-size: 10px;
    padding: 2px 6px;
    border-radius: 8px;
    font-weight: 600;
}

/* Favorite button */
.fav-cell { width: 50px; text-align: center; }
.fav-btn {
    background: none;
    border: none;
    font-size: 20px;
    cursor: pointer;
    transition: transform 0.2s, color 0.2s;
    color: var(--text-secondary);
    padding: 4px;
}
.fav-btn:hover { transform: scale(1.2); }
.fav-btn.active { color: #e63946; }

/* Card view */
.cards-wrap {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(218px, 1fr));
    gap: 16px;
    padding: 20px;
}
.cards-wrap.hidden { display: none; }
.card-item {
    background: var(--card);
    border-radius: 10px;
    overflow: hidden;
    box-shadow: 0 2px 12px var(--shadow);
    transition: transform 0.2s, box-shadow 0.2s;
    display: flex;
    flex-direction: column;
    min-height: 366px;
}
.card-item:hover {
    transform: translateY(-4px);
    box-shadow: 0 8px 24px var(--shadow);
}
.card-img {
    aspect-ratio: 4/3;
    background: linear-gradient(135deg, rgba(245,247,250,0.98), rgba(226,232,240,0.98));
    overflow: hidden;
    cursor: pointer;
    position: relative;
}
body.dark .card-img {
    background: linear-gradient(135deg, #20243a, #151827);
}
.card-img img {
    width: 100%;
    height: 100%;
    object-fit: cover;
}
.card-img.is-placeholder img {
    object-fit: contain;
    opacity: 0.72;
}
.card-img.is-placeholder::after {
    content: '官网暂无图片';
    position: absolute;
    left: 50%;
    bottom: 12px;
    transform: translateX(-50%);
    display: flex;
    align-items: center;
    justify-content: center;
    width: max-content;
    max-width: calc(100% - 24px);
    padding: 4px 10px;
    border-radius: 999px;
    background: rgba(255,255,255,0.78);
    color: #64748b;
    font-size: 12px;
    font-weight: 600;
    pointer-events: none;
}
body.dark .card-img.is-placeholder::after {
    background: rgba(15,15,26,0.82);
    color: #b9c0cf;
}
.card-img-overlay {
    position: absolute;
    inset: 0;
    background: linear-gradient(to top, rgba(0,0,0,0.6), transparent);
    opacity: 0;
    transition: opacity 0.2s;
    display: flex;
    align-items: flex-end;
    justify-content: center;
    padding-bottom: 10px;
}
.card-img:hover .card-img-overlay { opacity: 1; }
.card-img-count {
    background: rgba(0,0,0,0.7);
    color: #fff;
    padding: 4px 10px;
    border-radius: 12px;
    font-size: 12px;
}
.card-body {
    padding: 12px;
    display: flex;
    flex-direction: column;
    flex: 1;
}
.card-sku {
    font-family: "SF Mono", "Fira Code", Monaco, monospace;
    font-size: 12px;
    color: var(--red);
    font-weight: 700;
    margin-bottom: 4px;
    cursor: pointer;
    display: inline-block;
    min-height: 18px;
}
.card-name {
    font-size: 13px;
    line-height: 1.4;
    margin-bottom: 10px;
    color: #007bff;
    text-decoration: none;
    display: block;
    cursor: pointer;
    display: -webkit-box;
    -webkit-line-clamp: 4;
    -webkit-box-orient: vertical;
    overflow: hidden;
    min-height: 73px;
}
.card-name:hover {
    text-decoration: underline;
    color: #0056b3;
}
.card-footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-top: auto;
    gap: 10px;
}
.card-footer .fav-btn { font-size: 18px; padding: 0; }

/* Multi-image modal */
.modal-overlay {
    display: none;
    position: fixed;
    inset: 0;
    background: rgba(0,0,0,.9);
    z-index: 9999;
    cursor: pointer;
    animation: fadeIn .2s ease;
}
.modal-overlay.active { display: flex; align-items: center; justify-content: center; }
@keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
.modal-content {
    max-width: 95vw;
    max-height: 90vh;
    position: relative;
    animation: zoomIn .25s ease;
    cursor: default;
}
@keyframes zoomIn { from { transform: scale(.85); opacity: 0; } to { transform: scale(1); opacity: 1; } }
.modal-content.loading::after {
    content: "加载中...";
    position: absolute;
    left: 50%;
    top: 50%;
    transform: translate(-50%, -50%);
    color: #fff;
    font-size: 14px;
    background: rgba(0,0,0,0.55);
    padding: 8px 14px;
    border-radius: 8px;
    pointer-events: none;
}
.modal-content img {
    max-width: 90vw;
    max-height: 80vh;
    border-radius: 8px;
    box-shadow: 0 8px 40px rgba(0,0,0,.5);
    object-fit: contain;
    background: #000;
    opacity: 1;
    transition: opacity 0.12s ease;
}
.modal-close {
    position: absolute;
    top: -50px;
    right: 0;
    background: none;
    border: none;
    color: #fff;
    font-size: 36px;
    cursor: pointer;
    line-height: 1;
    opacity: .7;
    transition: opacity .2s;
}
.modal-close:hover { opacity: 1; }
.modal-nav {
    position: absolute;
    top: 50%;
    transform: translateY(-50%);
    background: rgba(255,255,255,0.2);
    border: none;
    color: #fff;
    font-size: 32px;
    width: 50px;
    height: 50px;
    border-radius: 50%;
    cursor: pointer;
    transition: background 0.2s;
    display: flex;
    align-items: center;
    justify-content: center;
}
.modal-nav:hover { background: rgba(255,255,255,0.4); }
.modal-nav.prev { left: -70px; }
.modal-nav.next { right: -70px; }
.modal-caption {
    text-align: center;
    color: #fff;
    font-size: 14px;
    margin-top: 15px;
}
.modal-counter {
    color: rgba(255,255,255,0.7);
    font-size: 12px;
    margin-top: 5px;
}

/* Category selector */
.category-select {
    min-width: 210px;
    font-weight: 700;
    cursor: pointer;
}
.category-select.active {
    background: var(--red);
    color: #fff;
    border-color: var(--red);
}

/* Back to top */
#backToTop {
    display: none;
    position: fixed;
    bottom: 30px;
    right: 30px;
    width: 44px;
    height: 44px;
    border-radius: 50%;
    background: var(--dark);
    color: #fff;
    border: none;
    cursor: pointer;
    font-size: 20px;
    z-index: 100;
    box-shadow: 0 2px 12px var(--shadow);
    transition: opacity .2s, transform .2s;
}
body.dark #backToTop { background: var(--red); }
#backToTop:hover { opacity: .85; transform: translateY(-2px); }
#backToTop.visible { display: flex; align-items: center; justify-content: center; }

/* Toast */
.toast {
    position: fixed;
    bottom: 30px;
    left: 50%;
    transform: translateX(-50%) translateY(20px);
    background: #333;
    color: #fff;
    padding: 10px 24px;
    border-radius: 20px;
    font-size: 13px;
    z-index: 10000;
    opacity: 0;
    transition: opacity .2s, transform .2s;
    pointer-events: none;
}
body.dark .toast { background: #fff; color: #333; }
.toast.show { opacity: 1; transform: translateX(-50%) translateY(0); }

/* Footer */
.footer {
    text-align: center;
    padding: 24px;
    color: var(--text-secondary);
    font-size: 12px;
    border-top: 1px solid var(--border);
}

/* Pagination */
.pagination {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    padding: 20px;
    flex-wrap: wrap;
}
.pagination-top {
    border-top: 1px solid var(--border);
    border-bottom: 1px solid var(--border);
    background: var(--card);
    padding: 12px 20px;
}
.pagination button {
    padding: 8px 14px;
    border: 1px solid var(--border);
    background: var(--card);
    color: var(--text);
    border-radius: 8px;
    cursor: pointer;
    font-size: 14px;
    transition: all 0.2s;
}
.pagination button:hover:not(:disabled) {
    border-color: var(--red);
    color: var(--red);
}
.pagination button:disabled {
    opacity: 0.4;
    cursor: not-allowed;
}
.pagination button.active {
    background: var(--red);
    color: #fff;
    border-color: var(--red);
}
.pagination .page-info {
    padding: 8px 14px;
    font-size: 14px;
    color: var(--text-secondary);
}
.pagination select {
    padding: 8px 12px;
    border: 1px solid var(--border);
    background: var(--card);
    color: var(--text);
    border-radius: 8px;
    cursor: pointer;
    font-size: 14px;
}
.page-jump {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    color: var(--text-secondary);
    font-size: 14px;
}
.page-jump input {
    width: 64px;
    padding: 8px 10px;
    border: 1px solid var(--border);
    background: var(--card);
    color: var(--text);
    border-radius: 8px;
    font-size: 14px;
    text-align: center;
}
.page-jump input:focus {
    outline: none;
    border-color: var(--red);
    box-shadow: 0 0 0 2px rgba(230,57,70,.1);
}
.page-jump input:disabled {
    opacity: 0.45;
    cursor: not-allowed;
}

/* Mobile */
@media (max-width: 768px) {
    .header { padding: 16px; }
    .header h1 { font-size: 18px; }
    .header p { font-size: 11px; }
    .controls { padding: 10px 12px; gap: 10px; }
    .control-main { justify-content: flex-start; }
    .control-actions { justify-content: flex-start; }
    .action-group, .update-actions { width: 100%; }
    .update-actions .update-btn { flex: 1 1 220px; }
    .controls input { min-width: 0; flex: 1 1 200px; }
    .search-wrap { min-width: 0; flex: 1 1 100%; }
    .stats-group { margin-left: 0; width: 100%; justify-content: flex-start; }
    .quick-filters { width: 100%; }
    .quick-filter { flex: 1 1 auto; }
    .category-select { flex-basis: 100%; }
    .cards-wrap { grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 12px; padding: 12px; }
    .card-item { min-height: 320px; }
    .card-name { -webkit-line-clamp: 5; min-height: 88px; }
    .modal-nav { display: none; }
    #backToTop { bottom: 20px; right: 16px; width: 38px; height: 38px; font-size: 16px; }
    .pagination { padding: 12px; gap: 6px; }
    .pagination button { padding: 6px 10px; font-size: 13px; }
    .pagination .page-info { font-size: 13px; padding: 6px 10px; }
    .pagination select { padding: 6px 8px; font-size: 13px; }
    .page-jump { font-size: 13px; gap: 4px; }
    .page-jump input { width: 56px; padding: 6px 8px; font-size: 13px; }
}

/* 图片懒加载样式 */
.img-lazy {
    opacity: 0;
    transition: opacity 0.3s ease;
    background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
}
.img-lazy.loaded {
    opacity: 1;
}
body.dark .img-lazy {
    background: linear-gradient(135deg, #2d3748 0%, #1a202c 100%);
}
</style>
</head>
<body>

<!-- Header -->
<div class="header">
    <h1>🏎️ Car Model-产品清单</h1>
    <p>数据来源: minigt.tsm-models.com · 抓取时间: 2026-06-04 · 共 {len_products} 款</p>
</div>

<!-- Status Panel -->
<div class="status-panel" id="statusPanel"></div>

<!-- Controls -->
<div class="controls">
    <div class="control-row control-main">
        <div class="search-wrap">
            <input type="text" id="search" placeholder="搜索产品名称或编号..." oninput="debouncedFilter()" autocomplete="off">
            <button class="search-clear" id="searchClearBtn" type="button" onclick="clearSearch()" title="清空搜索" aria-label="清空搜索">×</button>
        </div>
        <div class="stats-group" id="statsGroup">
            <span class="stat-badge">共 {len_products}</span>
            <span class="stat-badge released">✅ {count_released}</span>
            <span class="stat-badge preorder">📦 {count_preorder}</span>
            <span class="stat-badge soldout">❌ {count_soldout}</span>
        </div>
    </div>
    <div class="control-row">
        <div class="quick-filters">
        <select class="quick-filter active category-select" id="categoryDropdownBtn" data-filter="" onchange="selectCategoryFromDropdown(this.value)" aria-label="选择分类">
            {category_options_html}
        </select>
<<<<<<< Updated upstream
        <button class="quick-filter" data-scope="mini-gt topspeed spark spark64 inno poprace" data-filter="Pre-Order" onclick="setQuickFilter(this)">📦 Pre-Order</button>
        <button class="quick-filter" data-scope="mini-gt topspeed spark spark64 inno poprace" data-filter="Released" onclick="setQuickFilter(this)">✅ Released</button>
        <button class="quick-filter" data-scope="mini-gt topspeed spark spark64 inno poprace" data-filter="Sold Out" onclick="setQuickFilter(this)">❌ Sold Out</button>
=======
        <button class="quick-filter" data-scope="mini-gt topspeed spark spark64 inno poprace gcd dct tarmacworks greenlight trendshobby" data-filter="Pre-Order" onclick="setQuickFilter(this)">📦 Pre-Order</button>
        <button class="quick-filter" data-scope="mini-gt topspeed spark spark64 inno poprace gcd dct tarmacworks greenlight trendshobby" data-filter="Released" onclick="setQuickFilter(this)">✅ Released</button>
        <button class="quick-filter" data-scope="mini-gt topspeed spark spark64 inno poprace gcd dct tarmacworks greenlight trendshobby" data-filter="Sold Out" onclick="setQuickFilter(this)">❌ Sold Out</button>
>>>>>>> Stashed changes
        <button class="quick-filter fav-only" data-filter="fav" onclick="setQuickFilter(this)">⭐ 收藏</button>
        </div>
    </div>
    <div class="control-row control-actions">
        <div class="action-group">
            <div class="view-toggle">
                <button class="view-btn" data-view="table" onclick="setView(this)" title="表格视图">📊</button>
                <button class="view-btn active" data-view="cards" onclick="setView(this)" title="卡片视图">📦</button>
            </div>
            <button class="theme-btn" onclick="toggleTheme()" title="切换主题">🌙</button>
        </div>
        <div class="action-group update-actions">
            <button class="update-btn" data-scope="mini-gt" id="updateMiniBtn" onclick="triggerUpdate('minigt')">🔄 更新 MINI GT 产品</button>
            <button class="update-btn" data-scope="ar" id="updateArBtn" onclick="triggerUpdate('ar')">🔄 更新 AR 产品</button>
            <button class="update-btn" data-scope="topspeed" id="updateTopSpeedBtn" onclick="triggerUpdate('topspeed')">🔄 更新 TOP SPEED 产品</button>
            <button class="update-btn" data-scope="spark" id="updateSparkBtn" onclick="triggerUpdate('spark')">🔄 更新 SPARK 产品</button>
            <button class="update-btn" data-scope="spark64" id="updateSpark64Btn" onclick="triggerUpdate('spark64')">🔄 更新 SPARK 1:64 产品</button>
            <button class="update-btn" data-scope="inno" id="updateInnoBtn" onclick="triggerUpdate('inno')">🔄 更新 INNO 产品</button>
<<<<<<< Updated upstream
=======
            <button class="update-btn" data-scope="gcd" id="updateGcdBtn" onclick="triggerUpdate('gcd')">🔄 更新 GCD 产品</button>
            <button class="update-btn" data-scope="dct" id="updateDctBtn" onclick="triggerUpdate('dct')">🔄 更新 DCT 产品</button>
            <button class="update-btn" data-scope="tarmacworks" id="updateTarmacworksBtn" onclick="triggerUpdate('tarmacworks')">🔄 更新 TARMAC WORKS 产品</button>
            <button class="update-btn" data-scope="greenlight" id="updateGreenlightBtn" onclick="triggerUpdate('greenlight')">🔄 更新 GreenLight 产品</button>
            <button class="update-btn" data-scope="trendshobby" id="updateTrendsHobbyBtn" onclick="triggerUpdate('trendshobby')">🔄 更新 TH 产品</button>
>>>>>>> Stashed changes
        </div>
    </div>
</div>

<!-- Top Pagination -->
<div class="pagination pagination-top" id="paginationTop">
    <button onclick="goToFirstPage()" id="btnFirstTop">首页</button>
    <button onclick="goToPrevPage()" id="btnPrevTop">上一页</button>
    <span class="page-info" id="pageInfoTop">第 1 页 / 共 1 页</span>
    <label class="page-jump">
        跳至
        <input class="page-jump-input" id="pageJumpTop" type="number" min="1" value="1" inputmode="numeric" onkeydown="handlePageJumpKey(event)" onchange="jumpToPageInput(this)">
        页
    </label>
    <button class="page-jump-btn" onclick="jumpToPageInput(document.getElementById('pageJumpTop'))">跳转</button>
    <button onclick="goToNextPage()" id="btnNextTop">下一页</button>
    <button onclick="goToLastPage()" id="btnLastTop">末页</button>
    <select id="pageSizeTop" onchange="changePageSize(this.value)">
        <option value="20" selected>20/页</option>
        <option value="50">50/页</option>
        <option value="100">100/页</option>
    </select>
</div>

<!-- Table View -->
<div class="table-wrap hidden" id="tableView">
    <table>
        <thead>
            <tr>
                <th class="num" data-sort="num"># <span class="sort-arrow">↕</span></th>
                <th data-sort="sku">编号 <span class="sort-arrow">↕</span></th>
                <th data-sort="name">产品名称 <span class="sort-arrow">↕</span></th>
                <th data-sort="status">状态 <span class="sort-arrow">↕</span></th>
                <th>图片</th>
                <th>收藏</th>
            </tr>
        </thead>
        <tbody>
        </tbody>
    </table>
</div>

<!-- Cards View -->
<div class="cards-wrap" id="cardsView">
</div>

<!-- Pagination -->
<div class="pagination" id="pagination">
    <button onclick="goToFirstPage()" id="btnFirst">首页</button>
    <button onclick="goToPrevPage()" id="btnPrev">上一页</button>
    <span class="page-info" id="pageInfo">第 1 页 / 共 1 页</span>
    <label class="page-jump">
        跳至
        <input class="page-jump-input" id="pageJumpBottom" type="number" min="1" value="1" inputmode="numeric" onkeydown="handlePageJumpKey(event)" onchange="jumpToPageInput(this)">
        页
    </label>
    <button class="page-jump-btn" onclick="jumpToPageInput(document.getElementById('pageJumpBottom'))">跳转</button>
    <button onclick="goToNextPage()" id="btnNext">下一页</button>
    <button onclick="goToLastPage()" id="btnLast">末页</button>
    <select id="pageSizeBottom" onchange="changePageSize(this.value)">
        <option value="20" selected>20/页</option>
        <option value="50">50/页</option>
        <option value="100">100/页</option>
    </select>
</div>

<!-- Footer -->
<div class="footer">MINI GT Product Catalog · 点击图片查看大图 · 点击编号复制 · 数据本地收藏</div>

<!-- Multi-image Modal -->
<div class="modal-overlay" id="modalOverlay" onclick="closeModal()">
    <div class="modal-content" onclick="event.stopPropagation()">
        <button class="modal-close" onclick="closeModal()">&times;</button>
        <button class="modal-nav prev" onclick="prevImage()">&lt;</button>
        <img id="modalImg" src="" alt="">
        <button class="modal-nav next" onclick="nextImage()">&gt;</button>
        <div class="modal-caption" id="modalCaption"></div>
        <div class="modal-counter" id="modalCounter"></div>
    </div>
</div>

<!-- Back to Top -->
<button id="backToTop" onclick="window.scrollTo({top:0,behavior:'smooth'})" title="回到顶部">⬆</button>

<!-- Toast -->
<div class="toast" id="toast"></div>

<script>
// 所有产品数据 - 直接在 JS 中存储，避免解析问题
const productsData = PRODUCTS_JSON_PLACEHOLDER;

// 分类统计数据
const categoryStats = CATEGORY_STATS_PLACEHOLDER;
const placeholderImage = PLACEHOLDER_IMAGE_PLACEHOLDER;

// Global state
let currentImages = [];
let currentImageIndex = 0;
let currentModalName = '';
let currentModalCategory = 'mini-gt';
const preloadedImages = new Set();
const imageLoadCache = new Map();
const imageReady = new Set();
const imageFailed = new Set();
let modalLoadToken = 0;
let sortState = { col: '', dir: 1 };
let currentFilter = '';
// 兼容旧数据：同时读取两个键名
const oldFavorites = JSON.parse(localStorage.getItem('minigtFavorites') || '[]');
const newFavorites = JSON.parse(localStorage.getItem('minigt_favorites') || '[]');
let favorites = new Set([...oldFavorites, ...newFavorites]);
let currentView = 'cards';
let filterTimeout;
let currentPage = 1;
let pageSize = 20;  // 每页显示 20 个产品

// 当前分类状态
let currentCategory = 'mini-gt';

// 各分类的独立分页状态
const categoryPagination = {};
const categoryCurrentFilter = {};
const categoryCurrentPage = {};
const categoryScopedFilters = {
    'mini-gt': new Set(['', 'Pre-Order', 'Released', 'Sold Out', 'fav']),
    'ar': new Set(['', 'fav']),
    'topspeed': new Set(['', 'Pre-Order', 'Released', 'Sold Out', 'fav']),
    'spark': new Set(['', 'Pre-Order', 'Released', 'Sold Out', 'fav']),
    'spark64': new Set(['', 'Pre-Order', 'Released', 'Sold Out', 'fav']),
    'inno': new Set(['', 'Pre-Order', 'Released', 'Sold Out', 'fav']),
<<<<<<< Updated upstream
    'poprace': new Set(['', 'Pre-Order', 'Released', 'Sold Out', 'fav'])
=======
    'poprace': new Set(['', 'Pre-Order', 'Released', 'Sold Out', 'fav']),
    'gcd': new Set(['', 'Pre-Order', 'Released', 'Sold Out', 'fav']),
    'dct': new Set(['', 'Pre-Order', 'Released', 'Sold Out', 'fav']),
    'tarmacworks': new Set(['', 'Pre-Order', 'Released', 'Sold Out', 'fav']),
    'greenlight': new Set(['', 'Pre-Order', 'Released', 'Sold Out', 'fav']),
    'trendshobby': new Set(['', 'Pre-Order', 'Released', 'Sold Out', 'fav'])
>>>>>>> Stashed changes
};
const productByIndex = new Map(productsData.map(product => [String(product.index), product]));

function escapeHtml(value) {
    return String(value ?? '')
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#39;');
}

function escapeAttr(value) {
    return escapeHtml(value);
}

function productImageData(product) {
    return escapeAttr(JSON.stringify(product.images || []));
}

function productStatusClass(status) {
    const classes = {
        'Pre-Order': 'status-preorder',
        'Released': 'status-released',
        'Sold Out': 'status-soldout'
    };
    return classes[status] || '';
}

function renderTableProduct(product) {
    const images = product.images || [placeholderImage];
    const previewImages = product.previewImages || images.slice(0, product.categoryId === 'topspeed' ? 1 : 3);
    const remainingImageCount = Math.max(0, (product.imageCount || images.length) - previewImages.length);
    const imageHtml = previewImages.map((img, idx) => `
        <img src="${escapeAttr(img)}" data-src="${escapeAttr(img)}" alt="${escapeAttr(product.name)}" class="thumb-img img-lazy" loading="lazy" data-modal-index="${idx}" onerror="handleImageError(this, ${idx})">
    `).join('');
    const extraHtml = remainingImageCount > 0
        ? `<span class="img-count" data-modal-index="0">+${remainingImageCount}</span>`
        : '';

    return `
        <tr data-sku="${escapeAttr(product.sku)}" data-name="${escapeAttr(product.name)}" data-status="${escapeAttr(product.status)}" data-index="${escapeAttr(product.index)}" data-category="${escapeAttr(product.categoryId)}" data-images="${productImageData(product)}">
            <td class="num">${escapeHtml(product.index)}</td>
            <td class="sku" title="点击复制编号" data-copy-sku="${escapeAttr(product.sku)}">${escapeHtml(product.sku)}</td>
            <td class="name-cell">
                <a href="${escapeAttr(product.detailUrl)}" target="_blank" rel="noopener" title="在官网查看详情">${escapeHtml(product.name)}</a>
                <button class="copy-name-btn" type="button" data-copy-name="${escapeAttr(product.name)}" title="复制名称">📋</button>
            </td>
            <td class="status-cell"><span class="badge ${productStatusClass(product.status)}">${escapeHtml(product.status)}</span></td>
            <td class="img-cell">
                <div class="img-triplet" data-modal-index="0">
                    ${imageHtml}
                    ${extraHtml}
                </div>
            </td>
            <td class="fav-cell">
                <button class="fav-btn" type="button" data-sku="${escapeAttr(product.sku)}" title="收藏">☆</button>
            </td>
        </tr>
    `;
}

function renderCardProduct(product) {
    const images = product.images || [placeholderImage];
    const cover = product.coverImage || product.previewImages?.[0] || images[0] || placeholderImage;
    const noImageClass = cover === placeholderImage ? 'is-placeholder' : '';

    return `
        <div class="card-item" data-sku="${escapeAttr(product.sku)}" data-name="${escapeAttr(product.name)}" data-status="${escapeAttr(product.status)}" data-index="${escapeAttr(product.index)}" data-category="${escapeAttr(product.categoryId)}" data-images="${productImageData(product)}">
            <div class="card-img ${noImageClass}" data-modal-index="0">
                <img src="${escapeAttr(cover)}" data-src="${escapeAttr(cover)}" alt="${escapeAttr(product.name)}" loading="lazy" onload="this.classList.add('loaded')" onerror="handleImageError(this, 0)">
                <div class="card-img-overlay">
                    <span class="card-img-count">${escapeHtml(product.imageCount || images.length)} 图</span>
                </div>
            </div>
            <div class="card-body">
                <div class="card-sku" data-copy-sku="${escapeAttr(product.sku)}">${escapeHtml(product.sku)}</div>
                <a href="${escapeAttr(product.detailUrl)}" target="_blank" rel="noopener" class="card-name" title="在官网查看详情">${escapeHtml(product.name)}</a>
                <div class="card-footer">
                    <span class="badge ${productStatusClass(product.status)}">${escapeHtml(product.status)}</span>
                    <button class="fav-btn" type="button" data-sku="${escapeAttr(product.sku)}" title="收藏">☆</button>
                </div>
            </div>
        </div>
    `;
}

function renderCurrentPageProducts(products) {
    const tableBody = document.querySelector('#tableView tbody');
    const cardsView = document.getElementById('cardsView');
    if (currentView === 'table') {
        tableBody.innerHTML = products.map(renderTableProduct).join('');
        cardsView.innerHTML = '';
    } else {
        cardsView.innerHTML = products.map(renderCardProduct).join('');
        tableBody.innerHTML = '';
    }
    updateFavoriteButtons();
    return currentView === 'table'
        ? Array.from(tableBody.querySelectorAll('tr'))
        : Array.from(cardsView.querySelectorAll('.card-item'));
}

function readElementImages(element) {
    if (!element || !element.dataset.images) return [];
    try {
        const images = JSON.parse(element.dataset.images.replace(/&quot;/g, '"'));
        return Array.isArray(images) ? images.filter(Boolean) : [];
    } catch (e) {
        console.warn('Failed to parse preload images:', e);
        return [];
    }
}

function isHeavyImageCategory(categoryId) {
    return categoryId === 'topspeed';
}

function elementUsesHeavyImages(element) {
    return isHeavyImageCategory(element?.dataset?.category || '');
}

function preloadImage(src, priority = 'auto') {
    if (!src) return Promise.resolve(false);
    if (imageLoadCache.has(src)) return imageLoadCache.get(src);

    if (!preloadedImages.has(src) && !src.startsWith('data:')) {
        preloadedImages.add(src);
        const link = document.createElement('link');
        link.rel = 'preload';
        link.as = 'image';
        link.href = src;
        document.head.appendChild(link);
    }

    const promise = new Promise(resolve => {
        const img = new Image();
        img.decoding = 'async';
        img.fetchPriority = priority;
        img.onload = () => {
            imageReady.add(src);
            imageFailed.delete(src);
            resolve(true);
        };
        img.onerror = () => {
            imageFailed.add(src);
            resolve(false);
        };
        img.src = src;
    });

    imageLoadCache.set(src, promise);
    return promise;
}

function markImageLoaded(img) {
    if (!img) return;
    if (img.complete && img.naturalWidth > 0) {
        img.classList.add('loaded');
    }
}

function activateImage(img, priority = 'high') {
    if (!img) return;
    img.classList.add('img-lazy');
    img.removeAttribute('loading');
    img.fetchPriority = priority;
    img.addEventListener('load', () => img.classList.add('loaded'), {once: true});
    img.addEventListener('error', () => img.classList.add('loaded'), {once: true});
    markImageLoaded(img);
    const src = img.dataset.src || img.getAttribute('src') || img.currentSrc;
    if (!src) return;
    if (!img.getAttribute('src')) {
        img.src = src;
    }
    preloadImage(src);
}

function activateVisibleImages(items) {
    if (currentView !== 'cards') return;
    if (isHeavyImageCategory(currentCategory)) {
        items.slice(0, 8).forEach(item => activateImage(item.querySelector('.card-img img'), 'high'));
        return;
    }
    items.forEach(item => activateImage(item.querySelector('.card-img img'), 'high'));
}

function preloadProductImages(element, limit = 3) {
    if (elementUsesHeavyImages(element)) return;
    const images = readElementImages(element);
    images.slice(1, limit).forEach(src => preloadImage(src, 'high'));
}

function preloadCardCover(element, eager = false) {
    if (elementUsesHeavyImages(element)) return;
    const img = element?.querySelector('.card-img img');
    const src = img?.getAttribute('src');
    if (img && eager) {
        activateImage(img, 'high');
    }
    preloadImage(src);
}

function preloadPageCovers(items, eager = false) {
    if (isHeavyImageCategory(currentCategory)) return;
    items.forEach(item => preloadCardCover(item, eager));
}

function preloadPageCoversInChunks(items) {
    const chunkSize = 20;
    let offset = 0;
    
    const runChunk = () => {
        preloadPageCovers(items.slice(offset, offset + chunkSize), true);
        offset += chunkSize;
        if (offset < items.length) setTimeout(runChunk, 120);
    };
    
    runChunk();
}

function preloadUpcomingPageCovers(visibleProducts, endIndex) {
    if (currentView !== 'cards') return;
    if (isHeavyImageCategory(currentCategory)) return;
    if (document.getElementById('search')?.value.trim()) return;
    const nextPageStart = endIndex;
    const nextPageEnd = Math.min(nextPageStart + pageSize, visibleProducts.length);
    if (nextPageStart >= nextPageEnd) return;

    visibleProducts.slice(nextPageStart, nextPageEnd).forEach(product => {
        const src = product.coverImage || product.previewImages?.[0];
        if (src) preloadImage(src, 'auto');
    });
}

function preloadModalNeighbors() {
    if (!currentImages || currentImages.length < 2) return;
    const nextIndex = (currentImageIndex + 1) % currentImages.length;
    const prevIndex = (currentImageIndex - 1 + currentImages.length) % currentImages.length;
    preloadImage(currentImages[nextIndex], 'high');
    if (!isHeavyImageCategory(currentModalCategory)) {
        preloadImage(currentImages[prevIndex], 'high');
    }
}

function preloadModalAllImages(startIndex = currentImageIndex) {
    if (!currentImages || currentImages.length === 0) return;
    const total = currentImages.length;
    const priorityIndexes = isHeavyImageCategory(currentModalCategory)
        ? new Set([startIndex, (startIndex + 1) % total])
        : new Set([
            startIndex,
            (startIndex + 1) % total,
            (startIndex - 1 + total) % total,
        ]);

    priorityIndexes.forEach(index => {
        preloadImage(currentImages[index], 'high');
    });

    if (isHeavyImageCategory(currentModalCategory)) return;

    const remaining = currentImages.filter((_, index) => !priorityIndexes.has(index));
    const chunkSize = 2;
    let offset = 0;

    const loadChunk = () => {
        remaining.slice(offset, offset + chunkSize).forEach(src => preloadImage(src, 'auto'));
        offset += chunkSize;
        if (offset < remaining.length) setTimeout(loadChunk, 100);
    };

    if (remaining.length) {
        requestAnimationFrame(loadChunk);
    }
}

// 初始化各分类的状态
Object.keys(categoryStats).forEach(catId => {
    categoryPagination[catId] = [];
    categoryCurrentFilter[catId] = '';
    categoryCurrentPage[catId] = 1;
});

function getSafeFilterForCategory(categoryId, filter) {
    const allowedFilters = categoryScopedFilters[categoryId];
    if (!allowedFilters || allowedFilters.has(filter)) return filter;
    return '';
}

function updateCategoryDropdownLabel() {
    const select = document.getElementById('categoryDropdownBtn');
    const stats = categoryStats[currentCategory];
    if (!select || !stats) return;
    select.value = currentCategory;
}

function selectCategoryFromDropdown(categoryId) {
    if (!categoryId || categoryId === currentCategory) {
        updateCategoryDropdownLabel();
        return;
    }
    switchCategory(categoryId);
}

function syncQuickFilterButtons() {
    document.querySelectorAll('.quick-filter').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.filter === currentFilter);
    });
    updateCategoryDropdownLabel();
}

function syncScopedControls() {
    document.querySelectorAll('[data-scope]').forEach(control => {
        const scope = control.dataset.scope;
        const scopes = scope.split(/[\s,]+/).filter(Boolean);
        const visible = scopes.includes('all') || scopes.includes(currentCategory);
        control.classList.toggle('control-hidden', !visible);
    });

    const safeFilter = getSafeFilterForCategory(currentCategory, currentFilter);
    if (safeFilter !== currentFilter) {
        currentFilter = safeFilter;
        categoryCurrentFilter[currentCategory] = safeFilter;
    }

    syncQuickFilterButtons();
}

// 切换分类
function switchCategory(categoryId) {
    // 保存当前分类的状态
    if (currentCategory) {
        categoryCurrentFilter[currentCategory] = currentFilter;
        categoryCurrentPage[currentCategory] = currentPage;
        categoryPagination[currentCategory] = getVisibleProducts();
    }
    
    // 切换到新分类
    currentCategory = categoryId;
    currentFilter = getSafeFilterForCategory(categoryId, categoryCurrentFilter[categoryId] || '');
    currentPage = categoryCurrentPage[categoryId] || 1;
    
    // 更新标签激活状态
    document.querySelectorAll('.category-tab').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.category === categoryId);
    });
    // 更新筛选按钮状态
    syncQuickFilterButtons();
    syncScopedControls();
    
    // 更新分页大小选择器
    syncPaginationControls();
    
    // 更新统计信息
    updateCategoryStats();
    
    // 重新应用筛选
    applyFilter();
}

// 获取当前分类的产品数据
function getCategoryProducts() {
    if (currentFilter === 'fav') {
        return productsData;
    }
    return productsData.filter(p => {
        return p.categoryId === currentCategory;
    });
}

// 更新分类统计信息
function updateCategoryStats() {
    const stats = categoryStats[currentCategory];
    if (!stats) return;
    
    const statsGroup = document.getElementById('statsGroup');
    statsGroup.innerHTML = `
        <span class="stat-badge">共 ${stats.total}</span>
        <span class="stat-badge released">✅ ${stats.released}</span>
        <span class="stat-badge preorder">📦 ${stats.preorder}</span>
        <span class="stat-badge soldout">❌ ${stats.soldout}</span>
    `;
}

// 获取当前可见的产品
function getVisibleProducts() {
    let filtered = getCategoryProducts();
    
    // 应用筛选
    if (currentFilter) {
        filtered = filtered.filter(p => {
            if (currentFilter === 'fav') {
                return favorites.has(p.sku);
            }
            return p.status === currentFilter;
        });
    }
    
    // 应用搜索
    const search = document.getElementById('search').value.toLowerCase().trim();
    if (search) {
        filtered = filtered.filter(p => {
            const name = String(p.name || '').toLowerCase();
            const sku = String(p.sku || '').toLowerCase();
            return name.includes(search) || sku.includes(search);
        });
    }

    if (sortState.col) {
        filtered = [...filtered].sort((a, b) => compareProducts(a, b, sortState.col, sortState.dir));
    }
    
    return filtered;
}

function syncSearchClearButton() {
    const search = document.getElementById('search');
    const clearBtn = document.getElementById('searchClearBtn');
    if (!search || !clearBtn) return;
    clearBtn.classList.toggle('visible', search.value.length > 0);
}

function setupControlEventListeners() {
    if (window.__catalogControlsBound) return;
    window.__catalogControlsBound = true;

    document.addEventListener('input', event => {
        if (event.target?.id !== 'search') return;
        debouncedFilter();
    }, true);

    document.addEventListener('change', event => {
        const target = event.target;
        if (!target) return;

        if (target.id === 'categoryDropdownBtn') {
            selectCategoryFromDropdown(target.value);
            return;
        }

        if (target.id === 'pageSizeTop' || target.id === 'pageSizeBottom') {
            changePageSize(target.value);
        }
    }, true);

    document.addEventListener('click', event => {
        const target = event.target;
        if (!target?.closest) return;

        const clearButton = target.closest('#searchClearBtn');
        if (clearButton) {
            event.preventDefault();
            event.stopPropagation();
            clearSearch();
            return;
        }

        const copySku = target.closest('[data-copy-sku]');
        if (copySku) {
            event.preventDefault();
            event.stopPropagation();
            copySKU(copySku.dataset.copySku, copySku);
            return;
        }

        const copyName = target.closest('[data-copy-name]');
        if (copyName) {
            event.preventDefault();
            event.stopPropagation();
            copyText(copyName.dataset.copyName, copyName);
            return;
        }

        const favoriteButton = target.closest('.fav-btn[data-sku]');
        if (favoriteButton) {
            event.preventDefault();
            event.stopPropagation();
            toggleFavorite(favoriteButton.dataset.sku, favoriteButton);
            return;
        }

        const modalTrigger = target.closest('[data-modal-index]');
        if (modalTrigger) {
            const productElement = modalTrigger.closest('tr') || modalTrigger.closest('.card-item');
            if (productElement) {
                event.preventDefault();
                event.stopPropagation();
                openMultiModalFromElement(productElement, parseInt(modalTrigger.dataset.modalIndex, 10) || 0);
                return;
            }
        }

        const filterButton = target.closest('button.quick-filter[data-filter]');
        if (filterButton) {
            event.preventDefault();
            setQuickFilter(filterButton);
            return;
        }

        const viewButton = target.closest('.view-btn');
        if (viewButton) {
            event.preventDefault();
            event.stopPropagation();
            setView(viewButton);
            return;
        }

        const themeButton = target.closest('.theme-btn');
        if (themeButton) {
            event.preventDefault();
            event.stopPropagation();
            toggleTheme();
            return;
        }

        const updateButton = target.closest('.update-btn');
        if (updateButton) {
            event.preventDefault();
            event.stopPropagation();
            const updateTypeById = {
                updateMiniBtn: 'minigt',
                updateArBtn: 'ar',
                updateTopSpeedBtn: 'topspeed',
                updateSparkBtn: 'spark',
                updateSpark64Btn: 'spark64',
<<<<<<< Updated upstream
                updateInnoBtn: 'inno'
=======
                updateInnoBtn: 'inno',
                updateGcdBtn: 'gcd',
                updateDctBtn: 'dct',
                updateTarmacworksBtn: 'tarmacworks',
                updateGreenlightBtn: 'greenlight',
                updateTrendsHobbyBtn: 'trendshobby'
>>>>>>> Stashed changes
            };
            const updateType = updateTypeById[updateButton.id];
            if (updateType) triggerUpdate(updateType);
        }
    }, true);

    const search = document.getElementById('search');
    if (search && !search.dataset.boundInput) {
        search.addEventListener('input', debouncedFilter);
        search.dataset.boundInput = 'true';
    }

    const categorySelect = document.getElementById('categoryDropdownBtn');
    if (categorySelect && !categorySelect.dataset.boundChange) {
        categorySelect.addEventListener('change', event => selectCategoryFromDropdown(event.target.value));
        categorySelect.dataset.boundChange = 'true';
    }

    document.querySelectorAll('#pageSizeTop, #pageSizeBottom').forEach(select => {
        if (select.dataset.boundChange) return;
        select.addEventListener('change', event => changePageSize(event.target.value));
        select.dataset.boundChange = 'true';
    });
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    // Apply saved theme
    const savedTheme = localStorage.getItem('minigtTheme');
    if (savedTheme === 'dark') {
        document.body.classList.add('dark');
        document.querySelector('.theme-btn').textContent = '☀️';
    }
    // Update favorite buttons
    updateFavoriteButtons();
    // Setup sort handlers
    document.querySelectorAll('th[data-sort]').forEach(th => {
        th.addEventListener('click', () => {
            const col = th.dataset.sort;
            if (sortState.col === col) {
                sortState.dir *= -1;
            } else {
                sortState.col = col;
                sortState.dir = 1;
            }
            document.querySelectorAll('th').forEach(h => h.classList.remove('sorted'));
            th.classList.add('sorted');
            sortTable(col, sortState.dir);
        });
    });
    setupControlEventListeners();
    // Keyboard navigation for modal
    document.addEventListener('keydown', (e) => {
        if (!document.getElementById('modalOverlay').classList.contains('active')) return;
        if (e.key === 'Escape') closeModal();
        if (e.key === 'ArrowLeft') prevImage();
        if (e.key === 'ArrowRight') nextImage();
    });
    // Back to top
    window.addEventListener('scroll', () => {
        const btn = document.getElementById('backToTop');
        btn.classList.toggle('visible', window.scrollY > 500);
    });
    // Apply initial filter and pagination
    syncScopedControls();
    syncSearchClearButton();
    applyFilter();
});

// Theme toggle
function toggleTheme() {
    document.body.classList.toggle('dark');
    const isDark = document.body.classList.contains('dark');
    document.querySelector('.theme-btn').textContent = isDark ? '☀️' : '🌙';
    localStorage.setItem('minigtTheme', isDark ? 'dark' : 'light');
}

// View toggle
function setView(btn) {
    currentView = btn.dataset.view;
    document.querySelectorAll('.view-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById('tableView').classList.toggle('hidden', currentView !== 'table');
    document.getElementById('cardsView').classList.toggle('hidden', currentView !== 'cards');
    applyFilter();
}

// Quick filter
function setQuickFilter(btn) {
    currentFilter = btn.dataset.filter;
    categoryCurrentFilter[currentCategory] = currentFilter;
    currentPage = 1;  // Reset to first page when filter changes
    syncQuickFilterButtons();
    applyFilter();
}

// Search with debounce
function debouncedFilter() {
    clearTimeout(filterTimeout);
    currentPage = 1;  // Reset to first page when search changes
    const searchValue = document.getElementById('search')?.value.trim() || '';
    if (searchValue && currentFilter && currentFilter !== 'fav') {
        currentFilter = '';
        categoryCurrentFilter[currentCategory] = '';
        syncQuickFilterButtons();
    }
    syncSearchClearButton();
    filterTimeout = setTimeout(applyFilter, 200);
}

function clearSearch() {
    const search = document.getElementById('search');
    if (!search || !search.value) return;
    search.value = '';
    currentPage = 1;
    syncSearchClearButton();
    applyFilter();
    search.focus();
}

// Filter function with pagination
function applyFilter() {
    syncSearchClearButton();
    const visibleProducts = getVisibleProducts();
    const counts = { 'Pre-Order':0, 'Released':0, 'Sold Out':0 };

    visibleProducts.forEach(product => {
        if (counts[product.status] !== undefined) {
            counts[product.status]++;
        }
    });
    
    // Apply pagination
    updatePagination(visibleProducts);
    
    // Update stats
    const stats = document.getElementById('statsGroup');
    const totalForCategory = categoryStats[currentCategory]?.total || 0;
    stats.innerHTML = `
        <span class="stat-badge">显示 ${visibleProducts.length} / 共 ${totalForCategory}</span>
        <span class="stat-badge released">✅ ${counts['Released']}</span>
        <span class="stat-badge preorder">📦 ${counts['Pre-Order']}</span>
        <span class="stat-badge soldout">❌ ${counts['Sold Out']}</span>
    `;
}

// Update pagination UI
function updatePagination(visibleProducts) {
    const totalItems = visibleProducts.length;
    const totalPages = Math.max(1, Math.ceil(totalItems / pageSize));
    
    // Keep current page within valid range
    currentPage = Math.max(1, Math.min(currentPage, totalPages));
    
    // Calculate start and end indices
    const startIndex = (currentPage - 1) * pageSize;
    const endIndex = Math.min(startIndex + pageSize, totalItems);
    
    const currentPageProducts = visibleProducts.slice(startIndex, endIndex);
    const currentPageElements = renderCurrentPageProducts(currentPageProducts);
    activateVisibleImages(currentPageElements);
    preloadPageCovers(currentPageElements);
    preloadUpcomingPageCovers(visibleProducts, endIndex);
    
    syncPaginationControls(totalPages);
    
    // Store totalPages as global for easy access
    window.totalPages = totalPages;
}

function syncPaginationControls(totalPagesValue = window.totalPages || 1) {
    totalPagesValue = Math.max(1, parseInt(totalPagesValue, 10) || 1);

    document.querySelectorAll('.pagination .page-info').forEach(info => {
        info.textContent = `第 ${currentPage} 页 / 共 ${totalPagesValue} 页`;
    });

    [
        ['btnFirst', 'btnFirstTop', currentPage === 1],
        ['btnPrev', 'btnPrevTop', currentPage === 1],
        ['btnNext', 'btnNextTop', currentPage === totalPagesValue],
        ['btnLast', 'btnLastTop', currentPage === totalPagesValue],
    ].forEach(([bottomId, topId, disabled]) => {
        [bottomId, topId].forEach(id => {
            const button = document.getElementById(id);
            if (button) button.disabled = disabled;
        });
    });

    document.querySelectorAll('.pagination select').forEach(select => {
        select.value = String(pageSize);
    });

    document.querySelectorAll('.pagination .page-jump-input').forEach(input => {
        input.max = String(totalPagesValue);
        input.value = String(currentPage);
        input.disabled = totalPagesValue <= 1;
        input.setAttribute('aria-label', `跳转页码，共 ${totalPagesValue} 页`);
    });

    document.querySelectorAll('.pagination .page-jump-btn').forEach(button => {
        button.disabled = totalPagesValue <= 1;
    });
}

// Go to specific page
function goToPage(page) {
    const maxPage = Math.max(1, parseInt(window.totalPages, 10) || 1);
    page = parseInt(page, 10);
    if (!Number.isFinite(page)) return;
    if (page < 1 || page > maxPage) return;
    currentPage = page;
    applyFilter();
    // Scroll to top
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

function normalizeJumpPage(input) {
    const maxPage = Math.max(1, parseInt(input?.max || window.totalPages, 10) || 1);
    const fallbackPage = Math.max(1, Math.min(currentPage, maxPage));
    const rawPage = parseInt(input?.value, 10);
    const page = Number.isFinite(rawPage) ? Math.max(1, Math.min(rawPage, maxPage)) : fallbackPage;
    if (input) input.value = String(page);
    return page;
}

function jumpToPageInput(input) {
    if (!input || input.disabled) return;
    goToPage(normalizeJumpPage(input));
}

function handlePageJumpKey(event) {
    if (event.key === 'Enter') {
        event.preventDefault();
        jumpToPageInput(event.currentTarget);
    }
    if (event.key === 'Escape') {
        event.currentTarget.value = String(currentPage);
        event.currentTarget.blur();
    }
}

// Go to first page
function goToFirstPage() {
    goToPage(1);
}

// Go to previous page
function goToPrevPage() {
    goToPage(currentPage - 1);
}

// Go to next page
function goToNextPage() {
    goToPage(currentPage + 1);
}

// Go to last page
function goToLastPage() {
    goToPage(window.totalPages || 1);
}

// Change page size
function changePageSize(size) {
    pageSize = parseInt(size);
    currentPage = 1;
    syncPaginationControls();
    applyFilter();
}

// Sort function
function sortTable(col, dir) {
    if (currentView !== 'table') return;
    sortState = { col, dir };
    currentPage = 1;
    applyFilter();
}

function compareProducts(a, b, col, dir) {
    let va;
    let vb;
    if (col === 'num') {
        va = Number(a.index) || 0;
        vb = Number(b.index) || 0;
        return (va - vb) * dir;
    }
    if (col === 'status') {
        const order = { 'Pre-Order':0, 'Released':1, 'Sold Out':2 };
        va = order[a.status] ?? 99;
        vb = order[b.status] ?? 99;
        return (va - vb) * dir;
    }
    va = String(a[col] || '').toLowerCase();
    vb = String(b[col] || '').toLowerCase();
    return va.localeCompare(vb) * dir;
}

// 从 DOM 元素直接读取数据并打开图片（最可靠的方式）
function openMultiModalFromElement(element, imgIndex) {
    if (!element) {
        console.error('Element not found');
        return;
    }
    preloadProductImages(element, 3);
    
    // 尝试从 data 属性读取
    try {
        const images = JSON.parse(element.dataset.images.replace(/&quot;/g, '"'));
        const name = element.dataset.name || '产品图片';
        const category = element.dataset.category || 'mini-gt';
        
        if (images && images.length > 0) {
            const safeImgIndex = Math.max(0, Math.min(imgIndex || 0, images.length - 1));
            openMultiModal(images, name, safeImgIndex, category);
            return;
        }
    } catch (e) {
        console.warn('Failed to read from data-images:', e);
    }
    
    // 降级方案：从 productsData 通过 index 查找
    const index = parseInt(element.dataset.index);
    const product = productsData.find(p => p.index === index);
    if (product) {
        const safeImgIndex = Math.max(0, Math.min(imgIndex || 0, product.images.length - 1));
        openMultiModal(product.images, product.name, safeImgIndex, product.categoryId || 'mini-gt');
        return;
    }
    
    console.error('Failed to find product data');
}

// 保持兼容：通过索引从数组打开图片
function openMultiModalByIndex(index, imgIndex) {
    const product = productsData.find(p => p.index === index);
    if (!product) {
        console.error('Product not found for index:', index);
        return;
    }
    const safeImgIndex = Math.max(0, Math.min(imgIndex || 0, product.images.length - 1));
    openMultiModal(product.images, product.name, safeImgIndex, product.categoryId || 'mini-gt');
}

// Multi-image modal
function openMultiModal(images, name, index, category = 'mini-gt') {
    if (!images || images.length === 0) return;
    currentImages = images;
    currentImageIndex = index;
    currentModalName = name;
    currentModalCategory = category;
    modalLoadToken += 1;
    preloadModalAllImages(currentImageIndex);
    updateModalImage(true);
    document.getElementById('modalCaption').textContent = name;
    document.getElementById('modalOverlay').classList.add('active');
    document.body.style.overflow = 'hidden';
}
function updateModalImage(forceBlank = false) {
    if (!currentImages || currentImages.length === 0) return;
    const img = document.getElementById('modalImg');
    const content = img.closest('.modal-content');
    const nextSrc = currentImages[currentImageIndex];
    const token = ++modalLoadToken;
    const currentSrc = img.getAttribute('src') || '';
    
    if (content) content.classList.add('loading');
    document.getElementById('modalCounter').textContent = `${currentImageIndex + 1} / ${currentImages.length}`;
    preloadModalNeighbors();

    const showImage = () => {
        if (token !== modalLoadToken) return;
        img.onload = null;
        img.onerror = null;
        imageReady.add(nextSrc);
        imageFailed.delete(nextSrc);
        imageLoadCache.set(nextSrc, Promise.resolve(true));
        img.style.opacity = '1';
        document.getElementById('modalCaption').textContent = currentModalName;
        if (content) content.classList.remove('loading');
    };

    const showError = () => {
        if (token !== modalLoadToken) return;
        if (content) content.classList.remove('loading');
        document.getElementById('modalCaption').textContent = '图片加载失败';
    };

    if (forceBlank || !img.getAttribute('src')) {
        img.style.opacity = '0';
    }

    img.onload = showImage;
    img.onerror = showError;

    if (currentSrc !== nextSrc) {
        img.src = nextSrc;
    } else if (img.complete && img.naturalWidth > 0) {
        showImage();
    }

    preloadImage(nextSrc, 'high').then(loaded => {
        if (loaded && token === modalLoadToken && img.getAttribute('src') === nextSrc) {
            showImage();
        }
    });
}
function prevImage() {
    currentImageIndex = (currentImageIndex - 1 + currentImages.length) % currentImages.length;
    updateModalImage();
}
function nextImage() {
    currentImageIndex = (currentImageIndex + 1) % currentImages.length;
    updateModalImage();
}
function closeModal() {
    document.getElementById('modalOverlay').classList.remove('active');
    document.body.style.overflow = '';
}

// Image error handling
function handleImageError(img, idx) {
    const currentSrc = img.getAttribute('src') || img.dataset.src || '';
    const failedSources = new Set((img.dataset.failedSrcs || '').split('|').filter(Boolean));
    if (currentSrc) {
        failedSources.add(currentSrc);
        imageFailed.add(currentSrc);
    }

    const parent = img.closest('tr') || img.closest('.card-item');
    if (parent && parent.dataset.images) {
        try {
            const images = JSON.parse(parent.dataset.images.replace(/&quot;/g, '"'));
            for (let i = 0; i < images.length; i++) {
                const candidate = images[i];
                if (i !== idx && candidate && !failedSources.has(candidate) && candidate !== placeholderImage) {
                    img.dataset.failedSrcs = Array.from(failedSources).join('|');
                    img.src = candidate;
                    return;
                }
            }
        } catch (e) {
            console.warn('Failed to parse images:', e);
        }
    }

    img.onerror = null;
    img.src = placeholderImage;
    img.dataset.src = placeholderImage;
    img.classList.add('loaded');
    img.style.display = '';
}

// Favorites
function toggleFavorite(sku, btn) {
    if (favorites.has(sku)) {
        favorites.delete(sku);
        showToast('已取消收藏');
    } else {
        favorites.add(sku);
        showToast('已收藏');
    }
    // 同时保存两个键名，兼容旧版本
    const favoritesArray = [...favorites];
    localStorage.setItem('minigtFavorites', JSON.stringify(favoritesArray));
    localStorage.setItem('minigt_favorites', JSON.stringify(favoritesArray));
    updateFavoriteButtons();
    applyFilter();
}
function updateFavoriteButtons() {
    document.querySelectorAll('.fav-btn').forEach(btn => {
        const parent = btn.closest('tr') || btn.closest('.card-item');
        const sku = parent?.dataset.sku;
        if (sku) {
            btn.classList.toggle('active', favorites.has(sku));
            btn.textContent = favorites.has(sku) ? '⭐' : '☆';
        }
    });
}

// Copy functions
function copySKU(text, el) {
    copyToClipboard(text);
    if (el.classList) {
        el.classList.add('copied');
        setTimeout(() => el.classList.remove('copied'), 500);
    }
    showToast('已复制: ' + text);
}
function copyText(text, el) {
    copyToClipboard(text);
    showToast('已复制产品名称');
}
function copyToClipboard(text) {
    navigator.clipboard?.writeText(text).catch(() => {
        const ta = document.createElement('textarea');
        ta.value = text;
        ta.style.position = 'fixed';
        ta.style.opacity = '0';
        document.body.appendChild(ta);
        ta.select();
        document.execCommand('copy');
        document.body.removeChild(ta);
    });
}

// Toast
function showToast(msg) {
    const toast = document.getElementById('toast');
    toast.textContent = msg;
    toast.classList.add('show');
    clearTimeout(toast._timeout);
    toast._timeout = setTimeout(() => toast.classList.remove('show'), 1800);
}

// Update function (for buttons)
let statusCheckInterval = null;
const updateButtons = {
    minigt: {
        buttonId: 'updateMiniBtn',
        endpoint: '/api/update-minigt',
        label: '🔄 更新 MINI GT 产品',
        runningText: '⏳ MINI GT 更新中...',
        startText: '🚀 MINI GT 更新已开始，请耐心等待...'
    },
    ar: {
        buttonId: 'updateArBtn',
        endpoint: '/api/update-ar',
        label: '🔄 更新 AR 产品',
        runningText: '⏳ AR 更新中...',
        startText: '🚀 AR 更新已开始，请耐心等待...'
    },
    topspeed: {
        buttonId: 'updateTopSpeedBtn',
        endpoint: '/api/update-topspeed',
        label: '🔄 更新 TOP SPEED 产品',
        runningText: '⏳ TOP SPEED 更新中...',
        startText: '🚀 TOP SPEED 更新已开始，请耐心等待...'
    },
    spark: {
        buttonId: 'updateSparkBtn',
        endpoint: '/api/update-spark',
        label: '🔄 更新 SPARK 产品',
        runningText: '⏳ SPARK 更新中...',
        startText: '🚀 SPARK 更新已开始，请耐心等待...'
    },
    spark64: {
        buttonId: 'updateSpark64Btn',
        endpoint: '/api/update-spark64',
        label: '🔄 更新 SPARK 1:64 产品',
        runningText: '⏳ SPARK 1:64 更新中...',
        startText: '🚀 SPARK 1:64 更新已开始，请耐心等待...'
    },
    inno: {
        buttonId: 'updateInnoBtn',
        endpoint: '/api/update-inno',
        label: '🔄 更新 INNO 产品',
        runningText: '⏳ INNO 更新中...',
        startText: '🚀 INNO 更新已开始，请耐心等待...'
<<<<<<< Updated upstream
=======
    },
    gcd: {
        buttonId: 'updateGcdBtn',
        endpoint: '/api/update-gcd',
        label: '🔄 更新 GCD 产品',
        runningText: '⏳ GCD 更新中...',
        startText: '🚀 GCD 更新已开始，请耐心等待...'
    },
    dct: {
        buttonId: 'updateDctBtn',
        endpoint: '/api/update-dct',
        label: '🔄 更新 DCT 产品',
        runningText: '⏳ DCT 更新中...',
        startText: '🚀 DCT 更新已开始，请耐心等待...'
    },
    tarmacworks: {
        buttonId: 'updateTarmacworksBtn',
        endpoint: '/api/update-tarmacworks',
        label: '🔄 更新 TARMAC WORKS 产品',
        runningText: '⏳ TARMAC WORKS 更新中...',
        startText: '🚀 TARMAC WORKS 更新已开始，请耐心等待...'
    },
    greenlight: {
        buttonId: 'updateGreenlightBtn',
        endpoint: '/api/update-greenlight',
        label: '🔄 更新 GreenLight 产品',
        runningText: '⏳ GreenLight 更新中...',
        startText: '🚀 GreenLight 更新已开始，请耐心等待...'
    },
    trendshobby: {
        buttonId: 'updateTrendsHobbyBtn',
        endpoint: '/api/update-trendshobby',
        label: '🔄 更新 TH 产品',
        runningText: '⏳ TH 更新中...',
        startText: '🚀 TH 更新已开始，请耐心等待...'
>>>>>>> Stashed changes
    }
};

function closeStatusPanel() {
    const panel = document.getElementById('statusPanel');
    panel.className = 'status-panel';
    panel.innerHTML = '';
}

function showStatusPanel(message, state = '') {
    const panel = document.getElementById('statusPanel');
    panel.className = `status-panel visible${state ? ' ' + state : ''}`;
    panel.innerHTML = '';

    const messageEl = document.createElement('span');
    messageEl.className = 'status-message';
    messageEl.textContent = message;

    const closeBtn = document.createElement('button');
    closeBtn.className = 'status-close';
    closeBtn.type = 'button';
    closeBtn.title = '关闭提示';
    closeBtn.setAttribute('aria-label', '关闭提示');
    closeBtn.textContent = '×';
    closeBtn.onclick = closeStatusPanel;

    panel.appendChild(messageEl);
    panel.appendChild(closeBtn);
}

function setUpdateButtonsDisabled(disabled) {
    Object.values(updateButtons).forEach(config => {
        const btn = document.getElementById(config.buttonId);
        if (!btn) return;
        btn.disabled = disabled;
        if (!disabled) btn.textContent = config.label;
    });
}

function triggerUpdate(type) {
    const config = updateButtons[type] || updateButtons.ar;
    const btn = document.getElementById(config.buttonId);
    
    if (btn.disabled) return;
    
    setUpdateButtonsDisabled(true);
    btn.textContent = config.runningText;
    
    showStatusPanel('正在连接服务器...');
    
    // Try to call the update API
    fetch(config.endpoint)
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (data.status === 'started') {
                showStatusPanel(config.startText);
                startStatusCheck();
            } else if (data.status === 'running') {
                showStatusPanel('⏳ 已有更新在进行中...');
                startStatusCheck();
            } else {
                showStatusPanel('更新已触发，请稍后刷新页面', 'success');
                setUpdateButtonsDisabled(false);
            }
        })
        .catch(err => {
            console.error('Update error:', err);
            showStatusPanel('⚠️ 请确保已通过本地服务器访问页面 (http://localhost:5001)', 'error');
            setUpdateButtonsDisabled(false);
        });
}

function startStatusCheck() {
    if (statusCheckInterval) return;
    
    statusCheckInterval = setInterval(() => {
        fetch('/api/status')
            .then(response => response.json())
            .then(data => {
                if (data.running) {
                    showStatusPanel(data.log || '⏳ 正在更新中...');
                } else {
                    clearInterval(statusCheckInterval);
                    statusCheckInterval = null;
                    
                    if (data.log && data.log.includes('✅')) {
                        showStatusPanel(data.log, 'success');
                    } else if (data.log && data.log.includes('❌')) {
                        showStatusPanel(data.log, 'error');
                    } else {
                        showStatusPanel('✓ 准备就绪', 'success');
                    }
                    
                    setUpdateButtonsDisabled(false);
                }
            })
            .catch(err => {
                console.error('Status check error:', err);
                clearInterval(statusCheckInterval);
                statusCheckInterval = null;

                showStatusPanel('⚠️ 无法读取更新状态，请检查本地服务器后重试', 'error');
                setUpdateButtonsDisabled(false);
            });
    }, 2000);
}

// 图片懒加载优化
if ('IntersectionObserver' in window) {
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(e => {
            if (e.isIntersecting) {
                activateImage(e.target);
                const card = e.target.closest('.card-item');
                if (card) preloadProductImages(card, 3);
                observer.unobserve(e.target);
            }
        });
    }, {rootMargin: '100px'});
    document.querySelectorAll('img[loading="lazy"]').forEach(img => {
        img.classList.add('img-lazy');
        observer.observe(img);
    });
}

Object.assign(window, {
    selectCategoryFromDropdown,
    setQuickFilter,
    setView,
    toggleTheme,
    debouncedFilter,
    clearSearch,
    goToFirstPage,
    goToPrevPage,
    goToNextPage,
    goToLastPage,
    jumpToPageInput,
    handlePageJumpKey,
    changePageSize,
    openMultiModalFromElement,
    openMultiModal,
    closeModal,
    prevImage,
    nextImage,
    handleImageError,
    copySKU,
    copyText,
    toggleFavorite,
    triggerUpdate,
    closeStatusPanel
});

</script>
</body>
</html>'''

# 准备产品数据数组（索引从 1 开始，包含分类 ID）
products_list = []
for i, p in enumerate(products):
    # 从 categories_products 获取分类 ID
    cat_id = 'mini-gt'
    for c_id, cat_prods in categories_products.items():
        if p in cat_prods:
            cat_id = c_id
            break
    images = get_images(p)
    preview_limit = 1 if cat_id == 'topspeed' else 3
    modal_images = [modal_image_url(img, cat_id) for img in images]
    preview_images = [preview_image_url(img, cat_id) for img in images[:preview_limit]]
    products_list.append({
        'index': i + 1,
        'name': p.get('name', ''),
        'sku': p.get('sku', ''),
        'status': p.get('status', ''),
        'categoryId': cat_id,
        'detailUrl': product_url(p.get('detail_id', ''), cat_id),
        'images': modal_images,
        'previewImages': preview_images,
        'coverImage': preview_images[0] if preview_images else modal_images[0],
        'imageCount': len(images)
    })
products_json_str = json.dumps(products_list, ensure_ascii=False)

# 替换模板变量（使用单大括号，简单替换）
html = html.replace('{len_products}', str(len(products)))
html = html.replace('{count_released}', str(count_released))
html = html.replace('{count_preorder}', str(count_preorder))
html = html.replace('{count_soldout}', str(count_soldout))
html = html.replace('{category_tabs_html}', category_tabs_html)
html = html.replace('{category_options_html}', category_options_html.strip())
html = html.replace('{table_rows}', table_rows)
html = html.replace('{card_items}', card_items)

# 最后替换 JSON 占位符
html = html.replace('PRODUCTS_JSON_PLACEHOLDER', products_json_str)
html = html.replace('CATEGORY_STATS_PLACEHOLDER', category_stats_json)
html = html.replace('PLACEHOLDER_IMAGE_PLACEHOLDER', json.dumps(PLACEHOLDER_IMAGE))

# ── 写入文件 ──
with HTML_PATH.open('w', encoding='utf-8') as f:
    f.write(html)

print(f'✅ HTML 已生成: {len(products)} 款产品')
print(f'   Pre-Order: {count_preorder} | Released: {count_released} | Sold Out: {count_soldout}')

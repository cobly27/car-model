#!/usr/bin/env python3
"""生成 MINI GT 全产品清单 HTML（优化版）"""
import json
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / 'minigt_products.json'
HTML_PATH = BASE_DIR / 'MINI_GT_产品清单.html'

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
    key = (p['sku'], p['name'], p['image'])
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

# ── 生成大类切换标签 ──
category_tabs_html = ''
for cat in categories:
    cat_id = esc(cat.get('id', ''))
    cat_name = esc(cat.get('name', ''))
    cat_count = len(cat.get('products', []))
    active_class = 'active' if cat == categories[0] else ''
    category_tabs_html += f'<button class="category-tab {active_class}" data-category="{cat_id}" onclick="switchCategory(\'{cat_id}\')">{cat_name} ({cat_count})</button>\n        '

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
    return f'https://minigt.tsm-models.com/index.php?action=product-detail&id={detail_id}'

def get_images(p):
    """获取产品图片列表，对 MINI GT 按封面图、实物图排序，其他分类保留原顺序"""
    images = []
    if p.get('images') and len(p['images']) > 0:
        # 只对含 picfile 路径进行排序，AR 等其他分类保留原顺序
        has_picfile = any('picfile' in img or 'picfile_list' in img for img in p['images'])
        if has_picfile:
            # 分离 picfile_list 和 picfile 的图片
            list_images = [img for img in p['images'] if 'picfile_list' in img]
            main_images = [img for img in p['images'] if 'picfile/' in img and 'picfile_list' not in img]
            # 按顺序：封面图（主图）、实物图 1、实物图 2
            images = main_images + list_images
            if not images:
                images = p['images']
        else:
            # 非 MINI GT 图片保持原顺序
            images = p['images']
    elif p.get('image'):
        images = [p['image']]
    return images

table_rows = ''
card_items = ''
for i, p in enumerate(products):
    name = esc(p['name'])
    sku = esc(p['sku'])
    pid = p.get('detail_id', '')
    st = p.get('status', '')
    sc = status_class(st)
    images = get_images(p)
    
    # 生成图片 HTML - 每张图单独绑定点击事件（添加懒加载）
    img_html = ''
    for idx, img in enumerate(images[:3]):
        img_html += f'<img src="{esc(img)}" alt="{name}" class="thumb-img img-lazy" loading="lazy" onclick="event.stopPropagation();openMultiModalFromElement(this.closest(\'tr\') || this.closest(\'.card-item\'), {idx})" onerror="handleImageError(this, {idx})">'
    
    # 生成图片数据的 JSON 字符串，用于 data 属性
    images_json_data = json.dumps(images, ensure_ascii=False)
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
        f'<span class="img-count" onclick="event.stopPropagation();openMultiModalFromElement(this.closest(\'tr\'), 0)">+{len(images)-3}</span>' if len(images) > 3 else '',
        safe_name_data_attr,
        images_json_escaped,
        p.get('categoryId', 'mini-gt'),
        product_url(pid, p.get('categoryId', 'mini-gt'))
    )
    
    # 卡片项
    card_items += '''
<div class="card-item" data-sku="{0}" data-name="{9}" data-status="{2}" data-index="{4}" data-category="{11}" data-images="{10}">
    <div class="card-img" onclick="openMultiModalFromElement(this.closest(\'.card-item\'), 0)">
        <img src="{5}" alt="{1}" loading="lazy" onload="this.classList.add('loaded')">
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
        esc(images[0]), len(images), sc,
        '',
        safe_name_data_attr,
        images_json_escaped,
        p.get('categoryId', 'mini-gt'),
        product_url(pid, p.get('categoryId', 'mini-gt'))
    )

# 模板使用单大括号，避免处理问题
html = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Car Model-产品清单 ({len_products} 款)</title>
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
    padding: 14px 30px;
    background: var(--card);
    border-bottom: 1px solid var(--border);
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
    align-items: center;
    position: sticky;
    top: 0;
    z-index: 40;
    transition: background 0.3s;
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

/* Quick filters */
.quick-filters {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
}
.quick-filter {
    padding: 6px 12px;
    border-radius: 16px;
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
    padding: 8px 14px;
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
    padding: 12px 20px;
    background: #fff3cd;
    color: #856404;
    font-size: 14px;
    border-bottom: 1px solid #ffeaa7;
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

/* Stats */
.stats-group {
    margin-left: auto;
    display: flex;
    gap: 8px;
    align-items: center;
    flex-wrap: wrap;
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
.hidden { display: none; }

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
    grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
    gap: 16px;
    padding: 20px;
}
.cards-wrap.hidden { display: none; }
.card-item {
    background: var(--card);
    border-radius: 12px;
    overflow: hidden;
    box-shadow: 0 2px 12px var(--shadow);
    transition: transform 0.2s, box-shadow 0.2s;
}
.card-item:hover {
    transform: translateY(-4px);
    box-shadow: 0 8px 24px var(--shadow);
}
.card-img {
    aspect-ratio: 4/3;
    background: var(--border);
    overflow: hidden;
    cursor: pointer;
    position: relative;
}
.card-img img {
    width: 100%;
    height: 100%;
    object-fit: cover;
}
.card-img.no-img::after {
    content: '🖼️';
    position: absolute;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 40px;
    opacity: 0.5;
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
.card-body { padding: 12px; }
.card-sku {
    font-family: "SF Mono", "Fira Code", Monaco, monospace;
    font-size: 12px;
    color: var(--red);
    font-weight: 700;
    margin-bottom: 4px;
    cursor: pointer;
    display: inline-block;
}
.card-name {
    font-size: 13px;
    line-height: 1.4;
    margin-bottom: 10px;
    color: #007bff;
    text-decoration: none;
    display: block;
    cursor: pointer;
}
.card-name:hover {
    text-decoration: underline;
    color: #0056b3;
}
.card-footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
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

/* Category Tabs */
.category-tabs {
    display: flex;
    gap: 8px;
    padding: 12px 20px;
    background: var(--card);
    border-bottom: 1px solid var(--border);
    overflow-x: auto;
}
.category-tab {
    padding: 8px 16px;
    border: 1px solid var(--border);
    background: var(--bg);
    border-radius: 20px;
    cursor: pointer;
    font-size: 14px;
    font-weight: 500;
    white-space: nowrap;
    transition: all 0.2s;
    color: var(--text);
}
.category-tab:hover {
    border-color: var(--red);
    color: var(--red);
}
.category-tab.active {
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

/* Mobile */
@media (max-width: 768px) {
    .header { padding: 16px; }
    .header h1 { font-size: 18px; }
    .header p { font-size: 11px; }
    .controls { padding: 10px 12px; gap: 8px; }
    .controls input { min-width: 0; flex: 1 1 200px; }
    .stats-group { margin-left: 0; width: 100%; justify-content: flex-start; }
    .quick-filters { width: 100%; }
    .cards-wrap { grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 12px; padding: 12px; }
    .modal-nav { display: none; }
    #backToTop { bottom: 20px; right: 16px; width: 38px; height: 38px; font-size: 16px; }
    .pagination { padding: 12px; gap: 6px; }
    .pagination button { padding: 6px 10px; font-size: 13px; }
    .pagination .page-info { font-size: 13px; padding: 6px 10px; }
    .pagination select { padding: 6px 8px; font-size: 13px; }
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

<!-- Category Tabs -->
<div class="category-tabs">
    {category_tabs_html}
</div>

<!-- Status Panel -->
<div class="status-panel" id="statusPanel"></div>

<!-- Controls -->
<div class="controls">
    <input type="text" id="search" placeholder="搜索产品名称或编号..." oninput="debouncedFilter()">
    <div class="quick-filters">
        <button class="quick-filter active" data-filter="" onclick="setQuickFilter(this)">全部</button>
        <button class="quick-filter" data-filter="Pre-Order" onclick="setQuickFilter(this)">📦 Pre-Order</button>
        <button class="quick-filter" data-filter="Released" onclick="setQuickFilter(this)">✅ Released</button>
        <button class="quick-filter" data-filter="Sold Out" onclick="setQuickFilter(this)">❌ Sold Out</button>
        <button class="quick-filter fav-only" data-filter="fav" onclick="setQuickFilter(this)">⭐ 收藏</button>
    </div>
    <div class="view-toggle">
        <button class="view-btn" data-view="table" onclick="setView(this)">📊</button>
        <button class="view-btn active" data-view="cards" onclick="setView(this)">📦</button>
    </div>
    <button class="update-btn" id="updateBtn" onclick="triggerUpdate()">🔄 更新 AR 产品</button>
    <button class="theme-btn" onclick="toggleTheme()">🌙</button>
    <div class="stats-group" id="statsGroup">
        <span class="stat-badge">共 {len_products}</span>
        <span class="stat-badge released">✅ {count_released}</span>
        <span class="stat-badge preorder">📦 {count_preorder}</span>
        <span class="stat-badge soldout">❌ {count_soldout}</span>
    </div>
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
            {table_rows}
        </tbody>
    </table>
</div>

<!-- Cards View -->
<div class="cards-wrap" id="cardsView">
    {card_items}
</div>

<!-- Pagination -->
<div class="pagination" id="pagination">
    <button onclick="goToFirstPage()" id="btnFirst">首页</button>
    <button onclick="goToPrevPage()" id="btnPrev">上一页</button>
    <span class="page-info" id="pageInfo">第 1 页 / 共 1 页</span>
    <button onclick="goToNextPage()" id="btnNext">下一页</button>
    <button onclick="goToLastPage()" id="btnLast">末页</button>
    <select onchange="changePageSize(this.value)">
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

// Global state
let currentImages = [];
let currentImageIndex = 0;
let currentModalName = '';
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
const categoryPageSize = {};

// 初始化各分类的状态
Object.keys(categoryStats).forEach(catId => {
    categoryPagination[catId] = [];
    categoryCurrentFilter[catId] = '';
    categoryCurrentPage[catId] = 1;
    categoryPageSize[catId] = 20;
});

// 切换分类
function switchCategory(categoryId) {
    // 保存当前分类的状态
    if (currentCategory) {
        categoryCurrentFilter[currentCategory] = currentFilter;
        categoryCurrentPage[currentCategory] = currentPage;
        categoryPageSize[currentCategory] = pageSize;
        categoryPagination[currentCategory] = getVisibleProducts();
    }
    
    // 切换到新分类
    currentCategory = categoryId;
    currentFilter = categoryCurrentFilter[categoryId] || '';
    currentPage = categoryCurrentPage[categoryId] || 1;
    pageSize = categoryPageSize[categoryId] || 20;
    
    // 更新标签激活状态
    document.querySelectorAll('.category-tab').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.category === categoryId);
    });
    
    // 更新筛选按钮状态
    document.querySelectorAll('.quick-filter').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.filter === currentFilter);
    });
    
    // 更新分页大小选择器
    document.querySelector('.pagination select').value = pageSize;
    
    // 更新统计信息
    updateCategoryStats();
    
    // 重新应用筛选
    applyFilter();
}

// 获取当前分类的产品数据
function getCategoryProducts() {
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
            return p.name.toLowerCase().includes(search) || p.sku.toLowerCase().includes(search);
        });
    }
    
    return filtered;
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
    currentPage = 1;  // Reset to first page when filter changes
    document.querySelectorAll('.quick-filter').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    applyFilter();
}

// Search with debounce
function debouncedFilter() {
    clearTimeout(filterTimeout);
    currentPage = 1;  // Reset to first page when search changes
    filterTimeout = setTimeout(applyFilter, 200);
}

// Filter function with pagination
function applyFilter() {
    const q = document.getElementById('search').value.toLowerCase();
    const allRows = currentView === 'table' 
        ? document.querySelectorAll('#tableView tbody tr')
        : document.querySelectorAll('#cardsView .card-item');
    
    let count = 0;
    const counts = { 'Pre-Order':0, 'Released':0, 'Sold Out':0 };
    const visibleRows = [];
    
    // First pass: mark all matching rows and collect them
    allRows.forEach(row => {
        const sku = row.dataset.sku?.toLowerCase() || '';
        const name = row.dataset.name?.toLowerCase() || '';
        const status = row.dataset.status || '';
        const category = row.dataset.category || '';
        const isFav = favorites.has(row.dataset.sku);
        
        const matchSearch = !q || sku.includes(q) || name.includes(q);
        const matchStatus = !currentFilter ? true : (currentFilter === 'fav' ? isFav : status === currentFilter);
        // 收藏视图显示所有分类的收藏，不按分类过滤
        const matchCategory = currentFilter === 'fav' ? true : category === currentCategory;
        
        const visible = matchSearch && matchStatus && matchCategory;
        
        if (visible) {
            visibleRows.push(row);
            count++;
            if (counts[status] !== undefined) counts[status]++;
        }
    });
    
    // Apply pagination
    updatePagination(visibleRows);
    
    // Update stats
    const stats = document.getElementById('statsGroup');
    const totalForCategory = categoryStats[currentCategory]?.total || 0;
    stats.innerHTML = `
        <span class="stat-badge">显示 ${count} / 共 ${totalForCategory}</span>
        <span class="stat-badge released">✅ ${counts['Released']}</span>
        <span class="stat-badge preorder">📦 ${counts['Pre-Order']}</span>
        <span class="stat-badge soldout">❌ ${counts['Sold Out']}</span>
    `;
}

// Update pagination UI
function updatePagination(visibleRows) {
    const totalItems = visibleRows.length;
    const totalPages = Math.max(1, Math.ceil(totalItems / pageSize));
    
    // Keep current page within valid range
    currentPage = Math.max(1, Math.min(currentPage, totalPages));
    
    // Calculate start and end indices
    const startIndex = (currentPage - 1) * pageSize;
    const endIndex = Math.min(startIndex + pageSize, totalItems);
    
    // Show/hide rows based on pagination
    const allRows = currentView === 'table' 
        ? document.querySelectorAll('#tableView tbody tr')
        : document.querySelectorAll('#cardsView .card-item');
    
    allRows.forEach(row => row.classList.add('hidden'));
    
    for (let i = startIndex; i < endIndex; i++) {
        visibleRows[i].classList.remove('hidden');
    }
    
    // Update pagination UI
    document.getElementById('pageInfo').textContent = `第 ${currentPage} 页 / 共 ${totalPages} 页`;
    document.getElementById('btnFirst').disabled = currentPage === 1;
    document.getElementById('btnPrev').disabled = currentPage === 1;
    document.getElementById('btnNext').disabled = currentPage === totalPages;
    document.getElementById('btnLast').disabled = currentPage === totalPages;
    
    // Store totalPages as global for easy access
    window.totalPages = totalPages;
}

// Go to specific page
function goToPage(page) {
    if (page < 1 || page > totalPages) return;
    currentPage = page;
    applyFilter();
    // Scroll to top
    window.scrollTo({ top: 0, behavior: 'smooth' });
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
    goToPage(totalPages);
}

// Change page size
function changePageSize(size) {
    pageSize = parseInt(size);
    currentPage = 1;
    applyFilter();
}

// Sort function
function sortTable(col, dir) {
    if (currentView !== 'table') return;
    const tbody = document.querySelector('#tableView tbody');
    const rows = Array.from(tbody.querySelectorAll('tr'));
    
    rows.sort((a, b) => {
        let va, vb;
        if (col === 'num') {
            va = parseInt(a.querySelector('.num').textContent);
            vb = parseInt(b.querySelector('.num').textContent);
            return (va - vb) * dir;
        }
        if (col === 'sku') {
            va = (a.dataset.sku || '').toLowerCase();
            vb = (b.dataset.sku || '').toLowerCase();
            return va.localeCompare(vb) * dir;
        }
        if (col === 'name') {
            va = (a.dataset.name || '').toLowerCase();
            vb = (b.dataset.name || '').toLowerCase();
            return va.localeCompare(vb) * dir;
        }
        if (col === 'status') {
            const order = { 'Pre-Order':0, 'Released':1, 'Sold Out':2 };
            va = order[a.dataset.status] || 0;
            vb = order[b.dataset.status] || 0;
            return (va - vb) * dir;
        }
        return 0;
    });
    
    rows.forEach(row => tbody.appendChild(row));
}

// 从 DOM 元素直接读取数据并打开图片（最可靠的方式）
function openMultiModalFromElement(element, imgIndex) {
    if (!element) {
        console.error('Element not found');
        return;
    }
    
    // 尝试从 data 属性读取
    try {
        const images = JSON.parse(element.dataset.images.replace(/&quot;/g, '"'));
        const name = element.dataset.name || '产品图片';
        
        if (images && images.length > 0) {
            const safeImgIndex = Math.max(0, Math.min(imgIndex || 0, images.length - 1));
            openMultiModal(images, name, safeImgIndex);
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
        openMultiModal(product.images, product.name, safeImgIndex);
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
    openMultiModal(product.images, product.name, safeImgIndex);
}

// Multi-image modal
function openMultiModal(images, name, index) {
    if (!images || images.length === 0) return;
    currentImages = images;
    currentImageIndex = index;
    currentModalName = name;
    updateModalImage();
    document.getElementById('modalCaption').textContent = name;
    document.getElementById('modalOverlay').classList.add('active');
    document.body.style.overflow = 'hidden';
}
function updateModalImage() {
    if (!currentImages || currentImages.length === 0) return;
    const img = document.getElementById('modalImg');
    const content = img.closest('.modal-content');
    const nextSrc = currentImages[currentImageIndex];
    
    if (content) content.classList.add('loading');
    img.style.opacity = '0';
    img.onload = () => {
        img.style.opacity = '1';
        document.getElementById('modalCaption').textContent = currentModalName;
        if (content) content.classList.remove('loading');
    };
    img.onerror = () => {
        if (content) content.classList.remove('loading');
        document.getElementById('modalCaption').textContent = '图片加载失败';
    };
    // 先清空旧图，避免切换时旧图片继续停留造成“下一张没变”的错觉
    img.removeAttribute('src');
    img.src = nextSrc;
    document.getElementById('modalCounter').textContent = `${currentImageIndex + 1} / ${currentImages.length}`;
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
    // 尝试用其他图片替换
    const parent = img.closest('tr') || img.closest('.card-item');
    if (parent && parent.dataset.images) {
        try {
            const images = JSON.parse(parent.dataset.images.replace(/&quot;/g, '"'));
            // 尝试使用其他图片替换
            for (let i = 0; i < images.length; i++) {
                if (i !== idx && images[i]) {
                    img.src = images[i];
                    return;
                }
            }
        } catch (e) {
            console.warn('Failed to parse images:', e);
        }
    }
    // 如果没有其他图片可用，显示占位符
    img.style.display = 'none';
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

// Update function (for button)
let statusCheckInterval = null;
function triggerUpdate() {
    const btn = document.getElementById('updateBtn');
    const panel = document.getElementById('statusPanel');
    
    if (btn.disabled) return;
    
    btn.disabled = true;
    btn.textContent = '⏳ 更新中...';
    
    panel.textContent = '正在连接服务器...';
    panel.className = 'status-panel visible';
    
    // Try to call the update API
    fetch('/api/update-ar')
        .then(response => response.json())
        .then(data => {
            if (data.status === 'started') {
                panel.textContent = '🚀 更新已开始，请耐心等待...';
                startStatusCheck();
            } else if (data.status === 'running') {
                panel.textContent = '⏳ 已有更新在进行中...';
                startStatusCheck();
            } else {
                panel.textContent = '更新已触发，请稍后刷新页面';
                panel.className = 'status-panel visible success';
                btn.disabled = false;
                btn.textContent = '🔄 更新 AR 产品';
            }
        })
        .catch(err => {
            console.error('Update error:', err);
            panel.textContent = '⚠️ 请确保已通过本地服务器访问页面 (http://localhost:5001)';
            panel.className = 'status-panel visible error';
            btn.disabled = false;
            btn.textContent = '🔄 更新 AR 产品';
        });
}

function startStatusCheck() {
    if (statusCheckInterval) return;
    
    statusCheckInterval = setInterval(() => {
        fetch('/api/status')
            .then(response => response.json())
            .then(data => {
                const panel = document.getElementById('statusPanel');
                const btn = document.getElementById('updateBtn');
                
                if (data.running) {
                    panel.textContent = data.log || '⏳ 正在更新中...';
                    panel.className = 'status-panel visible';
                } else {
                    clearInterval(statusCheckInterval);
                    statusCheckInterval = null;
                    
                    if (data.log && data.log.includes('✅')) {
                        panel.textContent = '🎉 更新完成！请刷新页面查看最新数据';
                        panel.className = 'status-panel visible success';
                    } else if (data.log && data.log.includes('❌')) {
                        panel.textContent = data.log;
                        panel.className = 'status-panel visible error';
                    } else {
                        panel.textContent = '✓ 准备就绪';
                        panel.className = 'status-panel visible success';
                    }
                    
                    btn.disabled = false;
                    btn.textContent = '🔄 更新 AR 产品';
                }
            })
            .catch(err => console.error('Status check error:', err));
    }, 2000);
}

// 图片懒加载优化
if ('IntersectionObserver' in window) {
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(e => {
            if (e.isIntersecting) {
                e.target.classList.add('loaded');
                observer.unobserve(e.target);
            }
        });
    }, {rootMargin: '100px'});
    document.querySelectorAll('img[loading="lazy"]').forEach(img => {
        img.classList.add('img-lazy');
        observer.observe(img);
    });
}

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
    products_list.append({
        'index': i + 1,
        'name': p['name'],
        'sku': p['sku'],
        'categoryId': cat_id,
        'images': p.get('images', [p.get('image', '')])
    })
products_json_str = json.dumps(products_list, ensure_ascii=False)

# 替换模板变量（使用单大括号，简单替换）
html = html.replace('{len_products}', str(len(products)))
html = html.replace('{count_released}', str(count_released))
html = html.replace('{count_preorder}', str(count_preorder))
html = html.replace('{count_soldout}', str(count_soldout))
html = html.replace('{category_tabs_html}', category_tabs_html)
html = html.replace('{table_rows}', table_rows)
html = html.replace('{card_items}', card_items)

# 最后替换 JSON 占位符
html = html.replace('PRODUCTS_JSON_PLACEHOLDER', products_json_str)
html = html.replace('CATEGORY_STATS_PLACEHOLDER', category_stats_json)

# ── 写入文件 ──
with HTML_PATH.open('w', encoding='utf-8') as f:
    f.write(html)

print(f'✅ HTML 已生成: {len(products)} 款产品')
print(f'   Pre-Order: {count_preorder} | Released: {count_released} | Sold Out: {count_soldout}')

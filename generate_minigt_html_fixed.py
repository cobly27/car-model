#!/usr/bin/env python3
"""Generate MINI GT product HTML with 3 images per product row."""
import json

with open('/Users/cobly/Desktop/AI编程/minigt_products.json', 'r', encoding='utf-8') as f:
    products = json.load(f)

# Deduplicate by (detail_id, name)
seen = set()
unique = []
for p in products:
    key = (p.get('detail_id'), p.get('name', ''))
    if key not in seen:
        seen.add(key)
        unique.append(p)
products = unique

count_preorder = sum(1 for p in products if p.get('status') == 'Pre-Order')
count_released = sum(1 for p in products if p.get('status') == 'Released')
count_soldout = sum(1 for p in products if p.get('status') == 'Sold Out')

def esc(s):
    return (s or '').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')

def status_class(s):
    m = {'Pre-Order': 'status-preorder', 'Released': 'status-released', 'Sold Out': 'status-soldout'}
    return m.get(s, '')

def product_url(detail_id):
    return f'https://minigt.tsm-models.com/index.php?action=product-detail&id={detail_id}'

# Build table rows
rows = []
for i, p in enumerate(products):
    sku = esc(p.get('sku', ''))
    name = esc(p.get('name', ''))
    status = p.get('status', '')
    sc = status_class(status)
    pid = p.get('detail_id', '')
    
    # Up to 3 images
    imgs = p.get('images', [])
    # Sort images: prefer "big"/"picfile" over "list" (higher quality first)
    def img_sort_key(url):
        url_lower = url.lower()
        if 'picfile_list' in url_lower or 'product_pic_list' in url_lower:
            return 2  # thumbnails last
        return 1  # main images first
    
    imgs_sorted = sorted(imgs, key=img_sort_key)
    display_imgs = imgs_sorted[:3]
    
    # Build image cells HTML
    img_cells = ''
    for idx, img_url in enumerate(display_imgs):
        img_esc = esc(img_url)
        img_cells += f'<img src="{img_esc}" loading="lazy" alt="{name}" onerror="this.style.display=\'none\'">'
    
    # If fewer than 3 images, pad with empty placeholders
    for _ in range(len(display_imgs), 3):
        img_cells += '<div class="img-placeholder-cell"></div>'
    
    # Safely embed JSON array in onclick (escape double quotes for HTML)
    img_json = json.dumps([esc(u) for u in display_imgs]).replace('"', '&quot;')
    name_attr = name.replace('"', '&quot;').replace('\\', '\\\\')
    
    rows.append(f'''
        <tr data-sku="{sku}" data-name="{name}" data-status="{status}">
            <td class="num">{i+1}</td>
            <td class="sku" title="点击复制编号" onclick="copySKU('{sku}', this)">{sku}</td>
            <td class="name-cell">
                <a href="{product_url(pid)}" target="_blank" rel="noopener" title="在官网查看详情">{name}</a>
                <button class="copy-name-btn" onclick="copyText('{name}', this)" title="复制名称">📋</button>
            </td>
            <td class="status-cell"><span class="badge {sc}">{status}</span></td>
            <td class="img-cell">
                <div class="img-triplet" onclick="openModalTriplet({img_json}, 0, '{name_attr}')">
                    {img_cells}
                </div>
            </td>
        </tr>''')

rows_html = '\n'.join(rows)

html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>MINI GT 全产品清单 ({len(products)}款)</title>
<style>
* {{ margin:0; padding:0; box-sizing: border-box; }}
:root {{
    --red: #e63946;
    --dark: #1a1a2e;
    --bg: #f0f2f5;
    --card: #fff;
    --border: #e8e8e8;
}}
body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", sans-serif;
    background: var(--bg);
    color: var(--dark);
}}
.header {{
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
    color: #fff;
    padding: 24px 30px;
}}
.header h1 {{ font-size: 22px; font-weight: 700; margin-bottom: 4px; letter-spacing: .5px; }}
.header p {{ font-size: 13px; opacity: .75; }}
.header a {{ color: #fff !important; }}
.header a:hover {{ opacity: .85; }}

.controls {{
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
}}
.controls input, .controls select, .controls button {{
    padding: 8px 14px;
    border: 1px solid #d0d0d0;
    border-radius: 8px;
    font-size: 13px;
    background: #fff;
    font-family: inherit;
}}
.controls input:focus, .controls select:focus {{
    outline: none;
    border-color: var(--red);
    box-shadow: 0 0 0 2px rgba(230,57,70,.1);
}}
.controls input {{ min-width: 260px; }}
.stats-group {{
    margin-left: auto;
    display: flex;
    gap: 8px;
    align-items: center;
    flex-wrap: wrap;
}}
.stat-badge {{
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 4px 10px;
    border-radius: 14px;
    font-size: 12px;
    font-weight: 600;
    white-space: nowrap;
}}
.stat-badge.all {{ background: #e8e8e8; color: #555; }}
.stat-badge.released {{ background: #d4edda; color: #155724; }}
.stat-badge.preorder {{ background: #fff3cd; color: #856404; }}
.stat-badge.soldout {{ background: #f8d7da; color: #721c24; }}
.btn-export {{
    background: var(--dark) !important;
    color: #fff !important;
    border: none !important;
    cursor: pointer;
    transition: opacity .2s;
    font-weight: 600;
}}
.btn-export:hover {{ opacity: .85; }}

.table-wrap {{ overflow-x: auto; }}
table {{ width: 100%; table-layout: fixed; border-collapse: collapse; background: var(--card); min-width: 700px; }}
th:nth-child(1) {{ width: 45px; }}
th:nth-child(2) {{ width: 150px; }}
th:nth-child(4) {{ width: 90px; }}
th:nth-child(5) {{ width: 340px; }}
th {{
    background: #f8f8f8;
    padding: 10px 14px;
    text-align: left;
    font-size: 12px;
    font-weight: 600;
    color: #666;
    border-bottom: 2px solid #e0e0e0;
    text-transform: uppercase;
    letter-spacing: .5px;
    cursor: pointer;
    user-select: none;
    position: relative;
    transition: background .15s;
}}
th:hover {{ background: #efefef; }}
th .sort-arrow {{ font-size: 10px; margin-left: 4px; opacity: .3; }}
th.sorted .sort-arrow {{ opacity: 1; color: var(--red); }}
td {{ padding: 10px 14px; border-bottom: 1px solid #f0f0f0; font-size: 13px; vertical-align: middle; }}
tr:hover td {{ background: #fafafa; }}
.hidden {{ display: none; }}

.num {{ color: #999; text-align: center; }}
.sku {{
    font-family: "SF Mono", "Fira Code", Monaco, monospace;
    font-size: 12px;
    color: var(--red);
    font-weight: 700;
    white-space: nowrap;
    cursor: pointer;
    transition: background .15s;
}}
.sku:hover {{ background: #fff0f0; border-radius: 4px; }}
.sku.copied {{ animation: flash-green .5s ease; }}
@keyframes flash-green {{
    0% {{ background: #d4edda; color: #155724; }}
    100% {{ background: transparent; color: var(--red); }}
}}
.name-cell {{
    line-height: 1.45;
    font-size: 13px;
}}
.name-cell a {{
    color: var(--dark);
    text-decoration: none;
    transition: color .15s;
}}
.name-cell a:hover {{ color: var(--red); text-decoration: underline; }}
.copy-name-btn {{
    opacity:0;
    background: none;
    border: none;
    cursor: pointer;
    font-size: 13px;
    padding: 0 4px;
    transition: opacity .15s;
    vertical-align: middle;
}}
tr:hover .copy-name-btn {{ opacity: .6; }}
.copy-name-btn:hover {{ opacity: 1 !important; }}

/* ── Status badges ── */
.status-cell {{ text-align: center; }}
.badge {{
    display: inline-block;
    padding: 3px 10px;
    border-radius: 12px;
    font-size: 11px;
    font-weight: 600;
}}
.status-preorder {{ background: #fff3cd; color: #856404; }}
.status-released  {{ background: #d4edda; color: #155724; }}
.status-soldout   {{ background: #f8d7da; color: #721c24; }}

/* ── Image triplet ── */
.img-cell {{ text-align: center; }}
.img-triplet {{
    display: flex;
    gap: 4px;
    align-items: center;
    justify-content: center;
    max-width: 320px;
    cursor: pointer;
    padding: 4px 0;
}}
.img-triplet img {{
    width: 100px;
    height: 75px;
    object-fit: contain;
    border-radius: 4px;
    background: #f9f9f9;
    transition: transform .15s, box-shadow .15s;
    flex-shrink: 0;
}}
.img-triplet img:hover {{
    transform: scale(1.08);
    box-shadow: 0 2px 12px rgba(0,0,0,.15);
    z-index: 2;
}}
.img-placeholder-cell {{
    width: 100px;
    height: 75px;
    background: #f5f5f5;
    border-radius: 4px;
    flex-shrink: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 20px;
    color: #ccc;
}}

/* ── Image Modal ── */
.modal-overlay {{
    display: none;
    position: fixed;
    inset: 0;
    background: rgba(0,0,0,.82);
    z-index: 9999;
    cursor: pointer;
    animation: fadeIn .2s ease;
}}
.modal-overlay.active {{ display: flex; align-items: center; justify-content: center; flex-direction: column; }}
@keyframes fadeIn {{ from {{ opacity:0; }} to {{ opacity:1; }} }}
.modal-content {{
    position: relative;
    animation: zoomIn .25s ease;
    max-width: 90vw;
    max-height: 85vh;
}}
@keyframes zoomIn {{ from {{ transform: scale(.85); opacity:0; }} to {{ transform: scale(1); opacity:1; }} }}
.modal-content img {{
    max-width: 90vw;
    max-height: 85vh;
    border-radius: 8px;
    box-shadow: 0 8px 40px rgba(0,0,0,.5);
    object-fit: contain;
    background: #fff;
    padding: 8px;
}}
.modal-img-nav {{
    position: absolute;
    top: 50%;
    transform: translateY(-50%);
    background: rgba(0,0,0,.4);
    color: #fff;
    border: none;
    width: 40px;
    height: 60px;
    font-size: 22px;
    cursor: pointer;
    border-radius: 0 8px 8px 0;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: background .15s;
}}
.modal-img-nav:hover {{ background: rgba(0,0,0,.65); }}
.modal-img-nav.prev {{ left: -45px; border-radius: 0 8px 8px 0; }}
.modal-img-nav.next {{ right: -45px; border-radius: 8px 0 0 8px; }}
.modal-img-dots {{
    margin-top: 12px;
    display: flex;
    gap: 8px;
    justify-content: center;
}}
.modal-img-dot {{
    width: 10px; height: 10px;
    border-radius: 50%;
    background: rgba(255,255,255,.35);
    cursor: pointer;
    border: 1px solid rgba(255,255,255,.5);
    padding: 0;
    transition: background .15s;
}}
.modal-img-dot.active {{ background: #fff; }}

/* ── Back to Top ── */
#backToTop {{
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
    box-shadow: 0 2px 12px rgba(0,0,0,.2);
    transition: opacity .2s, transform .2s;
}}
#backToTop:hover {{ opacity: .85; transform: translateY(-2px); }}
#backToTop.visible {{ display: flex; align-items: center; justify-content: center; }}

/* ── Toast ── */
.toast {{
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
}}
.toast.show {{ opacity: 1; transform: translateX(-50%) translateY(0); }}

/* ── Footer ── */
.footer {{
    text-align: center;
    padding: 24px;
    color: #999;
    font-size: 12px;
    border-top: 1px solid var(--border);
}}

/* ── Mobile ── */
@media (max-width: 768px) {{
    .header {{ padding: 16px 16px; }}
    .header h1 {{ font-size: 18px; }}
    .header p {{ font-size: 11px; }}
    .controls {{ padding: 10px 12px; gap: 6px; }}
    .controls input {{ min-width: 0; flex: 1 1 160px; }}
    .stats-group {{ margin-left: 0; width: 100%; justify-content: space-between; }}
    table {{ min-width: auto; table-layout: auto; }}
    th:nth-child(1), th:nth-child(2), th:nth-child(4), th:nth-child(5) {{ width: auto; }}
    th, td {{ padding: 8px 6px; font-size: 11px; }}
    .sku {{ font-size: 10px; }}
    .name-cell {{ font-size: 11px; }}
    .status-cell {{ width: auto; }}
    .badge {{ font-size: 10px; padding: 2px 7px; }}
    .img-triplet {{ max-width: 220px; }}
    .img-triplet img {{ width: 65px; height: 48px; }}
    .img-placeholder-cell {{ width: 65px; height: 48px; }}
    .copy-name-btn {{ display: none; }}
    #backToTop {{ bottom: 20px; right: 16px; width: 38px; height: 38px; font-size: 16px; }}
}}
</style>
</head>
<body>

<!-- Header -->
<div class="header">
    <h1>🏎️ MINI GT 全产品清单</h1>
    <p>数据来源: <a href="https://minigt.tsm-models.com/index.php?action=product-list&b_id=13" target="_blank" rel="noopener">minigt.tsm-models.com</a> · 抓取时间: 2026-06-05 · 共 {len(products)} 款产品 · 每款显示3张产品图</p>
</div>

<!-- Controls -->
<div class="controls">
    <input type="text" id="search" placeholder="搜索产品名称或编号（支持模糊匹配）..." oninput="filterTable()">
    <select id="statusFilter" onchange="filterTable()">
        <option value="">🔽 全部状态</option>
        <option value="Pre-Order">📦 Pre-Order</option>
        <option value="Released">✅ Released</option>
        <option value="Sold Out">❌ Sold Out</option>
    </select>
    <button class="btn-export" onclick="exportCSV()" title="导出为 CSV 文件">📥 导出 CSV</button>
    <div class="stats-group" id="statsGroup">
        <span class="stat-badge all">全部 {len(products)}</span>
        <span class="stat-badge released">✅ {count_released}</span>
        <span class="stat-badge preorder">📦 {count_preorder}</span>
        <span class="stat-badge soldout">❌ {count_soldout}</span>
    </div>
</div>

<!-- Table -->
<div class="table-wrap">
<table>
<thead>
<tr>
    <th class="num" data-sort="num"># <span class="sort-arrow">↕</span></th>
    <th data-sort="sku">编号 <span class="sort-arrow">↕</span></th>
    <th data-sort="name">产品名称 <span class="sort-arrow">↕</span></th>
    <th data-sort="status">状态 <span class="sort-arrow">↕</span></th>
    <th>产品图片（3张）</th>
</tr>
</thead>
<tbody>
{rows_html}
</tbody>
</table>
</div>

<!-- Footer -->
<div class="footer">MINI GT Product Catalog · Generated by WorkBuddy · 点击图片查看大图 · 点击编号复制</div>

<!-- Image Modal (with navigation) -->
<div class="modal-overlay" id="modalOverlay" onclick="closeModal(event)">
    <div class="modal-content" onclick="event.stopPropagation()">
        <button class="modal-img-nav prev" onclick="modalNav(-1)">‹</button>
        <img id="modalImg" src="" alt="">
        <button class="modal-img-nav next" onclick="modalNav(1)">›</button>
        <div class="modal-img-dots" id="modalDots"></div>
    </div>
</div>

<!-- Back to Top -->
<button id="backToTop" onclick="window.scrollTo({{top:0,behavior:'smooth'}})" title="回到顶部">⬆</button>

<!-- Toast -->
<div class="toast" id="toast"></div>

<script>
// Modal state
var modalImgs = [];
var modalIdx = 0;

// Open modal with triplet navigation
function openModalTriplet(imgs, startIdx, caption) {{
    if (!imgs || imgs.length === 0) return;
    modalImgs = imgs;
    modalIdx = startIdx || 0;
    showModalImg();
    document.getElementById('modalOverlay').classList.add('active');
    document.body.style.overflow = 'hidden';
}}

function showModalImg() {{
    if (modalIdx < 0) modalIdx = modalImgs.length - 1;
    if (modalIdx >= modalImgs.length) modalIdx = 0;
    document.getElementById('modalImg').src = modalImgs[modalIdx];
    // Update dots
    var dots = document.getElementById('modalDots');
    dots.innerHTML = '';
    for (var i = 0; i < modalImgs.length; i++) {{
        var dot = document.createElement('button');
        dot.className = 'modal-img-dot' + (i === modalIdx ? ' active' : '');
        dot.onclick = (function(idx) {{ return function() {{ modalIdx = idx; showModalImg(); }}; }})(i);
        dots.appendChild(dot);
    }}
}}

function modalNav(dir) {{
    modalIdx += dir;
    showModalImg();
}}

function closeModal(e) {{
    if (e && e.target !== e.currentTarget) return;
    document.getElementById('modalOverlay').classList.remove('active');
    document.body.style.overflow = '';
}}

document.addEventListener('keydown', function(e) {{
    if (e.key === 'Escape') closeModal();
    if (e.key === 'ArrowLeft') modalNav(-1);
    if (e.key === 'ArrowRight') modalNav(1);
}});

// Back to Top
window.addEventListener('scroll', function() {{
    var btn = document.getElementById('backToTop');
    if (window.scrollY > 500) {{
        btn.classList.add('visible');
    }} else {{
        btn.classList.remove('visible');
    }}
}});

// Copy SKU
function copySKU(text, el) {{
    copyToClipboard(text);
    el.classList.add('copied');
    setTimeout(function() {{ el.classList.remove('copied'); }}, 500);
    showToast('已复制: ' + text);
}}

function copyText(text, el) {{
    copyToClipboard(text);
    showToast('已复制名称');
}}

function copyToClipboard(text) {{
    var ta = document.createElement('textarea');
    ta.value = text;
    ta.style.position = 'fixed';
    ta.style.opacity = '0';
    document.body.appendChild(ta);
    ta.select();
    document.execCommand('copy');
    document.body.removeChild(ta);
}}

// Toast
function showToast(msg) {{
    var toast = document.getElementById('toast');
    toast.textContent = msg;
    toast.classList.add('show');
    clearTimeout(toast._timeout);
    toast._timeout = setTimeout(function() {{ toast.classList.remove('show'); }}, 1800);
}}

// Normalize for fuzzy search
function normalize(s) {{
    return (s || '').toLowerCase()
        .replace(/[-–—\\s]+/g, '')
        .replace(/[&]+/g, 'and');
}}

// Filter
function filterTable() {{
    var q = document.getElementById('search').value;
    var qN = normalize(q);
    var sf = document.getElementById('statusFilter').value;
    var rows = document.querySelectorAll('tbody tr');
    var count = 0;
    var counts = {{'Pre-Order':0,'Released':0,'Sold Out':0}};
    rows.forEach(function(row) {{
        var sku = row.dataset.sku || '';
        var name = row.dataset.name || '';
        var st = row.dataset.status || '';
        var ok = (!qN || normalize(sku).indexOf(qN) >= 0 || normalize(name).indexOf(qN) >= 0);
        var ok2 = !sf || st === sf;
        if (ok && ok2) {{
            row.classList.remove('hidden');
            count++;
            if (counts[st] !== undefined) counts[st]++;
        }} else {{
            row.classList.add('hidden');
        }}
    }});
    document.getElementById('statsGroup').innerHTML =
        '<span class="stat-badge all">显示 ' + count + ' / 共 {len(products)} 款</span>' +
        '<span class="stat-badge released">✅ ' + counts['Released'] + '</span>' +
        '<span class="stat-badge preorder">📦 ' + counts['Pre-Order'] + '</span>' +
        '<span class="stat-badge soldout">❌ ' + counts['Sold Out'] + '</span>';
}}

// Column sort
var sortS = {{ col:'', dir:1 }};
document.querySelectorAll('th[data-sort]').forEach(function(th) {{
    th.addEventListener('click', function() {{
        var col = th.dataset.sort;
        if (sortS.col === col) sortS.dir *= -1;
        else {{ sortS.col = col; sortS.dir = 1; }}
        document.querySelectorAll('th').forEach(function(h){{ h.classList.remove('sorted'); }});
        th.classList.add('sorted');
        sortTable(col, sortS.dir);
    }});
}});

function sortTable(col, dir) {{
    var tb = document.querySelector('tbody');
    var rows = Array.from(tb.querySelectorAll('tr:not(.hidden)'));
    var all = Array.from(tb.querySelectorAll('tr'));
    var hid = all.filter(function(r){{ return r.classList.contains('hidden'); }});
    rows.sort(function(a,b) {{
        var va, vb;
        if (col==='num') {{ va=parseInt(a.querySelector('.num').textContent); vb=parseInt(b.querySelector('.num').textContent); return (va-vb)*dir; }}
        if (col==='sku') {{ va=(a.dataset.sku||'').toLowerCase(); vb=(b.dataset.sku||'').toLowerCase(); return va.localeCompare(vb)*dir; }}
        if (col==='name') {{ va=(a.dataset.name||'').toLowerCase(); vb=(b.dataset.name||'').toLowerCase(); return va.localeCompare(vb)*dir; }}
        if (col==='status') {{ var o={{'Pre-Order':0,'Released':1,'Sold Out':2}}; return ((o[a.dataset.status]||0)-(o[b.dataset.status]||0))*dir; }}
        return 0;
    }});
    rows.forEach(function(r){{ tb.appendChild(r); }});
    hid.forEach(function(r){{ tb.appendChild(r); }});
}}

// Export CSV
function exportCSV() {{
    var rows = document.querySelectorAll('tbody tr:not(.hidden)');
    var csv = '\\uFEFF序号,编号,产品名称,状态,图片链接1,图片链接2,图片链接3\\n';
    rows.forEach(function(row, i) {{
        var sku = row.dataset.sku || '';
        var name = (row.dataset.name || '').replace(/"/g, '""');
        var status = row.dataset.status || '';
        var imgs = row.querySelectorAll('.img-triplet img');
        var i1 = imgs[0] ? imgs[0].src : '';
        var i2 = imgs[1] ? imgs[1].src : '';
        var i3 = imgs[2] ? imgs[2].src : '';
        csv += (i+1) + ',"' + sku + '","' + name + '","' + status + '","' + i1 + '","' + i2 + '","' + i3 + '"\\n';
    }});
    var blob = new Blob([csv], {{type:'text/csv;charset=utf-8'}});
    var url = URL.createObjectURL(blob);
    var a = document.createElement('a');
    a.href = url; a.download = 'MINI_GT_产品清单.csv';
    document.body.appendChild(a); a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    showToast('CSV 已导出（当前筛选结果）');
}}
</script>
</body>
</html>'''

with open('/Users/cobly/Desktop/AI编程/MINI_GT_产品清单.html', 'w', encoding='utf-8') as f:
    f.write(html)

print(f'HTML generated: {len(products)} products, 3 images each')
print(f'Pre-Order: {count_preorder} | Released: {count_released} | Sold Out: {count_soldout}')

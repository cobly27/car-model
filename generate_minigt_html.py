#!/usr/bin/env python3
"""生成 MINI GT 全产品清单 HTML（优化版）"""
import json

# ── 读取数据 ──
with open('/Users/cobly/Desktop/AI编程/minigt_products.json', 'r', encoding='utf-8') as f:
    products = json.load(f)

# 去重
seen = set()
unique = []
for p in products:
    key = (p['sku'], p['name'], p['image'])
    if key not in seen:
        seen.add(key)
        unique.append(p)
products = unique

count_preorder = sum(1 for p in products if p.get('status') == 'Pre-Order')
count_released = sum(1 for p in products if p.get('status') == 'Released')
count_soldout = sum(1 for p in products if p.get('status') == 'Sold Out')

# ── 生成表格行 ──
def esc(s):
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')

def status_class(s):
    m = {'Pre-Order': 'status-preorder', 'Released': 'status-released', 'Sold Out': 'status-soldout'}
    return m.get(s, '')

def product_url(detail_id):
    """生成官网产品详情链接（使用数字ID而非SKU）"""
    return f'https://minigt.tsm-models.com/index.php?action=product-detail&id={detail_id}'

rows_html = ''
for i, p in enumerate(products):
    name = esc(p['name'])
    sku = esc(p['sku'])
    img = esc(p['image'])
    pid = p.get('detail_id', '')
    st = p.get('status', '')
    sc = status_class(st)
    rows_html += f'''
        <tr data-sku="{sku}" data-name="{name}" data-status="{st}">
            <td class="num">{i+1}</td>
            <td class="sku" title="点击复制编号" onclick="copySKU('{sku}', this)">{sku}</td>
            <td class="name-cell">
                <a href="{product_url(pid)}" target="_blank" rel="noopener" title="在官网查看详情">{name}</a>
                <button class="copy-name-btn" onclick="copyText('{name}', this)" title="复制名称">📋</button>
            </td>
            <td class="status-cell"><span class="badge {sc}">{st}</span></td>
            <td class="img-cell">
                <div class="img-wrapper" onclick="openModal('{img}', '{name}')">
                    <img src="{img}" loading="lazy" alt="{name}" onerror="this.style.display='none';this.parentElement.classList.add('broken')">
                    <div class="img-placeholder">🖼️<br>点击查看</div>
                </div>
            </td>
        </tr>'''

html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>MINI GT 全产品清单 ({len(products)}款)</title>
<style>
/* ══════════════════════════════════════
   重置 & 基础
   ══════════════════════════════════════ */
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
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

/* ══════════════════════════════════════
   Header
   ══════════════════════════════════════ */
.header {{
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
    color: #fff;
    padding: 24px 30px;
}}
.header h1 {{ font-size: 22px; font-weight: 700; margin-bottom: 4px; letter-spacing: .5px; }}
.header p {{ font-size: 13px; opacity: .75; }}

/* ══════════════════════════════════════
   Controls
   ══════════════════════════════════════ */
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

/* ══════════════════════════════════════
   Table
   ══════════════════════════════════════ */
.table-wrap {{ overflow-x: auto; }}
table {{ width: 100%; border-collapse: collapse; background: var(--card); min-width: 700px; }}
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

/* ── Columns ── */
.num {{
    width: 50px; color: #999; text-align: center;
}}
.sku {{
    font-family: "SF Mono", "Fira Code", Monaco, monospace;
    font-size: 12px;
    color: var(--red);
    font-weight: 700;
    white-space: nowrap;
    width: 140px;
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
    max-width: 480px;
}}
.name-cell a {{
    color: var(--dark);
    text-decoration: none;
    transition: color .15s;
}}
.name-cell a:hover {{ color: var(--red); text-decoration: underline; }}
.copy-name-btn {{
    opacity: 0;
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
.status-cell {{ width: 100px; text-align: center; }}
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

/* ══════════════════════════════════════
   Image cell
   ══════════════════════════════════════ */
.img-cell {{ width: 120px; text-align: center; }}
.img-wrapper {{
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 100px;
    height: 70px;
    border-radius: 6px;
    overflow: hidden;
    cursor: pointer;
    transition: box-shadow .15s, transform .15s;
    background: #f9f9f9;
    position: relative;
}}
.img-wrapper:hover {{
    box-shadow: 0 2px 12px rgba(0,0,0,.15);
    transform: translateY(-1px);
}}
.img-wrapper img {{
    max-width: 100%;
    max-height: 100%;
    object-fit: contain;
    display: block;
}}
.img-wrapper.broken .img-placeholder {{
    display: flex;
}}
.img-wrapper .img-placeholder {{
    display: none;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    width: 100%;
    height: 100%;
    font-size: 12px;
    color: #bbb;
    line-height: 1.4;
}}
.img-wrapper.broken img {{ display: none; }}

/* ══════════════════════════════════════
   Image Modal
   ══════════════════════════════════════ */
.modal-overlay {{
    display: none;
    position: fixed;
    inset: 0;
    background: rgba(0,0,0,.82);
    z-index: 9999;
    cursor: pointer;
    animation: fadeIn .2s ease;
}}
.modal-overlay.active {{ display: flex; align-items: center; justify-content: center; }}
@keyframes fadeIn {{ from {{ opacity: 0; }} to {{ opacity: 1; }} }}
.modal-content {{
    max-width: 90vw;
    max-height: 85vh;
    position: relative;
    animation: zoomIn .25s ease;
}}
@keyframes zoomIn {{ from {{ transform: scale(.85); opacity: 0; }} to {{ transform: scale(1); opacity: 1; }} }}
.modal-content img {{
    max-width: 90vw;
    max-height: 85vh;
    border-radius: 8px;
    box-shadow: 0 8px 40px rgba(0,0,0,.5);
    object-fit: contain;
    background: #fff;
    padding: 8px;
}}
.modal-close {{
    position: absolute;
    top: -40px;
    right: 0;
    background: none;
    border: none;
    color: #fff;
    font-size: 32px;
    cursor: pointer;
    line-height: 1;
    opacity: .7;
    transition: opacity .2s;
}}
.modal-close:hover {{ opacity: 1; }}
.modal-caption {{
    text-align: center;
    color: #fff;
    font-size: 13px;
    margin-top: 10px;
    max-width: 90vw;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}}

/* ══════════════════════════════════════
   Back to Top
   ══════════════════════════════════════ */
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

/* ══════════════════════════════════════
   Toast
   ══════════════════════════════════════ */
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

/* ══════════════════════════════════════
   Footer
   ══════════════════════════════════════ */
.footer {{
    text-align: center;
    padding: 24px;
    color: #999;
    font-size: 12px;
    border-top: 1px solid var(--border);
}}

/* ══════════════════════════════════════
   Mobile
   ══════════════════════════════════════ */
@media (max-width: 768px) {{
    .header {{ padding: 16px 16px; }}
    .header h1 {{ font-size: 18px; }}
    .header p {{ font-size: 11px; }}
    .controls {{
        padding: 10px 12px;
        gap: 6px;
    }}
    .controls input {{ min-width: 0; flex: 1 1 160px; }}
    .stats-group {{ margin-left: 0; width: 100%; justify-content: space-between; }}
    table {{ min-width: auto; }}
    th, td {{ padding: 8px 6px; font-size: 11px; }}
    .num {{ width: 30px; }}
    .sku {{ width: auto; font-size: 10px; }}
    .name-cell {{ max-width: 180px; font-size: 11px; }}
    .status-cell {{ width: auto; }}
    .badge {{ font-size: 10px; padding: 2px 7px; }}
    .img-cell {{ width: 70px; }}
    .img-wrapper {{ width: 60px; height: 45px; }}
    .copy-name-btn {{ display: none; }}
    #backToTop {{ bottom: 20px; right: 16px; width: 38px; height: 38px; font-size: 16px; }}
}}
</style>
</head>
<body>

<!-- ── Header ── -->
<div class="header">
    <h1>🏎️ MINI GT 全产品清单</h1>
    <p>数据来源: minigt.tsm-models.com · 抓取时间: 2026-06-04 · 共 {len(products)} 款</p>
</div>

<!-- ── Controls ── -->
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

<!-- ── Table ── -->
<div class="table-wrap">
<table>
<thead>
<tr>
    <th class="num" data-sort="num"># <span class="sort-arrow">↕</span></th>
    <th data-sort="sku">编号 <span class="sort-arrow">↕</span></th>
    <th data-sort="name">产品名称 <span class="sort-arrow">↕</span></th>
    <th data-sort="status">状态 <span class="sort-arrow">↕</span></th>
    <th>图片</th>
</tr>
</thead>
<tbody>
{rows_html}
</tbody>
</table>
</div>

<!-- ── Footer ── -->
<div class="footer">MINI GT Product Catalog · Generated by WorkBuddy · 点击图片查看大图 · 点击编号复制</div>

<!-- ── Image Modal ── -->
<div class="modal-overlay" id="modalOverlay" onclick="closeModal()">
    <div class="modal-content" onclick="event.stopPropagation()">
        <button class="modal-close" onclick="closeModal()">&times;</button>
        <img id="modalImg" src="" alt="">
        <div class="modal-caption" id="modalCaption"></div>
    </div>
</div>

<!-- ── Back to Top ── -->
<button id="backToTop" onclick="window.scrollTo({{top:0,behavior:'smooth'}})" title="回到顶部">⬆</button>

<!-- ── Toast ── -->
<div class="toast" id="toast"></div>

<script>
// ═══════════════════════════════════════
// Image Modal
// ═══════════════════════════════════════
function openModal(src, caption) {{
    document.getElementById('modalImg').src = src;
    document.getElementById('modalCaption').textContent = caption;
    document.getElementById('modalOverlay').classList.add('active');
    document.body.style.overflow = 'hidden';
}}
function closeModal() {{
    document.getElementById('modalOverlay').classList.remove('active');
    document.body.style.overflow = '';
}}
document.addEventListener('keydown', function(e) {{
    if (e.key === 'Escape') closeModal();
}});

// ═══════════════════════════════════════
// Back to Top
// ═══════════════════════════════════════
window.addEventListener('scroll', function() {{
    var btn = document.getElementById('backToTop');
    if (window.scrollY > 500) {{
        btn.classList.add('visible');
    }} else {{
        btn.classList.remove('visible');
    }}
}});

// ═══════════════════════════════════════
// Copy SKU / Name
// ═══════════════════════════════════════
function copySKU(text, el) {{
    copyToClipboard(text);
    el.classList.add('copied');
    setTimeout(function() {{ el.classList.remove('copied'); }}, 500);
    showToast('已复制: ' + text);
}}
function copyText(text, el) {{
    copyToClipboard(text);
    showToast('已复制产品名称');
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

// ═══════════════════════════════════════
// Toast
// ═══════════════════════════════════════
function showToast(msg) {{
    var toast = document.getElementById('toast');
    toast.textContent = msg;
    toast.classList.add('show');
    clearTimeout(toast._timeout);
    toast._timeout = setTimeout(function() {{ toast.classList.remove('show'); }}, 1800);
}}

// ═══════════════════════════════════════
// Normalize text for fuzzy search
// ═══════════════════════════════════════
function normalize(s) {{
    return s.toLowerCase()
        .replace(/[-–—\\s]+/g, '')  // remove hyphens and spaces
        .replace(/[&]+/g, 'and');    // normalize &
}}

// ═══════════════════════════════════════
// Filter & Search
// ═══════════════════════════════════════
function filterTable() {{
    var q = document.getElementById('search').value;
    var qNorm = normalize(q);
    var sf = document.getElementById('statusFilter').value;
    var rows = document.querySelectorAll('tbody tr');
    var count = 0;
    var counts = {{'Pre-Order':0, 'Released':0, 'Sold Out':0}};
    rows.forEach(function(row) {{
        var sku = row.dataset.sku || '';
        var name = row.dataset.name || '';
        var st = row.dataset.status || '';
        var matchSearch = !qNorm || normalize(sku).includes(qNorm) || normalize(name).includes(qNorm);
        var matchStatus = !sf || st === sf;
        if (matchSearch && matchStatus) {{
            row.classList.remove('hidden');
            count++;
            if (counts[st] !== undefined) counts[st]++;
        }} else {{
            row.classList.add('hidden');
        }}
    }});
    // Update stat badges
    document.getElementById('statsGroup').innerHTML =
        '<span class="stat-badge all">显示 ' + count + ' / 共 {len(products)} 款</span>' +
        '<span class="stat-badge released">✅ ' + counts['Released'] + '</span>' +
        '<span class="stat-badge preorder">📦 ' + counts['Pre-Order'] + '</span>' +
        '<span class="stat-badge soldout">❌ ' + counts['Sold Out'] + '</span>';
}}

// ═══════════════════════════════════════
// Column Sorting
// ═══════════════════════════════════════
var sortState = {{ col: '', dir: 1 }};  // 1=asc, -1=desc

document.querySelectorAll('th[data-sort]').forEach(function(th) {{
    th.addEventListener('click', function() {{
        var col = th.dataset.sort;
        if (sortState.col === col) {{
            sortState.dir *= -1;
        }} else {{
            sortState.col = col;
            sortState.dir = 1;
        }}
        // Update header arrows
        document.querySelectorAll('th').forEach(function(h) {{ h.classList.remove('sorted'); }});
        th.classList.add('sorted');
        sortTable(col, sortState.dir);
    }});
}});

function sortTable(col, dir) {{
    var tbody = document.querySelector('tbody');
    var rows = Array.from(tbody.querySelectorAll('tr:not(.hidden)'));
    var allRows = Array.from(tbody.querySelectorAll('tr'));
    var hiddenRows = allRows.filter(function(r) {{ return r.classList.contains('hidden'); }});

    rows.sort(function(a, b) {{
        var va, vb;
        if (col === 'num') {{
            va = parseInt(a.querySelector('.num').textContent);
            vb = parseInt(b.querySelector('.num').textContent);
            return (va - vb) * dir;
        }}
        if (col === 'sku') {{
            va = (a.dataset.sku || '').toLowerCase();
            vb = (b.dataset.sku || '').toLowerCase();
            return va.localeCompare(vb) * dir;
        }}
        if (col === 'name') {{
            va = (a.dataset.name || '').toLowerCase();
            vb = (b.dataset.name || '').toLowerCase();
            return va.localeCompare(vb) * dir;
        }}
        if (col === 'status') {{
            var order = {{'Pre-Order':0, 'Released':1, 'Sold Out':2}};
            va = order[a.dataset.status] || 0;
            vb = order[b.dataset.status] || 0;
            return (va - vb) * dir;
        }}
        return 0;
    }});

    // Re-append sorted visible rows + hidden rows at end
    rows.forEach(function(r) {{ tbody.appendChild(r); }});
    hiddenRows.forEach(function(r) {{ tbody.appendChild(r); }});
}}

// ═══════════════════════════════════════
// Export CSV
// ═══════════════════════════════════════
function exportCSV() {{
    var rows = document.querySelectorAll('tbody tr:not(.hidden)');
    var csv = '\\uFEFF序号,编号,产品名称,状态,图片链接\\n';
    rows.forEach(function(row, i) {{
        var sku = row.dataset.sku || '';
        var name = (row.dataset.name || '').replace(/"/g, '""');
        var status = row.dataset.status || '';
        var img = row.querySelector('img') ? row.querySelector('img').src : '';
        csv += (i+1) + ',"' + sku + '","' + name + '","' + status + '","' + img + '"\\n';
    }});
    var blob = new Blob([csv], {{type: 'text/csv;charset=utf-8'}});
    var url = URL.createObjectURL(blob);
    var a = document.createElement('a');
    a.href = url;
    a.download = 'MINI_GT_产品清单.csv';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    showToast('CSV 已导出（当前筛选结果）');
}}
</script>
</body>
</html>'''

# ── 写入文件 ──
with open('/Users/cobly/Desktop/AI编程/MINI_GT_产品清单.html', 'w', encoding='utf-8') as f:
    f.write(html)

print(f'✅ HTML 已生成: {len(products)} 款产品')
print(f'   Pre-Order: {count_preorder} | Released: {count_released} | Sold Out: {count_soldout}')

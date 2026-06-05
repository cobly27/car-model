#!/usr/bin/env python3
"""Scrape all MINI GT products from Full Collection and generate HTML catalog."""

import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
import re
import json

BASE_URL = "https://minigt.tsm-models.com"
# URL uses "p" parameter (0-indexed): p=0 = page 1, p=86 = page 87
LIST_URL = BASE_URL + "/index.php?action=product-list&b_id=13&p={}"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}
TIMEOUT = 30
MAX_WORKERS = 8

def get_total_pages():
    """Determine total number of pages from pagination."""
    url = LIST_URL.format(0)
    resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    max_page = 0
    for link in soup.find_all("a", href=re.compile(r"p=\d+")):
        href = link.get("href", "")
        match = re.search(r'p=(\d+)', href)
        if match:
            p = int(match.group(1))
            if p > max_page:
                max_page = p
    total = max_page + 1  # 0-indexed to count
    print(f"Detected p=0 to p={max_page} => {total} total pages")
    return total


def fetch_page(p):
    """Fetch one page (0-indexed) and extract product data."""
    url = LIST_URL.format(p)
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        page_products = []

        # Product cards: div.pro_wrap or div.pd-list-in
        cards = soup.select("div.pro_wrap, div.pd-list-in")

        for card in cards:
            # --- Image ---
            img_tag = card.find("img")
            if not img_tag:
                continue
            img_src = img_tag.get("src", "")
            img_alt = img_tag.get("alt", "").strip()
            if not img_src or not ("picfile" in img_src or "mini_gt" in img_src or "topspeed" in img_src):
                continue

            # --- Product Name ---
            name_tag = card.find("a", class_=re.compile(r"h6|text-dark|font-weight-bold"))
            if not name_tag:
                name_tag = card.find("a", href=re.compile(r"product-detail"))
            name = ""
            if name_tag:
                name = name_tag.get_text(strip=True)
            if not name:
                name = img_alt

            # --- SKU ---
            sku_tag = card.find("p", class_="m-0")
            sku = ""
            if sku_tag:
                sku = sku_tag.get_text(strip=True)

            # --- Status ---
            status = ""
            detail_links = card.find_all("a", href=re.compile(r"product-detail"))
            for link in detail_links:
                t = link.get_text(strip=True)
                if t and t != name and len(t) < 30 and not t.startswith("MGT"):
                    status = t
                    break

            # --- Image URL ---
            img_url = img_src if img_src.startswith("http") else BASE_URL + "/" + img_src.lstrip("/")

            page_products.append({
                "name": name,
                "sku": sku,
                "image": img_url,
                "status": status,
                "page": p
            })

        # Human-readable page number for output
        display_page = p + 1
        print(f"  Page {display_page} (p={p}): {len(page_products)} products")
        return page_products

    except Exception as e:
        display_page = p + 1
        print(f"  Page {display_page} (p={p}): ERROR - {e}")
        return []


def main():
    total_pages = get_total_pages()
    print(f"Fetching {total_pages} pages with {MAX_WORKERS} workers...")

    all_products = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(fetch_page, p): p for p in range(total_pages)}
        for future in as_completed(futures):
            p = futures[future]
            try:
                result = future.result()
                all_products.extend(result)
            except Exception as e:
                print(f"  p={p}: FAILED - {e}")

    # Sort by SKU number descending (newest first)
    def sku_sort_key(product):
        sku = product.get("sku", "")
        num_match = re.search(r'MGT0*(\d+)', sku)
        if num_match:
            return -int(num_match.group(1))
        return 0

    all_products.sort(key=sku_sort_key)

    # Count by status
    status_counts = {}
    for p in all_products:
        s = p.get("status", "Unknown")
        status_counts[s] = status_counts.get(s, 0) + 1

    print(f"\n{'='*50}")
    print(f"Total products: {len(all_products)}")
    for s, c in sorted(status_counts.items()):
        print(f"  {s}: {c}")

    # Save JSON
    json_path = "/Users/cobly/Desktop/AI编程/minigt_products.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(all_products, f, ensure_ascii=False, indent=2)
    print(f"JSON saved: {json_path}")

    # Generate HTML
    html = generate_html(all_products)
    html_path = "/Users/cobly/Desktop/AI编程/MINI_GT_产品清单.html"
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"HTML saved: {html_path}")

    return len(all_products)


def generate_html(products):
    count_preorder = sum(1 for p in products if p.get("status") == "Pre-Order")
    count_released = sum(1 for p in products if p.get("status") == "Released")
    count_soldout = sum(1 for p in products if p.get("status") == "Sold Out")

    rows_html = ""
    for i, p in enumerate(products):
        name = p["name"].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
        sku = p["sku"].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        img = p["image"].replace("&", "&amp;")
        status = p.get("status", "")
        status_class = ""
        if status == "Pre-Order":
            status_class = "status-preorder"
        elif status == "Released":
            status_class = "status-released"
        elif status == "Sold Out":
            status_class = "status-soldout"

        rows_html += f"""
        <tr data-sku="{sku}" data-name="{name}" data-status="{status}">
            <td class="num">{i+1}</td>
            <td class="sku">{sku}</td>
            <td class="name-cell">{name}</td>
            <td class="status-cell"><span class="badge {status_class}">{status}</span></td>
            <td class="img-cell"><img src="{img}" loading="lazy" alt="{name}" onerror="this.parentElement.textContent='N/A'"></td>
        </tr>"""

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>MINI GT 全产品清单 ({len(products)}款)</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", sans-serif; background: #f0f2f5; color: #1a1a2e; }}
.header {{ background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); color: #fff; padding: 24px 30px; }}
.header h1 {{ font-size: 22px; font-weight: 700; margin-bottom: 4px; letter-spacing: 0.5px; }}
.header p {{ font-size: 13px; opacity: 0.75; }}
.controls {{ padding: 14px 30px; background: #fff; border-bottom: 1px solid #e8e8e8; display: flex; gap: 12px; flex-wrap: wrap; align-items: center; position: sticky; top: 0; z-index: 50; }}
.controls input, .controls select {{ padding: 8px 14px; border: 1px solid #d0d0d0; border-radius: 8px; font-size: 13px; background: #fff; }}
.controls input:focus, .controls select:focus {{ outline: none; border-color: #e63946; box-shadow: 0 0 0 2px rgba(230,57,70,0.1); }}
.controls input {{ min-width: 280px; }}
.stats {{ margin-left: auto; font-size: 13px; color: #888; font-weight: 500; white-space: nowrap; }}
table {{ width: 100%; border-collapse: collapse; background: #fff; }}
th {{ background: #f8f8f8; padding: 10px 14px; text-align: left; font-size: 12px; font-weight: 600; color: #666; border-bottom: 2px solid #e0e0e0; text-transform: uppercase; letter-spacing: 0.5px; }}
td {{ padding: 10px 14px; border-bottom: 1px solid #f0f0f0; font-size: 13px; vertical-align: middle; }}
tr:hover td {{ background: #fafafa; }}
.num {{ width: 50px; color: #999; text-align: center; }}
.sku {{ font-family: "SF Mono", "Fira Code", Monaco, monospace; font-size: 12px; color: #e63946; font-weight: 700; white-space: nowrap; width: 160px; }}
.name-cell {{ line-height: 1.45; font-size: 13px; max-width: 500px; }}
.status-cell {{ width: 100px; text-align: center; }}
.badge {{ display: inline-block; padding: 3px 10px; border-radius: 12px; font-size: 11px; font-weight: 600; }}
.status-preorder {{ background: #fff3cd; color: #856404; }}
.status-released {{ background: #d4edda; color: #155724; }}
.status-soldout {{ background: #f8d7da; color: #721c24; }}
.img-cell {{ width: 110px; text-align: center; }}
.img-cell img {{ max-width: 90px; max-height: 65px; border-radius: 4px; object-fit: contain; transition: transform 0.2s; cursor: pointer; }}
.img-cell img:hover {{ transform: scale(3); z-index: 99; position: relative; background: #fff; box-shadow: 0 4px 24px rgba(0,0,0,0.2); border-radius: 6px; }}
.hidden {{ display: none; }}
.footer {{ text-align: center; padding: 24px; color: #999; font-size: 12px; border-top: 1px solid #e8e8e8; }}
</style>
</head>
<body>
<div class="header">
    <h1>MINI GT 全产品清单</h1>
    <p>数据来源: minigt.tsm-models.com · 抓取时间: 2026-06-04 · Pre-Order: {count_preorder} | Released: {count_released} | Sold Out: {count_soldout}</p>
</div>
<div class="controls">
    <input type="text" id="search" placeholder="搜索产品名称或编号..." oninput="filterTable()">
    <select id="statusFilter" onchange="filterTable()">
        <option value="">全部状态</option>
        <option value="Pre-Order">Pre-Order</option>
        <option value="Released">Released</option>
        <option value="Sold Out">Sold Out</option>
    </select>
    <span class="stats" id="stats">共 {len(products)} 款产品</span>
</div>
<table>
<thead>
<tr>
    <th class="num">#</th>
    <th>编号</th>
    <th>产品名称</th>
    <th>状态</th>
    <th>图片</th>
</tr>
</thead>
<tbody>
{rows_html}
</tbody>
</table>
<div class="footer">MINI GT Product Catalog · Generated by WorkBuddy</div>
<script>
function filterTable() {{
    const q = document.getElementById('search').value.toLowerCase();
    const sf = document.getElementById('statusFilter').value;
    const rows = document.querySelectorAll('tbody tr');
    let count = 0;
    rows.forEach(row => {{
        const matchSearch = row.dataset.sku.toLowerCase().includes(q) || row.dataset.name.toLowerCase().includes(q);
        const matchStatus = !sf || row.dataset.status === sf;
        if (matchSearch && matchStatus) {{
            row.classList.remove('hidden');
            count++;
        }} else {{
            row.classList.add('hidden');
        }}
    }});
    document.getElementById('stats').textContent = '显示 ' + count + ' / 共 {len(products)} 款产品';
}}
</script>
</body>
</html>"""


if __name__ == "__main__":
    main()

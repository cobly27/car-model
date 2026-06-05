"""Re-scrape MINI GT products, this time extracting the numeric product ID for detail links."""
import requests, json, re, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from bs4 import BeautifulSoup

BASE = "https://minigt.tsm-models.com/index.php?action=product-list&b_id=13"
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}

def fetch_page(page):
    url = f"{BASE}&p={page}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        r.encoding = 'utf-8'
        return page, r.text
    except Exception as e:
        print(f"  FAIL page {page}: {e}")
        return page, None

def parse_products(html, page_num):
    """Extract numeric ID, SKU, name, status, image from a page."""
    products = []
    soup = BeautifulSoup(html, 'html.parser')
    
    # Find all product detail links to get numeric IDs
    detail_pattern = re.compile(r'product-detail&id=(\d+)')
    
    for wrap in soup.select('div.pro_wrap'):
        prod = {}
        
        # Extract numeric ID from the first <a> inside pro_wrap (the image link)
        img_link = wrap.find('a', href=detail_pattern)
        if img_link:
            m = detail_pattern.search(img_link.get('href', ''))
            if m:
                prod['detail_id'] = int(m.group(1))
        
        # Product name + SKU
        name_el = wrap.select_one('a.h6')
        if name_el:
            prod['name'] = name_el.get_text(strip=True)
        
        # SKU / model number
        sku_el = wrap.select_one('p.m-0')
        if sku_el:
            prod['sku'] = sku_el.get_text(strip=True)
        else:
            prod['sku'] = ''
        
        # Status
        status_link = wrap.select_one('a.badge-new-1, a.badge-danger, a.badge-secondary')
        # Actually look for status text
        status = ''
        for a in wrap.select('a[href*="product-detail"]'):
            txt = a.get_text(strip=True)
            if txt in ('Pre-Order', 'Released', 'Sold Out'):
                status = txt
                break
        prod['status'] = status
        
        # Image
        img_el = wrap.select_one('img')
        if img_el:
            src = img_el.get('data-src') or img_el.get('src', '')
            if src and not src.startswith('http'):
                src = 'https://minigt.tsm-models.com/' + src.lstrip('/')
            prod['image'] = src
        else:
            prod['image'] = ''
        
        # Only include if we have minimum data
        if prod.get('name'):
            products.append(prod)
    
    return products

def main():
    all_products = []
    
    print("Fetching 88 pages (8 workers)...")
    with ThreadPoolExecutor(max_workers=8) as ex:
        futures = {ex.submit(fetch_page, p): p for p in range(88)}
        for f in as_completed(futures):
            page, html = f.result()
            if html:
                prods = parse_products(html, page)
                all_products.extend(prods)
                print(f"  page {page:2d}: {len(prods)} products")
    
    print(f"\nTotal raw: {len(all_products)}")
    
    # Deduplicate by (detail_id, name)
    seen = set()
    unique = []
    dupes = 0
    missing_id = 0
    for p in all_products:
        key = (p.get('detail_id'), p.get('name'))
        if key in seen:
            dupes += 1
            continue
        seen.add(key)
        unique.append(p)
        if not p.get('detail_id'):
            missing_id += 1
    
    print(f"Deduplicated: {len(unique)} (removed {dupes} dupes)")
    print(f"Missing detail_id: {missing_id}")
    
    # Sort by detail_id descending (newest first)
    unique.sort(key=lambda p: p.get('detail_id', 0), reverse=True)
    
    # Save JSON
    with open('/Users/cobly/Desktop/AI编程/minigt_products.json', 'w', encoding='utf-8') as f:
        json.dump(unique, f, ensure_ascii=False, indent=2)
    
    # Stats
    counts = {}
    for p in unique:
        s = p.get('status', 'Unknown')
        counts[s] = counts.get(s, 0) + 1
    
    print(f"\nStatus breakdown: {counts}")
    print(f"ID range: {unique[-1].get('detail_id')} ~ {unique[0].get('detail_id')}")
    
    # Sample
    print("\nFirst 5:")
    for p in unique[:5]:
        print(f"  id={p.get('detail_id'):5d} | {p.get('sku',''):18s} | {p.get('name','')[:70]}")
    
    return unique

if __name__ == '__main__':
    main()

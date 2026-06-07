#!/usr/bin/env python3
"""Scrape AR products from armodel.com.cn"""

import requests
from bs4 import BeautifulSoup
import re
import json
import time
import sys

BASE_URL = "https://www.armodel.com.cn"
LIST_URL = BASE_URL + "/product"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}
TIMEOUT = 30
REQUEST_DELAY = 1  # Seconds between requests


def fetch_list_page():
    """Fetch product list page and extract basic product info."""
    print(f"Fetching product list from {LIST_URL}...")
    resp = requests.get(LIST_URL, headers=HEADERS, timeout=TIMEOUT)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    
    products = []
    
    # Find product items - look for links with detail.html?id=
    for a in soup.find_all('a', href=re.compile(r'/product/detail\.html\?id=\d+')):
        # Get parent container structure
        parent = a.find_parent(['div', 'li', 'tr'])
        if not parent:
            continue
            
        # Extract product info from text content near the link
        text = a.get_text(strip=True)
        href = a.get('href', '')
        
        # Extract ID from URL
        match = re.search(r'id=(\d+)', href)
        if not match:
            continue
        product_id = int(match.group(1))
        
        # Try to get product name from nearby heading/tag or link text
        name = ''
        # First try to find nearby heading
        name_elem = a.find_previous(['h3', 'h4', 'strong', 'b'])
        if name_elem:
            name = name_elem.get_text(strip=True)
        # If no heading not found, use link text as name
        if not name:
            name = text
        
        # Get image URL
        img = ''
        img_elem = a.find_previous('img')
        if img_elem:
            img = img_elem.get('src', '') or img_elem.get('data-src', '')
            if img and not img.startswith('http'):
                img = BASE_URL + img
        
        # Get SKU and brand info from the link text
        link_text = text  # e.g. "ARbox ｜ 1:64 ｜ 690101101"
        sku = ''
        brand = ''
        scale = ''
        
        parts = link_text.split('｜')
        for part in parts:
            part = part.strip()
            if 'ARbox' in part or 'BBR' in part or 'AR+' in part:
                brand = part
            elif ':' in part or '1/' in part:
                scale = part
            elif part and not brand and not scale:
                sku = part
        
        # If still no SKU, generate a default one
        if not sku:
            sku = f"AR{product_id}"
        
        if name and product_id:
            products.append({
                'detail_id': product_id,
                'name': name,
                'sku': sku,
                'brand': brand,
                'scale': scale,
                'image': img,
                'detail_url': BASE_URL + '/product/detail.html?id=' + str(product_id)
            })
    
    return products


def fetch_detail_page(product_id):
    """Fetch product detail page for additional info."""
    url = BASE_URL + f'/product/detail.html?id={product_id}'
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        images = []
        # Find all product images
        for img in soup.find_all('img'):
            src = img.get('src', '') or img.get('data-src', '')
            if src and ('doubaocdn' in src or '/product/' in src or 'pic' in src.lower()):
                if src not in images:
                    images.append(src)
        
        # Get price if available
        price = ''
        price_elem = soup.find(string=re.compile(r'¥|价格|建议零售价'))
        if price_elem:
            match = re.search(r'[¥]?\s*(\d+\.?\d*)', price_elem)
            if match:
                price = match.group(1)
        
        return {
            'images': images,
            'price': price
        }
    except Exception as e:
        print(f"  Error fetching detail {product_id}: {e}")
        return {'images': [], 'price': ''}


def scrape_ar_products(limit=None):
    """Scrape AR products, limited to specified number, or all if None."""
    print("Fetching product list...")
    products = fetch_list_page()
    print(f"Found {len(products)} products")
    
    # Deduplicate by detail_id
    seen = set()
    unique = []
    for p in products:
        if p['detail_id'] not in seen:
            seen.add(p['detail_id'])
            unique.append(p)
    products = unique
    
    # Apply limit if specified
    if limit is not None and limit > 0:
        products = products[:limit]
    
    print(f"Fetching details for {len(products)} products...")
    for idx, p in enumerate(products):
        print(f"  [{idx+1}/{len(products)}] Fetching {p['name']}...")
        detail = fetch_detail_page(p['detail_id'])
        p['images'] = detail['images'] if detail['images'] else [p['image']] if p['image'] else []
        if detail['price']:
            p['price'] = detail['price']
        # Set default status to Released
        p['status'] = 'Released'
        
        # Add delay between requests
        if idx < len(products) - 1:
            time.sleep(REQUEST_DELAY)
    
    return products


if __name__ == '__main__':
    # Check for command line argument for limit
    limit = 2
    if len(sys.argv) > 1:
        try:
            limit = int(sys.argv[1])
        except ValueError:
            if sys.argv[1].lower() in ['all', 'full']:
                limit = None
    
    print(f"Scraping {'all' if limit is None else limit} products...")
    products = scrape_ar_products(limit=limit)
    print(f"\n--- {len(products)} Products ---")
    for p in products:
        print(f"  - {p['name']} ({p['sku']})")
    print("\n--- Products JSON ---")
    for p in products:
        print(json.dumps(p, ensure_ascii=False, indent=2))

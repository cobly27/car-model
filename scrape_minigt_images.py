"""Scrape all product detail pages for multi-image data (broad regex captures all upload paths)."""
import json, requests, re, time
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE = "https://minigt.tsm-models.com"
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}

# Broad regex to capture any product image URL from upload/ directory
IMG_RE = re.compile(r'<img\s+src="(upload/[^"]+\.(?:JPG|jpg|jpeg|png|JPEG|PNG))"', re.IGNORECASE)

def fetch_detail(detail_id):
    """Fetch product detail page and extract all image URLs."""
    url = f"{BASE}/index.php?action=product-detail&id={detail_id}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        r.encoding = 'utf-8'

        # Find the MAIN carousel-5 block (product gallery with big images)
        m = re.search(
            r'<div\s+class="[^"]*owl-carousel-5[^"]*">(.*?)</div>\s*<!--\s*產品 輪播圖 \(小圖\)',
            r.text, re.DOTALL
        )
        if m:
            gallery_html = m.group(1)
            img_srcs = re.findall(IMG_RE, gallery_html)
        else:
            # Fallback: entire page images
            img_srcs = re.findall(IMG_RE, r.text)

        # Deduplicate and build full URLs
        seen = set()
        images = []
        for src in img_srcs:
            if src in seen:
                continue
            seen.add(src)
            full_url = src if src.startswith('http') else f"{BASE}/{src.lstrip('/')}"
            images.append(full_url)

        return detail_id, images
    except Exception as e:
        return detail_id, None

def main():
    with open('/Users/cobly/Desktop/AI编程/minigt_products.json') as f:
        products = json.load(f)

    ids = list(set(p.get('detail_id') for p in products if p.get('detail_id')))
    print(f"Fetching {len(ids)} product detail pages...")

    results = {}
    completed = 0
    failed = 0

    with ThreadPoolExecutor(max_workers=10) as ex:
        futures = {ex.submit(fetch_detail, did): did for did in ids}
        for f in as_completed(futures):
            did, images = f.result()
            completed += 1
            if images is not None:
                results[did] = images
            else:
                failed += 1
            if completed % 100 == 0:
                print(f"  Progress: {completed}/{len(ids)} (failed: {failed})")

    print(f"\nDone! Fetched: {len(results)}, Failed: {failed}")

    # Update products
    for p in products:
        did = p.get('detail_id')
        if did and did in results:
            p['images'] = results[did]
        else:
            old_img = p.get('image', '')
            p['images'] = [old_img] if old_img else []

    # Stats
    img_counts = {}
    for p in products:
        n = len(p.get('images', []))
        img_counts[n] = img_counts.get(n, 0) + 1

    print(f"\nImage count distribution:")
    for k in sorted(img_counts.keys()):
        print(f"  {k} images: {img_counts[k]} products")

    multi = sum(c for k, c in img_counts.items() if k >= 3)
    single = sum(c for k, c in img_counts.items() if k < 3)
    print(f"Products with 3+ images: {multi}")
    print(f"Products with <3 images: {single}")

    with open('/Users/cobly/Desktop/AI编程/minigt_products.json', 'w', encoding='utf-8') as f:
        json.dump(products, f, ensure_ascii=False, indent=2)

    print(f"\nSaved {len(products)} products with images array")

if __name__ == '__main__':
    start = time.time()
    main()
    print(f"Total time: {time.time() - start:.1f}s")

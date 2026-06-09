#!/usr/bin/env python3
"""抓取 XCAR TOYS S 系列 POP RACE 图片，并用 macOS Vision OCR 提取产品名和编号。"""

import ast
import json
import re
import time
import urllib.parse
from pathlib import Path

import Quartz
import requests
import Vision
from Foundation import NSURL


BASE_DIR = Path(__file__).resolve().parent
OUTPUT_PATH = BASE_DIR / 'poprace_products_api.json'
SUMMARY_PATH = BASE_DIR / 'poprace_update_summary.json'
IMAGE_CACHE_DIR = BASE_DIR / 'static' / 'poprace_image_cache'
SOURCE_URL = 'https://www.xcartoys.com/S_series'
BODY_JS_RE = re.compile(r"src=['\"]([^'\"]+Body\.js[^'\"]*)['\"]")
PICTURE_ARRAY_RE = re.compile(r'\[\{"PictureId".*?\}\]')
SKU_RE = re.compile(r'\bS\s*(\d{1,3})\s*[-–—_]\s*(\d{1,3})\b', re.I)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    'Referer': SOURCE_URL,
}

JUNK_PATTERNS = [
    re.compile(r'^XCARTOYS$', re.I),
    re.compile(r'^POP\s*RACE$', re.I),
    re.compile(r'^1\s*/\s*64(?:\s+Diecast\s+Minicar)?$', re.I),
    re.compile(r'^Diecast\s+Minicar$', re.I),
]


def normalize_url(url):
    decoded = urllib.parse.unquote(url or '').strip()
    if decoded.startswith('//'):
        return 'https:' + decoded
    if decoded.startswith('/'):
        return 'https://www.xcartoys.com' + decoded
    return decoded


def clean_text(text):
    text = urllib.parse.unquote(text or '').replace('&nbsp;', ' ')
    text = re.sub(r'\s+', ' ', text).strip()
    text = text.replace('×', 'X')
    text = re.sub(r'[^\w\s\u4e00-\u9fff#&+./()\'"-]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip(' -_')
    return text


def normalize_sku(text):
    match = SKU_RE.search(text or '')
    if not match:
        return ''
    return f"S{int(match.group(1))}-{int(match.group(2)):02d}"


def is_junk_line(text):
    stripped = clean_text(text)
    if not stripped:
        return True
    if normalize_sku(stripped):
        return True
    return any(pattern.search(stripped) for pattern in JUNK_PATTERNS)


def fetch_picture_items():
    html = requests.get(SOURCE_URL, headers=HEADERS, timeout=30).text
    body_match = BODY_JS_RE.search(html)
    if not body_match:
        raise RuntimeError('未找到 S_series 的 Body.js 内容脚本')

    body_url = body_match.group(1)
    body_js = requests.get(body_url, headers=HEADERS, timeout=30).text
    write_match = re.match(r"document\.write\('(.*)'\);?\s*$", body_js, re.S)
    if not write_match:
        raise RuntimeError('Body.js 不是预期的 document.write 格式')

    body_html = ast.literal_eval("'" + write_match.group(1) + "'")
    largest = []
    for match in PICTURE_ARRAY_RE.finditer(body_html):
        try:
            items = json.loads(match.group(0))
        except json.JSONDecodeError:
            continue
        if len(items) > len(largest):
            largest = items

    if not largest:
        raise RuntimeError('未解析到 POP RACE 图片数组')
    return largest


def download_image(item):
    source_image_url = normalize_url(item.get('PictureUrl', ''))
    if not source_image_url:
        return '', None

    ext = Path(urllib.parse.urlparse(source_image_url).path).suffix.lower()
    if ext not in ('.jpg', '.jpeg', '.png', '.webp'):
        ext = '.jpg'
    filename = f"{item.get('PictureId')}{ext}"
    image_path = IMAGE_CACHE_DIR / filename
    if not image_path.exists():
        IMAGE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        response = requests.get(source_image_url, headers=HEADERS, timeout=30)
        response.raise_for_status()
        image_path.write_bytes(response.content)
    return f"/static/poprace_image_cache/{filename}", image_path


def ocr_image(image_path):
    url = NSURL.fileURLWithPath_(str(image_path))
    source = Quartz.CGImageSourceCreateWithURL(url, None)
    if source is None:
        return []
    image = Quartz.CGImageSourceCreateImageAtIndex(source, 0, None)
    if image is None:
        return []

    request = Vision.VNRecognizeTextRequest.alloc().init()
    request.setRecognitionLevel_(Vision.VNRequestTextRecognitionLevelAccurate)
    request.setUsesLanguageCorrection_(False)
    try:
        request.setRecognitionLanguages_(['en-US', 'zh-Hans'])
    except Exception:
        pass

    handler = Vision.VNImageRequestHandler.alloc().initWithCGImage_options_(image, {})
    ok, _error = handler.performRequests_error_([request], None)
    if not ok:
        return []

    lines = []
    for observation in request.results() or []:
        candidates = observation.topCandidates_(1)
        if not candidates:
            continue
        candidate = candidates[0]
        box = observation.boundingBox()
        lines.append({
            'text': clean_text(candidate.string()),
            'confidence': float(candidate.confidence()),
            'x': float(box.origin.x),
            'y': float(box.origin.y),
            'height': float(box.size.height),
        })
    return lines


def extract_product_fields(lines, title, picture_id):
    sku_candidates = []
    for line in lines:
        sku = normalize_sku(line['text'])
        if sku:
            score = line['confidence']
            if line['y'] < 0.22:
                score += 2
            sku_candidates.append((score, line['y'], sku))
    sku = ''
    bottom_y = None
    if sku_candidates:
        sku_candidates.sort(key=lambda item: (item[0], -item[1]), reverse=True)
        sku = sku_candidates[0][2]
        bottom_y_values = [y for _score, y, candidate_sku in sku_candidates if candidate_sku == sku and y < 0.22]
        bottom_y = min(bottom_y_values) if bottom_y_values else min(y for _score, y, candidate_sku in sku_candidates if candidate_sku == sku)

    def useful(line):
        text = clean_text(line['text'])
        if is_junk_line(text):
            return False
        if line['confidence'] < 0.45 and len(text) < 8:
            return False
        return bool(re.search(r'[A-Za-z\u4e00-\u9fff]', text))

    bottom_lines = []
    if bottom_y is not None:
        bottom_lines = [
            line for line in lines
            if useful(line) and 0.018 <= line['y'] <= min(0.20, bottom_y + 0.12)
        ]
        if not bottom_lines:
            bottom_lines = [
                line for line in lines
                if useful(line) and 0.08 <= line['y'] <= 0.18
            ]

    top_sku_y = None
    if sku_candidates:
        top_sku_y = max(y for _score, y, candidate_sku in sku_candidates if candidate_sku == sku)
    top_lines = []
    if top_sku_y is not None:
        top_lines = [
            line for line in lines
            if useful(line) and top_sku_y - 0.08 <= line['y'] <= top_sku_y + 0.02
        ]

    selected_lines = top_lines or bottom_lines
    selected_lines = sorted(selected_lines, key=lambda line: (-line['y'], line['x']))
    name = ' '.join(clean_text(line['text']) for line in selected_lines)
    name = re.sub(r'\s+', ' ', name).strip()

    title = clean_text(title)
    if not name or len(name) < 5:
        name = title
    if not sku:
        sku = f"POP-{picture_id}"
    if not name:
        name = sku

    return sku, name


def build_products():
    items = fetch_picture_items()
    grouped = {}
    ocr_success = 0
    ocr_failed = 0
    download_failed = 0

    for index, item in enumerate(items, 1):
        picture_id = str(item.get('PictureId', '')).strip()
        if not picture_id:
            continue
        try:
            image_url, image_path = download_image(item)
        except Exception:
            download_failed += 1
            continue
        if not image_url or image_path is None:
            download_failed += 1
            continue

        try:
            lines = ocr_image(image_path)
        except Exception:
            lines = []
        if lines:
            ocr_success += 1
        else:
            ocr_failed += 1

        title = item.get('PictureTitle', '')
        sku, name = extract_product_fields(lines, title, picture_id)
        display_order = int(item.get('DisplayOrder') or index)
        group = grouped.setdefault(sku, {
            'detail_id': sku,
            'sku': sku,
            'name': name,
            'status': 'Released',
            'image': image_url,
            'images': [],
            'poprace_picture_ids': [],
            'poprace_source_url': SOURCE_URL,
            'poprace_source_image_urls': [],
            'poprace_ocr_name': name,
            'poprace_title': clean_text(title),
            'poprace_display_order': display_order,
        })

        if image_url not in group['images']:
            group['images'].append(image_url)
        source_image_url = normalize_url(item.get('PictureUrl', ''))
        if source_image_url and source_image_url not in group['poprace_source_image_urls']:
            group['poprace_source_image_urls'].append(source_image_url)
        if picture_id not in group['poprace_picture_ids']:
            group['poprace_picture_ids'].append(picture_id)
        if display_order < group['poprace_display_order']:
            group['poprace_display_order'] = display_order
            group['image'] = image_url
        if len(name) > len(group.get('name', '')) and not name.startswith('POP-'):
            group['name'] = name
            group['poprace_ocr_name'] = name

        print(f"[{index}/{len(items)}] {sku} | {name}")
        time.sleep(0.02)

    products = sorted(grouped.values(), key=lambda product: product.get('poprace_display_order', 999999))
    for product in products:
        product['images'] = product['images'][:4]
        product['image'] = product['images'][0] if product['images'] else product['image']

    summary = {
        'source_url': SOURCE_URL,
        'picture_count': len(items),
        'fetched_count': len(products),
        'ocr_success_count': ocr_success,
        'ocr_failed_count': ocr_failed,
        'download_failed_count': download_failed,
        'max_images_per_product': 4,
    }
    return products, summary


def main():
    products, summary = build_products()
    if not products:
        raise RuntimeError('POP RACE 抓取结果为空')
    OUTPUT_PATH.write_text(json.dumps(products, ensure_ascii=False, indent=2), encoding='utf-8')
    SUMMARY_PATH.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"✅ POP RACE 抓取完成：{len(products)} 个产品，OCR 图片 {summary['ocr_success_count']} 张")


if __name__ == '__main__':
    main()

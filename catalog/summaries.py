"""Human-readable update summaries for the status panel."""

import json

from .config import SUMMARY_PATHS


def reset_update_summary(summary_path):
    if summary_path.exists():
        summary_path.unlink()


def load_update_summary(summary_path):
    if not summary_path.exists():
        return {}
    with summary_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def format_ar_update_summary():
    summary = load_update_summary(SUMMARY_PATHS["ar"])
    if not summary:
        return "✅ 全部更新完成！请刷新页面查看。"

    lines = [
        "✅ AR 产品更新完成！请刷新页面查看最新数据。",
        f"官网抓取：{summary.get('fetched_count', 0)} 个",
        f"官网总数：{summary.get('api_total_count', summary.get('fetched_count', 0))} 个，分页：{summary.get('page_count', 0)} 页",
        f"原 AR 数量：{summary.get('original_ar_count', 0)} 个",
        f"新增：{summary.get('added_count', 0)} 个，更新：{summary.get('updated_count', 0)} 个，未变：{summary.get('unchanged_count', 0)} 个",
        f"官网未返回但已保留：{summary.get('preserved_count', 0)} 个",
        f"详情图成功：{summary.get('detail_success_count', 0)} 个，失败保留原图：{summary.get('detail_failed_count', 0)} 个",
        f"最终 AR 数量：{summary.get('final_ar_count', 0)} 个，总产品数：{summary.get('total_products', 0)} 个",
    ]
    if summary.get("duplicate_count", 0):
        lines.insert(5, f"跳过重复 API 产品：{summary.get('duplicate_count', 0)} 个")
    if summary.get("missing_detail_count", 0):
        lines.insert(-1, f"缺少详情图数据：{summary.get('missing_detail_count', 0)} 个")
    return "\n".join(lines)


def format_minigt_update_summary():
    summary = load_update_summary(SUMMARY_PATHS["minigt"])
    if not summary:
        return "✅ 全部更新完成！请刷新页面查看。"

    lines = [
        "✅ MINI GT 产品更新完成！请刷新页面查看最新数据。",
        f"官网抓取：{summary.get('fetched_count', 0)} 个",
        f"官网分页：{summary.get('page_count', 0)} 页",
        f"原 MINI GT 数量：{summary.get('original_minigt_count', 0)} 个",
        f"新增：{summary.get('added_count', 0)} 个，更新：{summary.get('updated_count', 0)} 个，未变：{summary.get('unchanged_count', 0)} 个",
        f"官网未返回但已保留：{summary.get('preserved_count', 0)} 个",
        f"详情图目标：{summary.get('detail_target_count', 0)} 个，成功：{summary.get('detail_success_count', 0)} 个，失败保留原图：{summary.get('detail_failed_count', 0)} 个",
        f"最终 MINI GT 数量：{summary.get('final_minigt_count', 0)} 个，总产品数：{summary.get('total_products', 0)} 个",
    ]
    if summary.get("duplicate_count", 0):
        lines.insert(5, f"跳过重复官网产品：{summary.get('duplicate_count', 0)} 个")
    if summary.get("missing_detail_count", 0):
        lines.insert(-1, f"缺少详情图数据：{summary.get('missing_detail_count', 0)} 个")
    return "\n".join(lines)


def format_topspeed_update_summary():
    summary = load_update_summary(SUMMARY_PATHS["topspeed"])
    if not summary:
        return "✅ 全部更新完成！请刷新页面查看。"

    lines = [
        "✅ TOP SPEED 产品更新完成！请刷新页面查看最新数据。",
        f"官网子分类：{summary.get('category_count', 0)} 个",
        f"官网抓取：{summary.get('fetched_count', 0)} 个",
        f"原 TOP SPEED 数量：{summary.get('original_topspeed_count', 0)} 个",
        f"新增：{summary.get('added_count', 0)} 个，更新：{summary.get('updated_count', 0)} 个，未变：{summary.get('unchanged_count', 0)} 个",
        f"官网未返回但已保留：{summary.get('preserved_count', 0)} 个",
        f"详情成功：{summary.get('detail_success_count', 0)} 个，失败保留列表图：{summary.get('detail_failed_count', 0)} 个",
        f"每个 TOP SPEED 产品最多保留：{summary.get('max_images_per_product', 4)} 张图",
        f"最终 TOP SPEED 数量：{summary.get('final_topspeed_count', 0)} 个，总产品数：{summary.get('total_products', 0)} 个",
    ]
    if summary.get("duplicate_count", 0):
        lines.insert(6, f"跳过重复官网产品：{summary.get('duplicate_count', 0)} 个")
    return "\n".join(lines)


def format_spark_update_summary(summary_key="spark", label="SPARK"):
    summary = load_update_summary(SUMMARY_PATHS[summary_key])
    if not summary:
        return "✅ 全部更新完成！请刷新页面查看。"

    scale = summary.get("scale", "1:43")
    lines = [
        f"✅ {label} 产品更新完成！请刷新页面查看最新数据。",
        f"范围：{scale} MODEL",
        f"官网估算：{summary.get('expected_total', summary.get('api_total_hits', 0))} 个，查询桶：{summary.get('query_bucket_count', 0)} 个",
        f"官网抓取：{summary.get('fetched_count', 0)} 个",
        f"原 {label} 数量：{summary.get('original_spark_count', 0)} 个",
        f"新增：{summary.get('added_count', 0)} 个，更新：{summary.get('updated_count', 0)} 个，未变：{summary.get('unchanged_count', 0)} 个",
        f"官网未返回但已保留：{summary.get('preserved_count', 0)} 个",
        f"产品图目标：{summary.get('detail_image_target_count', 0)} 个，模式：{summary.get('detail_image_target_mode', 'missing')}，成功：{summary.get('detail_image_success_count', 0)} 个，失败保留原图：{summary.get('detail_image_failed_count', 0)} 个，缓存命中：{summary.get('detail_image_cache_hit_count', 0)} 个",
        f"跳过已满足图片上限：{summary.get('detail_image_skipped_count', 0)} 个，每个产品最多 {summary.get('max_images_per_product', 3)} 张图",
        f"图片 URL 成功：{summary.get('image_success_count', 0)} 个，缺失：{summary.get('image_failed_count', 0)} 个",
        f"更新后仍缺图：{summary.get('missing_image_count', 0)} 个",
        f"最终 {label} 数量：{summary.get('final_spark_count', 0)} 个，总产品数：{summary.get('total_products', 0)} 个",
    ]
    if summary.get("duplicate_count", 0):
        lines.insert(6, f"跳过重复官网产品：{summary.get('duplicate_count', 0)} 个")
    if summary.get("missing_image_examples"):
        lines.insert(-1, f"缺图样本：{', '.join(summary.get('missing_image_examples', [])[:8])}")
    return "\n".join(lines)


def format_inno_update_summary():
    summary = load_update_summary(SUMMARY_PATHS["inno"])
    if not summary:
        return "✅ 全部更新完成！请刷新页面查看。"

    lines = [
        "✅ INNO 产品更新完成！请刷新页面查看最新数据。",
        f"范围：{summary.get('scale', '1/64')}",
        f"官网分页：{summary.get('page_count', 0)} 页",
        f"官网抓取：{summary.get('fetched_count', 0)} 个",
        f"原 INNO 数量：{summary.get('original_inno_count', 0)} 个",
        f"新增：{summary.get('added_count', 0)} 个，更新：{summary.get('updated_count', 0)} 个，未变：{summary.get('unchanged_count', 0)} 个",
        f"官网未返回但已保留：{summary.get('preserved_count', 0)} 个",
        f"详情图成功：{summary.get('detail_success_count', 0)} 个，失败保留列表图：{summary.get('detail_failed_count', 0)} 个",
        f"每个 INNO 产品最多保留：{summary.get('max_images_per_product', 3)} 张图",
        f"最终 INNO 数量：{summary.get('final_inno_count', 0)} 个，总产品数：{summary.get('total_products', 0)} 个",
    ]
    if summary.get("duplicate_count", 0):
        lines.insert(7, f"跳过重复官网产品：{summary.get('duplicate_count', 0)} 个")
    return "\n".join(lines)


def format_poprace_update_summary():
    summary = load_update_summary(SUMMARY_PATHS["poprace"])
    if not summary:
        return "✅ 全部更新完成！请刷新页面查看。"

    lines = [
        "✅ POP RACE 产品更新完成！请刷新页面查看最新数据。",
        f"官网抓取：{summary.get('fetched_count', summary.get('picture_count', 0))} 个",
        f"原 POP RACE 数量：{summary.get('original_poprace_count', 0)} 个",
        f"新增：{summary.get('added_count', 0)} 个，更新：{summary.get('updated_count', 0)} 个，未变：{summary.get('unchanged_count', 0)} 个",
        f"官网未返回但已保留：{summary.get('preserved_count', 0)} 个",
        f"OCR 成功：{summary.get('ocr_success_count', 0)} 个，失败/兜底：{summary.get('ocr_failed_count', 0)} 个",
        f"最终 POP RACE 数量：{summary.get('final_poprace_count', 0)} 个，总产品数：{summary.get('total_products', 0)} 个",
    ]
    return "\n".join(lines)


def format_gcd_update_summary():
    summary = load_update_summary(SUMMARY_PATHS["gcd"])
    if not summary:
        return "✅ 全部更新完成！请刷新页面查看。"

    lines = [
        "✅ GCD 产品更新完成！请刷新页面查看最新数据。",
        f"官网分类：GCD（文章分类 ID {summary.get('category_id', 36)}）",
        f"官网分页：{summary.get('page_count', 0)} 页",
        f"官网抓取：{summary.get('fetched_count', 0)} 个",
        f"原 GCD 数量：{summary.get('original_gcd_count', 0)} 个",
        f"新增：{summary.get('added_count', 0)} 个，更新：{summary.get('updated_count', 0)} 个，未变：{summary.get('unchanged_count', 0)} 个",
        f"官网未返回但已保留：{summary.get('preserved_count', 0)} 个",
        f"详情图成功：{summary.get('detail_success_count', 0)} 个，失败保留列表图：{summary.get('detail_failed_count', 0)} 个",
        f"每个 GCD 产品最多保留：{summary.get('max_images_per_product', 4)} 张图",
        f"最终 GCD 数量：{summary.get('final_gcd_count', 0)} 个，总产品数：{summary.get('total_products', 0)} 个",
    ]
    if summary.get("duplicate_count", 0):
        lines.insert(7, f"跳过重复官网产品：{summary.get('duplicate_count', 0)} 个")
    return "\n".join(lines)


def format_dct_update_summary():
    summary = load_update_summary(SUMMARY_PATHS["dct"])
    if not summary:
        return "✅ 全部更新完成！请刷新页面查看。"

    lines = [
        "✅ DCT 产品更新完成！请刷新页面查看最新数据。",
        f"官网分类：DCT（文章分类 ID {summary.get('category_id', 37)}）",
        f"官网分页：{summary.get('page_count', 0)} 页",
        f"官网抓取：{summary.get('fetched_count', 0)} 个",
        f"原 DCT 数量：{summary.get('original_dct_count', 0)} 个",
        f"新增：{summary.get('added_count', 0)} 个，更新：{summary.get('updated_count', 0)} 个，未变：{summary.get('unchanged_count', 0)} 个",
        f"官网未返回但已保留：{summary.get('preserved_count', 0)} 个",
        f"详情图成功：{summary.get('detail_success_count', 0)} 个，失败保留列表图：{summary.get('detail_failed_count', 0)} 个",
        f"每个 DCT 产品最多保留：{summary.get('max_images_per_product', 4)} 张图",
        f"最终 DCT 数量：{summary.get('final_dct_count', 0)} 个，总产品数：{summary.get('total_products', 0)} 个",
    ]
    if summary.get("duplicate_count", 0):
        lines.insert(7, f"跳过重复官网产品：{summary.get('duplicate_count', 0)} 个")
    return "\n".join(lines)

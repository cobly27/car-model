"""File backup and subprocess helpers."""

import datetime
import shutil
import subprocess

from .config import BASE_DIR, HTML_PATH, PRODUCTS_PATH


def run_step(step_name, script_name):
    result = subprocess.run(
        ["python3", script_name],
        capture_output=True,
        text=True,
        cwd=BASE_DIR,
    )
    if result.returncode != 0:
        output = (result.stderr or result.stdout or "").strip()
        if len(output) > 500:
            output = output[-500:]
        raise RuntimeError(f"{step_name}失败：{script_name} 退出码 {result.returncode}。{output}")
    return result


def backup_files():
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    if PRODUCTS_PATH.exists():
        shutil.copy(PRODUCTS_PATH, BASE_DIR / f"minigt_products_backup_{timestamp}.json")
    if HTML_PATH.exists():
        shutil.copy(HTML_PATH, BASE_DIR / f"MINI_GT_产品清单_backup_{timestamp}.html")

#!/usr/bin/env python3
"""本地产品清单服务器。"""

import os
import subprocess
import webbrowser

from flask import Flask, jsonify, render_template, request, send_file

from catalog.brands import update_config
from catalog.config import BASE_DIR, HTML_PATH
from catalog.data import load_catalog_response
from catalog.health import catalog_health_response
from catalog.images import serve_inno_image, serve_topspeed_thumb
from catalog.tasks import UpdateManager

app = Flask(__name__)
os.chdir(BASE_DIR)
update_manager = UpdateManager()


@app.route("/")
def serve_index():
    """稳定版入口：继续提供已生成的旧 HTML。"""
    return send_file(HTML_PATH)


@app.route("/v2")
def serve_v2():
    """新版架构验证入口：轻量页面，启动后从 API 加载数据。"""
    return render_template("catalog_v2.html")


@app.route("/api/catalog-data")
def catalog_data():
    """返回当前产品 JSON 和分类统计，不改变原始字段结构。"""
    return jsonify(load_catalog_response())


@app.route("/api/catalog-health")
def catalog_health():
    """返回只读数据健康检查结果，方便更新后快速回归。"""
    return jsonify(catalog_health_response())


@app.route("/api/update-config")
def get_update_config():
    """返回新版页面的品牌更新按钮配置。"""
    return jsonify({"updates": update_config()})


@app.route("/api/topspeed-thumb")
def topspeed_thumb():
    return serve_topspeed_thumb(request.args.get("src", "").strip())


@app.route("/api/inno-image")
def inno_image():
    return serve_inno_image(request.args.get("src", "").strip())


@app.route("/api/update-ar")
def update_ar():
    return jsonify(update_manager.start("ar"))


@app.route("/api/update-minigt")
def update_minigt():
    return jsonify(update_manager.start("minigt"))


@app.route("/api/update-topspeed")
def update_topspeed():
    return jsonify(update_manager.start("topspeed"))


@app.route("/api/update-spark")
def update_spark():
    return jsonify(update_manager.start("spark"))


@app.route("/api/update-spark64")
def update_spark64():
    return jsonify(update_manager.start("spark64"))


@app.route("/api/update-inno")
def update_inno():
    return jsonify(update_manager.start("inno"))


@app.route("/api/update-poprace")
def update_poprace():
    return jsonify(update_manager.start("poprace"))


@app.route("/api/status")
def check_status():
    return jsonify(update_manager.status())


if __name__ == "__main__":
    try:
        import flask  # noqa: F401
    except ImportError:
        print("Flask未安装，正在安装...")
        subprocess.run(["pip3", "install", "flask"], check=False)

    print("\n" + "=" * 80)
    print("MINI GT 产品清单服务器已启动")
    print("=" * 80)
    print("访问地址：http://localhost:5001")
    print("新版入口：http://localhost:5001/v2")
    print("=" * 80)

    webbrowser.open("http://localhost:5001")
    app.run(host="127.0.0.1", port=5001, debug=False)

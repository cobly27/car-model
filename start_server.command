#!/bin/bash
cd "$(dirname "$0")"

# 检查Python是否安装
if ! command -v python3 &> /dev/null; then
    echo "❌ 未找到Python3，请先安装Python"
    read -p "按任意键退出..."
    exit 1
fi

# 检查是否需要安装依赖
echo "🔍 检查依赖..."
python3 -c "import flask" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "📦 安装Flask..."
    pip3 install flask
fi

echo ""
echo "=========================================="
echo "🚀 启动 MINI GT 产品清单服务器"
echo "=========================================="
echo ""

# 运行服务器
python3 run_server.py

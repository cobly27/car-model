
#!/usr/bin/env python3
"""MINI GT 产品清单本地服务器"""

from flask import Flask, jsonify
import subprocess
import os
import datetime
import shutil
import threading

app = Flask(__name__)
WORK_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(WORK_DIR)

# 状态变量
is_running = False
last_log = ""

def run_step(step_name, script_name):
    """运行更新脚本，失败时抛出包含输出的错误。"""
    result = subprocess.run(
        ['python3', script_name],
        capture_output=True,
        text=True,
        cwd=WORK_DIR
    )
    if result.returncode != 0:
        output = (result.stderr or result.stdout or '').strip()
        if len(output) > 500:
            output = output[-500:]
        raise RuntimeError(f"{step_name}失败：{script_name} 退出码 {result.returncode}。{output}")
    return result

def backup_files():
    """备份当前文件，保留历史"""
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    # 备份JSON数据
    if os.path.exists('minigt_products.json'):
        backup_name = f'minigt_products_backup_{timestamp}.json'
        shutil.copy('minigt_products.json', backup_name)
    # 备份HTML
    if os.path.exists('MINI_GT_产品清单.html'):
        backup_name = f'MINI_GT_产品清单_backup_{timestamp}.html'
        shutil.copy('MINI_GT_产品清单.html', backup_name)

def run_update_task():
    """在后台线程中执行完整更新任务"""
    global is_running, last_log
    is_running = True
    last_log = "开始更新AR产品..."
    
    try:
        # 备份
        last_log = "1/5 备份当前文件..."
        backup_files()
        
        # 1. 抓取AR产品列表
        last_log = "2/5 抓取AR产品列表..."
        run_step("抓取AR产品列表", "scrape_ar_api.py")
        
        # 2. 抓取详情图
        last_log = "3/5 抓取产品详情图片（可能需要较长时间）..."
        run_step("抓取产品详情图片", "scrape_ar_detail_images.py")
        
        # 3. 更新数据
        last_log = "4/5 更新产品数据..."
        run_step("更新产品数据", "update_ar_detail_images.py")
        
        # 4. 重新生成HTML
        last_log = "5/5 重新生成HTML页面..."
        run_step("重新生成HTML页面", "generate_minigt_html.py")
        
        last_log = "✅ 全部更新完成！请刷新页面查看。"
    except Exception as e:
        last_log = f"❌ 更新出错：{str(e)}"
    finally:
        is_running = False

@app.route('/')
def serve_index():
    """提供HTML页面"""
    with open('MINI_GT_产品清单.html', 'r', encoding='utf-8') as f:
        html = f.read()
    return html

@app.route('/api/update-ar')
def update_ar():
    """触发AR产品更新API"""
    global is_running
    if is_running:
        return jsonify({
            'status': 'running', 
            'message': '更新任务正在执行中，请耐心等待...',
            'log': last_log
        })
    
    # 启动后台任务
    thread = threading.Thread(target=run_update_task)
    thread.start()
    
    return jsonify({
        'status': 'started',
        'message': 'AR产品更新任务已启动，请等待完成...'
    })

@app.route('/api/status')
def check_status():
    """检查当前任务状态"""
    return jsonify({
        'running': is_running,
        'log': last_log
    })

if __name__ == '__main__':
    # 检查Flask是否安装
    try:
        import flask
    except ImportError:
        print("Flask未安装，正在安装...")
        subprocess.run(['pip3', 'install', 'flask'])
    
    print("\n" + "="*80)
    print("MINI GT 产品清单服务器已启动")
    print("="*80)
    print("访问地址：http://localhost:5001")
    print("="*80)
    
    # 打开浏览器
    import webbrowser
    webbrowser.open('http://localhost:5001')
    
    # 启动服务器
    app.run(host='127.0.0.1', port=5001, debug=False)

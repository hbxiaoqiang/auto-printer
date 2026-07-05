import os
import sys
import webbrowser
import threading
import signal

# 将项目根目录加入路径，确保 src 包可导入
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.config import HOST, PORT, logger
from src.app import app
from src.tray import run_tray


def open_demo():
    url = f"http://{HOST}:{PORT}/demo"
    logger.info(f"Opening demo page: {url}")
    webbrowser.open(url)


def main():
    logger.info(f"Starting Auto Printer on http://{HOST}:{PORT}")

    # 启动 Flask 服务（后台线程）
    server_thread = threading.Thread(
        target=lambda: app.run(host=HOST, port=PORT, threaded=True, use_reloader=False),
        daemon=True,
    )
    server_thread.start()

    # 创建托盘图标并在主线程运行（macOS 要求 Cocoa 应用必须在主线程初始化）
    icon = run_tray(
        open_demo=open_demo,
        shutdown=lambda: icon.stop(),
    )

    # 注册信号处理，在接收到 Ctrl+C 或终止信号时停止托盘图标
    signal.signal(signal.SIGINT, lambda s, f: icon.stop())
    signal.signal(signal.SIGTERM, lambda s, f: icon.stop())

    # 打开 Demo 页面
    threading.Timer(1.0, open_demo).start()

    # 主线程阻塞在托盘事件循环
    icon.run()

    logger.info("Tray stopped. Exiting.")
    os._exit(0)


if __name__ == "__main__":
    main()

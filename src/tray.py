import os
import sys
import threading
import webbrowser
from typing import Callable

import pystray
from PIL import Image, ImageDraw

from src.config import HOST, PORT, logger


def create_tray_icon() -> Image.Image:
    """生成一个简单的托盘图标（打印机形状）。"""
    width = 64
    height = 64
    color1 = "#4F46E5"
    color2 = "#FFFFFF"

    image = Image.new("RGB", (width, height), color1)
    draw = ImageDraw.Draw(image)

    # 简化的打印机机身
    draw.rectangle([12, 20, 52, 44], fill=color2, outline=color2)
    draw.rectangle([16, 10, 48, 20], fill=color2, outline=color2)
    draw.rectangle([20, 34, 44, 48], fill=color1, outline=color1)

    return image


def create_menu(open_demo: Callable[[], None], shutdown: Callable[[], None]):
    return pystray.Menu(
        pystray.MenuItem(
            "Open Demo",
            lambda icon, item: threading.Thread(target=open_demo, daemon=True).start(),
        ),
        pystray.MenuItem(
            "Exit",
            lambda icon, item: shutdown(),
        ),
    )


def run_tray(open_demo: Callable[[], None], shutdown: Callable[[], None]):
    """创建并返回托盘图标实例，由调用者在主线程执行 icon.run()。"""
    icon = pystray.Icon(
        "auto-printer",
        create_tray_icon(),
        "Auto Printer",
        create_menu(open_demo, shutdown),
    )
    return icon


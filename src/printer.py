import os
import sys
import shutil
import subprocess
import tempfile
from typing import List

import fitz  # PyMuPDF
from PIL import Image

from src.config import logger, TEMP_DIR
from src.tasks import task_manager


def render_pdf_to_images(pdf_path: str, dpi: int = 200) -> List[str]:
    """将 PDF 每一页渲染为 PNG 图像，返回图像路径列表。"""
    doc = fitz.open(pdf_path)
    images: List[str] = []
    base_dir = tempfile.mkdtemp(prefix="pages_", dir=TEMP_DIR)
    zoom = dpi / 72.0
    matrix = fitz.Matrix(zoom, zoom)

    for i, page in enumerate(doc):
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        img_path = os.path.join(base_dir, f"page_{i + 1}.png")
        pix.save(img_path)
        images.append(img_path)

    doc.close()
    return images


def get_printers():
    """获取系统可用且在线的打印机列表（排除离线的）。"""
    printers = []
    if sys.platform == "win32":
        import win32print
        for flags, name, desc, comment in win32print.EnumPrinters(
            win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
        ):
            printers.append(name)
    elif sys.platform == "darwin":
        result = subprocess.run(
            ["/usr/bin/lpstat", "-p"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            lines = result.stdout.splitlines()
            i = 0
            while i < len(lines):
                line = lines[i].strip()
                if not line or not line.startswith("打印机"):
                    i += 1
                    continue

                # 去掉前缀 "打印机"
                rest = line[3:]
                # 找到状态词位置
                status_pos = -1
                for marker in ["闲置", "is idle", "现在正在打印", "is printing"]:
                    pos = rest.find(marker)
                    if pos != -1:
                        status_pos = pos
                        break

                if status_pos == -1:
                    i += 1
                    continue

                name = rest[:status_pos].strip()

                # 检查当前行或下一行是否包含离线/未连接标志
                is_offline = False
                offline_markers = ["已离线", "disabled", "正在查找打印机", "未连接"]
                for marker in offline_markers:
                    if marker in line:
                        is_offline = True
                        break

                if not is_offline and i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    for marker in offline_markers:
                        if marker in next_line:
                            is_offline = True
                            i += 1  # 跳过下一行
                            break

                if name and not is_offline:
                    printers.append(name)

                i += 1
    return printers


def print_pdf(task_id: str, pdf_path: str, filename: str, printer_name: str = None) -> None:
    """根据平台调用对应打印逻辑。"""
    images: List[str] = []
    task_manager.update(task_id, "printing", f"Submitting to {printer_name or 'default'} printer")
    try:
        if sys.platform == "win32":
            images = render_pdf_to_images(pdf_path)
            if not images:
                raise RuntimeError("PDF has no pages")
            _print_images_windows(images, printer_name)
            task_manager.update(task_id, "done", f"Printed {len(images)} page(s)")
        elif sys.platform == "darwin":
            _print_pdf_macos(pdf_path, printer_name)
            task_manager.update(task_id, "done", f"Submitted to {printer_name or 'default'} printer")
        else:
            raise OSError(f"Unsupported platform: {sys.platform}")
    except Exception as e:
        logger.exception("Print failed")
        task_manager.update(task_id, "failed", str(e))
        raise
    finally:
        if images:
            try:
                shutil.rmtree(os.path.dirname(images[0]), ignore_errors=True)
            except Exception:
                pass


def _print_images_windows(images: List[str], printer_name: str = None) -> None:
    """Windows：使用 win32print 将 PNG 位图绘制到指定或默认打印机。"""
    import win32print
    import win32ui
    import win32con
    from PIL import ImageWin

    if printer_name:
        printer = printer_name
    else:
        printer = win32print.GetDefaultPrinter()
    if not printer:
        raise RuntimeError("No printer specified and no default printer found")

    for img_path in images:
        img = Image.open(img_path)
        if img.mode != "RGB":
            img = img.convert("RGB")

        hdc = win32ui.CreateDC()
        hdc.CreatePrinterDC(printer)
        hdc.StartDoc(img_path)
        hdc.StartPage()

        # 打印机可打印区域（像素）
        printable_width = hdc.GetDeviceCaps(win32con.HORZRES)
        printable_height = hdc.GetDeviceCaps(win32con.VERTRES)

        # 按纸张比例缩放图像并居中放置在白色画布上
        img.thumbnail((printable_width, printable_height), Image.Resampling.LANCZOS)
        bmp = Image.new("RGB", (printable_width, printable_height), "white")
        x = (printable_width - img.width) // 2
        y = (printable_height - img.height) // 2
        bmp.paste(img, (x, y))

        dib = ImageWin.Dib(bmp)
        dib.draw(hdc.GetHandleOutput(), (0, 0, printable_width, printable_height))

        hdc.EndPage()
        hdc.EndDoc()
        hdc.DeleteDC()


def _print_pdf_macos(pdf_path: str, printer_name: str = None) -> None:
    """macOS：使用 lp 命令直接提交 PDF 到指定或默认打印机。"""
    logger.info(f"_print_pdf_macos called with pdf_path={pdf_path}, printer_name={printer_name}")
    if not os.path.exists(pdf_path):
        raise RuntimeError(f"PDF file not found before printing: {pdf_path}")

    target_printer = printer_name
    if not target_printer:
        # 获取可用打印机列表，优先使用第一个已连接的打印机
        available = get_printers()
        if available:
            target_printer = available[0]
            logger.info(f"Auto-selected first available printer: {target_printer}")
        else:
            # fallback: 获取系统默认打印机
            result = subprocess.run(
                ["/usr/bin/lpstat", "-d"],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                for line in result.stdout.splitlines():
                    line_lower = line.lower()
                    if "system default destination" in line_lower or "默认目的位置" in line_lower:
                        for sep in [":", "："]:
                            if sep in line:
                                target_printer = line.split(sep, 1)[-1].strip()
                                break
                        break

    if not target_printer:
        target_printer = "_default"

    logger.info(f"Submitting PDF to macOS printer: {target_printer}")

    result = subprocess.run(
        ["/usr/bin/lp", "-d", target_printer, pdf_path],
        capture_output=True,
        text=True,
    )
    logger.info(f"lp returncode={result.returncode}")
    logger.info(f"lp stdout: {result.stdout.strip()}")
    logger.info(f"lp stderr: {result.stderr.strip()}")
    if result.returncode != 0:
        raise RuntimeError(f"lp failed: {result.stderr}")

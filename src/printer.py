import os
import sys
import shutil
import subprocess
import tempfile
from typing import List

import fitz  # PyMuPDF
from PIL import Image, ImageOps

from src.config import logger, TEMP_DIR
from src.tasks import task_manager


# 图片文件扩展名集合
IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff', '.webp'}


def detect_orientation(image_path: str) -> str:
    """检测图片方向，返回 'landscape'（横屏）或 'portrait'（竖屏）。
    
    宽度 > 高度 → 横屏
    高度 >= 宽度 → 竖屏（正方形默认竖屏）
    自动处理 EXIF 旋转信息。
    """
    img = Image.open(image_path)
    try:
        # 处理 EXIF 旋转，确保尺寸正确
        img = ImageOps.exif_transpose(img)
        width, height = img.size
        logger.info(f"Image size: {width}x{height}, orientation: {'landscape' if width > height else 'portrait'}")
        if width > height:
            return 'landscape'
        return 'portrait'
    finally:
        img.close()


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
            try:
                h_printer = win32print.OpenPrinter(name)
                try:
                    info = win32print.GetPrinter(h_printer, 2)
                    status = info.get("Status", 0)
                    bad_status = (
                        win32print.PRINTER_STATUS_OFFLINE
                        | win32print.PRINTER_STATUS_ERROR
                        | win32print.PRINTER_STATUS_NOT_AVAILABLE
                        | 0x00000001  # PRINTER_STATUS_UNKNOWN
                    )
                    if status & bad_status:
                        logger.warning(f"Printer {name} is offline or error (status={status}), skipping")
                        continue
                    printers.append(name)
                finally:
                    win32print.ClosePrinter(h_printer)
            except Exception as e:
                logger.warning(f"Failed to query printer {name}: {e}")
                continue
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


def print_file(task_id: str, file_path: str, filename: str, printer_name: str = None) -> None:
    """根据文件类型和平台调用对应打印逻辑。"""
    ext = os.path.splitext(filename.lower())[1]
    is_image = ext in IMAGE_EXTENSIONS
    images: List[str] = []
    task_manager.update(task_id, "printing", f"Submitting to {printer_name or 'default'} printer")
    logger.info(f"print_file called: file_path={file_path}, filename={filename}, is_image={is_image}, platform={sys.platform}")
    try:
        if sys.platform == "win32":
            if is_image:
                # Windows 直接打印图片，自动检测方向
                orientation = detect_orientation(file_path)
                logger.info(f"Windows image print: orientation={orientation}")
                _print_image_windows(file_path, printer_name, orientation)
                task_manager.update(task_id, "done", f"Printed image ({orientation})")
            else:
                images = render_pdf_to_images(file_path)
                if not images:
                    raise RuntimeError("PDF has no pages")
                # 检测 PDF 第一页方向
                orientation = detect_orientation(images[0])
                logger.info(f"Windows PDF print: detected orientation={orientation}")
                _print_images_windows(images, printer_name, orientation)
                task_manager.update(task_id, "done", f"Printed {len(images)} page(s) ({orientation})")
        elif sys.platform == "darwin":
            if is_image:
                # macOS 直接打印图片，自动检测方向
                orientation = detect_orientation(file_path)
                logger.info(f"macOS image print: orientation={orientation}")
                _print_image_macos(file_path, printer_name, orientation)
                task_manager.update(task_id, "done", f"Submitted image to {printer_name or 'default'} printer ({orientation})")
            else:
                # macOS PDF 打印：渲染第一页检测方向
                images = render_pdf_to_images(file_path)
                if not images:
                    raise RuntimeError("PDF has no pages")
                orientation = detect_orientation(images[0])
                logger.info(f"macOS PDF print: detected orientation={orientation}")
                _print_pdf_macos(file_path, printer_name, orientation)
                task_manager.update(task_id, "done", f"Submitted PDF to {printer_name or 'default'} printer ({orientation})")
                # 清理渲染的临时图片
                try:
                    shutil.rmtree(os.path.dirname(images[0]), ignore_errors=True)
                except Exception:
                    pass
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


def _print_images_windows(images: List[str], printer_name: str = None, orientation: str = None) -> None:
    """Windows：使用 win32print 将 PNG 位图绘制到指定或默认打印机。
    
    支持自动方向设置和图片自适应页面。
    """
    import win32print
    import win32ui
    import win32con
    from PIL import ImageWin

    if printer_name:
        printer = printer_name
        logger.info(f"Using specified printer: {printer}")
    else:
        # 优先获取在线打印机，没有在线打印机时回退到系统默认打印机
        available = get_printers()
        if available:
            printer = available[0]
            logger.info(f"Auto-selected first online printer: {printer}")
        else:
            printer = win32print.GetDefaultPrinter()
            logger.warning("No online printer found, falling back to default printer")
    if not printer:
        raise RuntimeError("No online printer available and no default printer found")

    for img_path in images:
        img = Image.open(img_path)
        if img.mode != "RGB":
            img = img.convert("RGB")

        # 获取打印机信息并设置方向
        h_printer = win32print.OpenPrinter(printer)
        try:
            # 获取当前打印机配置
            devmode = win32print.GetPrinter(h_printer, 2)["pDevMode"]
            
            if devmode is not None:
                # 设置方向: 1=竖屏(PORTRAIT), 2=横屏(LANDSCAPE)
                if orientation == 'landscape':
                    devmode.Orientation = 2  # DMORIENT_LANDSCAPE
                    logger.info("Set printer orientation to LANDSCAPE")
                elif orientation == 'portrait':
                    devmode.Orientation = 1  # DMORIENT_PORTRAIT
                    logger.info("Set printer orientation to PORTRAIT")
            else:
                logger.warning("Printer devmode is None, cannot set orientation")
            
            # 创建设备上下文，传入修改后的 devmode
            hdc = win32ui.CreateDC()
            hdc.CreatePrinterDC(printer, devmode)
        finally:
            win32print.ClosePrinter(h_printer)

        hdc.StartDoc(img_path)
        hdc.StartPage()

        # 打印机可打印区域（像素）
        printable_width = hdc.GetDeviceCaps(win32con.HORZRES)
        printable_height = hdc.GetDeviceCaps(win32con.VERTRES)
        logger.info(f"Printable area: {printable_width}x{printable_height}")

        # 计算缩放比例，保持宽高比并填满页面
        img_ratio = img.width / img.height
        page_ratio = printable_width / printable_height

        if img_ratio > page_ratio:
            # 图片更宽，以宽度为基准缩放
            new_width = printable_width
            new_height = int(printable_width / img_ratio)
        else:
            # 图片更高，以高度为基准缩放
            new_height = printable_height
            new_width = int(printable_height * img_ratio)

        # 确保不超过可打印区域
        new_width = min(new_width, printable_width)
        new_height = min(new_height, printable_height)

        # 居中放置
        x = (printable_width - new_width) // 2
        y = (printable_height - new_height) // 2

        logger.info(f"Image scaled to: {new_width}x{new_height}, position: ({x}, {y})")

        # 缩放图片
        if new_width != img.width or new_height != img.height:
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

        # 创建白色背景画布
        bmp = Image.new("RGB", (printable_width, printable_height), "white")
        bmp.paste(img, (x, y))

        dib = ImageWin.Dib(bmp)
        dib.draw(hdc.GetHandleOutput(), (0, 0, printable_width, printable_height))

        hdc.EndPage()
        hdc.EndDoc()
        hdc.DeleteDC()


def _print_image_windows(image_path: str, printer_name: str = None, orientation: str = None) -> None:
    """Windows：打印单张图片，支持自动方向。"""
    _print_images_windows([image_path], printer_name, orientation)


def _print_pdf_macos(pdf_path: str, printer_name: str = None, orientation: str = None) -> None:
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

    cmd = ["/usr/bin/lp", "-d", target_printer]
    # 添加方向参数
    if orientation == 'landscape':
        cmd.extend(["-o", "orientation-requested=4"])
    elif orientation == 'portrait':
        cmd.extend(["-o", "orientation-requested=3"])
    cmd.append(pdf_path)

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
    )
    logger.info(f"lp returncode={result.returncode}")
    logger.info(f"lp stdout: {result.stdout.strip()}")
    logger.info(f"lp stderr: {result.stderr.strip()}")
    if result.returncode != 0:
        raise RuntimeError(f"lp failed: {result.stderr}")


def _print_image_macos(image_path: str, printer_name: str = None, orientation: str = None) -> None:
    """macOS：使用 lp 命令直接提交图片到指定或默认打印机，支持自动方向。"""
    logger.info(f"_print_image_macos called with image_path={image_path}, printer_name={printer_name}, orientation={orientation}")
    if not os.path.exists(image_path):
        raise RuntimeError(f"Image file not found before printing: {image_path}")

    target_printer = printer_name
    if not target_printer:
        available = get_printers()
        if available:
            target_printer = available[0]
            logger.info(f"Auto-selected first available printer: {target_printer}")
        else:
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

    logger.info(f"Submitting image to macOS printer: {target_printer}, orientation={orientation}")

    cmd = ["/usr/bin/lp", "-d", target_printer]
    # 添加方向参数
    if orientation == 'landscape':
        cmd.extend(["-o", "orientation-requested=4"])
    elif orientation == 'portrait':
        cmd.extend(["-o", "orientation-requested=3"])
    # 添加图片自适应页面参数，确保图片铺满页面
    cmd.extend(["-o", "fit-to-page"])
    cmd.append(image_path)

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
    )
    logger.info(f"lp returncode={result.returncode}")
    logger.info(f"lp stdout: {result.stdout.strip()}")
    logger.info(f"lp stderr: {result.stderr.strip()}")
    if result.returncode != 0:
        raise RuntimeError(f"lp failed: {result.stderr}")

import os
import tempfile
import logging

# 服务配置
HOST = os.environ.get("AUTO_PRINTER_HOST", "127.0.0.1")
PORT = int(os.environ.get("AUTO_PRINTER_PORT", "5001"))
DEBUG = os.environ.get("AUTO_PRINTER_DEBUG", "0") == "1"

# 上传文件限制：50MB
MAX_CONTENT_LENGTH = 50 * 1024 * 1024

# 任务记录上限
MAX_TASK_HISTORY = 100

# 临时目录
TEMP_DIR = os.path.join(tempfile.gettempdir(), "auto-printer")
os.makedirs(TEMP_DIR, exist_ok=True)

# 日志
LOG_LEVEL = logging.DEBUG if DEBUG else logging.INFO
logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("auto-printer")

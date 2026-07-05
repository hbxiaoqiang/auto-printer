#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "Building Auto Printer for macOS..."

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 not found. Please install Python 3.11+ first."
    exit 1
fi

# 创建虚拟环境
if [ ! -d "$PROJECT_ROOT/.venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$PROJECT_ROOT/.venv"
fi

"$PROJECT_ROOT/.venv/bin/pip" install --upgrade pip
"$PROJECT_ROOT/.venv/bin/pip" install -r "$PROJECT_ROOT/requirements.txt"
"$PROJECT_ROOT/.venv/bin/pip" install pyinstaller

# 清理旧构建
rm -rf "$PROJECT_ROOT/build" "$PROJECT_ROOT/dist"

# 打包
"$PROJECT_ROOT/.venv/bin/pyinstaller" "$PROJECT_ROOT/auto-printer.spec" --clean --noconfirm

if [ -d "$PROJECT_ROOT/dist/AutoPrinter.app" ]; then
    echo "Build successful: $PROJECT_ROOT/dist/AutoPrinter.app"
else
    echo "Error: Build failed, AutoPrinter.app not found."
    exit 1
fi

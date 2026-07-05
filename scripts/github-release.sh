#!/usr/bin/env bash
set -euo pipefail

echo "=== Auto Printer GitHub 发布脚本 ==="
echo ""

# 1. 检查 gh
echo "1. 检查 GitHub CLI..."
if ! command -v gh &> /dev/null; then
    echo "   gh 未安装，正在通过 Homebrew 安装..."
    brew install gh
else
    echo "   gh 已安装"
fi

# 2. 登录 GitHub
echo "2. 检查 GitHub 登录状态..."
if ! gh auth status &> /dev/null; then
    echo "   请先登录 GitHub..."
    gh auth login --git-protocol https --web
    echo "   登录完成"
else
    echo "   已登录 GitHub"
fi

# 3. 创建仓库
echo "3. 创建 GitHub 仓库..."
cd /Users/qiangxu/work/vv/auto-printer
if ! gh repo view hbxiaoqiang/auto-printer &> /dev/null; then
    gh repo create auto-printer --public --source=. --push
else
    echo "   仓库已存在，直接推送..."
    git remote add origin https://github.com/hbxiaoqiang/auto-printer.git 2>/dev/null || true
    git push -u origin main --force
fi

# 4. 推送 tag
echo "4. 创建并推送 tag..."
git tag -d v1.0.0 2>/dev/null || true
git tag v1.0.0
git push origin v1.0.0 --force

echo ""
echo "=== 完成！ ==="
echo "GitHub Actions 已开始自动打包。"
echo "查看进度: https://github.com/hbxiaoqiang/auto-printer/actions"

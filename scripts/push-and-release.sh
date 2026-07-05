#!/usr/bin/env bash
set -euo pipefail

# 用法: ./scripts/push-and-release.sh <github-repo-url>
# 示例: ./scripts/push-and-release.sh https://github.com/qiangxu/auto-printer.git

if [ $# -lt 1 ]; then
    echo "Usage: $0 <github-repo-url>"
    echo "Example: $0 https://github.com/qiangxu/auto-printer.git"
    exit 1
fi

REPO_URL="$1"
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "=== Auto Printer Release Script ==="

# 检查远程仓库
echo "1. Adding remote origin..."
git remote remove origin 2>/dev/null || true
git remote add origin "$REPO_URL"

# 确保分支是 main
echo "2. Switching to main branch..."
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ "$CURRENT_BRANCH" != "main" ]; then
    git branch -m main 2>/dev/null || true
fi

# 推送代码
echo "3. Pushing code to GitHub..."
git push -u origin main --force

# 创建并推送 tag
echo "4. Creating tag v1.0.0..."
git tag -d v1.0.0 2>/dev/null || true
git tag v1.0.0
git push origin v1.0.0 --force

echo ""
echo "=== Done! ==="
echo "Tag v1.0.0 pushed to $REPO_URL"
echo "GitHub Actions will start building automatically."
echo "Check progress at: ${REPO_URL%.git}/actions"

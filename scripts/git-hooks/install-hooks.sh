#!/usr/bin/env bash
# 安装 git pre-commit 钩子 — 日志溯源卫士智能体仓库
# 用法: bash scripts/git-hooks/install-hooks.sh
# 说明: 把 scripts/git-hooks/pre-commit 软链到 .git/hooks/pre-commit
#       卸载: rm .git/hooks/pre-commit

set -e
REPO_ROOT="$(git rev-parse --show-toplevel)"
HOOK_SRC="$REPO_ROOT/scripts/git-hooks/pre-commit"
HOOK_DST="$REPO_ROOT/.git/hooks/pre-commit"

if [ ! -f "$HOOK_SRC" ]; then
  echo "❌ 找不到钩子源文件: $HOOK_SRC"
  exit 1
fi

ln -sf "$HOOK_SRC" "$HOOK_DST"
chmod +x "$HOOK_SRC"

echo "✅ pre-commit 钩子已安装:"
echo "   $HOOK_DST -> $HOOK_SRC"
echo ""
echo "现在每次 git commit 都会自动检查:"
echo "   - 禁止提交 test_validate_*.py / 缓存 / 密钥文件"
echo "   - Python / JSON 语法"
echo "   - 空白错误（行尾空格、缺末尾换行）"
echo ""
echo "跳过检查: git commit --no-verify"

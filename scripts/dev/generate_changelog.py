#!/usr/bin/env python3
"""自动生成/更新 CHANGELOG.md — 从 git log 提取提交，按类型分组。

用法:
    python3 scripts/dev/generate_changelog.py [--version X.Y.Z] [--dry-run]

行为:
    1. 读取仓库根 CHANGELOG.md（若存在）
    2. 用 git log 提取最近的提交（从上次 changelog 版本之后的 commit 或最近 N 条）
    3. 按类型分组: feat/新增、fix/修复、docs/文档、ci/工程、refactor/重构
    4. 在 CHANGELOG.md 顶部插入新版本小节
    5. --dry-run 只打印不写文件

设计:
    - 无第三方依赖，CI 和本地都能跑
    - 提交信息用 conventional 前缀 (feat:/fix:/docs:/ci:/refactor:/chore:)
      无前缀的按 "其他" 归组
    - 已存在的版本号跳过，避免重复插入
"""
import argparse
import os
import re
import subprocess
import sys
from datetime import date

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CHANGELOG_PATH = os.path.join(REPO_ROOT, "CHANGELOG.md")

# 类型前缀 → (中文分组, 图标)
TYPE_MAP = [
    (r"^feat(\(.*\))?:", ("新增功能", "✨")),
    (r"^fix(\(.*\))?:", ("修复", "🐛")),
    (r"^docs(\(.*\))?:", ("文档", "📝")),
    (r"^ci(\(.*\))?:", ("工程/CI", "🔧")),
    (r"^refactor(\(.*\))?:", ("重构", "♻️")),
    (r"^perf(\(.*\))?:", ("性能", "⚡")),
    (r"^test(\(.*\))?:", ("测试", "🧪")),
    (r"^style(\(.*\))?:", ("样式", "💄")),
    (r"^chore(\(.*\))?:", ("其他", "🧹")),
]

DEFAULT_OTHER = ("其他", "🧹")


def run_git(args: list[str]) -> str:
    r = subprocess.run(["git"] + args, capture_output=True, text=True, cwd=REPO_ROOT)
    if r.returncode != 0:
        print(f"[warn] git {' '.join(args)} 失败: {r.stderr.strip()}", file=sys.stderr)
        return ""
    return r.stdout.strip()


def get_last_release_commit() -> str:
    """找到上一个 release tag 对应的 commit，作为 changelog 起点。"""
    tag = run_git(["describe", "--tags", "--abbrev=0", "HEAD~1"]).strip()
    if tag:
        return tag
    # 无 tag 时回退: 用 CHANGELOG 中最新版本号在 git log 里找
    head = run_git(["rev-parse", "HEAD"])
    return head


def get_commits(since: str = "") -> list[str]:
    """提取提交信息列表（一行式 subject）。"""
    if since:
        log = run_git(["log", f"{since}..HEAD", "--pretty=format:%s"])
    else:
        log = run_git(["log", "-30", "--pretty=format:%s"])
    return [line for line in log.splitlines() if line.strip()]


def classify(commit: str) -> tuple[str, str]:
    """返回 (分组名, 图标)。"""
    for pattern, (group, icon) in TYPE_MAP:
        if re.match(pattern, commit):
            return group, icon
    return DEFAULT_OTHER


def build_changelog_section(version: str, commits: list[str]) -> str:
    """生成新版本小节 markdown。"""
    today = date.today().isoformat()
    groups: dict[str, list[str]] = {}
    icons: dict[str, str] = {}
    for c in commits:
        group, icon = classify(c)
        groups.setdefault(group, []).append(c)
        icons[group] = icon

    lines = [f"## [v{version}] - {today}", ""]
    for group, icon in icons.items():
        items = groups.get(group, [])
        if not items:
            continue
        lines.append(f"### {icon} {group}")
        for item in items:
            # 去掉 conventional 前缀，保留可读信息
            cleaned = re.sub(r"^(feat|fix|docs|ci|refactor|perf|test|style|chore)(\([^)]*\))?:\s*", "", item)
            lines.append(f"- {cleaned}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def update_changelog(version: str, dry_run: bool = False) -> bool:
    commits = get_commits()
    if not commits:
        print("没有可提取的提交。")
        return False

    section = build_changelog_section(version, commits)

    existing = ""
    if os.path.exists(CHANGELOG_PATH):
        with open(CHANGELOG_PATH, "r", encoding="utf-8") as f:
            existing = f.read()

    if f"[v{version}]" in existing:
        print(f"CHANGELOG.md 已包含 v{version}，跳过。")
        return False

    # 头部模板（保留原文件的说明文字）
    header = """# 更新日志

本文件记录「日志溯源卫士智能体」所有版本的变更内容。

---

"""
    if existing.startswith(header):
        body = existing[len(header):]
    else:
        body = existing

    new_content = header + section + "\n" + body

    if dry_run:
        print("=== [dry-run] 将写入 CHANGELOG.md ===")
        print(new_content[:1500])
        return True

    with open(CHANGELOG_PATH, "w", encoding="utf-8") as f:
        f.write(new_content)
    print(f"✅ CHANGELOG.md 已更新 (v{version}, {len(commits)} 条提交)")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="自动生成 CHANGELOG.md")
    parser.add_argument("--version", help="新版本号 (如 3.3.0)，缺省从 pyproject.toml 读取")
    parser.add_argument("--dry-run", action="store_true", help="只打印不写文件")
    args = parser.parse_args()

    version = args.version
    if not version:
        # 从 CLI 的 pyproject.toml 读取
        pp = os.path.join(REPO_ROOT, "log_trace_guard_cli", "pyproject.toml")
        if os.path.exists(pp):
            with open(pp, "r", encoding="utf-8") as f:
                m = re.search(r'^version\s*=\s*"([^"]+)"', f.read(), re.M)
                if m:
                    version = m.group(1)
    if not version:
        print("无法确定版本号，请用 --version 指定。", file=sys.stderr)
        sys.exit(1)

    update_changelog(version, dry_run=args.dry_run)


if __name__ == "__main__":
    main()

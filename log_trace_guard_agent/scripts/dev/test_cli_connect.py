#!/usr/bin/env python3
"""CLI 联调回归 — 验证 CLI 与 mock Splunk/ES 的连通性 + 退出码

用法:
  先启动 mock_services.py(mock Splunk 18089 / ES 19200),然后:
  python3 test_cli_connect.py
"""
import json
import os
import shutil
import subprocess
import sys

CLI_DIR = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "log_trace_guard_cli"))
MAIN = os.path.join(CLI_DIR, "main.py")

PASS = 0
FAIL = 0
FAILURES = []


def run_cli(*args, timeout=40):
    """运行 CLI,返回 (exit_code, stdout, stderr)"""
    proc = subprocess.run(
        [sys.executable, MAIN, *args],
        capture_output=True, text=True, timeout=timeout,
        cwd=CLI_DIR,
    )
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  [PASS] {name}")
    else:
        FAIL += 1
        FAILURES.append(name)
        print(f"  [FAIL] {name} — {detail}")


def main():
    print("═══ CLI 联调回归 ═══\n")

    # ── 基础 ──
    print("[基础]")
    code, out, _ = run_cli("--version")
    check("--version 退出码0", code == 0, f"exit={code}")
    check("--version 输出版本", "3.0.0" in out, out)

    code, out, _ = run_cli("--list-logs", "--json")
    check("--list-logs --json 退出码0", code == 0, f"exit={code}")
    check("--list-logs --json 输出合法JSON", out.strip().startswith("[") or out.strip().startswith("{"), out[:80])

    # ── 退出码契约 ──
    print("\n[退出码契约]")
    code, out, _ = run_cli("-f", "/nonexistent.log", "-p")
    check("文件不存在 → 退出码2", code == 2, f"exit={code} {out}")

    code, out, _ = run_cli("--sample", "5")
    check("缺 --log-file → 退出码2", code == 2, f"exit={code} {out}")

    # ── 无配置时的友好错误 ──
    print("\n[无配置友好提示]")
    code, out, _ = run_cli("--es-test")
    check("ES 未配置 → 退出码1+提示", code == 1 and "未配置" in out, f"exit={code} {out[:120]}")

    code, out, _ = run_cli("--splunk-test")
    check("Splunk 未配置 → 退出码1+提示", code == 1 and "未配置" in out, f"exit={code} {out[:120]}")

    code, out, _ = run_cli("--es-search", "not-json")
    check("ES 非法 DSL → 退出码2", code == 2, f"exit={code} {out[:120]}")

    # ── 配置后连通(mock) ──
    print("\n[配置后连通 mock]")
    cfg_dir = os.path.expanduser("~/.log-guard")
    os.makedirs(cfg_dir, exist_ok=True)
    cfg_path = os.path.join(cfg_dir, "config.json")
    backup = None
    if os.path.exists(cfg_path):
        backup = cfg_path + ".bak"
        shutil.copy2(cfg_path, backup)

    test_cfg = {
        "splunk": {"host": "127.0.0.1", "port": 18089, "scheme": "http",
                   "user": "admin", "password": "changeme"},
        "es": {"host": "127.0.0.1", "port": 19200, "scheme": "http",
               "user": "elastic", "password": "mock"},
    }
    with open(cfg_path, "w", encoding="utf-8") as f:
        json.dump(test_cfg, f, ensure_ascii=False, indent=2)

    try:
        code, out, _ = run_cli("--splunk-test")
        check("Splunk 连接测试成功", code == 0 and "成功" in out, f"exit={code} {out[:200]}")

        code, out, _ = run_cli("--es-test")
        check("ES 连接测试成功", code == 0 and "成功" in out, f"exit={code} {out[:200]}")

        code, out, _ = run_cli("--splunk-search", "search index=linux_secure")
        check("Splunk 搜索执行成功", code == 0 and "完成" in out, f"exit={code} {out[:200]}")

        code, out, _ = run_cli("--es-search", '{"query":{"match_all":{}}}')
        check("ES 搜索执行成功", code == 0 and "完成" in out, f"exit={code} {out[:200]}")

        code, out, _ = run_cli("--es-search", '{"query":{"match_all":{}}}', "--json")
        check("ES 搜索 --json 输出", code == 0 and out.strip().startswith("{"), out[:120])

        code, out, _ = run_cli("--es-query", "SSH爆破", "--json")
        check("ES 查询生成 --json", code == 0 and out.strip().startswith("{"), out[:150])
    finally:
        if backup:
            shutil.move(backup, cfg_path)
        else:
            os.remove(cfg_path)

    # 恢复后验证 config.json 未被污染
    code, out, _ = run_cli("--es-test")
    check("真实 config.json 未被污染", code == 1 and "未配置" in out, f"exit={code} {out[:100]}")

    print(f"\n结果: {PASS} 通过, {FAIL} 失败")
    if FAILURES:
        print("失败项:", ", ".join(FAILURES))
        sys.exit(1)
    print("全部通过 ✓")


if __name__ == "__main__":
    main()

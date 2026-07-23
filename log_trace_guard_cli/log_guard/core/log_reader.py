from __future__ import annotations
"""
日志文件读取器

提供本地日志文件的扫描、读取、格式检测、采样和匹配统计功能。
支持多种编码自动检测，大文件分页，关键词过滤。
"""

import os
import re
import stat
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# 编码检测
# ---------------------------------------------------------------------------

_ENCODING_CANDIDATES = ["utf-8", "utf-8-sig", "gbk", "utf-16", "latin-1"]


def _detect_encoding(file_path: str) -> str:
    """尝试自动检测文件编码，返回最可能的编码名称。"""
    try:
        file_size = os.path.getsize(file_path) or 1
        with open(file_path, "rb") as f:
            raw = f.read(min(8192, file_size))
    except PermissionError:
        return "binary"

    if raw[:3] == b"\xef\xbb\xbf":
        return "utf-8-sig"
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return "utf-16"

    # UTF-8 优先 — 用 errors='ignore' 忽略末尾不完整的多字节字符
    try:
        decoded = raw.decode("utf-8", errors="ignore")
        if decoded and any(ord(c) > 127 for c in decoded):
            return "utf-8"
        return "utf-8"
    except Exception:
        pass

    # 尝试其他编码
    for enc in ["utf-8-sig", "gbk"]:
        try:
            raw.decode(enc, errors="ignore")
            return enc
        except Exception:
            continue

    # 兜底
    return "latin-1"


def _safe_read_lines(
    file_path: str,
    encoding: str,
    line_limit: int,
    offset: int,
    grep: Optional[str] = None,
) -> tuple[list[str], int, int, bool]:
    """读取文件行，支持分页、偏移和关键字过滤。"""
    lines_out: list[str] = []
    total_lines = 0
    matched_lines = 0
    truncated = False
    grep_re = re.compile(grep) if grep else None

    with open(file_path, "r", encoding=encoding, errors="replace") as f:
        for raw_line in f:
            total_lines += 1
            line = raw_line.rstrip("\n").rstrip("\r")

            # 跳过偏移量之前的行
            if total_lines <= offset:
                continue

            # 关键字过滤
            if grep_re and not grep_re.search(line):
                continue

            matched_lines += 1

            # 检查行数限制
            if len(lines_out) >= line_limit:
                truncated = True
                # 继续计数但不保存
                if grep_re:
                    for _ in f:
                        total_lines += 1
                        if grep_re.search(_.rstrip("\n").rstrip("\r")):
                            matched_lines += 1
                else:
                    remaining = sum(1 for _ in f)
                    total_lines += remaining
                    matched_lines += remaining
                break

            lines_out.append(line)

    return lines_out, total_lines, matched_lines, truncated


# ---------------------------------------------------------------------------
# 日志格式检测
# ---------------------------------------------------------------------------

_LOG_FORMAT_PATTERNS: list[tuple[str, list[re.Pattern]]] = [
    (
        "syslog",
        [
            re.compile(r"^\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}\s+\S+\s+\S+"),
            re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}"),
            re.compile(r"^<\d{1,3}>\d{4}-\d{2}-\d{2}T"),
        ],
    ),
    (
        "json",
        [
            re.compile(r"^\s*\{.*\:.*\}", re.DOTALL),
            re.compile(r"^\s*\[.*\]\s*$"),
        ],
    ),
    (
        "apache",
        [
            re.compile(
                r'^\S+\s+\S+\s+\S+\s+\[.*\]\s+"[A-Z]+\s+\S+\s+\S+"\s+\d{3}\s+\d+'
            ),
            re.compile(r'^\S+ - \S+ \[.*\] "GET /'),
        ],
    ),
    (
        "nginx",
        [
            re.compile(
                r'^\S+\s+\S+\s+\S+\s+\[.*\]\s+"[A-Z]+\s+\S+\s+\S+"\s+\d{3}\s+\d+'
            ),
        ],
    ),
    (
        "windows_event",
        [
            re.compile(r"^LogName:\s+\S+"),
            re.compile(r"^EventID:\s+\d+"),
            re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+Z\s+\S+"),
        ],
    ),
    (
        "csv",
        [
            re.compile(r"^[^,]*,[^,]*,[^,]*,"),
            re.compile(r'^"[^"]*","[^"]*"'),
        ],
    ),
]


def _detect_format_from_lines(lines: list[str]) -> str:
    """根据样本行检测日志格式。"""
    if not lines:
        return "unknown"

    # 去除空行后取前 20 行
    sample = [ln for ln in lines if ln.strip()][:20]
    if not sample:
        return "unknown"

    scores: dict[str, int] = {}
    for fmt_name, patterns in _LOG_FORMAT_PATTERNS:
        score = 0
        for pat in patterns:
            score += sum(1 for ln in sample if pat.search(ln))
        if score > 0:
            scores[fmt_name] = score

    if not scores:
        return "unknown"

    # 返回匹配分数最高的格式
    return max(scores, key=scores.get)


# ---------------------------------------------------------------------------
# 文件系统辅助
# ---------------------------------------------------------------------------

_LOG_EXTENSIONS = {".log", ".txt", ".syslog", ".evtx"}


def _is_log_file(name: str) -> bool:
    """判断文件名是否属于日志文件扩展名。"""
    ext = Path(name).suffix.lower()
    return ext in _LOG_EXTENSIONS or ext == ""


def _guess_log_type(file_path: str, name: str) -> str:
    """根据文件名和路径猜测日志类型。"""
    lower = name.lower()
    path_lower = file_path.lower()

    if ".evtx" in lower:
        return "windows_event"
    if "syslog" in lower or path_lower.startswith("/var/log/"):
        return "syslog"
    if "access" in lower or "apache" in lower or "nginx" in lower:
        return "access"
    if "error" in lower or "err" in lower:
        return "error"
    if "application" in lower:
        return "application"
    return "unknown"


def _get_file_info(file_path: str) -> Optional[dict]:
    """获取文件元信息，返回 dict 或 None（出错时）。"""
    try:
        st = os.stat(file_path)
        # 跳过目录
        if stat.S_ISDIR(st.st_mode):
            return None
        name = Path(file_path).name
        mtime = datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        return {
            "path": str(file_path),
            "name": name,
            "size": st.st_size,
            "modified": mtime,
            "type": _guess_log_type(file_path, name),
        }
    except (OSError, PermissionError):
        return None


# ---------------------------------------------------------------------------
# 扫描路径 — 跨平台支持
# ---------------------------------------------------------------------------

def _get_auto_paths() -> list[str]:
    """根据当前操作系统返回自动扫描的日志路径列表。"""
    paths = []

    if sys.platform == "win32":
        # Windows — 使用环境变量获取系统路径
        windir = os.environ.get("SystemRoot", "C:\\Windows")
        paths.append(os.path.join(windir, "System32", "winevt", "Logs"))
        # 用户 AppData 本地日志
        local_app_data = os.environ.get("LOCALAPPDATA", "")
        if local_app_data:
            paths.append(local_app_data)
    else:
        # Linux / macOS / WSL
        paths.append("/var/log/")
        # WSL 环境：通过 /mnt/c/ 访问 Windows 路径
        mnt_c_windows = "/mnt/c/Windows"
        mnt_c_users = "/mnt/c/Users"
        if os.path.isdir(mnt_c_windows):
            paths.append(os.path.join(mnt_c_windows, "System32", "winevt", "Logs"))
        if os.path.isdir(mnt_c_users):
            paths.append(mnt_c_users)
        paths.append(str(Path.home() / ".local" / "share"))

    return paths


def _scan_directory(path: str, limit: int = 50) -> list[dict]:
    """扫描单个目录中的日志文件，按修改时间倒序排列。"""
    results: list[dict] = []
    try:
        for entry in os.scandir(path):
            if not _is_log_file(entry.name):
                continue
            info = _get_file_info(entry.path)
            if info:
                results.append(info)
    except (PermissionError, FileNotFoundError, NotADirectoryError):
        pass

    results.sort(key=lambda x: x["modified"], reverse=True)
    return results[:limit]


def _auto_detect_paths() -> list[dict]:
    """自动检测并扫描所有已知日志路径（跨平台）。"""
    all_results: list[dict] = []
    for base in _get_auto_paths():
        base_str = str(base)

        # 在 WSL 下 /mnt/c/Users/ 需要遍历子目录找 AppData/Local
        if base_str.startswith("/mnt/c/Users"):
            try:
                for user_entry in os.scandir(base_str):
                    app_data = os.path.join(
                        user_entry.path, "AppData", "Local"
                    )
                    if os.path.isdir(app_data):
                        all_results.extend(_scan_directory(app_data, 20))
            except (PermissionError, FileNotFoundError):
                pass
        else:
            all_results.extend(_scan_directory(base_str, 20))

    # 全局去重（按路径）
    seen = set()
    deduped: list[dict] = []
    for info in all_results:
        if info["path"] not in seen:
            seen.add(info["path"])
            deduped.append(info)

    deduped.sort(key=lambda x: x["modified"], reverse=True)
    return deduped[:50]


# ===================================================================
# LogReader — 公开 API
# ===================================================================


class LogReader:
    """本地日志文件读取器 — 分析电脑上的日志文件"""

    @staticmethod
    def list_log_files(path: Optional[str] = None) -> list[dict]:
        """Scan directory for log files. If path is None, auto-detect:
        - /var/log/ (Linux syslog)
        - /mnt/c/Windows/System32/winevt/Logs/ (Windows event logs)
        - /mnt/c/Users/*/AppData/Local/ (Windows app logs)
        - ~/.local/share/ (Linux user logs)

        Returns: [{"path": str, "name": str, "size": int, "modified": str, "type": str}, ...]
        type: syslog/application/access/error/unknown

        Only include files with extensions: .log, .txt, .syslog, or no extension.
        Also include .evtx for Windows.
        Sort by modification time (newest first). Limit to 50 files.
        """
        if path is None:
            return _auto_detect_paths()
        return _scan_directory(path, limit=50)

    @staticmethod
    def read_log(
        file_path: str,
        line_limit: int = 1000,
        offset: int = 0,
        grep: Optional[str] = None,
    ) -> dict:
        """Read log file content.

        Supports:
        - Large file paging (line_limit + offset)
        - Keyword filtering (grep)
        - Auto-detect encoding (utf-8, gbk, latin-1, utf-16)
        - Return stats: total_lines, matched_lines, file_size, encoding

        Returns: {"lines": [str], "total_lines": int, "matched_lines": int,
                  "encoding": str, "file_size": int, "truncated": bool}
        """
        file_path = str(Path(file_path).expanduser().resolve())

        if not os.path.isfile(file_path):
            return {
                "lines": [],
                "total_lines": 0,
                "matched_lines": 0,
                "encoding": "unknown",
                "file_size": 0,
                "truncated": False,
                "error": f"File not found: {file_path}",
            }

        file_size = os.path.getsize(file_path)
        encoding = _detect_encoding(file_path)

        # .evtx files are binary Windows Event Log format - cannot read as text
        if encoding == "binary" or file_path.lower().endswith(".evtx"):
            return {
                "lines": [],
                "total_lines": 0,
                "matched_lines": 0,
                "encoding": "binary",
                "file_size": file_size,
                "truncated": False,
                "error": "Windows Event Log (.evtx) files require administrator privileges or specialized tools to read",
                "is_binary": True,
            }

        try:
            lines, total_lines, matched_lines, truncated = _safe_read_lines(
                file_path, encoding, line_limit, offset, grep
            )
        except Exception as exc:
            return {
                "lines": [],
                "total_lines": 0,
                "matched_lines": 0,
                "encoding": encoding,
                "file_size": file_size,
                "truncated": False,
                "error": str(exc),
            }

        return {
            "lines": lines,
            "total_lines": total_lines,
            "matched_lines": matched_lines,
            "encoding": encoding,
            "file_size": file_size,
            "truncated": truncated,
        }

    @staticmethod
    def detect_log_format(lines: list[str]) -> str:
        """Auto-detect log format: syslog/json/csv/apache/nginx/windows_event/unknown"""
        return _detect_format_from_lines(lines)

    @staticmethod
    def sample_log(
        file_path: str,
        n: int = 20,
        grep: Optional[str] = None,
    ) -> dict:
        """Quick preview of log file (first n lines).

        Returns same structure as read_log but with line_limit=n.
        """
        return LogReader.read_log(file_path, line_limit=n, offset=0, grep=grep)

    @staticmethod
    def count_by_pattern(file_path: str, pattern: str) -> dict:
        """Count lines matching a pattern in a log file.

        Returns: {"file_path": str, "pattern": str, "total_lines": int,
                  "matched_lines": int, "encoding": str, "file_size": int}
        """
        file_path = str(Path(file_path).expanduser().resolve())

        if not os.path.isfile(file_path):
            return {
                "file_path": file_path,
                "pattern": pattern,
                "total_lines": 0,
                "matched_lines": 0,
                "encoding": "unknown",
                "file_size": 0,
                "error": "File not found",
            }

        file_size = os.path.getsize(file_path)
        encoding = _detect_encoding(file_path)
        grep_re = re.compile(pattern)
        total = 0
        matched = 0

        try:
            with open(file_path, "r", encoding=encoding, errors="replace") as f:
                for raw_line in f:
                    total += 1
                    if grep_re.search(raw_line.rstrip("\n").rstrip("\r")):
                        matched += 1
        except Exception as exc:
            return {
                "file_path": file_path,
                "pattern": pattern,
                "total_lines": 0,
                "matched_lines": 0,
                "encoding": encoding,
                "file_size": file_size,
                "error": str(exc),
            }

        return {
            "file_path": file_path,
            "pattern": pattern,
            "total_lines": total,
            "matched_lines": matched,
            "encoding": encoding,
            "file_size": file_size,
        }
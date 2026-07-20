"""测试夹具 — Mock LLM / Mock ChromaDB"""
import sys
import os

# 将项目根目录加入 PYTHONPATH，使 `from app.main import app` 等导入在任何目录下生效
PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..")
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pytest


@pytest.fixture
def sample_ssh_logs() -> list[str]:
    return [
        "Mar 15 10:30:25 server sshd[1234]: Accepted password for root from 192.168.1.1 port 22",
        "Mar 15 10:31:00 server sshd[1235]: Failed password for admin from 10.0.0.5 port 22",
        "Mar 15 10:32:00 server sudo: root : TTY=pts/0 ; PWD=/home ; USER=root ; COMMAND=/bin/rm -rf /tmp/test",
    ]


@pytest.fixture
def sample_web_logs() -> list[str]:
    return [
        '192.168.1.1 - - [10/Oct/2023:13:55:36 +0000] "GET /index.html HTTP/1.1" 200 2326 "-" "Mozilla/5.0"',
        '10.0.0.5 - - [10/Oct/2023:14:01:23 +0000] "POST /wp-admin/admin-ajax.php HTTP/1.1" 404 1234 "-" "python-requests/2.28"',
        '192.168.1.100 - frank [10/Oct/2023:15:00:00 +0000] "GET /admin HTTP/1.1" 403 512',
    ]


@pytest.fixture
def sample_malformed_inputs() -> list[str]:
    return [
        "",
        "   ",
        "not a log line at all",
        "!!@#$%^&*()",
    ]
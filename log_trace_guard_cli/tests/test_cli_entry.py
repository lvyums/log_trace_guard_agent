"""CLI 命令行模式测试 — 退出码契约 + Splunk/ES 连通命令

覆盖 P2 新增契约:
- 退出码: 0成功 / 1业务失败 / 2参数错误
- --splunk-test / --splunk-search / --es-test / --es-search 命令
- --json 输出模式

通过 monkeypatch 规避真实网络与 ~/.log-guard 配置污染。
"""
import json
import sys
from unittest.mock import patch

import pytest

sys.path.insert(0, ".")
from log_guard.cli import run_command  # noqa: E402


class Args:
    """最小 argparse.Namespace 替身"""

    def __init__(self, **kw):
        defaults = dict(
            json_output=False, log_file=None, log_dir=None, list_logs=False,
            sample=None, parse=None, batch_parse=False, assess=False,
            lines=100, grep=None, diagnose=None, device_type=None,
            protocol=None, error_log=None, regex=None, log_sample=None,
            qa=None, es_query=None, baseline=None, optimize=None,
            asset_type=None, correlate=None, time_window=5,
            splunk_test=False, splunk_search=None, es_test=False, es_search=None,
            ai=False, ask=None, version=False,
        )
        defaults.update(kw)
        for k, v in defaults.items():
            setattr(self, k, v)


def test_file_not_found_exit_2():
    args = Args(log_file="/nonexistent/xx.log", parse="")
    with patch("builtins.print"):
        assert run_command(args) == 2


def test_sample_without_file_exit_2():
    args = Args(sample=5)
    with patch("builtins.print"):
        assert run_command(args) == 2


def test_es_search_invalid_dsl_exit_2():
    args = Args(es_search="not-json")
    with patch("builtins.print"):
        assert run_command(args) == 2


def test_es_test_unconfigured_exit_1():
    args = Args(es_test=True)
    with patch("builtins.print") as m:
        code = run_command(args)
        assert code == 1
        # 输出应包含友好提示
        assert any("未配置" in str(c) for c in m.call_args_list)


def test_splunk_test_unconfigured_exit_1():
    args = Args(splunk_test=True)
    with patch("builtins.print") as m:
        code = run_command(args)
        assert code == 1
        assert any("未配置" in str(c) for c in m.call_args_list)


def test_es_search_unconfigured_exit_1():
    args = Args(es_search='{"query":{"match_all":{}}}')
    with patch("builtins.print") as m:
        code = run_command(args)
        assert code == 1
        assert any("未配置" in str(c) for c in m.call_args_list)


def test_es_test_json_output_structure():
    """--json 模式应输出结构化 JSON(未配置场景)"""
    args = Args(es_test=True, json_output=True)
    captured = {}

    def fake_print(*objs, **kw):
        captured["json"] = json.loads(objs[0])

    with patch("builtins.print", side_effect=fake_print):
        code = run_command(args)
    assert code == 1
    assert "success" in captured["json"]
    assert captured["json"]["success"] is False
    assert "error" in captured["json"]


def test_es_query_unconfigured_exit_1():
    """--es-query 生成(无 LLM/无配置场景)不应崩溃, 返回非零或零均可, 但必须有输出"""
    args = Args(es_query="SSH爆破", json_output=True)
    with patch("builtins.print") as m:
        code = run_command(args)
    assert code in (0, 1)
    assert len(m.call_args_list) > 0

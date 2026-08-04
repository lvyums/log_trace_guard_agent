#!/usr/bin/env python3
from __future__ import annotations
"""日志溯源卫士 CLI 智能体 v3.0 — 双模式：菜单操作 + AI 智能对话"""
# -*- coding: utf-8 -*-

import json
import os
import sys
import argparse
import textwrap
import time

# 确保项目根目录在路径中
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from log_guard.common.utils import Result, JsonConfigLoader, LogManager
from log_guard.core.log_reader import LogReader
from log_guard.modules.log_parse import LogParseService
from log_guard.modules.script_gen import (
    ScriptGenService,
    execute_es_query, test_regex_on_file, load_es_config, save_es_config,
    export_trace_report, trace_to_monitoring_rules,
    save_es_template, list_es_templates, delete_es_template, load_es_template,
    generate_splunk_query, execute_splunk_query, load_splunk_config, save_splunk_config,
)
from log_guard.modules.compliance import ComplianceService
from log_guard.modules.log_correlate import LogCorrelateService

try:
    from log_guard.modules.log_collect import LogCollectService
except ImportError:
    LogCollectService = None

# ── AI Core 导入（可选，无 LLM 时降级为纯菜单模式） ──
_AI_AVAILABLE = False
try:
    from log_guard.ai_core import get_orchestrator, get_context_manager, get_llm, settings as ai_settings
    _AI_AVAILABLE = True
except ImportError:
    pass

logger = LogManager.get_logger()

# 实例化服务
_log_parse_svc = LogParseService()
_script_gen_svc = ScriptGenService()
_compliance_svc = ComplianceService()
_log_collect_svc = None
if LogCollectService:
    _log_collect_svc = LogCollectService()
_log_correlate_svc = LogCorrelateService()


# ════════════════════════════════════════════
# 工具函数
# ════════════════════════════════════════════

def _print_banner():
    banner = r"""
╔══════════════════════════════════════════════════════╗
║       🔍 日志溯源卫士 CLI 智能体 v3.0               ║
║       菜单操作 + AI 智能对话 · 双模式兼容            ║
╚══════════════════════════════════════════════════════╝
"""
    print(banner)


def _print_header(title: str):
    width = 60
    print()
    print("=" * width)
    print(f"  {title}")
    print("=" * width)


def _print_section(title: str):
    print()
    print(f"─── {title} ───")


def _print_json(data, indent=2):
    import json
    try:
        print(json.dumps(data, ensure_ascii=False, indent=indent))
    except Exception:
        print(data)


def _show_nav_menu(items: list[dict], prompt: str = "请选择") -> int:
    for i, item in enumerate(items, 1):
        print(f"  [{i}] {item['label']}")
    print(f"  [0] 返回上级菜单")
    while True:
        try:
            choice = input(f"\n{prompt} [0-{len(items)}]: ").strip()
            if choice == "0" or choice == "":
                return -1
            idx = int(choice) - 1
            if 0 <= idx < len(items):
                return idx
            print("输入无效，请重新选择")
        except (ValueError, KeyboardInterrupt):
            return -1


def _show_status_bar(text: str):
    print(f"\n  >> {text}\n")


def _fmt_size(size: int) -> str:
    if size < 1024:
        return f"{size}B"
    elif size < 1024 * 1024:
        return f"{size // 1024}KB"
    else:
        return f"{size // (1024 * 1024)}MB"


def _input_int(prompt: str, default: int, min_val: int = 1, max_val: int = 10000) -> int:
    """读取整数输入，带范围校验和默认值。"""
    raw = input(prompt).strip()
    if not raw:
        return default
    try:
        val = int(raw)
    except ValueError:
        print(f"  ⚠️ 无效数字，使用默认值 {default}")
        return default
    if val < min_val or val > max_val:
        print(f"  ⚠️ 数值需在 {min_val}-{max_val} 之间，使用默认值 {default}")
        return default
    return val


def _confirm(prompt: str = "  确认执行？[Y/n]: ", default: bool = True) -> bool:
    """确认提示，返回 True/False。"""
    raw = input(prompt).strip().lower()
    if not raw:
        return default
    return raw in ("y", "yes", "是")


def _ensure_log_file_interactive(log_reader: LogReader) -> str:
    print("  自动扫描常见日志位置...")
    files = log_reader.list_log_files()
    if not files:
        print("  未在常见位置找到日志文件")
        path = input("  请输入日志文件路径（或输入空返回）: ").strip()
        return path if path else ""

    print(f"\n  找到 {len(files)} 个日志文件:")
    items = []
    for f in files[:20]:
        label = f"{f['name']} ({f['type']}, {_fmt_size(f['size'])})"
        items.append({"label": label, "path": f["path"]})

    idx = _show_nav_menu(items, "选择日志文件")
    if idx >= 0:
        return items[idx]["path"]

    path = input("\n  输入自定义路径（回车返回）: ").strip()
    return path


# ════════════════════════════════════════════
# 首次运行配置向导
# ════════════════════════════════════════════

def _first_run_wizard():
    """首次运行配置向导 — 引导用户配置 LLM API Key"""
    if not _AI_AVAILABLE:
        print("\n  AI Core 未加载，无法配置。")
        return
    _print_header("⚙️ 首次运行配置")
    print("\n  检测到 LLM API Key 未配置。")
    print("  配置后即可使用 AI 智能对话模式。")
    print("  （暂不配置也可使用传统菜单模式）\n")

    choice = input("  是否立即配置 API Key？[y/N]: ").strip().lower()
    if choice != "y":
        print("\n  已跳过配置。输入 /ai 可随时开启配置。")
        return

    api_key = input("\n  请输入 API Key: ").strip()
    if not api_key:
        print("  取消配置。")
        return

    base_url = input(f"  API 地址 [{ai_settings.llm_base_url}]: ").strip() or ai_settings.llm_base_url
    model = input(f"  模型名称 [{ai_settings.llm_model_name}]: ").strip() or ai_settings.llm_model_name

    # 保存到 ~/.log-guard/config.json
    ai_settings.llm_api_key = api_key
    ai_settings.llm_base_url = base_url
    ai_settings.llm_model_name = model
    path = ai_settings.save_config()

    print(f"\n  ✅ 配置已保存至: {path}")
    print("  现在可以输入 /ai 进入 AI 智能对话模式了！")


# ════════════════════════════════════════════
# AI 智能对话模式
# ════════════════════════════════════════════

def _show_ai_status_bar():
    """显示 AI 模式状态栏"""
    width = 60
    sep = "─" * width
    print(f"\n{sep}")
    print("  🤖 AI 智能对话模式  |  输入 /menu 切回菜单 | /clear 清空上下文")
    print(f"{sep}")


def _show_ai_welcome():
    """显示 AI 模式欢迎信息"""
    print()
    print("  你可以自由提问，例如：")
    print("    • 帮我分析「Failed password for root from 192.168.1.100」")
    print("    • SSH连接超时是什么原因")
    print("    • 企业日志留存需要满足什么等保要求")
    print("    • WAF和防火墙日志的区别是什么")
    print("    • 帮我生成检测SQL注入的正则规则")
    print()


def _run_ai_mode():
    """AI 智能对话主循环"""
    ai_available = _AI_AVAILABLE and getattr(ai_settings, 'is_configured', False)

    if not ai_available:
        _print_header("⚠️ AI 模式未就绪")
        print("\n  原因：LLM API Key 未配置或 AI Core 未加载。")
        print("  请先运行首次配置：")
        print("    1. 设置环境变量: export LLM_API_KEY=your_key")
        print("    2. 或运行配置向导: 输入 'y' 配置")
        print()
        choice = input("  是否立即配置？[y/N]: ").strip().lower()
        if choice == "y":
            _first_run_wizard()
            ai_available = _AI_AVAILABLE and getattr(ai_settings, 'is_configured', False)
            if not ai_available:
                print("  配置后仍未就绪，请检查 API Key 是否正确。")
                input("  按 Enter 返回菜单...")
                return
        else:
            return

    # 初始化 RAG 和 Orchestrator
    print("\n  ⏳ 正在初始化知识库...")
    try:
        from log_guard.ai_core import get_rag
        get_rag().load()
        print("  ✅ 知识库加载完成")
    except Exception as e:
        print(f"  ⚠️ 知识库加载异常: {e}")

    orchestrator = get_orchestrator()
    cm = get_context_manager()
    cm.new_session()

    _show_ai_status_bar()
    _show_ai_welcome()

    while True:
        try:
            user_input = input("  \033[1;36m你:\033[0m ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\n  已退出 AI 模式。")
            cm.save_chat_log()
            return

        if not user_input:
            continue

        # 全局指令
        if user_input == "/menu":
            print("  📋 切换到菜单模式...")
            cm.save_chat_log()
            return
        elif user_input == "/clear":
            cm.clear_current()
            print("  🧹 对话上下文已清空。")
            continue
        elif user_input == "/help":
            _show_ai_status_bar()
            _show_ai_welcome()
            continue
        elif user_input in ("/exit", "/quit"):
            print("  👋 再见！")
            cm.save_chat_log()
            return

        # 处理用户输入
        print(f"  \033[0;32m⚡ 思考中...\033[0m", end="\r")
        try:
            result = orchestrator.process(user_input)
            response = result["response"]
            intent = result["intent"]
            confidence = result["confidence"]
            has_rag = result["has_rag"]

            print(" " * 40, end="\r")  # 清除思考中
            print()
            # 意图标签
            intent_labels = {
                "log_parse": "🔍 日志解析",
                "collection": "📡 采集架构",
                "compliance": "📋 合规审计",
                "script_gen": "📝 脚本规则",
                "general": "💡 通用问答",
            }
            label = intent_labels.get(intent, "💡 通用问答")
            tag = f"{label} (置信度: {confidence:.0%})"
            if has_rag:
                tag += " 📚RAG"
            print(f"  \033[0;33m{tag}\033[0m")
            print()
            print(f"  {response}")
            print()

        except KeyboardInterrupt:
            print(" " * 40, end="\r")
            print("\n  已中断。")
        except Exception as e:
            print(" " * 40, end="\r")
            print(f"\n  ❌ 处理出错: {e}")


# ════════════════════════════════════════════
# 菜单模式（原有功能完全保留）
# ════════════════════════════════════════════

def _show_menu_status_bar(context: dict):
    """显示菜单模式状态栏"""
    width = 60
    sep = "─" * width
    mode = "AI 可用" if (_AI_AVAILABLE and getattr(ai_settings, 'is_configured', False)) else "仅菜单"
    log_info = f"日志: {context.get('log_file', '未选择')}" if context.get("log_file") else "日志: 未选择"
    print(f"\n{sep}")
    print(f"  📋 菜单模式 | {log_info} | 输入 /ai 进入对话 | 模式: {mode}")
    print(f"{sep}")


def _run_interactive_mode():
    """交互式菜单主循环"""
    log_reader = LogReader()
    context = {"source": "cli"}

    # 首次运行检查
    if _AI_AVAILABLE and not getattr(ai_settings, 'is_configured', False):
        _first_run_wizard()

    while True:
        _print_banner()
        if context.get("log_file"):
            print(f"  日志文件: {context['log_file']}")
            print(f"  日志行数: {context.get('log_lines', 0)}")
        else:
            print("  日志文件: 未选择")
        print()

        main_items = [
            {"label": "📂 选择日志文件", "desc": "从电脑中浏览和选择日志文件"},
            {"label": "🔍 日志解析", "desc": "识别、解析、风险研判日志内容"},
            {"label": "📡 日志采集", "desc": "采集方案、故障诊断、架构推荐"},
            {"label": "📝 脚本生成", "desc": "正则、ES查询、攻击溯源、脚本优化"},
            {"label": "📋 合规审计", "desc": "合规问答、基线生成、合规自查"},
            {"label": "🔄 联合日志审查", "desc": "多源日志关联分析、攻击链推演"},
            {"label": "🤖 AI 智能对话", "desc": "自由提问，AI 智能解析意图"},
            {"label": "🚪 退出", "desc": "退出 CLI 智能体"},
        ]

        idx = _show_nav_menu(main_items, "选择功能模块")
        if idx < 0:
            print("\n  👋 再见！")
            break

        if idx == 0:
            context = _menu_select_log(context, log_reader)
        elif idx == 1:
            _menu_log_parse(context, log_reader)
        elif idx == 2:
            _menu_log_collect(context)
        elif idx == 3:
            _menu_script_gen(context)
        elif idx == 4:
            _menu_compliance(context)
        elif idx == 5:
            _menu_log_correlate(context)
        elif idx == 6:
            _run_ai_mode()
        elif idx == 7:
            print("\n  👋 再见！")
            break


def _menu_select_log(context: dict, log_reader: LogReader) -> dict:
    _print_header("📂 选择日志文件")
    items = [
        {"label": "自动扫描常见位置", "desc": "扫描 /var/log/, Windows 事件日志等"},
        {"label": "手动输入路径", "desc": "输入完整的文件路径"},
        {"label": "查看当前选择", "desc": "显示当前选中的日志文件信息"},
    ]

    idx = _show_nav_menu(items)
    if idx < 0:
        return context

    if idx == 0:
        file_path = _ensure_log_file_interactive(log_reader)
    elif idx == 1:
        file_path = input("\n  输入日志文件路径: ").strip()
    else:
        if context.get("log_file"):
            print(f"\n  当前文件: {context['log_file']}")
            print(f"  行数: {context.get('log_lines', 0)}")
        else:
            print("\n  当前未选择日志文件")
        input("  按 Enter 继续...")
        return context

    if not file_path or not os.path.exists(file_path):
        print(f"\n  ❌ 文件不存在: {file_path}")
        input("  按 Enter 继续...")
        return context

    preview = log_reader.sample_log(file_path, n=10)
    if preview.get("is_binary"):
        print(f"\n  ⚠️ 二进制文件: {os.path.basename(file_path)}")
        print(f"     类型: Windows Event Log (.evtx)")
        print(f"     大小: {_fmt_size(preview['file_size'])}")
        print(f"     提示: .evtx 文件需要管理员权限或专用工具读取")
        print(f"     建议: 请以管理员身份运行，或使用 wevtutil/evenvtx 等工具导出")
    elif preview.get("lines"):
        print(f"\n  ✅ 已加载: {os.path.basename(file_path)}")
        print(f"     大小: {_fmt_size(preview['file_size'])}")
        format_type = log_reader.detect_log_format(preview["lines"])
        print(f"     格式: {format_type}")
        print(f"     行数: {preview['total_lines']}")
        print(f"     编码: {preview['encoding']}")
        print(f"\n  预览 (前{len(preview['lines'])}行):")
        for line in preview["lines"][:5]:
            print(f"    | {line.strip()[:100]}")

        context["log_file"] = file_path
        context["log_lines"] = preview["total_lines"]
        context["log_format"] = format_type
    else:
        print(f"\n  ⚠️ 文件为空或无法读取: {file_path}")

    input("  按 Enter 继续...")
    return context


def _menu_log_parse(context: dict, log_reader: LogReader):
    _print_header("🔍 日志解析")
    items = [
        {"label": "解析当前日志文件", "desc": "对选中的日志文件逐条解析"},
        {"label": "输入单行日志", "desc": "手动输入一条日志进行解析"},
        {"label": "批量解析", "desc": "批量解析当前日志文件（含风险研判）"},
        {"label": "字段释义查询", "desc": "查询日志字段含义"},
    ]

    idx = _show_nav_menu(items)
    if idx < 0:
        return

    if idx == 0:
        if not context.get("log_file"):
            print("\n  ⚠️ 请先选择日志文件")
            input("  按 Enter 继续...")
            return
        file_path = context["log_file"]
        grep = input("\n  关键词过滤（可选，直接回车不过滤）: ").strip()
        line_limit = _input_int("  读取行数 [默认50]: ", default=50)

        result = log_reader.read_log(file_path, line_limit=line_limit, grep=grep or None)
        lines = result.get("lines", [])
        if not lines:
            print("\n  没有匹配的日志行")
            input("  按 Enter 继续...")
            return

        _show_status_bar(f"正在逐条解析 {len(lines)} 条日志...")
        for i, line in enumerate(lines, 1):
            line = line.strip()
            if not line:
                continue
            parse_result = _log_parse_svc.parse_log(line)
            if parse_result.get("code") == 0 and "data" in parse_result:
                data = parse_result["data"]
                print(f"\n  [{i}] 类型: {data.get('device_type', '?')}")
                print(f"      时间: {data.get('timestamp', '-')}")
                print(f"      源IP: {data.get('src_ip', '-')}")
                print(f"      用户: {data.get('user', '-')}")
                print(f"      动作: {data.get('command', data.get('status', '-'))}")

                risk = _log_parse_svc.assess_risk(data)
                if risk.get("code") == 0 and "data" in risk:
                    rdata = risk["data"]
                    if rdata.get("risk_level") not in ("P3_低风险", "P3_NOISE", None):
                        print(f"      ⚠️ 风险: {rdata.get('risk_level', '-')} - {rdata.get('risk_desc', '-')}")
            else:
                print(f"\n  [{i}] ❌ 解析失败: {line[:80]}")

    elif idx == 1:
        line = input("\n  输入日志行: ").strip()
        if not line:
            return
        parse_result = _log_parse_svc.parse_log(line)
        _print_parse_single_natural(parse_result)
        if parse_result.get("code") == 0 and "data" in parse_result:
            risk = _log_parse_svc.assess_risk(parse_result["data"])
            rdata = risk.get("data", {})
            if rdata.get("risk_level") not in ("P3_NOISE", "P3_噪音", None):
                print(f"\n  ⚠️ 风险: {rdata.get('risk_level', '-')} - {rdata.get('risk_desc', '-')}")

    elif idx == 2:
        if not context.get("log_file"):
            print("\n  ⚠️ 请先选择日志文件")
            input("  按 Enter 继续...")
            return
        line_limit = _input_int("\n  读取行数 [默认200]: ", default=200)
        if not _confirm(f"  将解析 {line_limit} 行日志并进行风险研判，确认？[Y/n] "):
            return
        result = log_reader.read_log(context["log_file"], line_limit=line_limit)
        lines = result.get("lines", [])
        _show_status_bar(f"正在批量解析 {len(lines)} 行，含风险研判...")
        batch = _log_parse_svc.batch_parse(lines, do_assess=True)
        _print_parse_batch_natural(batch)

    elif idx == 3:
        field = input("\n  输入字段名称（如 src_ip, timestamp, user）: ").strip()
        if field:
            result = _log_parse_svc.explain_field(field)
            _print_natural(result)

    input("  按 Enter 继续...")


def _menu_log_collect(context: dict):
    _print_header("📡 日志采集")
    if _log_collect_svc is None:
        print("\n  ⚠️ 采集模块未加载")
        input("  按 Enter 继续...")
        return

    items = [
        {"label": "设备匹配", "desc": "根据设备类型推荐采集方案"},
        {"label": "采集方案", "desc": "生成详细的日志采集方案"},
        {"label": "故障诊断", "desc": "诊断日志采集中的故障"},
        {"label": "架构推荐", "desc": "根据规模推荐日志采集架构"},
    ]

    idx = _show_nav_menu(items)
    if idx < 0:
        return

    if idx == 0:
        dtype = input("设备类型 (如 firewall, switch, server): ").strip()
        model = input("设备型号 (可选): ").strip()
        scale = input("规模 [small/medium/large] (默认small): ").strip() or "small"
        result = _log_collect_svc.match_device(dtype, model, scale)
        _print_diagnose_natural(result)

    elif idx == 1:
        dtype = input("设备类型: ").strip()
        model = input("设备型号 (可选): ").strip()
        scale = input("规模 [small/medium/large] (默认small): ").strip() or "small"
        include = input("包含配置模板 [y/N]: ").strip().lower() == "y"
        result = _log_collect_svc.generate_plan(dtype, model, scale, include)
        _print_collect_plan_natural(result)

    elif idx == 2:
        symptom = input("故障症状描述: ").strip()
        dev = input("设备类型 (可选): ").strip() or None
        proto = input("传输协议 (可选): ").strip() or None
        err = input("错误日志 (可选): ").strip() or None
        result = _log_collect_svc.diagnose_fault(symptom, dev, proto, err)
        _print_diagnose_natural(result)

    elif idx == 3:
        count = _input_int("设备数量 (默认10): ", default=10)
        volume = input("日日志量 [small/medium/large] (默认medium): ").strip() or "medium"
        budget = input("预算 [low/medium/high] (默认medium): ").strip() or "medium"
        skill = input("团队水平 [basic/intermediate/advanced] (默认basic): ").strip() or "basic"
        result = _log_collect_svc.recommend_architecture(count, volume, budget, skill)
        _print_collect_arch_natural(result)

    input("  按 Enter 继续...")


def _menu_script_gen(context: dict):
    _print_header("📝 脚本生成")
    items = [
        {"label": "正则规则生成", "desc": "根据攻防场景生成正则检测规则"},
        {"label": "ES查询生成", "desc": "生成 Elasticsearch 检索语句"},
        {"label": "Splunk SPL生成", "desc": "生成 Splunk 搜索语句"},
        {"label": "攻击溯源", "desc": "分析攻击链路"},
        {"label": "脚本优化", "desc": "优化现有脚本（正则/ES查询）"},
        {"label": "连接配置", "desc": "配置 ES / Splunk 集群连接"},
    ]

    idx = _show_nav_menu(items)
    if idx < 0:
        return

    if idx == 0:
        scenario = input("\n  攻防场景描述: ").strip()
        sample = input("  日志样例 (可选): ").strip() or None
        device = input("  设备类型 (可选): ").strip() or None
        result = _script_gen_svc.generate_regex(scenario, sample, device)
        _print_regex_natural(result)

        if result.get("code") == 0:
            regexes = result.get("data", {}).get("regexes", [])
            if regexes:
                file_path = context.get("log_file")
                if not file_path or not os.path.exists(file_path):
                    file_path = input("\n  🎯 输入日志文件路径测试正则匹配 (Enter跳过): ").strip()
                if file_path and os.path.exists(file_path):
                    choice = input("  ⚡ 是否对日志文件执行规则测试？[y/N]: ").strip().lower()
                    if choice == "y":
                        from log_guard.core.log_reader import LogReader
                        reader = LogReader()
                        log_data = reader.read_log(file_path, line_limit=5000)
                        lines = log_data.get("lines", [])
                        if lines:
                            test_result = test_regex_on_file(regexes, lines)
                            _print_regex_test_result(test_result, file_path)
                        else:
                            print("  ⚠️ 日志文件为空或读取失败")

    elif idx == 1:
        _menu_es_query(context)

    elif idx == 2:
        _menu_splunk_query()

    elif idx == 3:
        file_path = context.get("log_file")
        if not file_path or not os.path.exists(file_path):
            file_path = input("\n  输入日志文件路径: ").strip()
            if not file_path or not os.path.exists(file_path):
                print("  ⚠️ 文件不存在，请先选择日志文件")
                input("  按 Enter 继续...")
                return
        attack_type = input("  攻击类型 (如 ssh_bruteforce, web_sql_injection, 可选): ").strip() or None
        logs = LogReader().read_log(file_path, line_limit=100).get("lines", [])
        result = _script_gen_svc.trace_attack(logs, attack_type)
        _print_trace_natural(result)

        # 溯源后：导出报告 + 生成监控规则
        if result.get("code") == 0:
            trace_data = result.get("data", {})
            if trace_data.get("attack_chain"):
                # 导出报告
                exp = input("\n  📄 是否导出溯源报告？[y/N]: ").strip().lower()
                if exp == "y":
                    fmt = input("  格式 [markdown/json] (默认markdown): ").strip() or "markdown"
                    rpt = export_trace_report(trace_data, fmt=fmt)
                    print(f"  ✅ 报告已导出: {rpt['path']} ({rpt['size']} 字节)")

                # 生成监控规则（闭环）
                mon = input("\n  🔄 是否基于溯源结果生成持续监控规则？[y/N]: ").strip().lower()
                if mon == "y":
                    rules = trace_to_monitoring_rules(trace_data)
                    _print_monitoring_rules(rules)

    elif idx == 4:
        script = input("\n  输入脚本内容: ").strip()
        stype = input("  脚本类型 [regex/es_query] (默认regex): ").strip() or "regex"
        scenario = input("  使用场景 (可选): ").strip() or None
        result = _script_gen_svc.optimize_script(script, stype, scenario)
        _print_optimize_natural(result)

    elif idx == 5:
        _menu_connection_config()

    input("\n  按 Enter 继续...")


# ════════════════════════════════════════════
# 连接配置（ES + Splunk）
# ════════════════════════════════════════════


def _menu_connection_config():
    """连接配置菜单：ES + Splunk"""
    _print_header("🔗 连接配置")
    print("  1. ES 集群连接")
    print("  2. Splunk 连接")
    print("  0. 返回\n")

    choice = input("  请选择: ").strip()
    if choice == "0":
        return
    elif choice == "1":
        _menu_es_config()
    elif choice == "2":
        _menu_splunk_config()


def _menu_es_config():
    """ES 集群连接配置菜单"""
    cfg = load_es_config()
    current = cfg.get("host", "未配置")
    _print_header("🔗 ES 集群连接配置")
    print(f"  当前配置: {current}\n")
    print("  1. 配置 ES 连接")
    print("  2. 查看当前配置")
    print("  3. 清除配置")
    print("  0. 返回\n")

    choice = input("  请选择: ").strip()
    if choice == "1":
        host = input("  ES 主机地址 (如 localhost): ").strip()
        if not host:
            print("  ❌ 主机地址不能为空")
            return
        port_str = input("  端口 [9200]: ").strip()
        port = int(port_str) if port_str.isdigit() else 9200
        scheme = input("  协议 [http] (http/https): ").strip() or "http"
        user = input("  用户名 (可选): ").strip()
        password = input("  密码 (可选): ").strip()
        path = save_es_config(host, port, scheme, user, password)
        print(f"\n  ✅ ES 连接配置已保存至 {path}")

        test_choice = input("\n  ⚡ 是否测试连接？[Y/n]: ").strip().lower()
        if test_choice != "n":
            test_result = execute_es_query(
                {"query": {"match_all": {}}}, "_cluster/health", size=1
            )
            if test_result["success"]:
                print(f"  ✅ ES 连接成功！集群健康状态: {json.dumps(test_result.get('samples', {}), ensure_ascii=False)[:100]}")
            else:
                print(f"  ❌ ES 连接失败: {test_result['error']}")

    elif choice == "2":
        if cfg:
            print(f"\n  主机: {cfg.get('host', '?')}")
            print(f"  端口: {cfg.get('port', '?')}")
            print(f"  协议: {cfg.get('scheme', '?')}")
            print(f"  用户名: {cfg.get('user', '(空)')}")
            print(f"  密码: {'****' if cfg.get('password') else '(空)'}")
        else:
            print("\n  ⚠️ 未配置 ES 连接")
    elif choice == "3":
        save_es_config("", 9200, "http", "", "")
        print("\n  ✅ ES 配置已清除")


def _menu_splunk_config():
    """Splunk 连接配置"""
    cfg = load_splunk_config()
    current = cfg.get("host", "未配置")
    _print_header("🔗 Splunk 连接配置")
    print(f"  当前配置: {current}\n")
    print("  1. 配置 Splunk 连接")
    print("  2. 查看当前配置")
    print("  3. 清除配置")
    print("  0. 返回\n")

    choice = input("  请选择: ").strip()
    if choice == "1":
        host = input("  Splunk 主机地址 (如 localhost): ").strip()
        if not host:
            print("  ❌ 主机地址不能为空")
            return
        port_str = input("  REST API 端口 [8089]: ").strip()
        port = int(port_str) if port_str.isdigit() else 8089
        scheme = input("  协议 [https] (http/https): ").strip() or "https"
        user = input("  用户名 (可选): ").strip()
        password = input("  密码 (可选): ").strip()
        path = save_splunk_config(host, port, scheme, user, password)
        print(f"\n  ✅ Splunk 连接配置已保存至 {path}")

        test_choice = input("\n  ⚡ 是否测试连接？[Y/n]: ").strip().lower()
        if test_choice != "n":
            test_result = execute_splunk_query("| version", max_results=1)
            if test_result["success"]:
                print(f"  ✅ Splunk 连接成功！返回 {test_result['event_count']} 条结果")
            else:
                print(f"  ❌ Splunk 连接失败: {test_result['error']}")

    elif choice == "2":
        if cfg:
            print(f"\n  主机: {cfg.get('host', '?')}")
            print(f"  端口: {cfg.get('port', '?')}")
            print(f"  协议: {cfg.get('scheme', '?')}")
            print(f"  用户名: {cfg.get('user', '(空)')}")
            print(f"  密码: {'****' if cfg.get('password') else '(空)'}")
        else:
            print("\n  ⚠️ 未配置 Splunk 连接")
    elif choice == "3":
        save_splunk_config("", 8089, "https", "", "")
        print("\n  ✅ Splunk 配置已清除")


# ════════════════════════════════════════════
# ES 查询子菜单（生成 + 模板管理 + 执行）
# ════════════════════════════════════════════


def _menu_es_query(context: dict = None):
    """ES 查询生成子菜单"""
    _print_header("🔎 ES 查询生成")
    print("  1. 按场景生成查询")
    print("  2. 管理 ES 查询模板")  
    print("  0. 返回\n")

    choice = input("  请选择: ").strip()
    if choice == "0":
        return

    if choice == "1":
        scenario = input("\n  检索场景描述: ").strip()
        index = input("  索引模式 (如 logstash-*): ").strip() or None
        time_range = input("  时间范围 (如 last_24h, last_7d): ").strip() or None
        result = _script_gen_svc.generate_es_query(scenario, index, time_range)
        _print_es_query_natural(result)

        if result.get("code") == 0:
            query = result.get("data", {}).get("query", {})
            if query:
                # 保存为模板
                save_tpl = input("\n  💾 是否将此查询保存为模板？[y/N]: ").strip().lower()
                if save_tpl == "y":
                    tpl_name = input("  模板名称: ").strip()
                    if tpl_name:
                        idx_pattern = index or result.get("data", {}).get("index_pattern", "logs-*")
                        save_es_template(tpl_name, query, scenario, idx_pattern, time_range or "last_24h")
                        print(f"  ✅ 模板「{tpl_name}」已保存")

                # 执行查询
                run = input("\n  ⚡ 是否向 ES 集群执行此查询？[y/N]: ").strip().lower()
                if run == "y":
                    idx_pattern = index or result.get("data", {}).get("index_pattern", "logs-*")
                    es_result = execute_es_query(query, idx_pattern)
                    _print_es_execute_result(es_result)

    elif choice == "2":
        _menu_es_templates()


def _menu_es_templates():
    """ES 查询模板管理"""
    templates = list_es_templates()
    if not templates:
        print("\n  ⚠️ 暂无模板")
        return

    _print_header("📚 ES 查询模板")
    items_json = json.dumps(templates, ensure_ascii=False, indent=2)
    print(f"  共 {len(templates)} 个模板:\n")
    for t in templates:
        print(f"  📌 {t['name']}")
        print(f"     场景: {t['scenario']}")
        print(f"     索引: {t['index_pattern']} | 时间: {t['time_range']}")
        print()

    print("  1. 加载模板并执行")
    print("  2. 删除模板")
    print("  0. 返回\n")

    choice = input("  请选择: ").strip()
    if choice == "1":
        name = input("  模板名称: ").strip()
        tpl = load_es_template(name)
        if not tpl:
            print(f"  ❌ 模板「{name}」不存在")
            return
        print(f"\n  📋 加载模板: {name}")
        print(f"     索引: {tpl['index_pattern']} | 时间: {tpl['time_range']}")
        print(f"     查询: {json.dumps(tpl['query'], ensure_ascii=False, indent=2)}")
        run = input("\n  ⚡ 是否执行此查询？[y/N]: ").strip().lower()
        if run == "y":
            es_result = execute_es_query(tpl['query'], tpl['index_pattern'])
            _print_es_execute_result(es_result)
    elif choice == "2":
        name = input("  输入要删除的模板名称: ").strip()
        if delete_es_template(name):
            print(f"  ✅ 模板「{name}」已删除")
        else:
            print(f"  ❌ 模板「{name}」不存在")


# ════════════════════════════════════════════
# Splunk SPL 查询子菜单
# ════════════════════════════════════════════


def _menu_splunk_query():
    """Splunk SPL 查询生成子菜单"""
    _print_header("📊 Splunk SPL 查询生成")
    print("  1. 按场景生成 SPL")
    print("  0. 返回\n")

    choice = input("  请选择: ").strip()
    if choice == "0":
        return

    scenario = input("\n  检索场景描述 (如 SSH爆破攻击, SQL注入): ").strip()
    if not scenario:
        print("  ⚠️ 场景描述不能为空")
        return
    index = input("  索引 [*]: ").strip() or "*"
    time_range = input("  时间范围 [last_24h] (last_1h/last_24h/last_7d): ").strip() or "last_24h"

    result = generate_splunk_query(scenario, index, time_range)
    _print_splunk_natural(result)

    # 执行查询
    run = input("\n  ⚡ 是否向 Splunk 集群执行此查询？[y/N]: ").strip().lower()
    if run == "y":
        cfg = load_splunk_config()
        if not cfg.get("host"):
            print("  ⚠️ Splunk 未配置，请先在「连接配置」中配置")
            return
        spl_result = execute_splunk_query(result["spl"])
        _print_splunk_execute_result(spl_result)


# ════════════════════════════════════════════
# ES 执行结果展示
# ════════════════════════════════════════════


def _print_es_execute_result(result: dict):
    """展示 ES 查询执行结果"""
    if not result.get("success"):
        print(f"\n  ❌ ES 查询执行失败")
        print(f"     错误: {result.get('error', '未知错误')}")
        return

    total = result.get("total", 0)
    hits = result.get("hits", 0)
    took = result.get("took_ms", 0)
    timed_out = result.get("timed_out", False)

    print(f"\n  🔎 ES 查询执行结果")
    print(f"     命中总数: {total}")
    print(f"     返回条数: {hits}")
    print(f"     耗时: {took}ms")
    if timed_out:
        print(f"     ⚠️ 查询超时")
    shards = result.get("shards", {})
    if shards:
        total_shards = shards.get("total", 0)
        failed_shards = shards.get("failed", 0)
        if failed_shards:
            print(f"     分片: {total_shards} 总 | ⚠️ {failed_shards} 失败")
        else:
            print(f"     分片: {total_shards} 全部成功")

    samples = result.get("samples", [])
    if samples:
        print(f"\n  样本数据 (前 {len(samples)} 条):")
        for i, s in enumerate(samples, 1):
            print(f"    [{i}] 索引: {s.get('index', '?')} | 评分: {s.get('score', 0):.2f}")
            preview = s.get("preview", "")
            if preview:
                print(f"        {preview[:200]}")
            print()


# ════════════════════════════════════════════
# 正则规则测试结果展示
# ════════════════════════════════════════════


def _print_regex_test_result(result: dict, file_path: str):
    """展示正则规则在日志文件上的测试结果"""
    total_lines = result.get("total_lines", 0)
    total_rules = result.get("total_rules", 0)
    total_matched = result.get("total_matched", 0)

    print(f"\n  📊 正则规则测试结果")
    print(f"     文件: {file_path}")
    print(f"     日志行数: {total_lines}")
    print(f"     规则数: {total_rules}")
    print(f"     总匹配数: {total_matched}\n")

    for r in result.get("results", []):
        name = r.get("name", "?")
        matched = r.get("matched", 0)
        total = r.get("total", 0)
        error = r.get("error")
        if error:
            print(f"  ❌ [{name}] — {error}")
            continue
        pct = (matched / total * 100) if total > 0 else 0
        icon = "✅" if matched > 0 else "⬜"
        print(f"  {icon} [{name}] 匹配 {matched}/{total} ({pct:.1f}%)")

        samples = r.get("samples", [])
        if samples:
            for s in samples:
                print(f"      第 {s['line_no']} 行: {s['content'][:120]}")
            print()


# ════════════════════════════════════════════
# 合规审计
# ════════════════════════════════════════════


def _menu_compliance(context: dict):
    _print_header("📋 合规审计")
    items = [
        {"label": "合规问答", "desc": "查询合规标准要求"},
        {"label": "基线生成", "desc": "自动生成合规基线"},
        {"label": "合规自查", "desc": "检查配置合规性"},
    ]

    idx = _show_nav_menu(items)
    if idx < 0:
        return

    if idx == 0:
        question = input("合规问题: ").strip()
        asset = input("资产类型 (可选): ").strip() or None
        std = input("标准过滤 (可选): ").strip() or None
        result = _compliance_svc.compliance_qa(question, asset, std)
        _print_qa_natural(result, question=question)

    elif idx == 1:
        count = _input_int("资产数量 (默认10): ", default=10)
        biz = input("业务类型 (如 enterprise, finance): ").strip() or "enterprise"
        devices_str = input("设备类型 (逗号分隔, 如 firewall,switch,server): ").strip()
        devices = [d.strip() for d in devices_str.split(",") if d.strip()]
        industry = input("行业 (可选): ").strip() or None
        result = _compliance_svc.generate_baseline(count, biz, devices, industry=industry)
        _print_baseline_natural(result)

    elif idx == 2:
        days = _input_int("日志保留天数: ", default=90, min_val=1, max_val=3650)
        backup = input("是否有备份 [y/N]: ").strip().lower() == "y"
        tamper = input("是否防篡改 [y/N]: ").strip().lower() == "y"
        dev_count = _input_int("设备数量: ", default=0, min_val=0, max_val=10000)
        result = _compliance_svc.compliance_check(
            log_retention_days=days, has_backup=backup,
            has_tamper_proof=tamper, device_count=dev_count
        )
        _print_compliance_check_natural(result)

    input("  按 Enter 继续...")





# ════════════════════════════════════════════
# 联合日志审查
# ════════════════════════════════════════════

def _menu_log_correlate(context: dict):
    _print_header("🔄 联合日志审查")
    items = [
        {"label": "从当前日志文件分析", "desc": "对选中的日志文件做跨源关联分析"},
        {"label": "手动输入日志行", "desc": "多行日志粘贴分析（每条一行）"},
        {"label": "查看攻击链模式", "desc": "查看系统支持的攻击链检测模式"},
    ]

    idx = _show_nav_menu(items)
    if idx < 0:
        return

    if idx == 0:
        # From file
        file_path = context.get("log_file")
        if not file_path or not os.path.exists(file_path):
            print("\n  ⚠️ 请先选择日志文件")
            input("  按 Enter 继续...")
            return

        line_limit = _input_int("\n  读取行数 [默认500]: ", default=500, max_val=10000)
        grep = input("  关键词过滤（可选）: ").strip() or None
        window = _input_int("  关联时间窗口(分钟) [默认5]: ", default=5, max_val=60)
        use_llm_opt = input("  LLM增强分析 [y/N]: ").strip().lower() == 'y'

        _show_status_bar(f"正在对 {os.path.basename(file_path)} 进行关联分析...")
        result = _log_correlate_svc.correlate_logs_from_file(
            file_path, line_limit=line_limit, grep=grep,
            time_window_minutes=window, detailed=True, use_llm=use_llm_opt,
        )
        _print_correlation_result(result)

    elif idx == 1:
        # Manual input
        print("\n  请输入日志行（每条一行，输入空行结束）:")
        lines = []
        while True:
            line = input("  ").strip()
            if not line:
                break
            lines.append(line)

        if not lines:
            print("\n  未输入任何日志。")
            input("  按 Enter 继续...")
            return

        window = _input_int("\n  关联时间窗口(分钟) [默认5]: ", default=5, max_val=60)
        use_llm_opt = input("  LLM增强分析 [y/N]: ").strip().lower() == 'y'

        _show_status_bar(f"正在分析 {len(lines)} 条日志...")
        result = _log_correlate_svc.correlate_logs(lines, time_window_minutes=window, detailed=True, use_llm=use_llm_opt)
        _print_correlation_result(result)

    elif idx == 2:
        # Show patterns
        patterns = _log_correlate_svc.available_patterns
        print(f"\n  系统支持 {len(patterns)} 种攻击链检测模式:\n")
        for p in patterns:
            risk_icon = {"P0": "🔴", "P1": "🟠", "P2": "🟡", "P3": "⚪"}
            icon = "🔴"
            for prefix, emoji in risk_icon.items():
                if p.get("risk_level", "").startswith(prefix):
                    icon = emoji
                    break
            stages = " → ".join(p.get("stages", []))
            print(f"  {icon} {p['name']}")
            print(f"     模式ID: {p['id']}")
            print(f"     风险等级: {p.get('risk_level', '?')}")
            print(f"     阶段链路: {stages}")
            print()

    input("  按 Enter 继续...")


def _print_correlation_result(result):
    """Print correlation result in a readable format."""
    import json as _json

    if result.get("code") != 0:
        print(f"\n  ❌ {result.get('msg', '未知错误')}")
        return

    data = result.get("data", result)
    print(f"\n  📊 分析概览")
    print(f"     解析事件: {data.get('total_events', 0)}")
    print(f"     设备类型: {', '.join(data.get('device_types', ['?']))}")
    print(f"     涉及实体: {', '.join(data.get('entities', ['?']))}")
    print(f"     攻击链数: {len(data.get('chains', []))}")
    print(f"     分析摘要: {data.get('summary', '')}")

    chains = data.get("chains", [])
    if chains:
        print(f"\n  🚨 检测到攻击链:")
        for i, c in enumerate(chains, 1):
            risk_icon = {"P0": "🔴", "P1": "🟠", "P2": "🟡", "P3": "⚪"}
            icon = "🔴"
            for prefix, emoji in risk_icon.items():
                if c.get("risk_level", "").startswith(prefix):
                    icon = emoji
                    break
            print(f"\n  {icon} [{i}] {c['chain_name']}")
            print(f"       置信度: {c.get('confidence', 0):.0%}")
            print(f"       风险等级: {c.get('risk_level', '?')}")
            print(f"       关联实体: {c.get('entity_key', '?')}")
            print(f"       匹配阶段: {' → '.join(c.get('matched_stages', []))}")
            if c.get("indicators"):
                print(f"       告警指标:")
                for ind in c["indicators"][:5]:
                    print(f"         • {ind}")
            if c.get("suggestion"):
                print(f"       处置建议: {c['suggestion']}")

    # Show detailed timeline (limit to 30 entries, skip events with no timestamp)
    timeline = data.get("timeline", [])
    if timeline:
        # Filter to events with timestamps and/or risk
        display_events = [
            e for e in timeline
            if e.get("timestamp") and e.get("timestamp") != "?"
        ]
        # Also include high/medium risk events even without timestamp
        for e in timeline:
            rl = e.get("risk_level", "")
            if rl and not rl.startswith("P3") and e not in display_events:
                display_events.append(e)

        # Sort by timestamp
        from log_guard.modules.log_correlate import _parse_timestamp
        display_events.sort(key=lambda e: _parse_timestamp(e.get("timestamp")) or datetime.min)

        if len(display_events) > 30:
            print(f"\n  📋 时间线详情 (前30条，共{len(display_events)}条):")
        else:
            print(f"\n  📋 时间线详情 ({len(display_events)}条):")

        for e in display_events[:30]:
            risk_indicator = ""
            rl = e.get("risk_level", "")
            if rl and not rl.startswith("P3"):
                risk_indicator = f" ⚠️{rl}"
            ts = e.get("timestamp", "?") or "?"
            print(f"    [{ts}] [{e.get('device_type', '?')}] "
                  f"{e.get('src_ip', '') or ''} {e.get('status', '') or ''}"
                  f"{risk_indicator}")


# ════════════════════════════════════════════
# 主入口 — 双模式自动检测
# ════════════════════════════════════════════

def _output(args, result, formatter=None):
    """统一输出：--json 输出 JSON，否则用 formatter 或默认自然语言"""
    if args.json_output:
        _print_json(result)
    elif formatter:
        formatter(result)
    else:
        _print_natural(result)


def _print_natural(result):
    """默认自然语言输出"""
    if isinstance(result, dict):
        code = result.get("code", 0)
        msg = result.get("msg", "")
        data = result.get("data", result)

        if code != 0:
            print(f"  ❌ {msg}")
            return

        # 根据数据内容智能输出
        if isinstance(data, dict):
            for k, v in data.items():
                if isinstance(v, list) and v:
                    print(f"  {k}: {len(v)} 条记录")
                elif isinstance(v, str) and len(v) > 50:
                    print(f"  {k}: {v[:50]}...")
                else:
                    print(f"  {k}: {v}")
        else:
            print(f"  {data}")
    else:
        print(f"  {result}")


def _print_list_logs_natural(result):
    """日志文件列表自然语言输出"""
    if isinstance(result, list):
        print(f"\n  找到 {len(result)} 个日志文件:\n")
        for i, f in enumerate(result[:20], 1):
            size_str = _fmt_size(f.get("size", 0))
            print(f"  [{i}] {f['name']}")
            print(f"      类型: {f.get('type', '?')} | 大小: {size_str}")
            print(f"      路径: {f['path']}")
            print()
        if len(result) > 20:
            print(f"  ... 还有 {len(result) - 20} 个文件")
    else:
        _print_natural(result)


def _print_sample_natural(result):
    """日志预览自然语言输出"""
    lines = result.get("lines", [])
    total = result.get("total_lines", 0)
    encoding = result.get("encoding", "?")
    size_str = _fmt_size(result.get("file_size", 0))

    print(f"\n  📄 日志预览")
    print(f"     总行数: {total} | 编码: {encoding} | 大小: {size_str}")
    print(f"     显示前 {len(lines)} 行:\n")
    for i, line in enumerate(lines, 1):
        print(f"  {i:3d} | {line.strip()[:120]}")
    if result.get("truncated"):
        print(f"\n  (已截断，完整文件共 {total} 行)")


def _print_parse_single_natural(result):
    """单条日志解析自然语言输出"""
    # Handle both formats: {"code": 0, "data": {...}} and direct {...}
    if "code" in result:
        if result.get("code") != 0:
            print(f"  ❌ 解析失败: {result.get('msg', '未知错误')}")
            return
        data = result.get("data", {})
    else:
        data = result

    if not data or not isinstance(data, dict):
        print(f"  ❌ 解析失败: 无法解析日志")
        return

    print(f"\n  🔍 日志解析结果")
    print(f"     类型: {data.get('device_type', '?')}")
    print(f"     时间: {data.get('timestamp', '-')}")
    print(f"     源IP: {data.get('src_ip', '-')}")
    print(f"     目的IP: {data.get('dst_ip', '-')}")
    print(f"     用户: {data.get('user', '-')}")
    print(f"     状态: {data.get('status', '-')}")
    print(f"     命令: {data.get('command', '-')}")
    extra = data.get("extra_info", {})
    if extra:
        print(f"     附加信息: {extra}")


def _print_parse_batch_natural(result):
    """批量解析自然语言输出"""
    total = result.get("total", 0)
    success = result.get("success_count", 0)
    fail = result.get("fail_count", 0)
    items = result.get("items", [])

    print(f"\n  📊 批量解析结果")
    print(f"     总计: {total} 条 | 成功: {success} 条 | 失败: {fail} 条")

    risk_summary = result.get("risk_summary", {})
    if risk_summary:
        print(f"\n  ⚠️ 风险统计:")
        print(f"     高风险: {risk_summary.get('high_risk_count', 0)} 条")
        print(f"     中风险: {risk_summary.get('medium_risk_count', 0)} 条")
        print(f"     低风险: {risk_summary.get('low_risk_count', 0)} 条")
        print(f"     噪音: {risk_summary.get('noise_count', 0)} 条")

    # 显示高风险项
    high_risk = [item for item in items if item.get("risk_assessment", {}).get("risk_level", "").startswith("P0") or
                 item.get("risk_assessment", {}).get("risk_level", "").startswith("P1")]
    if high_risk:
        print(f"\n  🔴 高风险日志:")
        for item in high_risk[:5]:
            risk = item.get("risk_assessment", {})
            print(f"     [{risk.get('risk_level', '?')}] {item.get('raw_log', '')[:80]}")


def _print_diagnose_natural(result):
    """故障诊断/设备匹配自然语言输出"""
    if result.get("code") != 0:
        print(f"  ❌ {result.get('msg', '诊断失败')}")
        return

    data = result.get("data", {})
    best = data.get("best_diagnosis", {})

    if best:
        # diagnose_fault result
        print(f"\n  🔧 故障诊断结果")
        print(f"     症状: {data.get('symptom', '?')}")
        print(f"     设备: {data.get('device_type', '?')}")
        print(f"     诊断: {best.get('fault_type', '?')}")
        print(f"     描述: {best.get('fault_desc', '?')}")
        print(f"     严重度: {best.get('severity', '?')}")

        causes = best.get("possible_causes", [])
        if causes:
            print(f"\n  📋 可能原因:")
            for i, c in enumerate(causes, 1):
                print(f"     {i}. {c}")

        steps = best.get("fix_steps", [])
        if steps:
            print(f"\n  🔨 修复步骤:")
            for s in steps:
                print(f"     {s}")

        prevention = best.get("prevention", [])
        if prevention:
            print(f"\n  🛡️ 预防措施:")
            for p in prevention:
                print(f"     • {p}")
    else:
        # match_device result
        print(f"\n  🔍 设备匹配结果")
        print(f"     设备类型: {data.get('device_type', '?')}")
        print(f"     设备型号: {data.get('device_model', '?')}")
        print(f"     匹配置信度: {data.get('match_confidence', '?')}")
        print(f"     匹配来源: {data.get('match_source', '?')}")

        plan = data.get("plan")
        if plan:
            print(f"\n  📡 采集方案")
            print(f"     协议: {plan.get('protocol', '?')}")
            print(f"     架构: {plan.get('architecture', '?')}")
            steps = plan.get("steps", [])
            if steps:
                print(f"     步骤:")
                for s in steps[:5]:
                    print(f"       • {s}")


def _print_regex_natural(result):
    """正则规则生成自然语言输出"""
    if result.get("code") != 0:
        print(f"  ❌ {result.get('msg', '生成失败')}")
        return

    data = result.get("data", {})
    regexes = data.get("regexes", [])

    print(f"\n  📝 正则规则生成结果")
    print(f"     场景: {data.get('scenario', '?')}")
    print(f"     生成 {len(regexes)} 条规则:\n")

    for i, r in enumerate(regexes, 1):
        print(f"  [{i}] {r.get('name', '?')} (优先级: {r.get('priority', '?')})")
        print(f"      描述: {r.get('description', '?')}")
        print(f"      正则: {r.get('pattern', '?')}")
        print(f"      示例: {r.get('match_example', '?')}")
        print()


def _print_es_query_natural(result):
    """ES查询生成自然语言输出"""
    if result.get("code") != 0:
        print(f"  ❌ {result.get('msg', '生成失败')}")
        return

    data = result.get("data", {})
    print(f"\n  🔎 ES查询生成结果")
    print(f"     索引模式: {data.get('index_pattern', '?')}")
    print(f"     时间范围: {data.get('time_range', '?')}")
    print(f"     说明: {data.get('note', '?')}")
    print(f"\n  查询语句:")
    query = data.get("query", {})
    print(json.dumps(query, ensure_ascii=False, indent=2))


def _print_baseline_natural(result):
    """合规基线自然语言输出"""
    if result.get("code") != 0:
        print(f"  ❌ {result.get('msg', '生成失败')}")
        return

    data = result.get("data", {})
    baselines = data.get("baselines", [])
    summary = data.get("summary", {})

    print(f"\n  📋 合规基线生成结果")
    print(f"     共生成 {len(baselines)} 条基线\n")

    severity_icons = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}

    for i, b in enumerate(baselines, 1):
        severity = b.get("severity", "?")
        icon = severity_icons.get(severity, "⚪")
        print(f"  {icon} [{b.get('baseline_id', '?')}] {b.get('name', '?')}")
        print(f"     分类: {b.get('category', '?')} | 严重度: {severity}")
        print(f"     描述: {b.get('description', '?')}")
        print(f"     检查频率: {b.get('check_frequency', '?')}")
        print(f"     处置建议: {b.get('remediation', '?')[:60]}...")
        print()

    dist = summary.get("severity_distribution", {})
    if dist:
        parts = [f"{k}: {v}" for k, v in dist.items()]
        print(f"  📊 严重度分布: {' | '.join(parts)}")


def _print_optimize_natural(result):
    """脚本优化自然语言输出"""
    if result.get("code") != 0:
        print(f"  ❌ {result.get('msg', '优化失败')}")
        return

    data = result.get("data", {})
    print(f"\n  ✨ 脚本优化结果")
    print(f"     评分: {data.get('score', '?')}/100")
    print(f"     类型: {data.get('script_type', '?')}")

    issues = data.get("issues", [])
    if issues:
        print(f"\n  ⚠️ 发现问题:")
        for issue in issues:
            print(f"     • {issue}")

    suggestions = data.get("suggestions", [])
    if suggestions:
        print(f"\n  💡 优化建议:")
        for s in suggestions:
            print(f"     • {s}")

    optimized = data.get("optimized_script", "")
    if optimized:
        print(f"\n  📜 优化后脚本:")
        print(f"     {optimized}")


def _print_trace_natural(result):
    """攻击溯源自然语言输出（替代旧的 _print_collect_plan_natural）"""
    if result.get("code") != 0:
        print(f"  ❌ {result.get('msg', '溯源失败')}")
        return

    data = result.get("data", {})
    attack_chain = data.get("attack_chain", [])
    timeline = data.get("timeline", [])
    summary = data.get("summary", "")

    print(f"\n  🔍 攻击溯源结果")
    if summary:
        print(f"     摘要: {summary[:200]}")

    print(f"\n  📋 攻击链 ({len(attack_chain)} 阶段):")
    stage_icons = {"侦查探测": "🔎", "初始入侵": "🚪", "权限提升": "⬆️",
                   "横向移动": "➡️", "持久化驻留": "🏠", "数据窃取/破坏": "💀"}
    for i, stage in enumerate(attack_chain, 1):
        stage_name = stage.get("stage", "?")
        icon = stage_icons.get(stage_name, "📌")
        count = stage.get("event_count", 0)
        print(f"\n  {icon} 阶段 {i}: {stage_name}（{count} 条事件）")
        for evt in stage.get("events", [])[:3]:
            print(f"       └ {evt[:150]}")
        if len(stage.get("events", [])) > 3:
            print(f"       └ ... 还有 {len(stage['events']) - 3} 条")

    if timeline:
        print(f"\n  ⏱ 时间线 ({len(timeline)} 节点):")
        for t in timeline[:5]:
            print(f"     [{t.get('sequence', '?')}] {t.get('event', '')[:100]} | {t.get('stage', '')}")
        if len(timeline) > 5:
            print(f"     ... 还有 {len(timeline) - 5} 个节点")


def _print_monitoring_rules(rules: dict):
    """展示从溯源结果生成的持续监控规则"""
    print(f"\n  🔄 溯源→监控规则（闭环生成）")
    print(f"     攻击类型: {rules.get('source_attack_type', '?')}")
    print(f"     提取关键词: {', '.join(rules.get('keywords', [])[:8])}")
    print(f"     提取IP: {', '.join(rules.get('ips', [])[:5]) or '(无)'}")

    es_query = rules.get("es_query", {})
    regex_rules = rules.get("regex_rules", [])

    print(f"\n  📦 ES 查询 DSL:")
    print(json.dumps(es_query, ensure_ascii=False, indent=2))

    print(f"\n  📜 正则规则（{len(regex_rules)} 条）:")
    for r in regex_rules:
        if len(r.get("pattern", "")) > 60:
            pat = r["pattern"][:60] + "..."
        else:
            pat = r.get("pattern", "")
        print(f"     • {r.get('name', '?')}: {pat}")

    # 可选保存为模板
    save_choice = input(f"\n  💾 是否将 ES 查询保存为模板？[y/N]: ").strip().lower()
    if save_choice == "y" and es_query:
        tpl_name = input(f"  模板名称 [溯源-{rules.get('source_attack_type', 'unknown')}]: ").strip()
        if not tpl_name:
            tpl_name = f"溯源-{rules.get('source_attack_type', 'unknown')}"
        save_es_template(tpl_name, es_query,
                         f"从攻击溯源自动生成: {rules.get('summary', '')[:60]}",
                         "logs-*", "last_24h")
        print(f"  ✅ 模板「{tpl_name}」已保存至 ES 模板库")


def _print_splunk_natural(result: dict):
    """Splunk SPL 查询自然语言输出"""
    print(f"\n  📊 Splunk SPL 查询")
    print(f"     场景: {result.get('scene_label', '?')}")
    print(f"     索引: {result.get('index', '*')}")
    print(f"     时间: {result.get('time_range', 'last_24h')}")
    print(f"     说明: {result.get('note', '?')}")
    print(f"\n  SPL 语句:")
    print(f"     {result.get('spl', '')}")


def _print_splunk_execute_result(result: dict):
    """Splunk 执行结果展示"""
    if result.get("success"):
        print(f"\n  ✅ Splunk 查询成功！返回 {result['event_count']} 条结果")
        if result.get("sid"):
            print(f"     搜索 ID: {result['sid']}")
        for item in result.get("results", [])[:5]:
            print(f"     └ {json.dumps(item, ensure_ascii=False)[:200]}")
        if len(result.get("results", [])) > 5:
            print(f"     └ ... 还有 {len(result['results']) - 5} 条")
    else:
        print(f"  ❌ Splunk 查询失败: {result.get('error', '未知错误')}")


def _print_collect_plan_natural(result):
    """采集方案自然语言输出（日志采集模块用）"""
    if result.get("code") != 0:
        print(f"  ❌ {result.get('msg', '生成失败')}")
        return

    data = result.get("data", {})
    plan = data.get("plan", data)
    print(f"\n  📡 采集方案")
    print(f"     设备类型: {plan.get('device_type', data.get('device_type', '?'))}")
    print(f"     设备型号: {plan.get('device_model', data.get('device_model', '?'))}")
    print(f"     传输协议: {plan.get('protocol', '?')}")
    print(f"     架构: {plan.get('architecture', '?')}")

    steps = plan.get("steps", [])
    if steps:
        print(f"\n  采集步骤:")
        for s in steps:
            print(f"     • {s}")

    config = plan.get("config_template", "")
    if config:
        print(f"\n  配置模板:")
        print(f"     {config}")

    notes = plan.get("notes", [])
    if notes:
        print(f"\n  注意事项:")
        for n in notes:
            print(f"     • {n}")


def _print_collect_arch_natural(result):
    """架构推荐自然语言输出"""
    if result.get("code") != 0:
        print(f"  ❌ {result.get('msg', '推荐失败')}")
        return

    data = result.get("data", {})
    rec = data.get("recommendation", data)

    print(f"\n  🏗️ 架构推荐")
    print(f"     方案: {rec.get('name', rec.get('type', '?'))}")
    params = data.get("input_parameters", {})
    print(f"     设备数量: {params.get('device_count', rec.get('device_count', '?'))}")
    print(f"     日志量级: {params.get('daily_log_volume_gb', rec.get('daily_log_volume_gb', '?'))} GB/天")
    print(f"     预算: {params.get('budget', '?')}")
    print(f"     团队水平: {params.get('team_skill', '?')}")

    reasoning = rec.get("reasoning", [])
    if reasoning:
        print(f"\n  推荐理由:")
        for r in reasoning:
            print(f"     • {r}")

    # Handle architecture recommendation data
    recs = data.get("recommendations", [])
    if recs:
        print(f"\n  推荐平台:")
        for p in recs[:5]:
            if isinstance(p, dict):
                print(f"     • {p.get('name', '?')} (评分: {p.get('score', '?')})")
                pros = p.get("pros", [])
                if pros:
                    print(f"       优势: {', '.join(pros[:3])}")

    choice = data.get("choice", "")
    if choice:
        print(f"\n  最终推荐: {choice}")


def _print_compliance_check_natural(result):
    """合规自查自然语言输出"""
    if result.get("code") != 0:
        print(f"  ❌ {result.get('msg', '检查失败')}")
        return

    data = result.get("data", {})
    print(f"\n  📋 合规自查结果")
    overall = "✅ 合规" if data.get("overall_compliance") else "❌ 不合规"
    print(f"     结论: {overall}")
    print(f"     总检查项: {data.get('total', '?')}")
    print(f"     通过: {data.get('passed', '?')} | 未通过: {data.get('failed', '?')}")
    print(f"     合规率: {data.get('compliance_percentage', '?')}%")

    high_fails = data.get("high_severity_fails", 0)
    if high_fails:
        print(f"     ⚠️ 高严重度未通过: {high_fails} 项")

    items = data.get("items", [])
    if items:
        severity_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}
        print(f"\n  检查详情:")
        for item in items:
            status = "✅" if item.get("status") == "pass" else "❌"
            icon = severity_icon.get(item.get("severity", ""), "⚪")
            print(f"     {status} {icon} {item.get('requirement', item.get('check_name', '?'))}")
            if item.get("status") != "pass":
                print(f"        建议: {item.get('suggestion', '')}")





def _call_llm_fallback(question: str) -> str:
    """调用大模型回答问题（兜底功能）"""
    if not _AI_AVAILABLE:
        return None, "AI Core 未加载"

    try:
        llm = get_llm()
        messages = [
            {"role": "system", "content": "你是一个网络安全和合规审计专家。请用中文回答用户的问题，给出专业、准确的建议。"},
            {"role": "user", "content": question}
        ]
        result = llm.chat(messages, temperature=0.7, max_tokens=1000)
        if result.get("success") and result.get("content"):
            return result["content"], None
        return None, result.get("error", "LLM 调用失败")
    except Exception as e:
        logger.warning(f"LLM fallback failed: {e}")
        return None, str(e)


def _print_qa_natural(result, question: str = ""):
    """合规问答自然语言输出"""
    if result.get("code") != 0:
        print(f"  ❌ {result.get('msg', '查询失败')}")
        return

    data = result.get("data", {})
    items = data.get("answered_questions", [])
    standards = data.get("standards", [])

    if not items:
        # 知识库未找到匹配，调用大模型兜底
        print(f"\n  ❓ 知识库中未找到匹配的合规标准")
        print(f"  🤖 正在调用 AI 助手回答...\n")

        if question:
            llm_answer, error = _call_llm_fallback(question)
            if llm_answer:
                print(f"  {llm_answer}")
                print(f"\n  ⚠️ 注意：以上回答由 AI 根据网络知识生成，暂不在本地资料库中，仅供参考。")
            else:
                print(f"  💡 AI 兜底回答失败: {error}")
                print(f"  💡 提示: 尝试扩大查询范围，或检查 LLM API 配置。")
        else:
            print(f"  💡 提示: 请提供具体问题，或尝试扩大查询范围。")
        return

    print(f"\n  📚 合规问答结果")
    print(f"     匹配 {len(items)} 条合规要求:\n")

    for std in standards:
        print(f"  📖 {std.get('name', '?')} ({std.get('standard_id', '?')})")
        for item in std.get("matched_items", []):
            print(f"     [{item.get('item_id', '?')}] {item.get('requirement', '?')}")
            print(f"       详情: {item.get('detail', '?')[:80]}...")
            print(f"       风险: {item.get('risk_if_not', '?')[:60]}...")
        print()


def run_command(args: argparse.Namespace) -> int:
    """命令行模式（无交互）— 返回退出码: 0成功 1业务失败 2参数错误"""
    log_reader = LogReader()

    if args.log_file and not os.path.exists(args.log_file):
        print(f"  ❌ 文件不存在: {args.log_file}")
        return 2

    if args.list_logs:
        files = log_reader.list_log_files(args.log_dir)
        if args.json_output:
            _print_json(files)
        else:
            _print_list_logs_natural(files)
        return 0

    if args.sample:
        if not args.log_file:
            print("  请指定 --log-file")
            return 2
        preview = log_reader.sample_log(args.log_file, n=args.sample)
        if args.json_output:
            _print_json(preview)
        else:
            _print_sample_natural(preview)
        return 0

    if args.parse is not None:
        if args.log_file:
            result = log_reader.read_log(args.log_file, line_limit=args.lines or 100, grep=args.grep)
            lines = result.get("lines", [])
            items = []
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                r = _log_parse_svc.parse_log(line)
                items.append(r)
            output = {"total": len(lines), "parsed": items}
            if args.json_output:
                _print_json(output)
            else:
                _print_parse_batch_natural({"code": 0, "data": output})
        else:
            # args.parse is the log line string when --parse is used with a value
            log_line = args.parse if isinstance(args.parse, str) and args.parse else None
            if log_line:
                result = _log_parse_svc.parse_log(log_line)
                if args.json_output:
                    _print_json(result)
                else:
                    _print_parse_single_natural(result)
            else:
                print("  请指定日志行字符串，例如: --parse \"Failed password for root from 192.168.1.100\"")
                return 2

    if args.batch_parse:
        if not args.log_file:
            print("  请指定 --log-file")
            return 2
        result = log_reader.read_log(args.log_file, line_limit=args.lines or 200, grep=args.grep)
        lines = result.get("lines", [])
        batch = _log_parse_svc.batch_parse(lines, do_assess=args.assess)
        if args.json_output:
            _print_json(batch)
        else:
            _print_parse_batch_natural(batch)
        return 0

    if args.splunk_test:
        result = execute_splunk_query("search index=* | head 1", max_results=1)
        if args.json_output:
            _print_json(result)
        else:
            if result.get("success"):
                print(f"  ✅ Splunk 连接成功, 返回 {result.get('event_count', 0)} 条")
            else:
                print(f"  ❌ Splunk 连接失败: {result.get('error', '未知错误')}")
        return 0 if result.get("success") else 1

    if args.splunk_search:
        result = execute_splunk_query(args.splunk_search)
        if args.json_output:
            _print_json(result)
        else:
            if result.get("success"):
                print(f"  ✅ Splunk 搜索完成, 命中 {result.get('event_count', 0)} 条")
                for ev in (result.get("results") or [])[:5]:
                    print(f"    - {ev.get('_time', '')} {str(ev.get('event', ''))[:100]}")
            else:
                print(f"  ❌ Splunk 搜索失败: {result.get('error', '未知错误')}")
        return 0 if result.get("success") else 1

    if args.es_test:
        result = execute_es_query({"query": {"match_all": {}}}, size=1)
        if args.json_output:
            _print_json(result)
        else:
            if result.get("success"):
                print(f"  ✅ ES 连接成功, 命中 {result.get('total', 0)} 条")
            else:
                print(f"  ❌ ES 连接失败: {result.get('error', '未知错误')}")
        return 0 if result.get("success") else 1

    if args.es_search:
        try:
            dsl = json.loads(args.es_search)
        except json.JSONDecodeError as e:
            print(f"  ❌ DSL JSON 解析失败: {e}")
            return 2
        result = execute_es_query(dsl)
        if args.json_output:
            _print_json(result)
        else:
            if result.get("success"):
                print(f"  ✅ ES 搜索完成, 命中 {result.get('total', 0)} 条 (耗时 {result.get('took_ms', 0)}ms)")
                for s in (result.get("samples") or [])[:5]:
                    print(f"    - {s.get('index', '')}: {s.get('preview', '')[:100]}")
            else:
                print(f"  ❌ ES 搜索失败: {result.get('error', '未知错误')}")
        return 0 if result.get("success") else 1

    if args.diagnose:
        if _log_collect_svc is None:
            print("  采集模块未加载")
            return 1
        result = _log_collect_svc.diagnose_fault(
            symptom=args.diagnose, device_type=args.device_type,
            protocol=args.protocol, error_log=args.error_log
        )
        if args.json_output:
            _print_json(result)
        else:
            _print_diagnose_natural(result)
        return 0

    if args.regex:
        result = _script_gen_svc.generate_regex(args.regex, args.log_sample, args.device_type)
        if args.json_output:
            _print_json(result)
        else:
            _print_regex_natural(result)
        return 0

    if args.es_query:
        result = _script_gen_svc.generate_es_query(search_scenario=args.es_query)
        if args.json_output:
            _print_json(result)
        else:
            _print_es_query_natural(result)
        return 0

    if args.baseline is not None:
        result = _compliance_svc.generate_baseline(asset_count=args.baseline)
        if args.json_output:
            _print_json(result)
        else:
            _print_baseline_natural(result)
        return 0

    if args.optimize:
        script, script_type = args.optimize
        result = _script_gen_svc.optimize_script(script=script, script_type=script_type)
        if args.json_output:
            _print_json(result)
        else:
            _print_optimize_natural(result)
        return 0

    if args.qa:
        result = _compliance_svc.compliance_qa(args.qa, args.asset_type)
        if args.json_output:
            _print_json(result)
        else:
            _print_qa_natural(result, question=args.qa)
        return 0

    if args.correlate is not None:
        if args.log_file:
            window = args.time_window or 5
            result = _log_correlate_svc.correlate_logs_from_file(
                args.log_file, line_limit=args.lines or 500,
                grep=args.grep, time_window_minutes=window,
                detailed=True,
            )
        else:
            correlate_input = args.correlate if isinstance(args.correlate, str) and args.correlate else ""
            result = _log_correlate_svc.correlate_logs(
                [correlate_input] if correlate_input else [],
                time_window_minutes=args.time_window or 5,
                detailed=True,
            )
        if args.json_output:
            _print_json(result)
        else:
            _print_correlation_result(result)
        return 0


def main():
    """主入口 — 支持 argparse 和交互模式"""
    # 快速启动：如果有参数就走命令行模式
    if len(sys.argv) > 1:
        parser = argparse.ArgumentParser(
            description="日志溯源卫士 CLI 智能体 v3.0 — 日志分析 + AI 智能对话",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog=textwrap.dedent("""\
                示例:
                  log-guard                    # 交互模式（默认）
                  log-guard --list-logs        # 列出本机日志
                  log-guard -f auth.log -p     # 解析日志文件
                  log-guard --diagnose "SSH连接超时"
                  log-guard -f /var/log/auth.log -c  # 多源日志关联分析
                  log-guard --ai              # 直接进入 AI 对话模式
            """),
        )

        parser.add_argument("--version", "-V", action="store_true", help="显示版本号")
        parser.add_argument("--ai", action="store_true", help="直接进入 AI 智能对话模式")
        parser.add_argument("--ask", help="非交互式 AI 问答（输出 JSON）")
        parser.add_argument("--json", dest="json_output", action="store_true", help="强制 JSON 输出（适合脚本调用）")
        parser.add_argument("--log-file", "-f", help="日志文件路径")
        parser.add_argument("--log-dir", "-d", help="日志文件目录")
        parser.add_argument("--list-logs", "-l", action="store_true", help="列出常见位置的日志文件")
        parser.add_argument("--sample", "-s", nargs="?", type=int, const=20, help="预览日志文件")
        parser.add_argument("--parse", "-p", nargs="?", const="", help="解析日志（可选：传入日志行字符串）")
        parser.add_argument("--batch-parse", "-b", action="store_true", help="批量解析")
        parser.add_argument("--assess", "-a", action="store_true", help="解析时同时风险研判")
        parser.add_argument("--lines", "-n", type=int, default=100, help="读取行数")
        parser.add_argument("--grep", "-g", help="关键词过滤")
        parser.add_argument("--diagnose", help="故障诊断")
        parser.add_argument("--device-type", help="设备类型")
        parser.add_argument("--protocol", help="传输协议")
        parser.add_argument("--error-log", help="错误日志内容")
        parser.add_argument("--regex", help="正则规则生成")
        parser.add_argument("--log-sample", help="日志样例")
        parser.add_argument("--qa", help="合规问答")
        parser.add_argument("--es-query", dest="es_query", help="ES 查询生成（需提供搜索场景描述）")
        parser.add_argument("--baseline", nargs="?", const=10, type=int, help="合规基线生成（可选资产数量，默认10）")
        parser.add_argument("--optimize", nargs=2, metavar=("SCRIPT", "TYPE"), help="脚本优化（脚本内容 + 类型: regex/es_query）")
        parser.add_argument("--asset-type", help="资产类型")
        parser.add_argument("--correlate", "-c", nargs="?", const="", help="联合日志审查（关联分析）")
        parser.add_argument("--time-window", "-w", type=int, default=5, help="关联时间窗口（分钟）")
        parser.add_argument("--splunk-test", action="store_true", help="测试 Splunk 连接")
        parser.add_argument("--splunk-search", help="执行 Splunk 搜索（传入 SPL 查询）")
        parser.add_argument("--es-test", action="store_true", help="测试 ES 连接")
        parser.add_argument("--es-search", help="执行 ES 搜索（传入 DSL JSON）")

        args = parser.parse_args()

        # --version
        if args.version:
            print("log-guard 3.0.0")
            return

        # --ask 非交互式 AI 问答
        if args.ask:
            if not (_AI_AVAILABLE and getattr(ai_settings, 'is_configured', False)):
                print("AI Core 未加载或 API Key 未配置")
                return
            orchestrator = get_orchestrator()
            result = orchestrator.process(args.ask)
            if args.json_output:
                print(json.dumps(result, ensure_ascii=False, indent=2))
            else:
                print(result["response"])
            return

        # --ai 直接进入 AI 对话模式
        if args.ai:
            try:
                _run_ai_mode()
            except KeyboardInterrupt:
                print("\n  👋 再见！")
            return

        has_command = any([
            args.list_logs, args.sample, args.parse, args.batch_parse,
            args.diagnose, args.regex, args.es_query, args.baseline is not None,
            args.optimize, args.qa, args.correlate,
            args.splunk_test, args.splunk_search, args.es_test, args.es_search,
        ])

        if has_command or args.log_file:
            sys.exit(run_command(args))

    # 交互模式（无参数或终端交互）
    try:
        _run_interactive_mode()
    except KeyboardInterrupt:
        print("\n\n  👋 再见！")
    except EOFError:
        print("\n  👋 再见！")


if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""日志溯源卫士 CLI 智能体 v2.0 — 双模式：菜单操作 + AI 智能对话"""
# -*- coding: utf-8 -*-

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
from log_guard.modules.script_gen import ScriptGenService
from log_guard.modules.compliance import ComplianceService
from log_guard.modules.training import TrainingService

try:
    from log_guard.modules.log_collect import LogCollectService
except ImportError:
    LogCollectService = None

# ── AI Core 导入（可选，无 LLM 时降级为纯菜单模式） ──
_AI_AVAILABLE = False
try:
    from log_guard.ai_core import get_orchestrator, get_context_manager, settings as ai_settings
    _AI_AVAILABLE = True
except ImportError:
    pass

logger = LogManager.get_logger()

# 实例化服务
_log_parse_svc = LogParseService()
_script_gen_svc = ScriptGenService()
_compliance_svc = ComplianceService()
_training_svc = TrainingService()
_log_collect_svc = None
if LogCollectService:
    _log_collect_svc = LogCollectService()


# ════════════════════════════════════════════
# 工具函数
# ════════════════════════════════════════════

def _print_banner():
    banner = r"""
╔══════════════════════════════════════════════════════╗
║       🔍 日志溯源卫士 CLI 智能体 v2.0               ║
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
    try:
        choice = input(f"\n{prompt} [0-{len(items)}]: ").strip()
        if choice == "0" or choice == "":
            return -1
        idx = int(choice) - 1
        if 0 <= idx < len(items):
            return idx
        print("输入无效，请重新选择")
        return _show_nav_menu(items, prompt)
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
    ai_available = _AI_AVAILABLE and ai_settings.is_configured

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
            ai_available = _AI_AVAILABLE and ai_settings.is_configured
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
                "training": "🎓 实训答疑",
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
    mode = "AI 可用" if (_AI_AVAILABLE and ai_settings.is_configured) else "仅菜单"
    log_info = f"日志: {context.get('log_file', '未选择')}" if context.get("log_file") else "日志: 未选择"
    print(f"\n{sep}")
    print(f"  📋 菜单模式 | {log_info} | 输入 /ai 进入对话 | 模式: {mode}")
    print(f"{sep}")


def _run_interactive_mode():
    """交互式菜单主循环"""
    log_reader = LogReader()
    context = {"source": "cli"}

    # 首次运行检查
    if _AI_AVAILABLE and not ai_settings.is_configured:
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
            {"label": "🎓 攻防实训", "desc": "实训场景、答案提交、成绩报告"},
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
            _menu_training(context)
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
    if preview.get("lines"):
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
        n = input("  读取行数 [默认50]: ").strip()
        line_limit = int(n) if n.isdigit() else 50

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
        result = _log_parse_svc.identify_log_type(line)
        print("\n【类型识别】")
        _print_json(result)
        parse_result = _log_parse_svc.parse_log(line)
        print("\n【解析结果】")
        _print_json(parse_result)
        if parse_result.get("code") == 0 and "data" in parse_result:
            risk = _log_parse_svc.assess_risk(parse_result["data"])
            print("\n【风险研判】")
            _print_json(risk)

    elif idx == 2:
        if not context.get("log_file"):
            print("\n  ⚠️ 请先选择日志文件")
            input("  按 Enter 继续...")
            return
        n = input("\n  读取行数 [默认200]: ").strip()
        line_limit = int(n) if n.isdigit() else 200
        result = log_reader.read_log(context["log_file"], line_limit=line_limit)
        lines = result.get("lines", [])
        print(f"\n  正在批量解析 {len(lines)} 行，含风险研判...")
        batch = _log_parse_svc.batch_parse(lines, do_assess=True)
        _print_json(batch)

    elif idx == 3:
        field = input("\n  输入字段名称（如 src_ip, timestamp, user）: ").strip()
        if field:
            result = _log_parse_svc.explain_field(field)
            _print_json(result)

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
        _print_json(result)

    elif idx == 1:
        dtype = input("设备类型: ").strip()
        model = input("设备型号 (可选): ").strip()
        scale = input("规模 [small/medium/large] (默认small): ").strip() or "small"
        include = input("包含配置模板 [y/N]: ").strip().lower() == "y"
        result = _log_collect_svc.generate_plan(dtype, model, scale, include)
        _print_json(result)

    elif idx == 2:
        symptom = input("故障症状描述: ").strip()
        dev = input("设备类型 (可选): ").strip() or None
        proto = input("传输协议 (可选): ").strip() or None
        err = input("错误日志 (可选): ").strip() or None
        result = _log_collect_svc.diagnose_fault(symptom, dev, proto, err)
        _print_json(result)

    elif idx == 3:
        count_str = input("设备数量: ").strip()
        count = int(count_str) if count_str.isdigit() else 10
        volume = input("日日志量 [small/medium/large] (默认medium): ").strip() or "medium"
        budget = input("预算 [low/medium/high] (默认medium): ").strip() or "medium"
        skill = input("团队水平 [basic/intermediate/advanced] (默认basic): ").strip() or "basic"
        result = _log_collect_svc.recommend_architecture(count, volume, budget, skill)
        _print_json(result)

    input("  按 Enter 继续...")


def _menu_script_gen(context: dict):
    _print_header("📝 脚本生成")
    items = [
        {"label": "正则规则生成", "desc": "根据攻防场景生成正则检测规则"},
        {"label": "ES查询生成", "desc": "生成 Elasticsearch 检索语句"},
        {"label": "攻击溯源", "desc": "分析攻击链路"},
        {"label": "平台选型", "desc": "推荐日志分析平台"},
        {"label": "脚本优化", "desc": "优化现有脚本（正则/ES查询）"},
    ]

    idx = _show_nav_menu(items)
    if idx < 0:
        return

    if idx == 0:
        scenario = input("攻防场景描述: ").strip()
        sample = input("日志样例 (可选): ").strip() or None
        device = input("设备类型 (可选): ").strip() or None
        result = _script_gen_svc.generate_regex(scenario, sample, device)
        _print_json(result)

    elif idx == 1:
        scenario = input("检索场景描述: ").strip()
        index = input("索引模式 (如 logstash-*): ").strip() or None
        time_range = input("时间范围 (如 last_24h, last_7d): ").strip() or None
        result = _script_gen_svc.generate_es_query(scenario, index, time_range)
        _print_json(result)

    elif idx == 2:
        file_path = context.get("log_file")
        if not file_path or not os.path.exists(file_path):
            print("\n  ⚠️ 请先选择日志文件")
            input("  按 Enter 继续...")
            return
        attack_type = input("攻击类型 (如 ssh_bruteforce, web_sql_injection, 可选): ").strip() or None
        logs = LogReader().read_log(file_path, line_limit=100).get("lines", [])
        result = _script_gen_svc.trace_attack(logs, attack_type)
        _print_json(result)

    elif idx == 3:
        count_str = input("设备数量 (默认50): ").strip()
        count = int(count_str) if count_str.isdigit() else 50
        volume = input("日日志量 [small/medium/large] (默认medium): ").strip() or "medium"
        budget = input("预算 [low/medium/high] (默认medium): ").strip() or "medium"
        skill = input("团队水平 [basic/intermediate/advanced] (默认basic): ").strip() or "basic"
        result = _script_gen_svc.recommend_platform(count, volume, budget, skill)
        _print_json(result)

    elif idx == 4:
        script = input("输入脚本内容: ").strip()
        stype = input("脚本类型 [regex/es_query] (默认regex): ").strip() or "regex"
        scenario = input("使用场景 (可选): ").strip() or None
        result = _script_gen_svc.optimize_script(script, stype, scenario)
        _print_json(result)

    input("  按 Enter 继续...")


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
        _print_json(result)

    elif idx == 1:
        count_str = input("资产数量: ").strip()
        count = int(count_str) if count_str.isdigit() else 10
        biz = input("业务类型 (如 enterprise, finance): ").strip() or "enterprise"
        devices_str = input("设备类型 (逗号分隔, 如 firewall,switch,server): ").strip()
        devices = [d.strip() for d in devices_str.split(",") if d.strip()]
        industry = input("行业 (可选): ").strip() or None
        result = _compliance_svc.generate_baseline(count, biz, devices, industry=industry)
        _print_json(result)

    elif idx == 2:
        days_str = input("日志保留天数: ").strip()
        days = int(days_str) if days_str.isdigit() else None
        backup = input("是否有备份 [y/N]: ").strip().lower() == "y"
        tamper = input("是否防篡改 [y/N]: ").strip().lower() == "y"
        dev_count_str = input("设备数量: ").strip()
        dev_count = int(dev_count_str) if dev_count_str.isdigit() else 0
        result = _compliance_svc.compliance_check(
            log_retention_days=days, has_backup=backup,
            has_tamper_proof=tamper, device_count=dev_count
        )
        _print_json(result)

    input("  按 Enter 继续...")


def _menu_training(context: dict):
    _print_header("🎓 攻防实训")
    items = [
        {"label": "下发实训场景", "desc": "获取实训任务"},
        {"label": "提交答案", "desc": "提交实训任务答案"},
        {"label": "生成实训报告", "desc": "查看实训成绩报告"},
    ]

    idx = _show_nav_menu(items)
    if idx < 0:
        return

    if idx == 0:
        cat = input("场景分类 [basic/collection/filtering/web_attack/lateral_movement/compliance] (可选): ").strip() or None
        sid = input("场景ID (如 S001, 可选): ").strip() or None
        result = _training_svc.dispatch_tasks(scenario_id=sid, category=cat)
        _print_json(result)

    elif idx == 1:
        sid = input("场景ID: ").strip()
        tid = input("任务ID: ").strip()
        stype = input("提交类型 [rule/script/conclusion/plan]: ").strip()
        content_str = input("答案内容 (JSON格式): ").strip()
        try:
            import json
            content = json.loads(content_str)
        except json.JSONDecodeError:
            content = {"text": content_str}
        student = input("学员ID (可选): ").strip() or None
        result = _training_svc.submit_answer(sid, tid, stype, content, student)
        _print_json(result)

    elif idx == 2:
        student = input("学员ID (可选): ").strip() or "anonymous"
        sid = input("场景ID (可选): ").strip() or None
        result = _training_svc.generate_report(student, sid)
        _print_json(result)

    input("  按 Enter 继续...")


# ════════════════════════════════════════════
# 主入口 — 双模式自动检测
# ════════════════════════════════════════════

def run_command(args: argparse.Namespace):
    """命令行模式（无交互）"""
    log_reader = LogReader()

    if args.log_file and not os.path.exists(args.log_file):
        print(Result.fail(f"文件不存在: {args.log_file}"))
        return

    if args.list_logs:
        files = log_reader.list_log_files(args.log_dir)
        _print_json(files)
        return

    if args.sample:
        if not args.log_file:
            print("请指定 --log-file")
            return
        preview = log_reader.sample_log(args.log_file, n=args.sample)
        _print_json(preview)
        return

    if args.parse:
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
            _print_json({"total": len(lines), "parsed": items})
        else:
            result = _log_parse_svc.parse_log(args.parse)
            _print_json(result)
        return

    if args.batch_parse:
        if not args.log_file:
            print("请指定 --log-file")
            return
        result = log_reader.read_log(args.log_file, line_limit=args.lines or 200, grep=args.grep)
        lines = result.get("lines", [])
        batch = _log_parse_svc.batch_parse(lines, do_assess=args.assess)
        _print_json(batch)
        return

    if args.diagnose:
        if _log_collect_svc is None:
            print("采集模块未加载")
            return
        result = _log_collect_svc.diagnose_fault(
            symptom=args.diagnose, device_type=args.device_type,
            protocol=args.protocol, error_log=args.error_log
        )
        _print_json(result)
        return

    if args.regex:
        result = _script_gen_svc.generate_regex(args.regex, args.log_sample, args.device_type)
        _print_json(result)
        return

    if args.qa:
        result = _compliance_svc.compliance_qa(args.qa, args.asset_type)
        _print_json(result)
        return

    if args.train:
        result = _training_svc.dispatch_tasks(category=args.train)
        _print_json(result)
        return


def main():
    """主入口 — 支持 argparse 和交互模式"""
    # 检查是否在交互式终端中运行
    is_interactive = sys.stdin.isatty()

    # 快速启动：如果有参数就走命令行模式
    if len(sys.argv) > 1:
        parser = argparse.ArgumentParser(
            description="日志溯源卫士 CLI 智能体 v2.0 — 日志分析 + AI 智能对话",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog=textwrap.dedent("""\
                示例:
                  log-guard                    # 交互模式（默认）
                  log-guard --list-logs        # 列出本机日志
                  log-guard -f auth.log -p     # 解析日志文件
                  log-guard --diagnose "SSH连接超时"
                  log-guard --ai              # 直接进入 AI 对话模式
            """),
        )

        parser.add_argument("--ai", action="store_true", help="直接进入 AI 智能对话模式")
        parser.add_argument("--log-file", "-f", help="日志文件路径")
        parser.add_argument("--log-dir", "-d", help="日志文件目录")
        parser.add_argument("--list-logs", "-l", action="store_true", help="列出常见位置的日志文件")
        parser.add_argument("--sample", "-s", type=int, nargs="?", const=20, help="预览日志文件")
        parser.add_argument("--parse", "-p", nargs="?", const=True, help="解析日志")
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
        parser.add_argument("--asset-type", help="资产类型")
        parser.add_argument("--train", help="实训场景分类")

        args = parser.parse_args()

        # --ai 直接进入 AI 对话模式
        if args.ai:
            try:
                _run_ai_mode()
            except KeyboardInterrupt:
                print("\n  👋 再见！")
            return

        has_command = any([
            args.list_logs, args.sample, args.parse, args.batch_parse,
            args.diagnose, args.regex, args.qa, args.train,
        ])

        if has_command or args.log_file:
            run_command(args)
            return

    # 交互模式（无参数或终端交互）
    try:
        _run_interactive_mode()
    except KeyboardInterrupt:
        print("\n\n  👋 再见！")
    except EOFError:
        print("\n  👋 再见！")


if __name__ == "__main__":
    main()
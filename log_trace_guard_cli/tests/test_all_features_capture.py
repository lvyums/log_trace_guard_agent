#!/usr/bin/env python3
"""测试所有 CLI 功能并捕获终端输出，生成 Markdown 展示文档。"""

import io
import sys
import os
import json
import contextlib
from pathlib import Path

# 确保项目根目录在路径中
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from log_guard.core.log_reader import LogReader
from log_guard.modules.log_parse import LogParseService
from log_guard.modules.script_gen import ScriptGenService
from log_guard.modules.compliance import ComplianceService
from log_guard.modules.log_correlate import LogCorrelateService
from log_guard.common.utils import Result

# 实例化服务
log_reader = LogReader()
log_parse_svc = LogParseService()
script_gen_svc = ScriptGenService()
compliance_svc = ComplianceService()
log_correlate_svc = LogCorrelateService()

TEST_LOG = str(PROJECT_ROOT / "tests" / "sample_logs" / "test_all_features.log")

def capture(fn, *args, **kwargs):
    """执行函数并捕获 stdout 输出，返回 (result, output_string)。"""
    buf = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = buf
    try:
        result = fn(*args, **kwargs)
    except Exception as e:
        result = {"error": str(e)}
    finally:
        sys.stdout = old_stdout
    return result, buf.getvalue()


def section(title):
    return f"\n{'='*60}\n  {title}\n{'='*60}\n"


# ═══════════════════════════════════════════════
# 1. 日志文件加载
# ═══════════════════════════════════════════════
print(section("📂 功能1: 日志文件加载与预览"))

result = log_reader.read_log(TEST_LOG, line_limit=5)
print(f"  日志文件: {os.path.basename(TEST_LOG)}")
print(f"  编码: {result['encoding']}")
print(f"  总行数: {result['total_lines']}")
print(f"  文件大小: {result['file_size']} bytes")
print(f"\n  预览前5行:")
for i, line in enumerate(result["lines"], 1):
    print(f"    {i:3d} | {line.rstrip()[:100]}")

fmt = log_reader.detect_log_format(result["lines"])
print(f"\n  格式检测: {fmt}")


# ═══════════════════════════════════════════════
# 2. 单条日志解析 — SSH
# ═══════════════════════════════════════════════
print(section("🔍 功能2: 单条日志解析 (SSH)"))

ssh_line = "Jul 21 03:14:22 web-server-01 sshd[28412]: Failed password for root from 192.168.1.100 port 38291 ssh2"
r = log_parse_svc.parse_log(ssh_line)
d = r.get("data", {})
risk = log_parse_svc.assess_risk(d)
rd = risk.get("data", {})

print(f"  输入: {ssh_line}")
print(f"  类型: {d.get('device_type')}")
print(f"  时间: {d.get('timestamp')}")
print(f"  源IP: {d.get('src_ip')}")
print(f"  用户: {d.get('user')}")
print(f"  状态: {d.get('status')}")
print(f"  风险: {rd.get('risk_level')} — {rd.get('risk_desc')}")


# ═══════════════════════════════════════════════
# 3. 单条日志解析 — Web
# ═══════════════════════════════════════════════
print(section("🔍 功能3: 单条日志解析 (Web)"))

web_line = '21/Jul/2026:10:23:46 +0800 "GET /admin.php?cmd=system(\'id\') HTTP/1.1" 403 512 "Mozilla/5.0" 10.10.10.1'
r = log_parse_svc.parse_log(web_line)
d = r.get("data", {})
risk = log_parse_svc.assess_risk(d)
rd = risk.get("data", {})

print(f"  输入: {web_line[:80]}...")
print(f"  类型: {d.get('device_type')}")
print(f"  时间: {d.get('timestamp')}")
print(f"  源IP: {d.get('src_ip')}")
print(f"  URL:  {d.get('command')}")
print(f"  状态: {d.get('status')}")
print(f"  风险: {rd.get('risk_level')} — {rd.get('risk_desc')}")


# ═══════════════════════════════════════════════
# 4. 单条日志解析 — WAF
# ═══════════════════════════════════════════════
print(section("🔍 功能4: 单条日志解析 (WAF)"))

waf_line = 'Jul 21 10:30:01 waf-primary modsecurity: [error] [client 10.10.10.1] SQL Injection detected [id 200001] [severity CRITICAL] [uri /api/search]'
r = log_parse_svc.parse_log(waf_line)
d = r.get("data", {})
risk = log_parse_svc.assess_risk(d)
rd = risk.get("data", {})

print(f"  输入: {waf_line[:80]}...")
print(f"  类型: {d.get('device_type')}")
print(f"  时间: {d.get('timestamp')}")
print(f"  源IP: {d.get('src_ip')}")
print(f"  状态: {d.get('status')}")
print(f"  附加: {d.get('extra_info')}")
print(f"  风险: {rd.get('risk_level')} — {rd.get('risk_desc')}")


# ═══════════════════════════════════════════════
# 5. 单条日志解析 — Firewall
# ═══════════════════════════════════════════════
print(section("🔍 功能5: 单条日志解析 (Firewall)"))

fw_line = 'Jul 21 15:00:01 firewall-01 kernel: [UFW BLOCK] IN=eth0 OUT= SRC=45.33.32.156 DST=192.168.1.10 PROTO=TCP SPT=44444 DPT=22 LEN=60'
r = log_parse_svc.parse_log(fw_line)
d = r.get("data", {})

print(f"  输入: {fw_line[:80]}...")
print(f"  类型: {d.get('device_type')}")
print(f"  时间: {d.get('timestamp')}")
print(f"  源IP: {d.get('src_ip')}")
print(f"  目的IP: {d.get('dst_ip')}")
print(f"  状态: {d.get('status')}")
print(f"  附加: {d.get('extra_info')}")


# ═══════════════════════════════════════════════
# 6. 单条日志解析 — Database
# ═══════════════════════════════════════════════
print(section("🔍 功能6: 单条日志解析 (Database)"))

db_line = "2026-07-21T16:00:10.000000+08:00 13 Query SELECT * FROM users WHERE username='admin' AND password='test123'"
r = log_parse_svc.parse_log(db_line)
d = r.get("data", {})

print(f"  输入: {db_line[:80]}...")
print(f"  类型: {d.get('device_type')}")
print(f"  时间: {d.get('timestamp')}")
print(f"  状态: {d.get('status')}")
print(f"  命令: {d.get('command')}")
print(f"  附加: {d.get('extra_info')}")


# ═══════════════════════════════════════════════
# 7. 批量解析 + 风险研判
# ═══════════════════════════════════════════════
print(section("🔍 功能7: 批量解析 + 风险研判"))

result = log_reader.read_log(TEST_LOG, line_limit=50, grep="sshd|Failed password")
lines = result.get("lines", [])
print(f"  过滤关键词: sshd|Failed password")
print(f"  匹配行数: {len(lines)}")

batch = log_parse_svc.batch_parse(lines, do_assess=True)
print(f"\n  批量解析结果:")
print(f"    总计: {batch['total']} 条")
print(f"    成功: {batch['success_count']} 条")
print(f"    失败: {batch['fail_count']} 条")
risk_summary = batch.get("risk_summary", {})
print(f"    高风险: {risk_summary.get('high_risk_count', 0)} 条")
print(f"    中风险: {risk_summary.get('medium_risk_count', 0)} 条")
print(f"    低风险: {risk_summary.get('low_risk_count', 0)} 条")
print(f"    噪音: {risk_summary.get('noise_count', 0)} 条")

high_risk = [i for i in batch.get("items", []) if i.get("risk_assessment", {}).get("risk_level", "").startswith(("P0", "P1"))]
if high_risk:
    print(f"\n  高风险日志:")
    for item in high_risk[:3]:
        risk = item.get("risk_assessment", {})
        print(f"    [{risk.get('risk_level')}] {item.get('raw_log', '')[:70]}")


# ═══════════════════════════════════════════════
# 8. 正则规则生成
# ═══════════════════════════════════════════════
print(section("📝 功能8: 正则规则生成"))

r = script_gen_svc.generate_regex(
    scenario="SSH暴力破解检测 - 连续多次Failed password",
    log_sample="Jul 21 03:14:22 sshd: Failed password for root from 192.168.1.100 port 38291 ssh2",
    device_type="ssh"
)
d = r.get("data", {})
print(f"  场景: {d.get('scenario', '?')}")
print(f"  生成规则数: {len(d.get('regexes', []))}")
for i, reg in enumerate(d.get("regexes", []), 1):
    print(f"\n  [{i}] {reg.get('name', '?')} (优先级: {reg.get('priority', '?')})")
    print(f"      描述: {reg.get('description', '?')}")
    print(f"      正则: {reg.get('pattern', '?')}")
    print(f"      示例: {reg.get('match_example', '?')}")


# ═══════════════════════════════════════════════
# 9. ES 查询生成
# ═══════════════════════════════════════════════
print(section("📝 功能9: ES查询生成"))

r = script_gen_svc.generate_es_query(
    search_scenario="查询最近24小时内所有SSH登录失败事件",
    index_pattern="logstash-ssh-*",
    time_range="last_24h"
)
d = r.get("data", {})
print(f"  索引模式: {d.get('index_pattern', '?')}")
print(f"  时间范围: {d.get('time_range', '?')}")
print(f"  说明: {d.get('note', '?')}")
print(f"\n  查询语句:")
query = d.get("query", {})
print(json.dumps(query, ensure_ascii=False, indent=4))


# ═══════════════════════════════════════════════
# 10. 脚本优化
# ═══════════════════════════════════════════════
print(section("📝 功能10: 脚本优化"))

r = script_gen_svc.optimize_script(
    script=".*Failed password.*",
    script_type="regex",
    scenario="SSH暴力破解检测"
)
d = r.get("data", {})
print(f"  原始脚本: .*Failed password.*")
print(f"  评分: {d.get('score', '?')}/100")
issues = d.get("issues", [])
if issues:
    print(f"  发现问题:")
    for issue in issues:
        print(f"    • {issue}")
suggestions = d.get("suggestions", [])
if suggestions:
    print(f"  优化建议:")
    for s in suggestions:
        print(f"    • {s}")
optimized = d.get("optimized_script", "")
if optimized:
    print(f"  优化后: {optimized}")


# ═══════════════════════════════════════════════
# 11. 合规基线生成
# ═══════════════════════════════════════════════
print(section("📋 功能11: 合规基线生成"))

r = compliance_svc.generate_baseline(
    asset_count=50,
    business_type="enterprise",
    device_types=["firewall", "switch", "server"],
    industry="finance"
)
d = r.get("data", {})
baselines = d.get("baselines", [])
summary = d.get("summary", {})
print(f"  生成基线数: {len(baselines)}")
print(f"  严重度分布: {summary.get('severity_distribution', {})}")
for i, b in enumerate(baselines[:5], 1):
    sev = b.get("severity", "?")
    icon = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}.get(sev, "⚪")
    print(f"\n  {icon} [{b.get('baseline_id', '?')}] {b.get('name', '?')}")
    print(f"     分类: {b.get('category', '?')} | 严重度: {sev}")
    print(f"     描述: {b.get('description', '?')}")
if len(baselines) > 5:
    print(f"\n  ... 还有 {len(baselines)-5} 条基线")


# ═══════════════════════════════════════════════
# 12. 合规自查
# ═══════════════════════════════════════════════
print(section("📋 功能12: 合规自查"))

r = compliance_svc.compliance_check(
    log_retention_days=3,
    has_backup=True,
    has_tamper_proof=True,
    device_count=19
)
d = r.get("data", {})
overall = "✅ 合规" if d.get("overall_compliance") else "❌ 不合规"
print(f"  结论: {overall}")
print(f"  总检查项: {d.get('total', '?')}")
print(f"  通过: {d.get('passed', '?')} | 未通过: {d.get('failed', '?')}")
print(f"  合规率: {d.get('compliance_percentage', '?')}%")

items = d.get("items", [])
severity_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}
for item in items:
    status = "✅" if item.get("status") == "pass" else "❌"
    icon = severity_icon.get(item.get("severity", ""), "⚪")
    print(f"  {status} {icon} {item.get('requirement', '?')}")
    if item.get("status") != "pass":
        print(f"      建议: {item.get('suggestion', '')}")


# ═══════════════════════════════════════════════
# 13. 攻击溯源
# ═══════════════════════════════════════════════
print(section("📝 功能13: 攻击溯源"))

result = log_reader.read_log(TEST_LOG, line_limit=30, grep="sshd|Failed password|sudo")
logs = result.get("lines", [])
r = script_gen_svc.trace_attack(logs, attack_type="ssh_bruteforce")
d = r.get("data", {})
print(f"  攻击类型: {d.get('attack_type', '?')}")
print(f"  溯源结果: {d.get('summary', d.get('description', '?'))}")
indicators = d.get("indicators", d.get("evidence", []))
if indicators:
    print(f"  关键指标:")
    for ind in indicators[:5]:
        if isinstance(ind, dict):
            print(f"    • {ind.get('description', ind.get('indicator', '?'))}")
        else:
            print(f"    • {ind}")


# ═══════════════════════════════════════════════
# 14. 联合日志审查
# ═══════════════════════════════════════════════
print(section("🔄 功能14: 联合日志审查"))

result = log_reader.read_log(TEST_LOG, line_limit=50)
lines = result.get("lines", [])
r = log_correlate_svc.correlate_logs(lines, time_window_minutes=5, detailed=True)
d = r.get("data", {})

print(f"  解析事件: {d.get('total_events', 0)}")
print(f"  设备类型: {', '.join(d.get('device_types', []))}")
entities = d.get("entities", [])
print(f"  涉及实体: {', '.join(entities[:10])}{'...' if len(entities)>10 else ''}")
chains = d.get("chains", [])
print(f"  攻击链数: {len(chains)}")
print(f"  分析摘要: {d.get('summary', '')}")

for i, c in enumerate(chains, 1):
    risk_icon = {"P0": "🔴", "P1": "🟠", "P2": "🟡", "P3": "⚪"}
    icon = "🔴"
    for prefix, emoji in risk_icon.items():
        if c.get("risk_level", "").startswith(prefix):
            icon = emoji
            break
    print(f"\n  {icon} [{i}] {c.get('chain_name', '?')}")
    print(f"     置信度: {c.get('confidence', 0):.0%}")
    print(f"     风险等级: {c.get('risk_level', '?')}")
    print(f"     关联实体: {c.get('entity_key', '?')}")
    print(f"     匹配阶段: {' → '.join(c.get('matched_stages', []))}")
    suggestion = c.get("suggestion", "")
    if suggestion:
        print(f"     处置建议: {suggestion}")


# ═══════════════════════════════════════════════
# 完成
# ═══════════════════════════════════════════════
print(section("✅ 全部 14 项功能测试完成"))

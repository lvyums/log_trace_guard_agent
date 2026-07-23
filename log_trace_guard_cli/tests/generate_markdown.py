#!/usr/bin/env python3
"""从 CLI 输出生成 Markdown 展示文档。"""
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
output_file = PROJECT_ROOT / "tests" / "sample_logs" / "cli_demo_output.txt"
md_file = PROJECT_ROOT / "tests" / "sample_logs" / "cli全功能展示.md"

output = output_file.read_text(encoding="utf-8")

# Parse output by section headers
# Format: "============================================================\n  Title\n============================================================"
lines = output.split("\n")
sections = []
i = 0
while i < len(lines):
    line = lines[i]
    if line.strip() == "=" * 60:
        # Next line is title
        if i + 2 < len(lines) and lines[i + 2].strip() == "=" * 60:
            title = lines[i + 1].strip()
            # Collect content until next separator
            content_lines = []
            i += 3  # skip title + second separator
            while i < len(lines):
                if lines[i].strip() == "=" * 60:
                    break
                content_lines.append(lines[i])
                i += 1
            content = "\n".join(content_lines).strip()
            sections.append((title, content))
            continue
    i += 1

# Build markdown
md = """# 日志溯源卫士 CLI 全功能展示

> 测试日志文件: `tests/sample_logs/test_all_features.log`
> 测试日期: 2026-07-23
> 覆盖: 6 种解析器 (SSH/Web/WAF/Firewall/DB/Generic) x 4 个风险等级 (P0-P3)

---

## 功能菜单总览

```
╔══════════════════════════════════════════════════════╗
║       🔍 日志溯源卫士 CLI 智能体 v2.0               ║
║       菜单操作 + AI 智能对话 · 双模式兼容            ║
╚══════════════════════════════════════════════════════╝

  [1] 📂 选择日志文件
  [2] 🔍 日志解析
  [3] 📡 日志采集
  [4] 📝 脚本生成
  [5] 📋 合规审计
  [6] 🎓 攻防实训
  [7] 🔄 联合日志审查
  [8] 🤖 AI 智能对话
  [9] 🚪 退出
```

---

## 测试日志文件

测试日志 `test_all_features.log` 包含 **6 种日志格式** 的 **122 行**真实样本：

| 解析器 | 日志格式示例 | 样本数 |
|--------|-------------|--------|
| SSH | `sshd[pid]: Failed password for root from ...` | 14 条 |
| Web | `21/Jul/2026:10:23:45 "GET /wp-admin HTTP/1.1" 200` | 14 条 |
| WAF | `modsecurity: [error] [client ...] SQL Injection detected` | 6 条 |
| Firewall | `[UFW BLOCK] IN=eth0 SRC=45.33.32.156 DST=...` | 7 条 |
| DB | `Query SELECT * FROM users WHERE ...` | 7 条 |
| Generic | `[2026-07-21 18:00:00] [INFO] Application started` | 12 条 |

风险覆盖: P0_高危(8条) / P1_中危(10条) / P2_低危(1条) / P3_噪音(41条)

---

## 功能展示

"""

desc_map = {
    "功能1": "加载测试日志文件，自动检测编码、格式，预览内容",
    "功能2": "识别 SSH 日志类型，提取源IP/用户/状态，评估风险等级",
    "功能3": "识别 Web 日志类型，提取URL/状态码/源IP，评估风险等级",
    "功能4": "识别 WAF 日志类型，提取攻击类型/规则ID，评估风险等级",
    "功能5": "识别防火墙日志类型，提取源/目的IP/协议/端口",
    "功能6": "识别数据库日志类型，提取SQL语句/连接信息",
    "功能7": "批量解析多条日志，统计风险分布，标记高风险项",
    "功能8": "根据攻防场景描述自动生成正则检测规则",
    "功能9": "根据检索场景生成 Elasticsearch 查询语句",
    "功能10": "分析现有正则/ES查询的质量并给出优化建议",
    "功能11": "根据资产情况生成安全合规检查基线",
    "功能12": "对照合规标准逐项检查配置合规性",
    "功能13": "分析日志中的攻击链路，定位攻击者行为",
    "功能14": "跨源日志关联分析，检测攻击链和异常模式",
    "功能15": "下发攻防实训任务，支持多种攻击场景分类",
    "功能16": "生成学员实训成绩报告和任务详情",
}

for title, content in sections:
    if not title:
        continue

    desc = ""
    for key, val in desc_map.items():
        if key in title:
            desc = val
            break

    md += f"### {title}\n\n"
    if desc:
        md += f"> {desc}\n\n"
    md += f"```\n{content}\n```\n\n---\n\n"

md_file.write_text(md, encoding="utf-8")
print(f"Generated: {md_file}")
print(f"  Sections: {len(sections)}")
print(f"  Size: {len(md)} chars")

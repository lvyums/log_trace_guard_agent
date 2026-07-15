"""模块五：原理讲解与复盘机制 — 纠错后自动输出错误原因、正确标准、底层攻防原理"""

from typing import Optional


class ErrorAnalysis:
    """错误分析与复盘 — 根据校验结果生成原理讲解"""

    # 攻防场景原理库
    ATTACK_PRINCIPLES = {
        "ssh_brute": {
            "name": "SSH暴力破解",
            "principle": (
                "SSH暴力破解是攻击者通过自动化工具（如Hydra、Medusa）尝试大量用户名/密码组合，"
                "试图获得服务器SSH登录权限的攻击方式。"
            ),
            "defense": (
                "1. 禁用root密码登录，使用密钥认证\n"
                "2. 配置fail2ban自动封禁频繁失败IP\n"
                "3. 修改SSH默认端口（22→高位端口）\n"
                "4. 启用MFA多因素认证"
            ),
            "detection": (
                "检测特征：同一源IP短时间内多次Failed password记录、"
                "尝试多个用户名、登录间隔均匀（自动化工具特征）"
            ),
        },
        "sql_injection": {
            "name": "SQL注入攻击",
            "principle": (
                "SQL注入是攻击者通过在输入参数中插入SQL语句，欺骗后端数据库执行非授权查询的攻击方式。"
                "核心原理：应用程序未对用户输入进行充分过滤，直接将输入拼接到SQL语句中。"
            ),
            "defense": (
                "1. 使用参数化查询（PreparedStatement）\n"
                "2. 输入验证和过滤（白名单策略）\n"
                "3. 最小权限原则（数据库账户仅授予必要权限）\n"
                "4. 部署WAF（Web应用防火墙）"
            ),
            "detection": (
                "检测特征：URL参数含单引号/OR/UNION SELECT/--等SQL关键词、"
                "返回500错误后返回异常数据、参数编码异常"
            ),
        },
        "lateral_movement": {
            "name": "横向移动攻击",
            "principle": (
                "横向移动是攻击者在获得初始入口后，在内网中横向跳跃、扩大战果的攻击技术。"
                "常见手法：Pass-the-Hash、SMB远程执行、PsExec、WMI远程执行、RDP横向。"
            ),
            "defense": (
                "1. 网络分段（VLAN隔离、微隔离）\n"
                "2. 最小权限管理（限制管理员账号使用）\n"
                "3. 启用Windows Defender Credential Guard\n"
                "4. 部署EDR/NDR检测横向移动行为"
            ),
            "detection": (
                "检测特征：异常的内网扫描行为、非预期的SMB连接、"
                "管理员账号在非管理设备上登录、异常的远程服务创建"
            ),
        },
        "webshell": {
            "name": "WebShell上传与利用",
            "principle": (
                "WebShell是攻击者上传到Web服务器的恶意脚本文件，"
                "通过Web请求即可执行系统命令，实现远程控制。"
                "常见形式：一句话木马（如<?php @eval($_POST['cmd']);?>）、大马。"
            ),
            "defense": (
                "1. 严格文件上传验证（类型/大小/内容检查）\n"
                "2. 上传目录禁止执行权限\n"
                "3. 部署WebShell检测工具（如D盾、河马）\n"
                "4. 定期扫描Web目录异常文件"
            ),
            "detection": (
                "检测特征：上传目录出现新文件、异常文件扩展名（.php/.jsp/.asp）、"
                "文件包含`eval`/`system`/`exec`等危险函数"
            ),
        },
        "c2_communication": {
            "name": "C2通信（命令与控制）",
            "principle": (
                "C2通信是被攻陷的资产与攻击者控制服务器之间的通信信道。"
                "常见协议：HTTP/HTTPS伪装、DNS隧道、ICMP隧道、WebSocket。"
            ),
            "defense": (
                "1. 严格出站访问控制（仅允许白名单域名/IP）\n"
                "2. 部署DNS安全检测（检测DNS隧道）\n"
                "3. 启用TLS解密（SSL Inspection）\n"
                "4. 部署NDR网络检测与响应系统"
            ),
            "detection": (
                "检测特征：固定时间间隔的外联行为、异常域名（高随机性/DDNS）、"
                "非标准端口加密通信、大流量外发"
            ),
        },
    }

    # 合规场景原理库
    COMPLIANCE_PRINCIPLES = {
        "log_retention": {
            "name": "日志留存合规",
            "principle": (
                "等保2.0三级要求日志留存不少于6个月（180天），"
                "这是为了确保在安全事件发生后能够追溯历史记录。"
            ),
            "practice": "配置日志轮转策略，确保日志文件按时间/大小自动归档，并设置保留周期为180天以上",
        },
        "log_tamper_proof": {
            "name": "日志防篡改",
            "principle": (
                "日志防篡改是确保日志记录的法律效力的关键机制，"
                "防止攻击者在入侵后清理、篡改日志以掩盖痕迹。"
            ),
            "practice": "使用WORM存储、区块链存证、日志签名、Syslog远程实时备份等方式",
        },
    }

    # 字段提取原理
    FIELD_EXTRACTION_PRINCIPLES = {
        "regex": {
            "name": "正则表达式日志提取",
            "principle": (
                "正则表达式是日志分析的核心工具，通过模式匹配从非结构化日志中提取结构化字段。"
            ),
            "practice": "使用命名捕获组(?P<name>)提高可读性，注意转义特殊字符，先确定日志格式再编写正则",
        },
        "es_query": {
            "name": "Elasticsearch查询",
            "principle": (
                "ES Query DSL是Elasticsearch的结构化查询语言，基于JSON格式，"
                "支持全文搜索、精确匹配、范围查询、聚合分析等多种查询方式。"
            ),
            "practice": "使用bool查询组合多个条件，term精确匹配，match全文搜索，range范围过滤",
        },
    }

    @classmethod
    def analyze(cls, task_type: str, submit_type: str,
                task_title: str, checks: list,
                score: int, grade: str) -> str:
        """生成原理讲解与复盘内容"""
        parts = []

        # 1. 总体评价
        if grade == "A":
            parts.append("✅ 作答优秀！答案完全正确。")
        elif grade == "B":
            parts.append("⚠️ 作答基本正确，但存在可优化之处。")
        else:
            parts.append("❌ 作答需要改进，部分关键要素缺失或错误。")

        # 2. 错误点定位
        incorrect = [c for c in checks if c["status"] == "incorrect"]
        partial = [c for c in checks if c["status"] == "partial"]

        if incorrect:
            parts.append(f"\n📍 错误定位（{len(incorrect)}处）：")
            for c in incorrect:
                parts.append(f"  • 字段「{c['field']}」：{c['detail']}")

        if partial:
            parts.append(f"\n🔍 优化建议（{len(partial)}处）：")
            for c in partial:
                parts.append(f"  • 字段「{c['field']}」：{c['detail']}")

        # 3. 底层原理讲解
        principle = cls._get_principle(task_title, task_type)
        if principle:
            parts.append(f"\n📖 底层原理 — {principle['name']}：")
            parts.append(f"  {principle['principle']}")

        # 4. 防御/最佳实践
        practice = cls._get_practice(task_title, task_type)
        if practice:
            parts.append(f"\n🛡️ 最佳实践：")
            parts.append(f"  {practice}")

        # 5. 岗位实操要点
        operation = cls._get_operation(task_title, task_type)
        if operation:
            parts.append(f"\n💼 岗位实操要点：")
            parts.append(f"  {operation}")

        # 6. 提升方向
        if grade == "C":
            parts.append(f"\n📈 提升建议：")
            parts.append("  • 建议重新学习相关知识点后再次作答")
            parts.append("  • 参考题目中的hint提示")
            parts.append("  • 关注关键字段的完整性和准确性")

        return "\n".join(parts)

    @classmethod
    def _get_principle(cls, title: str, task_type: str) -> Optional[dict]:
        """根据任务标题和类型获取对应原理"""
        title_lower = title.lower()

        if "ssh" in title_lower or "爆破" in title_lower or "暴力" in title_lower:
            return cls.ATTACK_PRINCIPLES.get("ssh_brute")
        if "sql" in title_lower or "注入" in title_lower:
            return cls.ATTACK_PRINCIPLES.get("sql_injection")
        if "横向" in title_lower or "内网" in title_lower or "渗透" in title_lower:
            return cls.ATTACK_PRINCIPLES.get("lateral_movement")
        if "webshell" in title_lower or "上传" in title_lower or "shell" in title_lower:
            return cls.ATTACK_PRINCIPLES.get("webshell")
        if "c2" in title_lower or "外联" in title_lower or "通信" in title_lower:
            return cls.ATTACK_PRINCIPLES.get("c2_communication")
        if "留存" in title_lower or "存储" in title_lower:
            return cls.COMPLIANCE_PRINCIPLES.get("log_retention")
        if "防篡改" in title_lower:
            return cls.COMPLIANCE_PRINCIPLES.get("log_tamper_proof")
        if "正则" in title_lower or "提取" in title_lower:
            return cls.FIELD_EXTRACTION_PRINCIPLES.get("regex")
        if "es" in title_lower or "检索" in title_lower or "query" in title_lower:
            return cls.FIELD_EXTRACTION_PRINCIPLES.get("es_query")
        return None

    @classmethod
    def _get_practice(cls, title: str, task_type: str) -> Optional[str]:
        """获取最佳实践"""
        title_lower = title.lower()
        mapping = {
            "ssh": "企业应配置SSH密钥认证、fail2ban、堡垒机，实现登录行为全审计。",
            "sql": "开发阶段应使用ORM框架或参数化查询，上线前进行渗透测试和代码审计。",
            "正则": "使用在线正则工具（如regex101.com）调试，先在小样本上验证再批量使用。",
            "采集": "推荐使用Filebeat/Logstash/Elasticsearch标准化采集栈，统一日志格式。",
            "合规": "建立合规基线后，应定期（每季度）进行合规自查，确保持续符合标准。",
        }
        for keyword, practice in mapping.items():
            if keyword in title_lower:
                return practice
        return None

    @classmethod
    def _get_operation(cls, title: str, task_type: str) -> Optional[str]:
        """获取岗位实操要点"""
        title_lower = title.lower()
        mapping = {
            "ssh": "运维人员应定期检查SSH登录日志，关注异常IP和失败登录。",
            "sql": "安全运维人员应掌握WAF规则配置，了解常见SQL注入绕过技术。",
            "正则": "日志分析工程师应建立常用正则模板库，提高日常分析效率。",
            "采集": "系统管理员应熟悉主流日志采集工具（rsyslog、Filebeat、Logstash）的配置。",
            "溯源": "安全分析师应掌握多源日志关联分析方法，按时间线还原攻击链路。",
            "合规": "合规审计人员应跟踪最新法规动态，定期更新合规检查清单。",
        }
        for keyword, op in mapping.items():
            if keyword in title_lower:
                return op
        return None
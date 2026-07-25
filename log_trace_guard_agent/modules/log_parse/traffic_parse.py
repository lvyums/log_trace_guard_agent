"""网络流量 CSV 解析器 — 支持 Wireshark / tcpdump / 通用 CSV 导出格式"""

import csv
import io
import re

from modules.log_parse.base_parser import BaseParser, ParsedLogFields


class TrafficParser(BaseParser):
    """网络流量 CSV 解析器"""

    device_type = "traffic"

    # 常见 CSV 列名映射
    _COL_ALIASES = {
        "no": None, "no.": None, "number": None, "#": None,
        "time": "timestamp", "timestamp": "timestamp", "datetime": "timestamp",
        "src": "src_ip", "source": "src_ip", "src_ip": "src_ip", "ip.src": "src_ip",
        "dst": "dst_ip", "destination": "dst_ip", "dst_ip": "dst_ip", "ip.dst": "dst_ip",
        "src_port": "src_port", "sport": "src_port", "tcp.srcport": "src_port",
        "dst_port": "dst_port", "dport": "dst_port", "tcp.dstport": "dst_port",
        "protocol": "protocol", "proto": "protocol",
        "length": "length", "len": "length", "size": "length",
        "info": "info", "info+": "info",
        "flags": "flags",
    }

    # IP 正则
    _IP_RE = re.compile(
        r"\b(?:\d{1,3}\.){3}\d{1,3}\b"
    )

    # 常见协议关键字
    _PROTOCOLS = {
        "tcp", "udp", "icmp", "arp", "dns", "http", "https", "ftp", "ssh",
        "smtp", "pop3", "imap", "ssl", "tls", "quic", "igmp", "icmpv6",
    }

    def can_parse(self, log_line: str) -> bool:
        """检测是否为 CSV 流量行（含 IP 地址 + 协议/端口信息）"""
        stripped = log_line.strip()
        if not stripped:
            return False

        # 跳过 CSV header 行
        lower = stripped.lower()
        if any(kw in lower for kw in ("no.,time", "no., timestamp", "source,destination", "src,dst")):
            return False

        # 必须包含至少一个 IP 地址
        if not self._IP_RE.search(stripped):
            return False

        # 包含协议关键字或端口号
        has_protocol = any(p in lower for p in self._PROTOCOLS)
        has_port = bool(re.search(r":\d{2,5}\b", stripped))
        has_comma = "," in stripped

        # CSV 行：有逗号 + IP + (协议 or 端口)
        return has_comma and (has_protocol or has_port)

    def parse_fields(self, log_line: str) -> ParsedLogFields:
        """解析 CSV 流量行"""
        stripped = log_line.strip()
        result = ParsedLogFields(
            device_type="traffic",
            raw_log=stripped[:500],
        )

        # 尝试 CSV 解析
        try:
            reader = csv.reader(io.StringIO(stripped))
            cells = [c.strip() for c in next(reader)]
        except Exception:
            cells = [c.strip() for c in stripped.split(",")]

        if not cells:
            return self.validate(result)

        # 映射列名（使用 header 推断或默认位置）
        col_map = self._infer_columns(cells)

        # 提取字段
        for idx, val in cells:
            mapped = col_map.get(idx)
            if not val or not mapped:
                continue
            if mapped == "src_ip" and self._IP_RE.fullmatch(val):
                result.src_ip = val
            elif mapped == "dst_ip" and self._IP_RE.fullmatch(val):
                result.dst_ip = val
            elif mapped == "timestamp":
                result.timestamp = val
            elif mapped == "src_port":
                result.src_port = val
            elif mapped == "dst_port":
                result.dst_port = val
            elif mapped == "protocol":
                result.protocol = val.upper()
            elif mapped == "length":
                result.action = val  # 复用 action 字段存 length
            elif mapped == "info":
                result.user_agent = val  # 复用 user_agent 字段存 info
            elif mapped == "flags":
                result.attack_type = val  # 复用 attack_type 字段存 flags

        # 补充：如果没提取到协议，从 Info 字段或值中推断
        if not result.protocol:
            info_text = (result.user_agent or "").lower() + " " + stripped.lower()
            for proto in self._PROTOCOLS:
                if proto in info_text:
                    result.protocol = proto.upper()
                    break

        return self.validate(result)

    def _infer_columns(self, cells: list[str]) -> dict:
        """推断每列的含义，返回 {index: mapped_name}"""
        col_map: dict = {}
        for i, cell in enumerate(cells):
            alias = self._COL_ALIASES.get(cell.lower().strip('"').strip())
            if alias:
                col_map[i] = alias
            elif self._IP_RE.fullmatch(cell):
                # 未映射的列但值是 IP，按顺序推断
                if "src_ip" not in col_map.values():
                    col_map[i] = "src_ip"
                elif "dst_ip" not in col_map.values():
                    col_map[i] = "dst_ip"
            elif cell.isdigit() and 1 <= len(cell) <= 5:
                # 短数字可能是端口
                if "src_port" not in col_map.values():
                    col_map[i] = "src_port"
                elif "dst_port" not in col_map.values():
                    col_map[i] = "dst_port"
            elif cell.upper() in {p.upper() for p in self._PROTOCOLS}:
                col_map[i] = "protocol"
        return col_map

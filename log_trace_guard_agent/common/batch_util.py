"""批量解析工具类 — 解耦可复用的辅助函数"""

import asyncio
from typing import Optional
from collections import Counter
from datetime import datetime

from app.settings import RiskLevel
from common.time_util import parse_log_time
from common.logger import LogManager

logger = LogManager.get_logger()


class BatchStats:
    """批量解析统计信息收集器"""

    def __init__(self):
        self.total = 0
        self.success_count = 0
        self.fail_count = 0
        self.risk_counts = Counter()
        self.device_type_counts = Counter()
        self.src_ip_counts = Counter()
        self.dst_ip_counts = Counter()
        self.user_counts = Counter()
        self.status_counts = Counter()
        self.timestamps: list[datetime] = []
        self.errors: list[str] = []

    def record_success(self, parse_result: dict, risk_result: Optional[dict] = None):
        """记录一条成功解析的结果"""
        self.success_count += 1

        # 设备类型统计
        device_type = parse_result.get("device_type", "unknown")
        self.device_type_counts[device_type] += 1

        # IP 统计
        src_ip = parse_result.get("src_ip")
        if src_ip:
            self.src_ip_counts[src_ip] += 1
        dst_ip = parse_result.get("dst_ip")
        if dst_ip:
            self.dst_ip_counts[dst_ip] += 1

        # 用户统计
        user = parse_result.get("user")
        if user:
            self.user_counts[user] += 1

        # 状态统计
        status = parse_result.get("status")
        if status:
            self.status_counts[status] += 1

        # 时间戳收集
        ts_str = parse_result.get("timestamp")
        if ts_str:
            ts = parse_log_time(ts_str)
            if ts:
                self.timestamps.append(ts)

        # 风险统计
        if risk_result:
            risk_level = risk_result.get("risk_level", "")
            if risk_level:
                self.risk_counts[risk_level] += 1

    def record_fail(self, error: str):
        """记录一条失败的解析"""
        self.fail_count += 1
        self.errors.append(error)

    def get_summary(self, do_assess: bool = False) -> dict:
        """生成汇总报告"""
        summary = {
            "total": self.total,
            "success_count": self.success_count,
            "fail_count": self.fail_count,
        }

        # 设备类型分布
        if self.device_type_counts:
            summary["device_distribution"] = dict(self.device_type_counts.most_common())

        # 源 IP Top 5
        if self.src_ip_counts:
            summary["top_src_ips"] = dict(self.src_ip_counts.most_common(5))

        # 目标 IP Top 5
        if self.dst_ip_counts:
            summary["top_dst_ips"] = dict(self.dst_ip_counts.most_common(5))

        # 用户 Top 5
        if self.user_counts:
            summary["top_users"] = dict(self.user_counts.most_common(5))

        # 状态分布
        if self.status_counts:
            summary["status_distribution"] = dict(self.status_counts.most_common())

        # 时间范围
        if self.timestamps:
            min_ts = min(self.timestamps)
            max_ts = max(self.timestamps)
            summary["time_range"] = {
                "start": min_ts.isoformat() if min_ts else None,
                "end": max_ts.isoformat() if max_ts else None,
            }

        # 风险统计
        if do_assess and self.risk_counts:
            summary["risk_summary"] = dict(self.risk_counts)

        return summary


class BatchProcessor:
    """批量日志处理器 — 支持并发处理"""

    def __init__(self, max_concurrency: int = 10):
        self.max_concurrency = max_concurrency
        self._semaphore = asyncio.Semaphore(max_concurrency)

    async def process_batch(self, logs: list[str], process_func, do_assess: bool = False) -> list[dict]:
        """并发处理一批日志

        Args:
            logs: 日志行列表
            process_func: 异步处理函数，接受 (log_line, do_assess) 返回 (parse_result, risk_result)
            do_assess: 是否进行风险研判

        Returns:
            处理结果列表
        """
        stats = BatchStats()
        stats.total = len(logs)

        async def _process_one(index: int, log_line: str) -> dict:
            """处理单条日志"""
            item = {
                "index": index,
                "log_line": log_line[:100],
                "parse_result": None,
                "risk_result": None,
                "error": None,
            }

            try:
                async with self._semaphore:
                    parse_result, risk_result = await process_func(log_line, do_assess)

                if parse_result is None:
                    item["error"] = "解析失败"
                    stats.record_fail("解析失败")
                else:
                    item["parse_result"] = parse_result
                    if risk_result:
                        item["risk_result"] = risk_result
                    stats.record_success(parse_result, risk_result)

            except Exception as e:
                error_msg = str(e)[:200]
                item["error"] = error_msg
                stats.record_fail(error_msg)
                logger.warning(f"处理第 {index + 1} 条日志失败: {e}")

            return item

        # 并发处理所有日志
        tasks = [_process_one(i, log) for i, log in enumerate(logs)]
        items = await asyncio.gather(*tasks)

        return items, stats


def merge_batch_results(items: list[dict], stats: BatchStats, do_assess: bool = False) -> dict:
    """合并批量解析结果"""
    return {
        "total": stats.total,
        "success_count": stats.success_count,
        "fail_count": stats.fail_count,
        "items": items,
        "summary": stats.get_summary(do_assess),
    }

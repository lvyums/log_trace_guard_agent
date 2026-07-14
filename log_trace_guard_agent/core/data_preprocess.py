"""全局数据预处理底座"""

import re

from common.logger import LogManager

logger = LogManager.get_logger()


class DataPreprocessor:
    """全局数据预处理 — 清洗、去空、格式统一"""

    @classmethod
    def clean(cls, text: str) -> str:
        """去空、去控制字符、统一换行"""
        if not text:
            return ""
        # 去除控制字符
        text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)
        # 统一换行符
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        return text.strip()

    @classmethod
    def normalize(cls, text: str) -> str:
        """格式统一"""
        # 去除 BOM
        if text.startswith("﻿"):
            text = text[1:]
        # 合并多余空行
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()
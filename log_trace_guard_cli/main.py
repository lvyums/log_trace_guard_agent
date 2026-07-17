#!/usr/bin/env python3
"""日志溯源卫士 CLI 智能体 — 从终端直接分析本地日志"""
# -*- coding: utf-8 -*-

import sys
import os

# 项目根目录
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

from log_guard.cli import main

if __name__ == "__main__":
    main()
"""日志溯源卫士 CLI 智能体 — setup.py（兼容旧版 pip）"""
from setuptools import setup, find_packages

setup(
    name="log-guard",
    version="3.0.0",
    description="🔍 日志溯源卫士 CLI 智能体 — 终端日志分析 + AI 智能对话",
    packages=find_packages(include=["log_guard*"]),
    package_data={"log_guard": ["data/rule_data/*.json"]},
    include_package_data=True,
    python_requires=">=3.8",
    install_requires=[
        "requests>=2.25",
    ],
    entry_points={
        "console_scripts": [
            "log-guard=log_guard.cli:main",
        ],
    },
)
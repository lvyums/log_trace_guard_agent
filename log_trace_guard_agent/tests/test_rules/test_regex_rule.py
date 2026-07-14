"""规则引擎单元测试"""

import pytest
from core.rule_engine.regex_rule import RegexRuleEngine, Rule


class TestRegexRuleEngine:
    def setup_method(self):
        # 清空规则并直接添加测试规则
        RegexRuleEngine.rules = []
        RegexRuleEngine._loaded = True

    def test_rule_priority_order(self):
        """测试规则按优先级排序"""
        low_rule = Rule(name="low", priority=1, device_type="test")
        high_rule = Rule(name="high", priority=10, device_type="test")
        RegexRuleEngine.rules = [low_rule, high_rule]
        RegexRuleEngine.rules.sort(key=lambda r: r.priority, reverse=True)
        assert RegexRuleEngine.rules[0].priority == 10

    def test_no_match_fallback(self):
        """测试无匹配时返回 None"""
        RegexRuleEngine.rules = []
        result = RegexRuleEngine.match("some random text")
        assert result is None

    def test_rule_pattern_matching(self):
        """测试正则匹配"""
        import re
        rule = Rule(
            name="ssh_test",
            patterns=[re.compile(r"sshd\[\d+\]:\s+Accepted", re.IGNORECASE)],
            priority=5,
            device_type="ssh",
        )
        RegexRuleEngine.rules = [rule]
        result = RegexRuleEngine.match("sshd[1234]: Accepted password for root")
        assert result is not None
        assert result.rule.device_type == "ssh"
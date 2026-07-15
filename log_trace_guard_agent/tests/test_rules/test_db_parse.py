"""DB 解析器单元测试"""

import pytest
from modules.log_parse.db_parse import DBParser


class TestDBLogParser:
    def setup_method(self):
        self.parser = DBParser()

    def test_db_mysql_general_log(self):
        """MySQL general_log 格式"""
        log = '2023-10-11T14:32:23.000000+08:00  12 Query SELECT * FROM users WHERE id=1'
        assert self.parser.can_parse(log)
        result = self.parser.parse_fields(log)
        assert result.device_type == "db"
        assert result.method == "QUERY"
        assert "SELECT * FROM users" in result.sql_statement
        assert result.is_dangerous is False

    def test_db_mysql_connect(self):
        """MySQL general_log Connect 格式"""
        log = '2023-10-11T14:32:23.000000+08:00  15 Connect root@localhost on mysql'
        assert self.parser.can_parse(log)
        result = self.parser.parse_fields(log)
        assert result.device_type == "db"
        assert result.user == "root"

    def test_db_mysql_dangerous_query(self):
        """MySQL 高危查询"""
        log = '2023-10-11T14:32:24.000000+08:00  18 Query DROP TABLE users'
        assert self.parser.can_parse(log)
        result = self.parser.parse_fields(log)
        assert result.device_type == "db"
        assert result.method == "QUERY"
        assert result.is_dangerous is True

    def test_db_postgresql_connection(self):
        """PostgreSQL 连接日志格式"""
        log = '2023-10-11 14:32:25.000 CST [12345] LOG:  connection received: host=192.168.1.1 user=admin'
        assert self.parser.can_parse(log)
        result = self.parser.parse_fields(log)
        assert result.device_type == "db"
        assert result.src_ip == "192.168.1.1"
        assert result.user == "admin"

    def test_db_mysql_slow_log(self):
        """MySQL slow_log 格式"""
        log = '# Time: 2023-10-11T14:32:23.000000+08:00\n# User@Host: root[root] @ [192.168.1.1]'
        assert self.parser.can_parse(log)
        result = self.parser.parse_fields(log)
        assert result.device_type == "db"
        assert result.user == "root"
        assert result.src_ip == "192.168.1.1"

    def test_db_malformed_input(self, sample_malformed_inputs):
        for log in sample_malformed_inputs:
            assert not self.parser.can_parse(log)

    def test_db_empty_input(self):
        assert not self.parser.can_parse("")
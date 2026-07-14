"""数据库解析器单元测试"""

import pytest
from modules.log_parse.db_parse import DBParser


class TestDBParser:
    def setup_method(self):
        self.parser = DBParser()

    def test_mysql_general_log(self):
        log = '2023-10-11T14:32:23.000000+08:00  12 Query SELECT * FROM users WHERE id=1'
        assert self.parser.can_parse(log)
        result = self.parser.parse_fields(log)
        assert result["device_type"] == "db"
        assert result["method"] == "QUERY"
        assert result["sql_statement"] == "SELECT * FROM users WHERE id=1"
        assert result["is_dangerous"] is False

    def test_mysql_connect(self):
        log = '2023-10-11T14:32:23.000000+08:00  12 Connect root@localhost on mydb'
        assert self.parser.can_parse(log)
        result = self.parser.parse_fields(log)
        assert result["device_type"] == "db"
        assert result["user"] == "root"

    def test_dangerous_sql(self):
        log = '2023-10-11T14:32:23.000000+08:00  12 Query DROP TABLE users'
        assert self.parser.can_parse(log)
        result = self.parser.parse_fields(log)
        assert result["is_dangerous"] is True

    def test_postgresql_log(self):
        log = '2023-10-11 14:32:23.000 CST [12345] LOG:  connection received: host=192.168.1.1 user=admin'
        assert self.parser.can_parse(log)
        result = self.parser.parse_fields(log)
        assert result["device_type"] == "db"
        assert result["src_ip"] == "192.168.1.1"
        assert result["user"] == "admin"

    def test_db_malformed_input(self, sample_malformed_inputs):
        for log in sample_malformed_inputs:
            assert not self.parser.can_parse(log)

    def test_db_empty_input(self):
        assert not self.parser.can_parse("")

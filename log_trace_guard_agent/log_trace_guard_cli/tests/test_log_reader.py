"""Tests for core/log_reader.py"""
import os
import sys
import tempfile
import unittest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from log_guard.core.log_reader import LogReader


class TestLogReader(unittest.TestCase):
    def setUp(self):
        self.reader = LogReader()
        self.temp_dir = tempfile.mkdtemp()

    def _create_log_file(self, name: str, lines: list[str]) -> str:
        path = os.path.join(self.temp_dir, name)
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        return path

    def test_read_log_normal(self):
        path = self._create_log_file("test.log", [
            "Jan 15 10:00:00 server sshd[123]: Failed password for root",
            "Jan 15 10:00:01 server sshd[124]: Accepted password for admin",
            "Jan 15 10:00:02 server sudo: root command",
        ])
        result = self.reader.read_log(path)
        self.assertEqual(result["total_lines"], 3)
        self.assertEqual(result["matched_lines"], 3)
        self.assertEqual(len(result["lines"]), 3)
        self.assertIn("encoding", result)
        self.assertIn("file_size", result)
        self.assertFalse(result["truncated"])

    def test_read_log_with_line_limit(self):
        path = self._create_log_file("test.log", [f"line {i}" for i in range(100)])
        result = self.reader.read_log(path, line_limit=10)
        self.assertEqual(len(result["lines"]), 10)
        self.assertTrue(result["truncated"])
        self.assertEqual(result["total_lines"], 100)

    def test_read_log_with_grep(self):
        path = self._create_log_file("test.log", [
            "sshd: Failed password",
            "sshd: Accepted password",
            "sudo: command",
            "sshd: Failed password",
        ])
        result = self.reader.read_log(path, grep="Failed")
        self.assertEqual(result["matched_lines"], 2)
        self.assertEqual(len(result["lines"]), 2)
        self.assertIn("Failed", result["lines"][0])

    def test_read_log_with_offset(self):
        path = self._create_log_file("test.log", [f"line {i}" for i in range(10)])
        result = self.reader.read_log(path, offset=5, line_limit=10)
        self.assertEqual(len(result["lines"]), 5)
        self.assertEqual(result["lines"][0], "line 5")

    def test_read_log_file_not_found(self):
        result = self.reader.read_log("/nonexistent/path/file.log")
        self.assertIn("error", result)
        self.assertEqual(result["total_lines"], 0)
        self.assertEqual(result["lines"], [])

    def test_read_log_empty_file(self):
        path = self._create_log_file("empty.log", [])
        result = self.reader.read_log(path)
        self.assertEqual(result["total_lines"], 0)
        self.assertEqual(result["lines"], [])

    def test_sample_log(self):
        path = self._create_log_file("test.log", [f"line {i}" for i in range(50)])
        result = self.reader.sample_log(path, n=5)
        self.assertEqual(len(result["lines"]), 5)

    def test_detect_log_format_syslog(self):
        lines = [
            "Jan 15 10:00:00 server sshd[123]: test",
            "Jan 15 10:00:01 server sshd[124]: test2",
        ]
        fmt = self.reader.detect_log_format(lines)
        self.assertEqual(fmt, "syslog")

    def test_detect_log_format_apache(self):
        lines = [
            '192.168.1.1 - - [10/Jan/2024:12:00:00 +0000] "GET /index.html HTTP/1.1" 200 1234',
        ]
        fmt = self.reader.detect_log_format(lines)
        self.assertEqual(fmt, "apache")

    def test_detect_log_format_json(self):
        lines = ['{"event": "test", "timestamp": "2024-01-01T10:00:00Z"}']
        fmt = self.reader.detect_log_format(lines)
        self.assertEqual(fmt, "json")

    def test_detect_log_format_csv(self):
        lines = ["timestamp,event,user,ip", "2024-01-01,login,admin,10.0.0.1"]
        fmt = self.reader.detect_log_format(lines)
        self.assertEqual(fmt, "csv")

    def test_detect_log_format_unknown(self):
        lines = ["some random line without any known format"]
        fmt = self.reader.detect_log_format(lines)
        self.assertEqual(fmt, "unknown")

    def test_detect_log_format_empty_lines(self):
        fmt = self.reader.detect_log_format([])
        self.assertEqual(fmt, "unknown")

    def test_count_by_pattern(self):
        path = self._create_log_file("test.log", [
            "sshd: Failed password",
            "sshd: Accepted password",
            "sudo: command",
            "sshd: Failed password",
        ])
        result = self.reader.count_by_pattern(path, "Failed")
        self.assertEqual(result["matched_lines"], 2)

    def test_count_by_pattern_file_not_found(self):
        result = self.reader.count_by_pattern("/nonexistent", "test")
        self.assertIn("error", result)

    def test_list_log_files_in_directory(self):
        self._create_log_file("auth.log", ["test"])
        self._create_log_file("syslog.log", ["test2"])
        self._create_log_file("readme.txt", ["not a log"])
        files = self.reader.list_log_files(self.temp_dir)
        self.assertGreaterEqual(len(files), 2)
        names = [f["name"] for f in files]
        self.assertIn("auth.log", names)
        self.assertIn("syslog.log", names)

    def test_encoding_detection_utf8(self):
        path = self._create_log_file("utf8.log", ["hello", "world"])
        result = self.reader.read_log(path)
        self.assertEqual(result["encoding"], "utf-8")

    def test_tilde_expansion(self):
        """Test that ~ is expanded in paths."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = os.path.join(tmpdir, "test.log")
            with open(log_file, "w") as f:
                f.write("line1\n")
            home = os.path.expanduser("~")
            rel = log_file.replace(home, "~")
            if rel != log_file:
                result = self.reader.read_log(rel)
                self.assertIn("lines", result)
            else:
                self.skipTest("Home dir is root, cannot test tilde expansion")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
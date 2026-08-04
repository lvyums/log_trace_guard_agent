#!/usr/bin/env python3
"""联调 mock 服务 — Splunk(18089) + Elasticsearch(19200)

用于本地/CI 联调验证,模拟两类日志平台的最小 REST 接口:

Splunk 模拟:
  POST /services/auth/login          → 登录(sessionKey)
  POST /services/search/jobs         → 提交搜索,返回 sid
  GET  /services/search/jobs/{sid}   → 状态(isDone)
  GET  /services/search/jobs/{sid}/results?output_mode=json → 结果

ES 模拟:
  GET  /_cluster/health              → 集群健康
  POST /{index}/_search              → 搜索(回显 DSL,返回固定样例数据)

用法:
  python3 mock_services.py           # 同时启动 Splunk 18089 + ES 19200
  python3 mock_services.py --splunk-only
  python3 mock_services.py --es-only

标准库实现,零第三方依赖。
"""
import json
import re
import sys
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

SPLUNK_PORT = 18089
ES_PORT = 19200

# ── 样例数据 ──────────────────────────────────────────────
SPLUNK_SAMPLE_RESULTS = [
    {"_time": "2026-08-01T10:22:31.000+08:00", "src_ip": "192.168.1.100",
     "user": "root", "event": "Failed password for root from 192.168.1.100 port 22 ssh2"},
    {"_time": "2026-08-01T10:23:05.000+08:00", "src_ip": "192.168.1.100",
     "user": "admin", "event": "Failed password for admin from 192.168.1.100 port 22 ssh2"},
    {"_time": "2026-08-01T10:24:40.000+08:00", "src_ip": "10.0.0.55",
     "user": "root", "event": "Accepted password for root from 10.0.0.55 port 22 ssh2"},
]

ES_SAMPLE_HITS = [
    {"_index": "linux-secure-2026.08", "_id": "1",
     "_source": {"timestamp": "2026-08-01T10:22:31Z", "host": "web01",
                 "src_ip": "192.168.1.100", "message": "Failed password for root from 192.168.1.100 port 22 ssh2"}},
    {"_index": "linux-secure-2026.08", "_id": "2",
     "_source": {"timestamp": "2026-08-01T10:23:05Z", "host": "web01",
                 "src_ip": "192.168.1.100", "message": "Failed password for admin from 192.168.1.100 port 22 ssh2"}},
    {"_index": "linux-secure-2026.08", "_id": "3",
     "_source": {"timestamp": "2026-08-01T10:24:40Z", "host": "web02",
                 "src_ip": "10.0.0.55", "message": "Accepted password for root from 10.0.0.55 port 22 ssh2"}},
]


class _Base(BaseHTTPRequestHandler):
    server_version = "MockService/1.0"

    def log_message(self, fmt, *args):  # 静默访问日志
        pass

    def _send_json(self, obj, status=200):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_text(self, text, status=200):
        body = text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/xml; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self) -> str:
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0:
            return ""
        return self.rfile.read(length).decode("utf-8", errors="replace")


class SplunkHandler(_Base):
    def do_POST(self):
        path = self.path.split("?")[0]

        if path == "/services/auth/login":
            self._send_json({"sessionKey": "mock-session-key-123"})
            return

        if path == "/services/search/jobs":
            body = self._read_body()
            sid = f"mock_sid_{uuid.uuid4().hex[:8]}"
            # 返回 Splunk 风格的 sid(纯文本, 需要客户端 _extract_sid 解析)
            self._send_text(f"<response><sid>{sid}</sid></response>")
            return

        self._send_json({"error": "not found"}, 404)

    def do_GET(self):
        path = self.path.split("?")[0]

        # 状态查询: /services/search/jobs/{sid}
        m = re.match(r"^/services/search/jobs/([^/]+)$", path)
        if m:
            self._send_text(
                '<response><entry><content><dict><key name="isDone">1</key></dict></content></entry></response>'
            )
            return

        # 结果查询: /services/search/jobs/{sid}/results?output_mode=json
        m = re.match(r"^/services/search/jobs/([^/]+)/results$", path)
        if m:
            # Splunk REST 的 JSON 模式返回 {"results": [...]} 包装
            self._send_json({"results": SPLUNK_SAMPLE_RESULTS})
            return

        self._send_json({"error": "not found"}, 404)


class ESHandler(_Base):
    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/":
            self._send_json({"name": "mock-es", "cluster_name": "mock", "version": {"number": "8.11.0"}})
            return
        if path == "/_cluster/health":
            self._send_json({"cluster_name": "mock", "status": "green",
                             "number_of_nodes": 1, "active_shards": 0})
            return
        self._send_json({"error": "not found"}, 404)

    def do_POST(self):
        path = self.path.split("?")[0]
        # /{index}/_search
        m = re.match(r"^/([^/]+)/_search$", path)
        if m:
            self._read_body()  # 丢弃 DSL
            self._send_json({
                "took": 3, "timed_out": False,
                "hits": {"total": {"value": len(ES_SAMPLE_HITS), "relation": "eq"},
                         "max_score": 1.0, "hits": ES_SAMPLE_HITS},
            })
            return
        self._send_json({"error": "not found"}, 404)


def _serve(handler_cls, port: int):
    httpd = ThreadingHTTPServer(("127.0.0.1", port), handler_cls)
    print(f"[mock] {handler_cls.__name__} listening on 127.0.0.1:{port}")
    httpd.serve_forever()


def main():
    splunk_only = "--splunk-only" in sys.argv
    es_only = "--es-only" in sys.argv

    threads = []
    if not es_only:
        threads.append(threading.Thread(target=_serve, args=(SplunkHandler, SPLUNK_PORT), daemon=True))
    if not splunk_only:
        threads.append(threading.Thread(target=_serve, args=(ESHandler, ES_PORT), daemon=True))

    for t in threads:
        t.start()
    print("[mock] all services started. Ctrl+C to stop.")
    try:
        while True:
            import time
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[mock] stopping...")


if __name__ == "__main__":
    main()

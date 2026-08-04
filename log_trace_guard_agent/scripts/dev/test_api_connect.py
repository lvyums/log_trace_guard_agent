#!/usr/bin/env python3
"""API 联调回归 — 验证后端与 mock Splunk/ES 的连通性

覆盖:
  Splunk: 连接测试 / 搜索执行 / 打开 URL / 配置保存(.env 持久化)
  ES:     连接测试 / 搜索执行 / 配置保存
  管理端点: /health /admin/reload /admin/metrics(新增企业级端点)

用法:
  先启动后端(127.0.0.1:8000)与 mock_services.py,然后:
  python3 test_api_connect.py
"""
import json
import sys
import urllib.request

BASE = "http://127.0.0.1:8000"
SPLUNK_CFG = {"base_url": "http://127.0.0.1:18089", "auth_token": "mock-token", "verify_ssl": False}
ES_CFG = {"base_url": "http://127.0.0.1:19200", "username": "elastic", "password": "mock", "verify_ssl": False}

PASS = 0
FAIL = 0
FAILURES = []


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  [PASS] {name}")
    else:
        FAIL += 1
        FAILURES.append(name)
        print(f"  [FAIL] {name} — {detail}")


def call(method, path, body=None):
    url = BASE + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    if body is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode())
        except Exception:
            return e.code, {}
    except Exception as e:
        return 0, {"msg": str(e)}


def main():
    print("═══ API 联调回归 ═══\n")

    # ── 基础 ──
    print("[基础]")
    st, r = call("GET", "/health")
    check("健康检查 /health 200", st == 200 and r.get("data", {}).get("status") == "healthy", f"{st} {r}")

    # ── Splunk ──
    print("\n[Splunk]")
    # 无配置测试必须放在配置保存之前(保存接口写 .env 但不更新内存单例)
    st, r = call("POST", "/api/v1/script-gen/splunk/search", {"spl_query": "search index=x"})
    check("Splunk 无配置返回友好错误", st == 200 and r.get("code") != 0, f"{st} {r.get('msg')}")

    st, r = call("POST", "/api/v1/script-gen/splunk/test", {"splunk_config": SPLUNK_CFG, "spl_query": "search index=linux_secure"})
    check("Splunk 连接测试", st == 200 and r.get("code") == 0, f"{st} {r.get('msg')}")
    check("Splunk 测试返回结果数>0", st == 200 and r.get("data", {}).get("event_count", 0) > 0, str(r.get("data", {}))[:120])

    st, r = call("POST", "/api/v1/script-gen/splunk/search", {"splunk_config": SPLUNK_CFG, "spl_query": "search index=linux_secure"})
    check("Splunk 搜索执行", st == 200 and r.get("code") == 0, f"{st} {r.get('msg')}")
    check("Splunk 搜索结果含事件", st == 200 and len(r.get("data", {}).get("results", [])) > 0, str(r.get("data", {}))[:120])

    st, r = call("POST", "/api/v1/script-gen/splunk/open-url", {"splunk_config": SPLUNK_CFG, "spl_query": "search index=linux_secure"})
    check("Splunk 打开 URL 生成", st == 200 and r.get("code") == 0 and "open_url" in r.get("data", {}), f"{st} {r.get('msg')}")

    st, r = call("POST", "/api/v1/script-gen/splunk/config", {"splunk_base_url": "http://127.0.0.1:18089", "splunk_auth_token": "mock-token"})
    check("Splunk 配置保存(.env)", st == 200 and r.get("code") == 0, f"{st} {r.get('msg')}")

    # ── ES ──
    print("\n[Elasticsearch]")
    dsl = json.dumps({"query": {"match_all": {}}})
    st, r = call("POST", "/api/v1/script-gen/es/search", {"query_dsl": dsl})
    check("ES 无配置返回友好错误", st == 200 and r.get("code") != 0, f"{st} {r.get('msg')}")

    st, r = call("POST", "/api/v1/script-gen/es/test", {"es_config": ES_CFG})
    check("ES 连接测试", st == 200 and r.get("code") == 0, f"{st} {r.get('msg')}")

    st, r = call("POST", "/api/v1/script-gen/es/search", {"es_config": ES_CFG, "query_dsl": dsl, "index_pattern": "linux-secure-*"})
    check("ES 搜索执行", st == 200 and r.get("code") == 0, f"{st} {r.get('msg')}")
    check("ES 搜索结果含命中", st == 200 and r.get("data", {}).get("total", 0) > 0, str(r.get("data", {}))[:120])

    st, r = call("POST", "/api/v1/script-gen/es/config", {"es_base_url": "http://127.0.0.1:19200", "es_username": "elastic", "es_password": "mock"})
    check("ES 配置保存(.env)", st == 200 and r.get("code") == 0, f"{st} {r.get('msg')}")

    st, r = call("POST", "/api/v1/script-gen/es/search", {"es_config": ES_CFG, "query_dsl": "not-json"})
    check("ES 非法 DSL 返回错误", st == 200 and r.get("code") != 0, f"{st} {r.get('msg')}")

    # ── 管理端点(新增企业级) ──
    print("\n[管理端点]")
    st, r = call("POST", "/api/v1/admin/reload")
    check("配置热加载 /admin/reload", st == 200 and r.get("code") == 0, f"{st} {r.get('msg')}")
    check("reload 返回变更字段", "changed_count" in r.get("data", {}), str(r.get("data", {}))[:120])

    st, r = call("GET", "/api/v1/admin/metrics")
    check("指标 /admin/metrics", st == 200 and r.get("code") == 0, f"{st} {r.get('msg')}")
    check("指标含 LLM 统计", "llm" in r.get("data", {}), str(r.get("data", {}))[:120])

    # 恢复 .env(清除测试写入的配置),并 reload 同步内存单例
    call("POST", "/api/v1/script-gen/splunk/config", {"splunk_base_url": "", "splunk_auth_token": ""})
    call("POST", "/api/v1/script-gen/es/config", {"es_base_url": "", "es_username": "", "es_password": ""})
    call("POST", "/api/v1/admin/reload")

    print(f"\n结果: {PASS} 通过, {FAIL} 失败")
    if FAILURES:
        print("失败项:", ", ".join(FAILURES))
        sys.exit(1)
    print("全部通过 ✓")


if __name__ == "__main__":
    main()

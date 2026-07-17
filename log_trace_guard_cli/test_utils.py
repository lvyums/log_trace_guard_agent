"""Quick smoke test for utils.py"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from log_guard.common.utils import (
    Result,
    JsonConfigLoader,
    LogManager,
    clean_syslog_prefix,
    normalize_whitespace,
    is_gibberish,
    extract_ip_from_str,
    truncate,
    DATA_DIR,
)

# --- Result ---
r = Result.ok({"a": 1}, "done")
assert r["code"] == 0, r
assert r["msg"] == "done", r
assert r["data"] == {"a": 1}, r
assert "timestamp" in r, r

r2 = Result.fail("bad", 500)
assert r2["code"] == 500, r2
assert r2["msg"] == "bad", r2
assert r2["data"] == {}, r2

r3 = Result.from_exception(403, "forbidden")
assert r3["code"] == 403
print("Result: OK")

# --- DATA_DIR ---
assert DATA_DIR.endswith("data/rule_data"), f"DATA_DIR={DATA_DIR}"
print(f"DATA_DIR: {DATA_DIR}")

# --- JsonConfigLoader ---
loader = JsonConfigLoader()
loader2 = JsonConfigLoader()
assert loader is loader2, "JsonConfigLoader is not singleton"

cfg = JsonConfigLoader.load("risk_rules.json")
assert isinstance(cfg, dict), f"Expected dict, got {type(cfg)}"
print(f"  risk_rules.json loaded, top-level keys: {list(cfg.keys())[:5]}")

val = JsonConfigLoader.get("risk_rules.json", "nonexistent_key", default="fallback")
assert val == "fallback", f"Expected fallback, got {val}"

JsonConfigLoader.clear_cache()
print("JsonConfigLoader: OK")

# --- str_util ---
assert clean_syslog_prefix("Mar 15 10:30:25 server test") == "test"
assert normalize_whitespace("a   b   c") == "a b c"
assert is_gibberish("") is True
assert is_gibberish("normal text") is False
assert extract_ip_from_str("from 192.168.1.1 request") == "192.168.1.1"
assert extract_ip_from_str("no ip here") is None
assert truncate("hello world", 5) == "hello..."
assert truncate("short", 100) == "short"
print("str_util: OK")

# --- LogManager ---
logger = LogManager.get_logger("test_smoke")
assert logger is not None
LogManager.log_parse_failure("raw line here", context="test line")
print("LogManager: OK")

print("\nALL TESTS PASSED")
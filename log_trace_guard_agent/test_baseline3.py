import sys
sys.path.insert(0, 'E:/Code/code.python/agent/log_trace_guard_agent')

from modules.compliance.baseline_gen import BaselineGenStrategy

strategy = BaselineGenStrategy()

# Test 1: No filters
result1 = strategy.execute({
    "asset_count": 50,
    "business_type": "互联网金融",
    "device_types": [],
    "monitor_scenarios": [],
    "industry": "金融"
})
print(f"Test 1 (no filters): {len(result1['baselines'])} baselines")

# Test 2: Device type only
result2 = strategy.execute({
    "asset_count": 50,
    "business_type": "互联网金融",
    "device_types": ["server"],
    "monitor_scenarios": [],
    "industry": "金融"
})
print(f"Test 2 (server only): {len(result2['baselines'])} baselines")

# Test 3: Device type + monitor scenario
result3 = strategy.execute({
    "asset_count": 50,
    "business_type": "互联网金融",
    "device_types": ["server"],
    "monitor_scenarios": ["异常登录"],
    "industry": "金融"
})
print(f"Test 3 (server + 异常登录): {len(result3['baselines'])} baselines")
for bl in result3['baselines']:
    print(f"  - {bl['baseline_id']}: {bl['name']}")

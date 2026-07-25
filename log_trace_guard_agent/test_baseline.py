import json

with open('E:/Code/code.python/agent/log_trace_guard_agent/data/rule_data/compliance_baselines.json', 'r', encoding='utf-8') as f:
    baselines = json.load(f)

print(f'Total baselines: {len(baselines)}')
for bl in baselines:
    ms = bl['monitor_scenario']
    devices = bl.get('applicable_devices', [])
    print(f"  {bl['baseline_id']}: ms='{ms}' devices={devices}")
    
# Test matching
expanded_keywords = {'异常登录', '异地ip'}
for bl in baselines:
    ms = bl['monitor_scenario']
    ms_lower = ms.lower()
    matches = [kw for kw in expanded_keywords if kw in ms_lower or kw in ms]
    print(f"  Match test '{ms}': {matches}")

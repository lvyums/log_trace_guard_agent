import json

with open('E:/Code/code.python/agent/log_trace_guard_agent/data/rule_data/compliance_baselines.json', 'r', encoding='utf-8') as f:
    baselines = json.load(f)

device_types = ['server']
monitor_scenarios = ['异常登录']

# Step 1: Filter by device type
selected = []
for bl in baselines:
    bl_devices = [d.lower() for d in bl.get('applicable_devices', [])]
    if 'all' in bl_devices:
        selected.append(bl)
    elif any(d.lower() in bl_devices for d in device_types):
        selected.append(bl)

print(f"After device filter: {len(selected)} baselines")
for bl in selected:
    print(f"  {bl['baseline_id']}: {bl['monitor_scenario']}")

# Step 2: Filter by monitor scenario
scenario_keywords = [s.lower() for s in monitor_scenarios]
scenario_map = {
    '入侵': ['异常登录', '端口扫描', '高危命令', '异常外联'],
    '登录': ['异常登录', '异地ip'],
    '扫描': ['端口扫描'],
    '数据库': ['数据库批量'],
    '数据泄露': ['数据库批量', '异常外联'],
    '恶意软件': ['高危命令', '异常外联'],
    '外联': ['异常外联'],
    '日志': ['日志存储'],
    '命令': ['高危命令'],
    '监控': ['监控'],
}

expanded_keywords = set()
for kw in scenario_keywords:
    expanded_keywords.add(kw)
    for map_key, map_values in scenario_map.items():
        if map_key in kw:
            expanded_keywords.update(map_values)

print(f"\nExpanded keywords: {expanded_keywords}")

selected2 = []
for bl in selected:
    ms = bl.get('monitor_scenario', '')
    ms_lower = ms.lower()
    matches = [kw for kw in expanded_keywords if kw in ms_lower or kw in ms]
    if matches:
        selected2.append(bl)
        print(f"  Matched: {bl['baseline_id']} - {ms}")

print(f"\nFinal selected: {len(selected2)} baselines")

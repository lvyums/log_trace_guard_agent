import sys
sys.path.insert(0, 'E:/Code/code.python/agent/log_trace_guard_agent')

# Simulate the exact API flow
from modules.compliance.service import ComplianceService

import asyncio

async def test():
    # Test 1: Without monitor_scenarios
    result1 = await ComplianceService.generate_baseline(
        asset_count=50,
        business_type="互联网金融",
        device_types=["server"],
        monitor_scenarios=None,
        industry="金融",
    )
    print(f"Test 1 (no monitor_scenarios): baselines={len(result1['data']['baselines'])}")

    # Test 2: With monitor_scenarios
    result2 = await ComplianceService.generate_baseline(
        asset_count=50,
        business_type="互联网金融",
        device_types=["server"],
        monitor_scenarios=["异常登录"],
        industry="金融",
    )
    print(f"Test 2 (with monitor_scenarios): baselines={len(result2['data']['baselines'])}")

asyncio.run(test())

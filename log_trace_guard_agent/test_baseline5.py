import sys
sys.path.insert(0, 'E:/Code/code.python/agent/log_trace_guard_agent')

from modules.compliance.schemas import BaselineGenReq

# Test Pydantic parsing
req = BaselineGenReq(
    asset_count=50,
    business_type="互联网金融",
    device_types=["server"],
    monitor_scenarios=["异常登录"],
    industry="金融",
)

print(f"asset_count: {req.asset_count}")
print(f"business_type: {req.business_type}")
print(f"device_types: {req.device_types}")
print(f"monitor_scenarios: {req.monitor_scenarios}")
print(f"industry: {req.industry}")

# Now test the service directly
import asyncio
from modules.compliance.service import ComplianceService

async def test():
    result = await ComplianceService.generate_baseline(
        asset_count=req.asset_count,
        business_type=req.business_type,
        device_types=req.device_types,
        monitor_scenarios=req.monitor_scenarios,
        industry=req.industry,
    )
    print(f"baselines: {len(result['data']['baselines'])}")

asyncio.run(test())

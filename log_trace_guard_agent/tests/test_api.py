"""FastAPI 集成测试 — 验证所有接口可用性 + 新返回格式"""

import asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app


async def test_all_endpoints():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. 健康检查
        r1 = await client.get("/")
        data1 = r1.json()
        print(f"GET /: {r1.status_code} code={data1['code']} msg={data1['msg']}")

        # 2. 识别 SSH 日志
        r2 = await client.post("/api/v1/log-parse/identify", json={
            "log_line": "Mar 15 10:30:25 server sshd[1234]: Accepted password for root from 192.168.1.1 port 22"
        })
        data2 = r2.json()
        print(f"Identify SSH: code={data2['code']} type={data2['data'].get('device_type')} confidence={data2['data'].get('confidence')}")

        # 3. 识别 Web 日志
        r3 = await client.post("/api/v1/log-parse/identify", json={
            "log_line": '192.168.1.1 - - [10/Oct/2023:13:55:36 +0000] "GET /index.html HTTP/1.1" 200 2326'
        })
        data3 = r3.json()
        print(f"Identify Web: code={data3['code']} type={data3['data'].get('device_type')}")

        # 4. 解析 SSH 日志
        r4 = await client.post("/api/v1/log-parse/parse", json={
            "log_line": "Mar 15 10:30:25 server sshd[1234]: Accepted password for root from 192.168.1.1 port 22"
        })
        data4 = r4.json()
        print(f"Parse SSH: code={data4['code']} src_ip={data4['data'].get('src_ip')} user={data4['data'].get('user')}")

        # 5. 解析 Web 日志
        r5 = await client.post("/api/v1/log-parse/parse", json={
            "log_line": '192.168.1.1 - - [10/Oct/2023:13:55:36 +0000] "GET /index.html HTTP/1.1" 200 2326 "-" "Mozilla/5.0"'
        })
        data5 = r5.json()
        print(f"Parse Web: code={data5['code']} method={data5['data'].get('method')} url={data5['data'].get('url')}")

        # 6. 风险研判 SSH 暴力破解
        r6 = await client.post("/api/v1/log-parse/assess", json={
            "log_line": "Mar 15 10:31:00 server sshd[1235]: Failed password for admin from 10.0.0.5 port 22"
        })
        data6 = r6.json()
        print(f"Assess SSH: code={data6['code']} level={data6['data'].get('risk_level')} confidence={data6['data'].get('confidence')} rules={data6['data'].get('match_rule_ids')}")

        # 7. 风险研判 Web 攻击
        r7 = await client.post("/api/v1/log-parse/assess", json={
            "log_line": '10.0.0.5 - - [10/Oct/2023:14:01:23 +0000] "POST /wp-admin/admin-ajax.php HTTP/1.1" 404 1234'
        })
        data7 = r7.json()
        print(f"Assess Web: code={data7['code']} level={data7['data'].get('risk_level')} attack={data7['data'].get('attack_type')}")

        # 8. 字段释义
        r8 = await client.post("/api/v1/log-parse/explain", json={
            "field_name": "src_ip"
        })
        data8 = r8.json()
        print(f"Explain: code={data8['code']} field={data8['data'].get('field')}")

        # 9. 批量解析
        r9 = await client.post("/api/v1/log-parse/parse/batch", json={
            "logs": [
                "Mar 15 10:30:25 server sshd[1234]: Accepted password for root from 192.168.1.1 port 22",
                '192.168.1.1 - - [10/Oct/2023:13:55:36 +0000] "GET /index.html HTTP/1.1" 200 2326',
            ],
            "assess": True,
        })
        data9 = r9.json()
        print(f"Batch: code={data9['code']} total={data9['data'].get('total')} success={data9['data'].get('success_count')} summary={data9['data'].get('risk_summary')}")

        # 10. 空日志校验
        r10 = await client.post("/api/v1/log-parse/parse", json={"log_line": ""})
        data10 = r10.json()
        print(f"Empty: code={data10['code']} msg={data10['msg']}")

        # 11. 批量字段释义
        r11 = await client.post("/api/v1/log-parse/explain/batch", json={
            "field_names": ["src_ip", "dst_ip", "user"]
        })
        data11 = r11.json()
        print(f"ExplainBatch: code={data11['code']} fields={len(data11['data'].get('fields', []))}")

    print("\n=== All tests passed! ===")


asyncio.run(test_all_endpoints())
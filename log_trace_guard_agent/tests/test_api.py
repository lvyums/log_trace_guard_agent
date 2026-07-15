"""FastAPI 集成测试 — 验证所有接口可用性 + 新返回格式"""

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_health_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/health")
        data = r.json()
        assert r.status_code == 200
        assert data["code"] == 0
        print(f"GET /health: {r.status_code} code={data['code']}")


@pytest.mark.asyncio
async def test_identify_ssh_log():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post("/api/v1/log-parse/identify", json={
            "log_line": "Mar 15 10:30:25 server sshd[1234]: Accepted password for root from 192.168.1.1 port 22"
        })
        data = r.json()
        assert data["code"] == 0
        assert data["data"].get("device_type") == "ssh"
        print(f"Identify SSH: code={data['code']} type={data['data'].get('device_type')}")


@pytest.mark.asyncio
async def test_identify_web_log():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post("/api/v1/log-parse/identify", json={
            "log_line": '192.168.1.1 - - [10/Oct/2023:13:55:36 +0000] "GET /index.html HTTP/1.1" 200 2326'
        })
        data = r.json()
        assert data["code"] == 0
        assert data["data"].get("device_type") == "web"
        print(f"Identify Web: code={data['code']} type={data['data'].get('device_type')}")


@pytest.mark.asyncio
async def test_parse_ssh_log():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post("/api/v1/log-parse/parse", json={
            "log_line": "Mar 15 10:30:25 server sshd[1234]: Accepted password for root from 192.168.1.1 port 22"
        })
        data = r.json()
        assert data["code"] == 0
        assert data["data"].get("src_ip") == "192.168.1.1"
        assert data["data"].get("user") == "root"
        print(f"Parse SSH: code={data['code']} src_ip={data['data'].get('src_ip')} user={data['data'].get('user')}")


@pytest.mark.asyncio
async def test_parse_web_log():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post("/api/v1/log-parse/parse", json={
            "log_line": '192.168.1.1 - - [10/Oct/2023:13:55:36 +0000] "GET /index.html HTTP/1.1" 200 2326 "-" "Mozilla/5.0"'
        })
        data = r.json()
        assert data["code"] == 0
        assert data["data"].get("method") == "GET"
        print(f"Parse Web: code={data['code']} method={data['data'].get('method')} url={data['data'].get('url')}")


@pytest.mark.asyncio
async def test_assess_ssh_brute_force():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post("/api/v1/log-parse/assess", json={
            "log_line": "Mar 15 10:31:00 server sshd[1235]: Failed password for admin from 10.0.0.5 port 22"
        })
        data = r.json()
        assert data["code"] == 0
        print(f"Assess SSH: code={data['code']} level={data['data'].get('risk_level')} confidence={data['data'].get('confidence')}")


@pytest.mark.asyncio
async def test_assess_web_attack():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post("/api/v1/log-parse/assess", json={
            "log_line": '10.0.0.5 - - [10/Oct/2023:14:01:23 +0000] "POST /wp-admin/admin-ajax.php HTTP/1.1" 404 1234'
        })
        data = r.json()
        assert data["code"] == 0
        print(f"Assess Web: code={data['code']} level={data['data'].get('risk_level')} attack={data['data'].get('attack_type')}")


@pytest.mark.asyncio
async def test_explain_field():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post("/api/v1/log-parse/explain", json={"field_name": "src_ip"})
        data = r.json()
        assert data["code"] == 0
        print(f"Explain: code={data['code']} field={data['data'].get('field')}")


@pytest.mark.asyncio
async def test_batch_parse():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post("/api/v1/log-parse/parse/batch", json={
            "logs": [
                "Mar 15 10:30:25 server sshd[1234]: Accepted password for root from 192.168.1.1 port 22",
                '192.168.1.1 - - [10/Oct/2023:13:55:36 +0000] "GET /index.html HTTP/1.1" 200 2326',
            ],
            "assess": True,
        })
        data = r.json()
        assert data["code"] == 0
        print(f"Batch: code={data['code']} total={data['data'].get('total')} success={data['data'].get('success_count')}")


@pytest.mark.asyncio
async def test_empty_log_validation():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post("/api/v1/log-parse/parse", json={"log_line": ""})
        data = r.json()
        assert data["code"] != 0
        print(f"Empty: code={data['code']} msg={data['msg']}")


@pytest.mark.asyncio
async def test_batch_explain():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post("/api/v1/log-parse/explain/batch", json={
            "field_names": ["src_ip", "dst_ip", "user"]
        })
        data = r.json()
        assert data["code"] == 0
        print(f"ExplainBatch: code={data['code']} fields={len(data['data'].get('fields', []))}")
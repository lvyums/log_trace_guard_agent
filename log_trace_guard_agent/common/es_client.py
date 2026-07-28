"""Elasticsearch REST API 客户端 — 纯工具，无业务逻辑"""

import json
import time
from typing import Optional

import requests

from common.logger import LogManager

logger = LogManager.get_logger()


class ESClient:
    """Elasticsearch REST API 客户端"""

    def __init__(
        self,
        base_url: str,
        username: str = "",
        password: str = "",
        verify_ssl: bool = True,
    ):
        self._base_url = base_url.rstrip("/")
        self._username = username
        self._password = password
        self._verify_ssl = verify_ssl
        self._session: Optional[requests.Session] = None

    def _get_session(self) -> requests.Session:
        """创建带认证的 Session"""
        if self._session is not None:
            return self._session

        session = requests.Session()
        session.verify = self._verify_ssl

        if self._username and self._password:
            session.auth = (self._username, self._password)

        self._session = session
        return session

    def search(
        self,
        query_dsl: str,
        index_pattern: str = "",
        max_results: int = 100,
        timeout: int = 30,
    ) -> dict:
        """
        执行 ES 搜索并返回结果。

        流程: POST /{index}/_search

        Args:
            query_dsl: ES Query DSL JSON 字符串
            index_pattern: 索引名称（为空则搜索所有索引）
            max_results: 最大返回条数
            timeout: 请求超时（秒）

        Returns:
            {"results": [...], "total": N, "error": None, ...}
        """
        session = self._get_session()
        start_time = time.time()

        try:
            # 解析 DSL，注入 size
            try:
                body = json.loads(query_dsl)
            except json.JSONDecodeError as e:
                return {"results": [], "total": 0, "error": f"DSL JSON 解析失败: {str(e)}"}

            body["size"] = max_results

            # 构建 URL
            path = index_pattern.strip("/") if index_pattern else "_all"
            search_url = f"{self._base_url}/{path}/_search"

            headers = {"Content-Type": "application/json"}
            resp = session.post(
                search_url,
                data=json.dumps(body),
                headers=headers,
                timeout=timeout,
            )
            resp.raise_for_status()

            data = resp.json()
            hits = data.get("hits", {}).get("hits", [])
            total = data.get("hits", {}).get("total", {}).get("value", len(hits))
            took = data.get("took", 0)
            elapsed = round(time.time() - start_time, 2)

            # 提取 _source 简化结果
            results = []
            for hit in hits:
                row = {
                    "_id": hit.get("_id", ""),
                    "_index": hit.get("_index", ""),
                    "_score": hit.get("_score"),
                    "source": hit.get("_source", {}),
                }
                results.append(row)

            logger.info(f"ES 搜索完成: index={path}, total={total}, results={len(results)}, took={took}ms")

            return {
                "results": results,
                "total": total,
                "took": took,
                "execution_time": elapsed,
                "error": None,
            }

        except requests.exceptions.ConnectionError:
            return {"results": [], "total": 0, "error": "ES 连接失败，请检查 ES_BASE_URL"}
        except requests.exceptions.Timeout:
            return {"results": [], "total": 0, "error": f"ES 请求超时（{timeout}s）"}
        except requests.exceptions.HTTPError as e:
            return {"results": [], "total": 0, "error": f"ES HTTP 错误: {e.response.status_code} {e.response.text[:200]}"}
        except Exception as e:
            logger.warning(f"ES 搜索异常: {e}")
            return {"results": [], "total": 0, "error": f"搜索执行失败: {str(e)}"}

    def test_connection(self, timeout: int = 10) -> dict:
        """测试 ES 连接，获取集群信息"""
        session = self._get_session()
        try:
            resp = session.get(f"{self._base_url}/", timeout=timeout)
            resp.raise_for_status()
            info = resp.json()
            return {
                "success": True,
                "cluster_name": info.get("cluster_name", ""),
                "version": info.get("version", {}).get("number", ""),
                "error": None,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def health(self, timeout: int = 10) -> dict:
        """获取 ES 集群健康状态"""
        session = self._get_session()
        try:
            resp = session.get(f"{self._base_url}/_cluster/health", timeout=timeout)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            return {"status": "unavailable", "error": str(e)}

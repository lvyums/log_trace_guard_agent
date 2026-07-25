"""Splunk REST API 客户端 — 纯工具，无业务逻辑"""

import time
import urllib.parse
from typing import Optional

import requests

from common.logger import LogManager

logger = LogManager.get_logger()


class SplunkClient:
    """Splunk REST API 客户端"""

    def __init__(
        self,
        base_url: str,
        username: str = "",
        password: str = "",
        auth_token: str = "",
        verify_ssl: bool = True,
    ):
        self._base_url = base_url.rstrip("/")
        self._username = username
        self._password = password
        self._auth_token = auth_token
        self._verify_ssl = verify_ssl
        self._session: Optional[requests.Session] = None

    def _get_session(self) -> requests.Session:
        """创建带认证的 Session"""
        if self._session is not None:
            return self._session

        session = requests.Session()
        session.verify = self._verify_ssl

        if self._auth_token:
            session.headers["Authorization"] = f"Splunk {self._auth_token}"
        elif self._username and self._password:
            session.auth = (self._username, self._password)

        self._session = session
        return session

    def execute_search(
        self,
        spl_query: str,
        max_results: int = 100,
        timeout: int = 30,
    ) -> dict:
        """
        执行 Splunk 搜索并返回结果。

        流程: POST /services/search/jobs → 轮询状态 → GET /services/search/jobs/{sid}/results

        Returns:
            {"results": [...], "sid": "...", "event_count": N, "error": None}
        """
        session = self._get_session()
        start_time = time.time()

        try:
            # 1. 提交搜索任务
            search_url = f"{self._base_url}/services/search/jobs"
            post_data = {
                "search": spl_query,
                "max_count": str(max_results),
            }
            resp = session.post(search_url, data=post_data)
            resp.raise_for_status()

            # 解析 sid
            sid = self._extract_sid(resp.text)
            if not sid:
                return {"results": [], "sid": "", "event_count": 0, "error": "无法获取搜索任务 ID"}

            # 2. 轮询等待完成
            job_url = f"{self._base_url}/services/search/jobs/{sid}"
            deadline = time.time() + timeout

            while time.time() < deadline:
                status_resp = session.get(job_url)
                status_resp.raise_for_status()

                if '"isDone":"1"' in status_resp.text or '"isDone">1<' in status_resp.text:
                    break
                time.sleep(1)
            else:
                return {"results": [], "sid": sid, "event_count": 0, "error": f"搜索超时（{timeout}s）"}

            # 3. 获取结果
            results_url = f"{self._base_url}/services/search/jobs/{sid}/results?count={max_results}&output_mode=json"
            results_resp = session.get(results_url)
            results_resp.raise_for_status()

            data = results_resp.json()
            results = data.get("results", [])
            elapsed = round(time.time() - start_time, 2)

            logger.info(f"Splunk 搜索完成: sid={sid}, results={len(results)}, elapsed={elapsed}s")

            return {
                "results": results,
                "sid": sid,
                "event_count": len(results),
                "execution_time": elapsed,
                "error": None,
            }

        except requests.exceptions.ConnectionError:
            return {"results": [], "sid": "", "event_count": 0, "error": "Splunk 连接失败，请检查 SPLUNK_BASE_URL"}
        except requests.exceptions.Timeout:
            return {"results": [], "sid": "", "event_count": 0, "error": f"Splunk 请求超时（{timeout}s）"}
        except requests.exceptions.HTTPError as e:
            return {"results": [], "sid": "", "event_count": 0, "error": f"Splunk HTTP 错误: {e.response.status_code}"}
        except Exception as e:
            logger.warning(f"Splunk 搜索异常: {e}")
            return {"results": [], "sid": "", "event_count": 0, "error": f"搜索执行失败: {str(e)}"}

    def build_open_url(self, spl_query: str) -> str:
        """构建 Splunk Web UI 跳转链接"""
        encoded_query = urllib.parse.quote(spl_query, safe="")
        return f"{self._base_url}/en-US/app/search/search?q={encoded_query}"

    @staticmethod
    def _extract_sid(xml_text: str) -> Optional[str]:
        """从 XML 响应中提取 sid"""
        import re
        match = re.search(r"<sid>([^<]+)</sid>", xml_text)
        return match.group(1) if match else None

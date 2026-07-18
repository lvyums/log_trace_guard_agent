"""轻量级 RAG 引擎 — API 嵌入 + 余弦相似度 + 本地向量缓存"""
import json
import os
import math
from typing import Optional

from .llm_client import get_embedding
from .settings import settings


class RAGEngine:
    """轻量 RAG 知识库引擎
    - 不用 ChromaDB / ONNX
    - API 远程嵌入（raytoken embedding），支持批量请求
    - 向量存本地 JSON 缓存，增量更新
    - 运行时全量加载到内存做余弦相似度搜索
    - 限制每个源文件的最大文档数，避免过度嵌入
    """

    def __init__(self):
        self._vectors: list[dict] = []
        self._loaded = False
        self._data_dir = self._find_data_dir()

    # 每个源文件最大嵌入文档数（避免 API 调用过多）
    _MAX_DOCS_PER_SOURCE = 50

    def _find_data_dir(self) -> str:
        """查找 rule_data 目录"""
        candidates = [
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "rule_data"),
            os.path.join(os.getcwd(), "log_guard", "data", "rule_data"),
            os.path.join(os.getcwd(), "data", "rule_data"),
        ]
        for path in candidates:
            if os.path.isdir(path):
                return path
        return candidates[0]

    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        """余弦相似度"""
        dot = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a))
        nb = math.sqrt(sum(x * x for x in b))
        if na == 0 or nb == 0:
            return 0.0
        return dot / (na * nb)

    def _load_json_files(self) -> list[dict]:
        """加载所有规则 JSON 文件，展平为可检索文档列表"""
        docs = []
        if not os.path.isdir(self._data_dir):
            return docs

        for fname in sorted(os.listdir(self._data_dir)):
            if not fname.endswith(".json"):
                continue
            fpath = os.path.join(self._data_dir, fname)
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                continue

            name = fname.replace(".json", "")
            count = 0
            if isinstance(data, list):
                for i, item in enumerate(data):
                    if count >= self._MAX_DOCS_PER_SOURCE:
                        break
                    text = json.dumps(item, ensure_ascii=False)[:2000]
                    docs.append({
                        "id": f"{name}-{i}",
                        "source": name,
                        "text": text,
                        "metadata": item,
                    })
                    count += 1
            elif isinstance(data, dict):
                for key, val in data.items():
                    if count >= self._MAX_DOCS_PER_SOURCE:
                        break
                    text = f"{key}: {json.dumps(val, ensure_ascii=False)[:2000]}"
                    docs.append({
                        "id": f"{name}-{key}",
                        "source": name,
                        "text": text,
                        "metadata": {key: val},
                    })
                    count += 1
        return docs

    def _build_vectors(self, docs: list[dict]) -> list[dict]:
        """批量生成文档向量（调用 API，分批发送）"""
        embedder = get_embedding()
        if not docs:
            return []

        # 提取所有文本，限制长度
        texts = [doc["text"][:1000] for doc in docs]
        # 批量调用 API
        embeddings = embedder.embed_batch(texts)

        vectors = []
        for doc, vec in zip(docs, embeddings):
            if vec:
                vectors.append({
                    "id": doc["id"],
                    "source": doc["source"],
                    "text": doc["text"],
                    "metadata": doc["metadata"],
                    "vector": vec,
                })
        return vectors

    def _save_cache(self, vectors: list[dict]):
        """保存向量到缓存文件"""
        try:
            cache_data = []
            for v in vectors:
                cache_data.append({
                    "id": v["id"],
                    "source": v["source"],
                    "text": v["text"],
                    "metadata": v["metadata"],
                    "vector": v["vector"],
                })
            with open(settings.vector_cache_path, "w", encoding="utf-8") as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _load_cache(self) -> Optional[list[dict]]:
        """从缓存文件加载向量"""
        path = settings.vector_cache_path
        if not os.path.isfile(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    def load(self):
        """加载知识库（缓存优先，缓存不存在则重新生成）"""
        if self._loaded:
            return

        # 尝试加载缓存
        cached = self._load_cache()
        if cached and len(cached) > 0:
            self._vectors = cached
            self._loaded = True
            return

        # 重新生成
        docs = self._load_json_files()
        if not docs:
            self._loaded = True
            return

        vectors = self._build_vectors(docs)
        if vectors:
            self._vectors = vectors
            self._save_cache(vectors)

        self._loaded = True

    def search(self, query: str, top_k: int = None) -> list[dict]:
        """搜索知识库，返回最相似文档"""
        self.load()

        if not self._vectors:
            return []

        top_k = top_k or settings.rag_top_k
        embedder = get_embedding()
        query_vec = embedder.embed(query[:1000])
        if not query_vec:
            return []

        # 计算相似度（全量扫描）
        scored = []
        for vec in self._vectors:
            score = self._cosine_similarity(query_vec, vec["vector"])
            if score >= settings.rag_similarity_threshold:
                scored.append({
                    "id": vec["id"],
                    "source": vec["source"],
                    "text": vec["text"],
                    "score": round(score, 4),
                })

        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k]

    def search_text(self, query: str, top_k: int = None) -> str:
        """搜索并返回格式化文本（供 Prompt 注入）"""
        results = self.search(query, top_k)
        if not results:
            return ""

        lines = []
        for r in results:
            source = r["source"]
            text = r["text"][:500]
            score = r["score"]
            lines.append(f"[{source}] (相似度: {score:.2f})\n{text}")

        return "\n\n---\n\n".join(lines)

    @property
    def is_ready(self) -> bool:
        return self._loaded or bool(self._vectors)

    @property
    def stats(self) -> dict:
        return {
            "loaded": self._loaded,
            "vectors": len(self._vectors),
            "cache_exists": os.path.isfile(settings.vector_cache_path),
        }


_rag_instance = None


def get_rag() -> RAGEngine:
    global _rag_instance
    if _rag_instance is None:
        _rag_instance = RAGEngine()
    return _rag_instance
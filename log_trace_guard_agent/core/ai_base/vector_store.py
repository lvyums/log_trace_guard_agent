"""向量库管理 — ChromaDB 封装"""

from typing import Optional

import chromadb
from chromadb.config import Settings as ChromaSettings

from common.logger import LogManager

logger = LogManager.get_logger()


class VectorStore:
    """向量库管理，封装 ChromaDB 基本操作"""

    def __init__(self, collection_name: str, persist_dir: str):
        self.collection_name = collection_name
        self.persist_dir = persist_dir
        self._client: Optional[chromadb.PersistentClient] = None
        self._collection: Optional[chromadb.Collection] = None
        self._init_client()

    def _init_client(self):
        """初始化 ChromaDB 客户端并加载集合"""
        try:
            self._client = chromadb.PersistentClient(
                path=self.persist_dir,
                settings=ChromaSettings(anonymized_telemetry=False),
            )
            # 获取或创建集合
            try:
                self._collection = self._client.get_collection(self.collection_name)
            except Exception:
                # 集合不存在时创建新集合
                self._collection = self._client.create_collection(self.collection_name)
                logger.info(f"创建新集合: {self.collection_name}")
        except Exception as e:
            logger.error(f"ChromaDB 初始化失败: {e}")
            raise

    def add_documents(self, documents: list[str], metadatas: list[dict], ids: list[str]):
        """添加文档到向量库"""
        if not documents:
            return
        try:
            self._collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids,
            )
        except Exception as e:
            logger.error(f"添加文档失败: {e}")

    def similarity_search(self, query: str, k: int = 5, score_threshold: float = 0.6) -> list[dict]:
        """向量检索 + 过滤低分结果"""
        try:
            results = self._collection.query(
                query_texts=[query],
                n_results=k,
            )
            items = []
            distances = results.get("distances", [[]])[0] if results.get("distances") else []
            documents = results.get("documents", [[]])[0] if results.get("documents") else []
            metadatas = results.get("metadatas", [[]])[0] if results.get("metadatas") else []
            ids = results.get("ids", [[]])[0] if results.get("ids") else []

            for i, doc in enumerate(documents):
                score = 1 - distances[i] if i < len(distances) else 0
                if score >= score_threshold:
                    items.append({
                        "id": ids[i] if i < len(ids) else "",
                        "document": doc,
                        "metadata": metadatas[i] if i < len(metadatas) else {},
                        "score": score,
                    })
            return items
        except Exception as e:
            logger.error(f"向量检索失败: {e}")
            return []

    def count(self) -> int:
        """返回集合中文档数量"""
        try:
            return self._collection.count()
        except Exception:
            return 0


class EmbeddingCache:
    """Embedding 结果 LRU 缓存"""

    def __init__(self, maxsize: int = 1000):
        self._cache: dict[str, list[float]] = {}
        self._maxsize = maxsize

    def get(self, key: str) -> Optional[list[float]]:
        return self._cache.get(key)

    def set(self, key: str, embedding: list[float]):
        if len(self._cache) >= self._maxsize:
            # 简单淘汰：删除第一个键
            self._cache.pop(next(iter(self._cache)))
        self._cache[key] = embedding

    def clear(self):
        self._cache.clear()
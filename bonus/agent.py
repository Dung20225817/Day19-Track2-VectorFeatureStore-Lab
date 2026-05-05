"""HybridMemoryAgent — combines Qdrant episodic memory + Feast user profile.

Run: python bonus/agent.py
Or import and use HybridMemoryAgent in demo.py.
"""
from __future__ import annotations

import io
import sys
import time

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add repo root to sys.path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "app" / "feast_repo"))

import polars as pl
from fastembed import TextEmbedding
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    Filter,
    FieldCondition,
    MatchValue,
    PointStruct,
    VectorParams,
)
from rank_bm25 import BM25Okapi

COLLECTION = "user_memories"
EMBED_MODEL = "BAAI/bge-small-en-v1.5"
EMBED_DIM = 384
RRF_K = 60
TOP_K = 5


class HybridMemoryAgent:
    """Minimal AI memory agent combining vector episodic store + Feast feature store.

    Uses in-memory Qdrant + SQLite Feast (lite path).
    """

    def __init__(self) -> None:
        self.embedder = TextEmbedding(model_name=EMBED_MODEL)
        self.qdrant = QdrantClient(":memory:")
        self.qdrant.create_collection(
            collection_name=COLLECTION,
            vectors_config=VectorParams(size=EMBED_DIM, distance=Distance.COSINE),
        )
        self._memories: list[dict] = []  # in-memory mirror for BM25
        self._bm25: BM25Okapi | None = None
        self._next_id: int = 0
        self._feast_store = self._init_feast()

    def _init_feast(self):
        try:
            from feast import FeatureStore
            feast_dir = ROOT / "app" / "feast_repo"
            if (feast_dir / "registry.db").exists():
                return FeatureStore(repo_path=str(feast_dir))
        except Exception:
            pass
        return None

    def _rebuild_bm25(self) -> None:
        if not self._memories:
            self._bm25 = None
            return
        tokenized = [m["text"].lower().split() for m in self._memories]
        self._bm25 = BM25Okapi(tokenized)

    def remember(self, text: str, user_id: str = "u_001") -> None:
        """Add a new piece of episodic memory for this user."""
        vec = next(self.embedder.embed([text])).tolist()
        point_id = self._next_id
        self._next_id += 1

        self.qdrant.upsert(
            collection_name=COLLECTION,
            points=[PointStruct(
                id=point_id,
                vector=vec,
                payload={
                    "text": text,
                    "user_id": user_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )],
        )
        self._memories.append({"id": point_id, "text": text, "user_id": user_id})
        self._rebuild_bm25()

    def _get_user_profile(self, user_id: str) -> dict:
        """Fetch stable user profile from Feast online store."""
        if self._feast_store is None:
            return {}
        try:
            result = self._feast_store.get_online_features(
                features=[
                    "user_profile_features:reading_speed_wpm",
                    "user_profile_features:preferred_language",
                    "user_profile_features:topic_affinity",
                    "query_velocity_features:queries_last_hour",
                    "query_velocity_features:distinct_topics_24h",
                ],
                entity_rows=[{"user_id": user_id}],
            ).to_dict()
            return {k: v[0] for k, v in result.items() if k != "user_id"}
        except Exception:
            return {}

    def _search_hybrid(self, query: str, user_id: str) -> list[str]:
        """Hybrid search over user's episodic memories using RRF."""
        user_filter = Filter(
            must=[FieldCondition(key="user_id", match=MatchValue(value=user_id))]
        )

        # Semantic search
        q_vec = next(self.embedder.embed([query])).tolist()
        sem_hits = self.qdrant.query_points(
            collection_name=COLLECTION,
            query=q_vec,
            query_filter=user_filter,
            limit=max(TOP_K * 5, 20),
        ).points
        sem_texts = [h.payload["text"] for h in sem_hits]

        # BM25 keyword search (filter to this user first)
        user_memories = [m for m in self._memories if m["user_id"] == user_id]
        if not user_memories:
            return sem_texts[:TOP_K]

        bm25_local = BM25Okapi([m["text"].lower().split() for m in user_memories])
        scores = bm25_local.get_scores(query.lower().split())
        kw_texts = [
            user_memories[i]["text"]
            for i in sorted(range(len(scores)), key=lambda x: -scores[x])[:max(TOP_K * 5, 20)]
        ]

        # RRF fusion
        rrf: dict[str, float] = {}
        for rank, text in enumerate(kw_texts, start=1):
            rrf[text] = rrf.get(text, 0.0) + 1.0 / (RRF_K + rank)
        for rank, text in enumerate(sem_texts, start=1):
            rrf[text] = rrf.get(text, 0.0) + 1.0 / (RRF_K + rank)

        return [t for t, _ in sorted(rrf.items(), key=lambda kv: -kv[1])[:TOP_K]]

    def recall(self, query: str, user_id: str = "u_001") -> str:
        """Retrieve top-K memories + user profile features → return assembled context."""
        profile = self._get_user_profile(user_id)
        top_memories = self._search_hybrid(query, user_id)

        # Assemble context string
        lines = [f"[User: {user_id}]"]

        if profile:
            topic = profile.get("topic_affinity", "unknown")
            speed = profile.get("reading_speed_wpm", "?")
            lang = profile.get("preferred_language", "?")
            recent_queries = profile.get("queries_last_hour", 0)
            topics_24h = profile.get("distinct_topics_24h", 0)
            lines.append(
                f"Profile: reads {speed}wpm | lang={lang} | "
                f"top_interest={topic} | {recent_queries} queries/h | "
                f"{topics_24h} distinct topics/24h"
            )

        if top_memories:
            lines.append(f"Top {len(top_memories)} relevant memories:")
            for i, mem in enumerate(top_memories, 1):
                snippet = mem[:120].replace("\n", " ")
                lines.append(f"  [{i}] {snippet}")
        else:
            lines.append("No relevant memories found.")

        return "\n".join(lines)


if __name__ == "__main__":
    print("=== HybridMemoryAgent smoke test ===\n")
    agent = HybridMemoryAgent()

    # Seed some memories
    memories = [
        ("Kubernetes là hệ thống quản lý container mã nguồn mở của Google. "
         "Nó tự động hóa việc triển khai, scaling, và quản lý containerized applications.", "u_001"),
        ("Docker giúp đóng gói ứng dụng vào container. "
         "Kết hợp với Kubernetes, tạo thành nền tảng cloud native mạnh mẽ.", "u_001"),
        ("Auto-scaling trong cloud cho phép tự động tăng giảm số lượng instances "
         "theo lưu lượng người dùng. AWS có ASG, GCP có Managed Instance Groups.", "u_001"),
        ("Machine learning pipeline cần Feature Store để tránh training-serving skew. "
         "Feast là giải pháp open-source phổ biến nhất năm 2024.", "u_001"),
        ("Bảo mật cloud: luôn dùng IAM roles, không hardcode credentials, "
         "enable CloudTrail/audit logs, encrypt data at rest.", "u_001"),
    ]

    print("Seeding memories...")
    for text, uid in memories:
        agent.remember(text, uid)
    print(f"Seeded {len(memories)} memories.\n")

    print("Testing recall...")
    test_query = "Kubernetes container management"
    context = agent.recall(test_query, "u_001")
    print(f"Query: {test_query!r}")
    print(context)
    print()
    print("smoke test passed")

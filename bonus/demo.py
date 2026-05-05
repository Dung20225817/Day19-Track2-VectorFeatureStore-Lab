"""Demo: 5 queries showing HybridMemoryAgent capabilities.

Run: python bonus/demo.py
Expected: exits 0 with 5 query outputs printed.
"""
import io
import sys
from pathlib import Path

# Fix Windows console encoding for Vietnamese text
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from bonus.agent import HybridMemoryAgent


def main() -> None:
    print("=" * 70)
    print("HybridMemoryAgent Demo — 5 queries")
    print("=" * 70)
    print()

    agent = HybridMemoryAgent()

    # Seed episodic memories
    print("Seeding episodic memories for u_001...")
    seed_memories = [
        "Kubernetes là hệ thống orchestration container của Google. Tôi đã đọc "
        "về pod scheduling, deployment strategies, và service mesh với Istio.",

        "Docker containers giúp isolate ứng dụng. Best practice: dùng multi-stage "
        "build để giảm image size, không chạy container as root.",

        "Auto-scaling trên AWS: EC2 Auto Scaling Group theo CPU metrics. "
        "GCP: Managed Instance Groups với custom metrics từ Cloud Monitoring. "
        "Cả hai đều support predictive scaling dựa trên lịch sử.",

        "Bảo mật cloud computing: Zero Trust model, MFA bắt buộc, "
        "encrypt data at rest và in-transit, audit logs với CloudTrail/Stackdriver. "
        "Principle of least privilege cho IAM roles.",

        "Feast Feature Store: định nghĩa FeatureView với entity, TTL, source. "
        "materialize-incremental đẩy data từ offline (Parquet) sang online (SQLite/Redis). "
        "get_online_features() trả về <10ms P99 với local SQLite.",

        "Machine learning pipeline: data collection → feature engineering → training → "
        "evaluation → serving. Training-serving skew xảy ra khi features tính khác nhau "
        "giữa training và inference. Feature Store giải quyết vấn đề này.",

        "Kafka là distributed message broker. Producers gửi events, consumers đọc "
        "từ partitions. Flink process streaming data real-time. "
        "Dùng cho query_velocity features trong AI assistant.",
    ]

    for mem in seed_memories:
        agent.remember(mem, user_id="u_001")
    print(f"Seeded {len(seed_memories)} memories.\n")
    print("=" * 70)
    print()

    queries = [
        # Query 1: Simple vector hit — specific topic question
        ("Q1: Simple vector hit (Kubernetes)",
         "Tôi đã đọc gì về Kubernetes?",
         "u_001"),

        # Query 2: Need profile context — requires topic_affinity
        ("Q2: Profile context needed (recommendation)",
         "Recommend tài liệu nên đọc tiếp theo cho tôi",
         "u_001"),

        # Query 3: Fresh activity — queries_last_hour
        ("Q3: Recent activity context",
         "Tôi đang quan tâm đến chủ đề gì gần đây?",
         "u_001"),

        # Query 4: Paraphrase query — vector search wins
        ("Q4: Paraphrase query (auto-scaling without exact keywords)",
         "Tài liệu về tự động điều chỉnh tài nguyên hạ tầng theo nhu cầu",
         "u_001"),

        # Query 5: Mixed hybrid + profile
        ("Q5: Mixed hybrid + profile (cloud security)",
         "Cho tôi summary về bảo mật đám mây và những gì cần chú ý",
         "u_001"),
    ]

    for label, query, user_id in queries:
        print(f"--- {label} ---")
        print(f"Query: {query!r}")
        context = agent.recall(query, user_id=user_id)
        print(context)
        print()

    print("=" * 70)
    print("Demo completed successfully. All 5 queries processed.")
    print("=" * 70)


if __name__ == "__main__":
    main()
    sys.exit(0)

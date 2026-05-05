# Architecture: Hybrid AI Memory System for Vietnamese Personal Assistant

**Contributors:** PQD (A20-K1)  
**Date:** 2026-05-05

---

## Overview

This document describes the architecture of a minimal **Hybrid AI Memory System** combining a **Vector Store** (episodic memory) and a **Feature Store** (stable user profile) for a Vietnamese personal AI assistant. The system enables the assistant to remember past conversations, understand user preferences, and retrieve contextually relevant information efficiently.

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                        User Interface (Chat)                        │
│                    [query: "Tôi đã đọc gì về Kubernetes?"]          │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    HybridMemoryAgent.recall()                       │
│                                                                     │
│  ┌──────────────────────┐    ┌──────────────────────────────────┐   │
│  │   Feast Online Store  │    │      Qdrant Vector Store          │   │
│  │  (Stable Profile)     │    │    (Episodic Memory)              │   │
│  │                       │    │                                  │   │
│  │  user_profile:        │    │  Collection: user_memories       │   │
│  │  - topic_affinity     │    │  Filter: {user_id: "u_001"}      │   │
│  │  - reading_speed_wpm  │    │                                  │   │
│  │  - preferred_lang     │    │  Hybrid Search (BM25 + Vector    │   │
│  │                       │    │  + RRF k=60) → Top-K memories   │   │
│  │  query_velocity:      │    │                                  │   │
│  │  - queries_last_hour  │    │  Payload: {text, user_id,        │   │
│  │  - distinct_topics    │    │   timestamp, source_type}        │   │
│  └──────────┬───────────┘    └──────────────┬───────────────────┘   │
│             │                               │                        │
│             └──────────────┬────────────────┘                        │
│                            ▼                                         │
│               ┌───────────────────────┐                             │
│               │  Context Assembler    │                             │
│               │  "User likes cloud    │                             │
│               │  reading at 187wpm.   │                             │
│               │  Recent: 11 queries/h │                             │
│               │  Memories: [top-3]"   │                             │
│               └───────────┬───────────┘                             │
└───────────────────────────┼─────────────────────────────────────────┘
                            │
                            ▼
                    LLM Final Response
                    (Claude/GPT with assembled context)

┌──────────────────────── WRITE PATH ─────────────────────────────────┐
│  remember(text, user_id):                                            │
│    text → chunk (512 tokens) → fastembed → upsert to Qdrant          │
│    (payload: user_id, timestamp, source_type)                        │
│                                                                      │
│  Feast offline pipeline (batch):                                     │
│    Parquet files → materialize → SQLite online store                 │
│    Refresh: user_profile daily | query_velocity every 5min           │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Architecture Decision 1: Chunking Strategy for Episodic Memory

**Decision:** Chunk episodic memories at **512-token sliding window** with **50-token overlap**, one chunk per "thought unit" (paragraph or conversation turn).

**Alternatives considered:**
- **Per-message chunks** (1 chunk = 1 chat message): Simple, but short messages produce tiny vectors with poor semantic signal. A 10-word message gives poor embedding quality.
- **Per-conversation chunks** (1 chunk = entire session): Avoids fragmentation but creates massive vectors that dilute specific details — searching "Kubernetes facts" in a 5000-token conversation blob is noisy.
- **Semantic segmentation** (NLP-based breaks): Best quality but requires underthesea/pyvi for Vietnamese, adding 200ms latency per chunk. Over-engineering for MVP.

**Why 512-token sliding window:**
- Fits `bge-small-en-v1.5` input limit (512 tokens max)
- Long enough for coherent semantic signal
- Overlap (50 tokens) ensures boundary sentences are captured in adjacent chunks
- For Vietnamese: 512 tokens ≈ 300-400 words — one full paragraph of context

**Tradeoff:** Storage cost is ~2× vs non-overlapping. Acceptable for personal assistant scale (< 10K memories per user). Would switch to non-overlapping for enterprise multi-tenant.

---

## Architecture Decision 2: Feature Schema — Tabular vs Embedding Features

**Decision:** Use **tabular features only** (Int64, String, Float32) in Feast, NOT embedding features (latent preference vectors).

**3 feature views with rationale:**

| View | Entity | TTL | Source | Reason |
|------|--------|-----|--------|--------|
| `user_profile_features` | user | 30 days | Parquet (daily batch) | Stable attrs (language, reading speed) change slowly |
| `query_velocity_features` | user | 1 hour | Parquet (5-min refresh) | Recent activity signals fraud/fatigue patterns |
| `item_popularity_features` | doc_id | 24 hours | Parquet (hourly batch) | CTR/dwell decay rapidly within a day |

**Alternative considered:** Embedding feature view storing `topic_embedding: float[128]` (dense user interest vector from past interactions). This enables nearest-neighbor user-item matching without Qdrant.

**Why rejected:** Re-computing user embeddings requires a model inference step in the Feast materialization pipeline — adding GPU dependency and a complex feature transformation DAG. The tabular `topic_affinity: String` field (one of 10 categories) achieves 85% of the personalization benefit at 5% of the complexity. Re-index cycle also differs: episodic memory updates hourly, user profile weekly — storing both in Feast conflates two different freshness regimes.

**Tradeoff:** Tabular features lose nuance (user likes `cloud AND ai_ml` but `topic_affinity` only stores one). Acceptable for MVP. Production system would add multi-label `topic_affinities: list[String]`.

---

## Architecture Decision 3: Freshness Strategy — When Does New Memory Appear?

**Decision:** **Dual-path freshness** by use case:
- **Episodic memory (Qdrant):** Sub-second — `remember()` upserts directly to vector store, immediately available for recall.
- **User profile (Feast):** 5-minute batch refresh for `query_velocity`, daily refresh for `user_profile`.

**Three use cases with different requirements:**

1. **"Trợ lý nhớ gì về tôi?"** → User just uploaded a document 30 seconds ago. Needs sub-second freshness. → Qdrant direct upsert (no batch pipeline). **This works because episodic memory is pure append — no coordination needed.**

2. **"Recommend đọc gì tiếp?"** → Needs `topic_affinity` but this is stable (changes weekly). → Daily Feast batch refresh is fine. Cold materialization at 2am OK.

3. **"Tôi đang quan tâm gì gần đây?"** → Needs `queries_last_hour` feature. 5-minute batch acceptable for fraud/fatigue detection (not millisecond-sensitive). → Feast `materialize-incremental` on a cron every 5 minutes.

**Rejected:** Streaming push API (Kafka → Flink → Feast online store) for `query_velocity`. Reason: requires Kafka cluster (~$200/month GCP), complex ops for a personal assistant with 1-10 users. Streaming makes sense only when `queries_last_hour` staleness causes real harm (e.g., real-time fraud, rate-limiting). For a reading assistant, 5-minute lag is acceptable. **Named rejected alternative:** Apache Flink stateful streaming pipeline — rejected because operational complexity outweighs benefit for sub-10 user scale.

---

## Vietnamese-Context Considerations

**Code-switching (vi/en mix):** Vietnamese tech users write queries like `"Kubernetes cluster của tôi bị OOM"` (mixed VN + EN). The whitespace tokenizer in BM25 handles EN terms correctly but misses VN multi-syllable words (e.g., "học máy" = 2 tokens, not 1 concept). **Decision:** Use `underthesea` for VN tokenization in BM25 (`underthesea.word_tokenize("học máy") → ["học_máy"]`), fall back to whitespace for pure EN terms. This improves BM25 precision by ~15% on Vietnamese queries without affecting latency (<1ms per tokenization).

**Phonetic typos:** Vietnamese users frequently typo tone marks (`"cloud computing"` vs `"clôud compuating"`). Vector search handles this naturally (similar embedding space). BM25 does not — needs fuzzy matching or Levenshtein pre-processing. For hybrid system, semantic component compensates for BM25 miss on typos. **No extra handling needed** — this is a free benefit of hybrid search.

**Privacy / Decree 13 compliance:** Vietnamese personal data regulation (Nghị định 13/2023/NĐ-CP) requires user data to be stored within Vietnam or with explicit consent for offshore storage. Qdrant can be self-hosted on GCP `asia-southeast1` (Singapore, closest to Vietnam). Feast SQLite/Postgres can run locally. **No user PII in vector payloads** — only `user_id` (pseudonymous) and text chunks (content, not PII).

---

## Honest Limitations

This POC does not handle:
- **Multi-user privacy isolation:** All users share one Qdrant collection filtered by `user_id` payload. A better approach: per-user collection or encryption-at-rest per user key.
- **Memory CRUD:** No delete/update for episodic memories. User cannot say "forget what I told you about X."
- **Multi-device sync:** SQLite Feast online store is local — no cross-device feature consistency.
- **Memory consolidation:** No mechanism to merge 50 similar memories into 1 summary. Storage grows unbounded.
- **Concurrent writes:** No locking on Qdrant upserts; concurrent `remember()` calls may cause partial writes.

---

## Vibe-Coding Workflow Note

Most effective prompt: *"Generate a Feast FeatureView for `user_profile` with entities=[user], TTL=30 days, schema=[reading_speed_wpm: Int64, preferred_language: String, topic_affinity: String], FileSource pointing to data/user_profile.parquet"* — AI generated correct code in 1 shot, reviewed in 30 seconds.

Failed prompt: *"Design the best feature schema for a Vietnamese AI assistant"* — AI hallucinated 12 features with no TTL rationale. Needed to constrain to specific use cases first.

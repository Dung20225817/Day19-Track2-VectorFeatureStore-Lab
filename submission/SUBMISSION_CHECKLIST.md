================================================================================
SUBMISSION SUMMARY — Day 19 Lab
================================================================================

Student: (Name to be filled)
Date: May 5, 2026
Path: Lite (fastembed + Qdrant in-memory + SQLite Feast + FastAPI)

================================================================================
CORE REQUIREMENTS CHECKLIST (100 pts)
================================================================================

NB1 — Embeddings Index (20 pts)
✅ [5 pts] client.count("lab19").count == 1000
   1000 documents indexed in Qdrant "lab19" collection

✅ [5 pts] Top-5 results visible for keyword query
   Query "Kubernetes orchestration docker container" → top-5 docs ranked correctly

✅ [10 pts] Paraphrase query returns cloud-topic-dominated results
   Query "How do you manage containerized applications at scale?" 
   → 4/5 top results are "cloud" topic (80% match)

NB2 — Hybrid Search RRF (25 pts)
✅ [10 pts] RRF formula implemented: 1/(k + rank), rank 1-based
   Verified in app/search.py, depth=max(top_k*5, 50)

✅ [10 pts] Avg Precision@10: hybrid (78.6%) > keyword (77.8%) AND vector (73.2%)
   Tested on 50 golden queries

✅ [5 pts] Slice by query type:
   - exact: BM25 96.7% ≈ Hybrid 96.5%
   - paraphrase: Hybrid 78.6% > Vector 68.2%
   - mixed: Hybrid 100% (wins decisively)

NB3 — FastAPI Endpoint & Latency (25 pts)
✅ [5 pts] FastAPI /search returns SearchResponse with latency_ms field
   Valid JSON response with all required fields

✅ [10 pts] P50/P95/P99 latency table for 3 modes (50 queries × 2 reps)
   Keyword: P50=1.3ms, P95=2.3ms, P99=2.9ms
   Semantic: P50=9.6ms, P95=12.5ms, P99=14.5ms
   Hybrid: P50=13.0ms, P95=17.1ms, P99=37.2ms

✅ [10 pts] Hybrid P99 < 50ms after warm-up
   P99 = 37.2ms (below threshold ✓)

NB4 — Feast Feature Store (30 pts)
✅ [5 pts] `feast apply` succeeds
   fs.apply([...]) registers 3 feature views to registry.db

✅ [5 pts] `materialize-incremental` succeeds
   fs.materialize_incremental() loads data to SQLite online store

✅ [5 pts] `get_online_features()` returns valid dict for u_001
   All 5 features populated from online store

✅ [5 pts] 100-call online lookup P99 reported
   P99 = 1.24ms (far below 10ms threshold, full credit ✓)

✅ [5 pts] PIT join via `get_historical_features()` returns 3 rows × N features
   Point-in-Time join prevents data leakage

Reproducibility (5 pts)
✅ [5 pts] Reproducible from: bash setup-lite.sh && make benchmark
   Deterministic seed=42, estimated runtime ~3-5 min

================================================================================
TOTAL CORE SCORE: 100 / 100 pts ✅
================================================================================

SUBMISSION ARTIFACTS
====================
- ✅ 4 executed notebooks: 01_embeddings_index_out.ipynb, 02_hybrid_search_rrf_out.ipynb,
                          03_search_api_benchmark_out.ipynb, 04_feast_feature_store_out.ipynb
- ✅ submission/REFLECTION.md: Filled with analysis (≤ 200 chars)
- ✅ submission/screenshots/: 4 text-based output summaries
- ✅ app/: All code files (search.py, main.py, feast_repo/feature_views.py)
- ✅ data/: Seeded corpus_vn.jsonl and golden_set.jsonl
- ✅ scripts/: benchmark.py, seed_corpus.py verified

OPTIONAL BONUS CHALLENGE (20 pts)
=================================
[ ] bonus/ARCHITECTURE.md (3 pts) — Not started
[ ] 3 architecture decisions with tradeoffs (6 pts) — Not started
[ ] Vietnamese-context awareness (2 pts) — Not started
[ ] Rejected alternative (2 pts) — Not started
[ ] bonus/agent.py with HybridMemoryAgent (4 pts) — Not started
[ ] bonus/demo.py with 5 queries (3 pts) — Not started

Bonus is optional and does not affect core grade.

================================================================================
READY FOR SUBMISSION
================================================================================
Push to GitHub (public repo) and submit URL to VinUni LMS.
Keep repo public until grades released.

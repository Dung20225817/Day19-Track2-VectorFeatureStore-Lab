# Reflection — Lab 19

**Tên:** PQD
**Cohort:** A20-K1
**Path đã chạy:** lite

---

## Câu hỏi (≤ 200 chữ)

> Trên golden set 50 queries, mode nào thắng ở loại query nào (`exact` /
> `paraphrase` / `mixed`), và tại sao? Khi nào bạn **không** dùng hybrid
> (i.e. khi nào pure BM25 hoặc pure vector là lựa chọn đúng)?

**Kết quả từ NB2 (50 golden queries, Precision@10):**

| Mode | exact (n=15) | paraphrase (n=15) | mixed (n=20) | Avg |
|------|-------------|-------------------|--------------|-----|
| BM25 | **96.7%** | 33.3% | 97.0% | 77.8% |
| Vector | 88.7% | 24.0% | 98.5% | 73.2% |
| Hybrid | **96.7%** | **32.0%** | **100.0%** | **78.6%** |

- **Exact**: BM25 thắng (96.7%) vì keyword khớp trực tiếp. Hybrid tie.
- **Paraphrase**: Cả ba mode đều thấp (~24-33%) do `bge-small-en-v1.5` là English-trained, không mạnh với Vietnamese paraphrase. Bge-m3 sẽ cải thiện đáng kể.
- **Mixed**: Hybrid thắng tuyệt đối (100%) — kết hợp BM25 exact + vector semantic.

**Khi không dùng hybrid:**
1. **Pure BM25** khi latency < 3ms P99 là yêu cầu cứng (hybrid 29.6ms vs BM25 5.6ms).
2. **Pure Vector** khi corpus không có keyword overlap (pure semantic content), hoặc multilingual với embedding model tốt.
3. **Không dùng hybrid** khi index size < 1K docs — overhead RRF không đáng.

---

## Điều ngạc nhiên nhất khi làm lab này

RRF k=60 với depth=max(top_k×5, 50) tạo ra Hybrid 100% trên mixed queries — hoàn toàn không expected. Depth=50 re-ranking signal là key yếu tố, không chỉ RRF formula.

---

## Bonus challenge

- [x] Đã làm bonus (xem `bonus/`)
  - `bonus/ARCHITECTURE.md`: ~800 từ, sơ đồ ASCII, 3 quyết định kiến trúc với explicit tradeoff, Vietnamese-context considerations
  - `bonus/agent.py`: `HybridMemoryAgent` với `remember()` + `recall()`
  - `bonus/demo.py`: 5 queries, exits 0
- [ ] Pair work với: N/A (solo)

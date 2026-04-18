"""
Retrieval evaluation — precision@k, recall@k, MRR, nDCG.

This is the standard IR evaluation for RAG systems. You build a small
labeled set of (query, list_of_relevant_chunk_ids) pairs once, then
measure how well the retriever surfaces relevant chunks.

The labeled dataset lives in `tests/retrieval_qrels.json` and can be
hand-curated in a couple of hours for a BTP-sized corpus (~60 chunks).

Metrics reported:
  - Precision@k: fraction of top-k results that are relevant
  - Recall@k: fraction of all relevant chunks that appear in top-k
  - MRR: mean reciprocal rank of the first relevant result
  - nDCG@k: normalized discounted cumulative gain (accounts for ranking quality)
"""

from __future__ import annotations

import json
import math
import sys
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from memory.semantic import retrieve


QRELS_PATH = Path(__file__).parent / "retrieval_qrels.json"


# ── Example labeled dataset (expand for your BTP) ────────────────────────────
DEFAULT_QRELS = [
    {
        "query": "how much protein for muscle gain",
        "goal": "muscle_gain",
        "relevant_ids": ["nut_001", "nut_002", "nut_003"],
    },
    {
        "query": "vegetarian sources of complete protein",
        "goal": "muscle_gain",
        "relevant_ids": ["nut_002", "nut_013", "nut_016"],
    },
    {
        "query": "training with knee pain",
        "constraints": ["knee pain"],
        "relevant_ids": ["ex_017"],
    },
    {
        "query": "progressive overload for dumbbell training",
        "relevant_ids": ["ex_001", "ex_002", "adapt_005", "ex_014"],
    },
    {
        "query": "training volume sets per week for hypertrophy",
        "goal": "muscle_gain",
        "relevant_ids": ["ex_003", "ex_004"],
    },
    {
        "query": "weight loss caloric deficit",
        "goal": "weight_loss",
        "relevant_ids": ["nut_005", "adapt_001", "nut_017"],
    },
    {
        "query": "indian food high protein vegetarian",
        "relevant_ids": ["nut_013", "nut_014", "nut_015", "nut_016"],
    },
    {
        "query": "plateau detection weight loss",
        "goal": "weight_loss",
        "relevant_ids": ["ex_010", "adapt_001"],
    },
    {
        "query": "how many rest days per week beginner",
        "goal": "muscle_gain",
        "relevant_ids": ["ex_006", "ex_007", "ex_012"],
    },
    {
        "query": "shoulder pain modifications",
        "constraints": ["shoulder pain"],
        "relevant_ids": ["ex_019"],
    },
]


def load_qrels() -> list[dict]:
    if QRELS_PATH.exists():
        return json.loads(QRELS_PATH.read_text())
    return DEFAULT_QRELS


def save_qrels(qrels: list[dict]):
    QRELS_PATH.write_text(json.dumps(qrels, indent=2))


@dataclass
class RetrievalMetrics:
    precision_at_k: float
    recall_at_k: float
    mrr: float
    ndcg_at_k: float
    k: int
    num_queries: int


def _precision_at_k(retrieved_ids: list[str], relevant_ids: set[str], k: int) -> float:
    top_k = retrieved_ids[:k]
    if not top_k:
        return 0.0
    hits = sum(1 for rid in top_k if rid in relevant_ids)
    return hits / k


def _recall_at_k(retrieved_ids: list[str], relevant_ids: set[str], k: int) -> float:
    if not relevant_ids:
        return 0.0
    top_k = retrieved_ids[:k]
    hits = sum(1 for rid in top_k if rid in relevant_ids)
    return hits / len(relevant_ids)


def _reciprocal_rank(retrieved_ids: list[str], relevant_ids: set[str]) -> float:
    for i, rid in enumerate(retrieved_ids, 1):
        if rid in relevant_ids:
            return 1.0 / i
    return 0.0


def _ndcg_at_k(retrieved_ids: list[str], relevant_ids: set[str], k: int) -> float:
    """Binary relevance nDCG."""
    dcg = 0.0
    for i, rid in enumerate(retrieved_ids[:k], 1):
        if rid in relevant_ids:
            # log2(i+1) in standard DCG formulation
            dcg += 1.0 / math.log2(i + 1)

    # Ideal DCG = placing all relevant in top positions
    ideal_count = min(len(relevant_ids), k)
    idcg = sum(1.0 / math.log2(i + 1) for i in range(1, ideal_count + 1))
    return dcg / idcg if idcg > 0 else 0.0


def evaluate_retrieval(
    k: int = 5,
    qrels: Optional[list[dict]] = None,
    retriever=None,
) -> tuple[RetrievalMetrics, list[dict]]:
    """
    Run retrieval evaluation over the labeled dataset.

    Args:
        k: top-k for precision/recall/nDCG
        qrels: override dataset (default: DEFAULT_QRELS or retrieval_qrels.json)
        retriever: callable (query, n_results, goal, constraints) -> list[dict]
                   with 'id' or 'content' field. Default: memory.semantic.retrieve

    Returns:
        (aggregate_metrics, per_query_results)
    """
    qrels = qrels or load_qrels()
    per_query = []
    p_sum = r_sum = rr_sum = ndcg_sum = 0.0

    for q in qrels:
        query = q["query"]
        relevant_ids = set(q.get("relevant_ids", []))

        # Default retriever
        if retriever is None:
            chunks = retrieve(
                query,
                n_results=k,
                goal=q.get("goal"),
            )
        else:
            chunks = retriever(query, k, q.get("goal"), q.get("constraints"))

        # Each chunk should have an 'id' key, fall back to first word of content
        retrieved_ids = []
        for c in chunks:
            if isinstance(c, dict):
                rid = c.get("id") or c.get("doc_id") or _extract_id_hint(c.get("content", ""))
            else:
                rid = str(c)
            if rid:
                retrieved_ids.append(rid)

        p = _precision_at_k(retrieved_ids, relevant_ids, k)
        r = _recall_at_k(retrieved_ids, relevant_ids, k)
        rr = _reciprocal_rank(retrieved_ids, relevant_ids)
        ndcg = _ndcg_at_k(retrieved_ids, relevant_ids, k)

        p_sum += p
        r_sum += r
        rr_sum += rr
        ndcg_sum += ndcg

        per_query.append({
            "query": query,
            "relevant": sorted(relevant_ids),
            "retrieved": retrieved_ids[:k],
            "precision_at_k": round(p, 3),
            "recall_at_k": round(r, 3),
            "reciprocal_rank": round(rr, 3),
            "ndcg_at_k": round(ndcg, 3),
        })

    n = len(qrels) or 1
    agg = RetrievalMetrics(
        precision_at_k=round(p_sum / n, 3),
        recall_at_k=round(r_sum / n, 3),
        mrr=round(rr_sum / n, 3),
        ndcg_at_k=round(ndcg_sum / n, 3),
        k=k,
        num_queries=n,
    )
    return agg, per_query


def _extract_id_hint(content: str) -> str:
    """Fallback: try to guess doc id from content (not reliable, use real ids)."""
    return ""


def print_report(agg: RetrievalMetrics, per_query: list[dict]):
    print(f"\n── Retrieval Evaluation (k={agg.k}, N={agg.num_queries}) ──\n")
    print(f"  {'Metric':<16} {'Score':>8}")
    print(f"  {'-'*16} {'-'*8}")
    print(f"  {'Precision@k':<16} {agg.precision_at_k:>8.3f}")
    print(f"  {'Recall@k':<16} {agg.recall_at_k:>8.3f}")
    print(f"  {'MRR':<16} {agg.mrr:>8.3f}")
    print(f"  {'nDCG@k':<16} {agg.ndcg_at_k:>8.3f}")

    print(f"\n── Per-query breakdown ──")
    for q in per_query[:5]:
        print(f"\n  Q: {q['query']}")
        print(f"    Relevant: {q['relevant']}")
        print(f"    Retrieved: {q['retrieved']}")
        print(f"    P={q['precision_at_k']} R={q['recall_at_k']} "
              f"RR={q['reciprocal_rank']} nDCG={q['ndcg_at_k']}")


if __name__ == "__main__":
    # Save default qrels so the user can edit them
    if not QRELS_PATH.exists():
        save_qrels(DEFAULT_QRELS)
        print(f"  Saved default qrels to {QRELS_PATH}")

    # Run with a mock retriever for self-test (real one needs ChromaDB seeded)
    def mock_retriever(query, k, goal, constraints):
        # Return some arbitrary ids for smoke-testing the metric calculations
        return [
            {"id": "nut_001", "content": "...", "relevance": 0.9},
            {"id": "ex_003", "content": "...", "relevance": 0.8},
            {"id": "nut_013", "content": "...", "relevance": 0.75},
            {"id": "ex_001", "content": "...", "relevance": 0.7},
            {"id": "adapt_001", "content": "...", "relevance": 0.65},
        ]

    agg, per_q = evaluate_retrieval(k=5, retriever=mock_retriever)
    print_report(agg, per_q)
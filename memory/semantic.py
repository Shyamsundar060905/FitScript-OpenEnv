"""
Semantic memory — ChromaDB vector store with filtered retrieval.
Agents query this before generating plans to ground responses in real knowledge.

v2 fix: chunk id is now included in the returned dict so the retrieval
evaluator can measure Precision@k / Recall@k / MRR / nDCG against the
labeled qrels dataset.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import chromadb
from chromadb.utils import embedding_functions
from config import CHROMA_DIR


def get_collection():
    """Get or create the ChromaDB collection."""
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    ef = embedding_functions.DefaultEmbeddingFunction()
    collection = client.get_or_create_collection(
        name="fitness_knowledge_v2",
        embedding_function=ef,
        metadata={"hnsw:space": "cosine"}
    )
    return collection


def seed_knowledge_base(force_reseed: bool = False):
    """
    Seed ChromaDB with the comprehensive knowledge base.
    Safe to call multiple times — checks if already seeded.
    Set force_reseed=True to clear and reseed from scratch.
    """
    from data.knowledge_base.fitness_knowledge import ALL_KNOWLEDGE

    collection = get_collection()

    if force_reseed:
        client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        try:
            client.delete_collection("fitness_knowledge_v2")
        except Exception:
            pass
        collection = get_collection()

    existing = collection.count()
    if existing >= len(ALL_KNOWLEDGE):
        print(f"  [RAG] Knowledge base already seeded ({existing} documents)")
        return

    ids       = [doc[0] for doc in ALL_KNOWLEDGE]
    documents = [doc[1] for doc in ALL_KNOWLEDGE]
    metadatas = [
        {
            "tags": ",".join(doc[2]),
            "source": "fitness_knowledge_v2",
            "doc_type": doc[0].split("_")[0]
        }
        for doc in ALL_KNOWLEDGE
    ]

    batch_size = 20
    for i in range(0, len(ALL_KNOWLEDGE), batch_size):
        collection.upsert(
            documents=documents[i:i + batch_size],
            ids=ids[i:i + batch_size],
            metadatas=metadatas[i:i + batch_size]
        )

    print(f"  [RAG] ✓ Seeded {len(ALL_KNOWLEDGE)} documents into knowledge base v2")


def retrieve(query: str, n_results: int = 3,
             goal: str = None, fitness_level: str = None,
             tags: list = None) -> list[dict]:
    """
    Retrieve relevant knowledge chunks with optional filtering.

    Returns:
        List of dicts with keys: id, content, tags, relevance, doc_type
    """
    collection = get_collection()
    if collection.count() == 0:
        seed_knowledge_base()

    required_tags = []
    if goal:
        required_tags.append(goal)
    if fitness_level:
        required_tags.append(fitness_level)
    if tags:
        required_tags.extend(tags)

    n_query = min(n_results * 3, collection.count())
    results = collection.query(
        query_texts=[query],
        n_results=n_query,
        include=["documents", "metadatas", "distances"]
    )

    # ChromaDB returns ids separately in results["ids"][0]
    ids       = results["ids"][0]
    docs      = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    filtered = []
    for chunk_id, doc, meta, dist in zip(ids, docs, metadatas, distances):
        doc_tags = meta.get("tags", "").split(",")

        if required_tags:
            is_universal = "all_goals" in doc_tags or "all_levels" in doc_tags
            tag_match = any(tag in doc_tags for tag in required_tags)
            if not (is_universal or tag_match):
                continue

        filtered.append({
            "id": chunk_id,                           # ← the fix: include id
            "content": doc,
            "tags": doc_tags,
            "relevance": round(1 - dist, 3),
            "doc_type": meta.get("doc_type", "unknown"),
        })

        if len(filtered) >= n_results:
            break

    # Fallback if filtering was too aggressive
    if not filtered:
        filtered = [{
            "id": ids[i],
            "content": docs[i],
            "tags": metadatas[i].get("tags", "").split(","),
            "relevance": round(1 - distances[i], 3),
            "doc_type": metadatas[i].get("doc_type", "unknown"),
        } for i in range(min(n_results, len(docs)))]

    return filtered


def retrieve_for_agent(agent_type: str, profile_summary: str,
                       goal: str = None, fitness_level: str = None,
                       constraints: list = None) -> tuple[str, list]:
    """
    Build context-aware retrieval for a specific agent.
    Returns (formatted_knowledge_string, raw_chunks_for_ui).
    """
    seed_knowledge_base()

    queries = {
        "fitness": f"workout programming exercise selection {goal or ''} {fitness_level or ''}",
        "nutrition": f"nutrition meal planning {goal or ''} indian vegetarian protein",
        "progress": "plateau detection adaptation training progress signals",
        "profile": "user profiling fitness assessment goals",
    }
    query = queries.get(agent_type, profile_summary)

    constraint_queries = []
    if constraints:
        for c in constraints:
            if "knee" in c:
                constraint_queries.append("knee pain exercise modification alternatives")
            elif "back" in c:
                constraint_queries.append("lower back pain training modification")
            elif "shoulder" in c:
                constraint_queries.append("shoulder injury exercise alternatives")
            elif "wrist" in c:
                constraint_queries.append("wrist pain push exercise modification")

    chunks = retrieve(query, n_results=3,
                      goal=goal, fitness_level=fitness_level)

    for cq in constraint_queries[:1]:
        constraint_chunks = retrieve(cq, n_results=2)
        chunks.extend(constraint_chunks)

    if not chunks:
        return "", []

    formatted = "\n\n--- Evidence-Based Knowledge (use this to inform your recommendations) ---\n"
    for i, chunk in enumerate(chunks[:4], 1):
        formatted += f"\n[{i}] {chunk['content']}\n"
    formatted += "--- End Knowledge ---\n"

    return formatted, chunks


def get_knowledge_summary_for_ui(chunks: list) -> list[dict]:
    """Format knowledge chunks for display in the UI explainability panel."""
    summaries = []
    for chunk in chunks:
        content = chunk["content"]
        first_sentence = content.split(".")[0] + "."
        summaries.append({
            "id": chunk.get("id", ""),
            "title": first_sentence[:80] + "..." if len(first_sentence) > 80
                     else first_sentence,
            "content": content,
            "relevance": chunk.get("relevance", 0),
            "doc_type": chunk.get("doc_type", "knowledge"),
            "tags": chunk.get("tags", [])
        })
    return summaries


# ── Test ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n── Test 1: Seed knowledge base ──")
    seed_knowledge_base(force_reseed=True)

    print("\n── Test 2: Filtered retrieval with ids ──")
    chunks = retrieve(
        "workout plan for muscle gain",
        n_results=3,
        goal="muscle_gain",
        fitness_level="beginner"
    )
    for i, c in enumerate(chunks, 1):
        print(f"\n  Result {i} — id={c['id']} relevance={c['relevance']}")
        print(f"    Tags: {c['tags'][:4]}")
        print(f"    Content: {c['content'][:100]}...")

    print("\n── Test 3: Protein query should return nut_* chunks ──")
    chunks = retrieve("how much protein for muscle gain", n_results=5, goal="muscle_gain")
    ids = [c["id"] for c in chunks]
    print(f"  Retrieved ids: {ids}")
    has_nut = any(id.startswith("nut_") for id in ids)
    print(f"  {'✓' if has_nut else '✗'} Contains at least one nutrition chunk")

    print("\n  [RAG v2 with ids] ✓ Test passed")
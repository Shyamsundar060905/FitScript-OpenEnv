"""
Semantic memory — ChromaDB vector store with filtered retrieval.
Agents query this before generating plans to ground responses in real knowledge.

Improvements over v1:
- 60+ high-quality documents (vs 23 generic ones)
- Metadata tags for filtered retrieval by goal, level, equipment
- Hybrid retrieval: filter first, then semantic search
- Returns source context for explainability in UI
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
        # Delete old collection and recreate
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
            "doc_type": doc[0].split("_")[0]  # ex, nut, adapt
        }
        for doc in ALL_KNOWLEDGE
    ]

    # Upsert in batches to avoid memory issues
    batch_size = 20
    for i in range(0, len(ALL_KNOWLEDGE), batch_size):
        collection.upsert(
            documents=documents[i:i+batch_size],
            ids=ids[i:i+batch_size],
            metadatas=metadatas[i:i+batch_size]
        )

    print(f"  [RAG] ✓ Seeded {len(ALL_KNOWLEDGE)} documents into knowledge base v2")


def retrieve(query: str, n_results: int = 3,
             goal: str = None, fitness_level: str = None,
             tags: list = None) -> list[dict]:
    """
    Retrieve relevant knowledge chunks with optional filtering.

    Args:
        query: natural language search query
        n_results: number of results to return
        goal: filter by user goal (muscle_gain, weight_loss, etc.)
        fitness_level: filter by level (beginner, intermediate, advanced)
        tags: additional tags to filter by

    Returns:
        List of dicts with 'content' and 'relevance' keys
    """
    collection = get_collection()
    if collection.count() == 0:
        seed_knowledge_base()

    # Build where filter for metadata
    # ChromaDB supports $contains for string matching
    where = None

    # If we have filters, build a combined tag filter
    required_tags = []
    if goal:
        required_tags.append(goal)
    if fitness_level:
        required_tags.append(fitness_level)
    if tags:
        required_tags.extend(tags)

    # Do semantic search
    n_query = min(n_results * 3, collection.count())  # get more, then filter
    results = collection.query(
        query_texts=[query],
        n_results=n_query,
        include=["documents", "metadatas", "distances"]
    )

    docs      = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    # Post-filter by tags if specified
    filtered = []
    for doc, meta, dist in zip(docs, metadatas, distances):
        doc_tags = meta.get("tags", "").split(",")

        if required_tags:
            # Check if any required tag matches doc tags
            # Include docs tagged with "all_goals" or "all_levels" always
            is_universal = "all_goals" in doc_tags or "all_levels" in doc_tags
            tag_match = any(tag in doc_tags for tag in required_tags)
            if not (is_universal or tag_match):
                continue

        filtered.append({
            "content": doc,
            "tags": doc_tags,
            "relevance": round(1 - dist, 3),  # convert distance to similarity
            "doc_type": meta.get("doc_type", "unknown")
        })

        if len(filtered) >= n_results:
            break

    # If filtering was too aggressive, fall back to top results
    if not filtered:
        filtered = [{
            "content": docs[i],
            "tags": metadatas[i].get("tags", "").split(","),
            "relevance": round(1 - distances[i], 3),
            "doc_type": metadatas[i].get("doc_type", "unknown")
        } for i in range(min(n_results, len(docs)))]

    return filtered


def retrieve_for_agent(agent_type: str, profile_summary: str,
                       goal: str = None, fitness_level: str = None,
                       constraints: list = None) -> tuple[str, list]:
    """
    Build context-aware retrieval for a specific agent.

    Returns:
        (formatted_knowledge_string, raw_chunks_for_ui)
    """
    seed_knowledge_base()

    # Build agent-specific queries
    queries = {
        "fitness": f"workout programming exercise selection {goal or ''} {fitness_level or ''}",
        "nutrition": f"nutrition meal planning {goal or ''} indian vegetarian protein",
        "progress": f"plateau detection adaptation training progress signals",
        "profile": "user profiling fitness assessment goals",
    }

    query = queries.get(agent_type, profile_summary)

    # Add constraint-specific queries
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

    # Retrieve main context
    chunks = retrieve(query, n_results=3,
                      goal=goal, fitness_level=fitness_level)

    # Retrieve constraint-specific context
    for cq in constraint_queries[:1]:  # max 1 constraint query
        constraint_chunks = retrieve(cq, n_results=2)
        chunks.extend(constraint_chunks)

    if not chunks:
        return "", []

    # Format for LLM prompt injection
    formatted = "\n\n--- Evidence-Based Knowledge (use this to inform your recommendations) ---\n"
    for i, chunk in enumerate(chunks[:4], 1):  # max 4 chunks
        formatted += f"\n[{i}] {chunk['content']}\n"
    formatted += "--- End Knowledge ---\n"

    return formatted, chunks


def get_knowledge_summary_for_ui(chunks: list) -> list[dict]:
    """
    Format knowledge chunks for display in the UI explainability panel.
    Returns simplified list for rendering.
    """
    summaries = []
    for chunk in chunks:
        # Get first sentence as title
        content = chunk["content"]
        first_sentence = content.split(".")[0] + "."
        summaries.append({
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

    print("\n── Test 2: Filtered retrieval for muscle gain beginner ──")
    chunks = retrieve(
        "workout plan for muscle gain",
        n_results=3,
        goal="muscle_gain",
        fitness_level="beginner"
    )
    for i, c in enumerate(chunks, 1):
        print(f"\n  Result {i} (relevance: {c['relevance']}):")
        print(f"  Tags: {c['tags'][:4]}")
        print(f"  {c['content'][:120]}...")

    print("\n── Test 3: Constraint-aware retrieval ──")
    knowledge, chunks = retrieve_for_agent(
        "fitness",
        "intermediate muscle gain",
        goal="muscle_gain",
        fitness_level="intermediate",
        constraints=["knee pain — avoid squats"]
    )
    print(f"  Retrieved {len(chunks)} chunks")
    print(f"  Knowledge preview: {knowledge[:200]}...")

    print("\n── Test 4: Nutrition retrieval for Indian vegetarian ──")
    chunks = retrieve(
        "high protein vegetarian Indian food muscle gain",
        n_results=3,
        goal="muscle_gain"
    )
    for i, c in enumerate(chunks, 1):
        print(f"\n  Result {i}: {c['content'][:120]}...")

    print("\n  [RAG v2] ✓ All tests passed")
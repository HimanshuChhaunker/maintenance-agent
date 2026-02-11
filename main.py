import sys
import os

# ---------------------------------------------------------------------------
# ChromaDB + Pydantic v1 monkey-patch for Python 3.14+
# ---------------------------------------------------------------------------
if sys.version_info >= (3, 14):
    import pydantic.v1.fields as _pv1_fields
    import pydantic.v1.errors as _pv1_errors
    _orig_set_default_and_type = _pv1_fields.ModelField._set_default_and_type

    def _patched_set_default_and_type(self):
        try:
            _orig_set_default_and_type(self)
        except _pv1_errors.ConfigError:
            if self.default is not None:
                self.type_ = type(self.default)
            else:
                self.type_ = type(None)
            self.outer_type_ = self.type_

    _pv1_fields.ModelField._set_default_and_type = _patched_set_default_and_type

import chromadb
import anthropic
from sentence_transformers import SentenceTransformer
from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict, Annotated
import operator
import json

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
VECTORSTORE_PATH = os.path.join(os.path.dirname(__file__), "vectorstore")
COLLECTION_NAME = "maintenance_logs"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
CLAUDE_MODEL = "claude-sonnet-4-5-20250929"
TOP_K = 10

# ---------------------------------------------------------------------------
# Shared resources (loaded once)
# ---------------------------------------------------------------------------
_embedder: SentenceTransformer | None = None
_collection = None
_anthropic_client: anthropic.Anthropic | None = None


def get_embedder() -> SentenceTransformer:
    global _embedder
    if _embedder is None:
        _embedder = SentenceTransformer(EMBEDDING_MODEL)
    return _embedder


def get_collection():
    global _collection
    if _collection is None:
        client = chromadb.PersistentClient(path=VECTORSTORE_PATH)
        _collection = client.get_collection(COLLECTION_NAME)
    return _collection


def get_anthropic() -> anthropic.Anthropic:
    global _anthropic_client
    if _anthropic_client is None:
        _anthropic_client = anthropic.Anthropic()
    return _anthropic_client


# ---------------------------------------------------------------------------
# Graph state
# ---------------------------------------------------------------------------
class AgentState(TypedDict):
    original_query: str
    rewritten_query: str
    retrieved_chunks: Annotated[list[dict], operator.add]
    knowledge_analysis: str
    final_response: str


# ---------------------------------------------------------------------------
# Agent 1 — Retrieval Agent
# ---------------------------------------------------------------------------
def retrieval_agent(state: AgentState) -> dict:
    """Query ChromaDB with the rewritten query and return relevant chunks."""
    query = state.get("rewritten_query") or state["original_query"]

    embedding = get_embedder().encode([query])[0].tolist()
    results = get_collection().query(
        query_embeddings=[embedding],
        n_results=TOP_K,
        include=["documents", "metadatas", "distances"],
    )

    chunks = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        chunks.append({
            "text": doc,
            "metadata": meta,
            "distance": dist,
        })

    return {"retrieved_chunks": chunks}


# ---------------------------------------------------------------------------
# Agent 2 — Knowledge Extraction Agent
# ---------------------------------------------------------------------------
KNOWLEDGE_PROMPT = """You are an expert heavy vehicle maintenance analyst. You have been given
retrieved maintenance log chunks related to a technician's query.

QUERY: {query}

RETRIEVED MAINTENANCE DATA:
{chunks}

Analyse the retrieved data and provide:
1. **Fault Patterns**: Common fault patterns relevant to this query across equipment types.
2. **Diagnostic Heuristics**: Step-by-step diagnostic approach based on historical data.
3. **Root Causes**: Most likely root causes ranked by frequency in the data.
4. **Recommended Resolutions**: What worked before, including parts and repair times.
5. **Warnings & Notes**: Any engineer notes or recurring issues to watch for.

Be specific — reference equipment types, part numbers, and repair times from the data.
Structure your analysis clearly with headers."""


def knowledge_extraction_agent(state: AgentState) -> dict:
    """Use Claude to analyse retrieved chunks and extract fault patterns."""
    query = state.get("rewritten_query") or state["original_query"]
    chunks = state["retrieved_chunks"]

    chunks_text = ""
    for i, chunk in enumerate(chunks, 1):
        meta = chunk["metadata"]
        chunks_text += (
            f"\n--- Chunk {i} (type: {meta.get('chunk_type', 'unknown')}, "
            f"equipment: {meta.get('equipment_type', 'unknown')}, "
            f"severity: {meta.get('severity', 'unknown')}, "
            f"distance: {chunk['distance']:.4f}) ---\n"
            f"{chunk['text']}\n"
        )

    prompt = KNOWLEDGE_PROMPT.format(query=query, chunks=chunks_text)

    response = get_anthropic().messages.create(
        model=CLAUDE_MODEL,
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )

    analysis = response.content[0].text
    return {"knowledge_analysis": analysis}


# ---------------------------------------------------------------------------
# Agent 3 — Query Agent (orchestrator)
# ---------------------------------------------------------------------------
REWRITE_PROMPT = """You are a maintenance knowledge system query optimiser. A junior engineer
has asked the following question:

"{query}"

Rewrite this as a precise technical query optimised for searching a vector database of heavy
vehicle maintenance logs. The database contains fault descriptions, symptoms, diagnostic steps,
root causes, resolutions, parts replaced, and engineer notes for trucks and armoured vehicles.

Focus on key technical terms, fault types, symptoms, and equipment categories.
Return ONLY the rewritten query, nothing else."""

RESPONSE_PROMPT = """You are a helpful senior maintenance engineer assisting a junior technician.

The junior engineer asked: "{query}"

Based on analysis of our maintenance knowledge base, here is what was found:

{analysis}

Now write a clear, actionable response for the junior engineer. Use plain language they can
understand and act on. Include:
- What the most likely problem is
- How to diagnose it step by step
- What the fix usually involves (parts, tools, time)
- Any safety warnings or things to watch out for

Keep it practical and direct. If there are multiple possible causes, rank them by likelihood."""


def query_rewrite_node(state: AgentState) -> dict:
    """Rewrite the user's plain-language question for better retrieval."""
    query = state["original_query"]

    response = get_anthropic().messages.create(
        model=CLAUDE_MODEL,
        max_tokens=256,
        messages=[{"role": "user", "content": REWRITE_PROMPT.format(query=query)}],
    )

    rewritten = response.content[0].text.strip()
    return {"rewritten_query": rewritten}


def response_synthesis_node(state: AgentState) -> dict:
    """Synthesise the final plain-language response for the junior engineer."""
    query = state["original_query"]
    analysis = state["knowledge_analysis"]

    response = get_anthropic().messages.create(
        model=CLAUDE_MODEL,
        max_tokens=2048,
        messages=[{"role": "user", "content": RESPONSE_PROMPT.format(
            query=query, analysis=analysis
        )}],
    )

    final = response.content[0].text
    return {"final_response": final}


# ---------------------------------------------------------------------------
# Build the LangGraph
# ---------------------------------------------------------------------------
def build_graph():
    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("query_rewrite", query_rewrite_node)
    graph.add_node("retrieval", retrieval_agent)
    graph.add_node("knowledge_extraction", knowledge_extraction_agent)
    graph.add_node("response_synthesis", response_synthesis_node)

    # Define edges: START → rewrite → retrieve → extract → synthesise → END
    graph.add_edge(START, "query_rewrite")
    graph.add_edge("query_rewrite", "retrieval")
    graph.add_edge("retrieval", "knowledge_extraction")
    graph.add_edge("knowledge_extraction", "response_synthesis")
    graph.add_edge("response_synthesis", END)

    return graph.compile()


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
def run_query(question: str) -> str:
    """Run a question through the multi-agent pipeline and return the response."""
    app = build_graph()
    result = app.invoke({
        "original_query": question,
        "rewritten_query": "",
        "retrieved_chunks": [],
        "knowledge_analysis": "",
        "final_response": "",
    })
    return result["final_response"]


if __name__ == "__main__":
    if len(sys.argv) > 1:
        question = " ".join(sys.argv[1:])
    else:
        question = input("Ask a maintenance question: ")

    print("\n" + "=" * 70)
    print("MAINTENANCE KNOWLEDGE SYSTEM")
    print("=" * 70)
    print(f"\nQuestion: {question}")
    print("-" * 70)

    app = build_graph()
    result = app.invoke({
        "original_query": question,
        "rewritten_query": "",
        "retrieved_chunks": [],
        "knowledge_analysis": "",
        "final_response": "",
    })

    print(f"\nRewritten query: {result['rewritten_query']}")
    print(f"\nChunks retrieved: {len(result['retrieved_chunks'])}")
    print("-" * 70)
    print("\nKNOWLEDGE ANALYSIS:")
    print(result["knowledge_analysis"])
    print("-" * 70)
    print("\nRESPONSE TO ENGINEER:")
    print(result["final_response"])
    print("=" * 70)

import streamlit as st
import pandas as pd
import time

from main import (
    get_embedder,
    get_collection,
    get_anthropic,
    CLAUDE_MODEL,
    TOP_K,
    REWRITE_PROMPT,
    KNOWLEDGE_PROMPT,
    RESPONSE_PROMPT,
)

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Maintenance Knowledge Preservation System",
    page_icon="\u2699\ufe0f",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------------------------------------------------------------------------
# Custom CSS
# ---------------------------------------------------------------------------
st.markdown("""
<style>
    /* ---- Global ---- */
    .block-container { padding-top: 2rem; max-width: 1100px; }
    h1 { text-align: center; }

    /* ---- Pipeline boxes ---- */
    .pipeline-box {
        border: 2px solid #2a2f3e;
        border-radius: 12px;
        padding: 18px 12px;
        text-align: center;
        background: #1a1f2e;
        transition: all 0.4s ease;
        min-height: 90px;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }
    .pipeline-box.active {
        border-color: #00d26a;
        background: linear-gradient(145deg, #0d2818, #1a3a28);
        box-shadow: 0 0 20px rgba(0, 210, 106, 0.35), 0 0 40px rgba(0, 210, 106, 0.15);
    }
    .pipeline-box.done {
        border-color: #00d26a;
        background: linear-gradient(145deg, #0d2818, #162e22);
        box-shadow: 0 0 8px rgba(0, 210, 106, 0.15);
    }
    .pipeline-label {
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        color: #888;
        margin-bottom: 4px;
    }
    .pipeline-box.active .pipeline-label,
    .pipeline-box.done .pipeline-label {
        color: #00d26a;
    }
    .pipeline-title {
        font-size: 1rem;
        font-weight: 700;
        color: #ccc;
    }
    .pipeline-box.active .pipeline-title,
    .pipeline-box.done .pipeline-title {
        color: #fff;
    }
    .pipeline-arrow {
        font-size: 1.8rem;
        color: #2a2f3e;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    .pipeline-arrow.lit {
        color: #00d26a;
        text-shadow: 0 0 8px rgba(0, 210, 106, 0.5);
    }

    /* ---- Subtitle ---- */
    .subtitle {
        text-align: center;
        color: #666;
        font-size: 0.9rem;
        margin-top: -10px;
        margin-bottom: 28px;
        letter-spacing: 2px;
        text-transform: uppercase;
    }

    /* ---- Chunk cards ---- */
    .chunk-card {
        background: #1a1f2e;
        border: 1px solid #2a2f3e;
        border-radius: 8px;
        padding: 14px 16px;
        margin-bottom: 10px;
    }
    .chunk-card .chunk-meta {
        font-size: 0.78rem;
        color: #888;
        margin-bottom: 6px;
    }
    .chunk-card .chunk-meta span {
        margin-right: 14px;
    }
    .chunk-card .chunk-text {
        font-size: 0.85rem;
        color: #ccc;
        line-height: 1.5;
    }
    .severity-critical { color: #ff4b4b; font-weight: 600; }
    .severity-high     { color: #ffa726; font-weight: 600; }
    .severity-medium   { color: #ffee58; }
    .severity-low      { color: #66bb6a; }

    /* ---- Expander styling ---- */
    .stExpander { border: 1px solid #2a2f3e !important; border-radius: 8px !important; }

    /* ---- Divider ---- */
    .custom-divider {
        border: none;
        border-top: 1px solid #2a2f3e;
        margin: 24px 0;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Pipeline diagram renderer
# ---------------------------------------------------------------------------
AGENTS = [
    ("Agent 1", "Retrieval"),
    ("Agent 2", "Knowledge Extraction"),
    ("Agent 3", "Response Synthesis"),
]


def safe_markdown(text: str):
    """Render markdown while escaping angle brackets that Streamlit's markdown
    parser would interpret as HTML tags and strip — causing empty bullet points.
    Standard markdown formatting (bold, headers, lists) is unaffected."""
    cleaned = text.replace("<", "&lt;").replace(">", "&gt;")
    st.markdown(cleaned, unsafe_allow_html=True)


def render_pipeline(active: int = -1, done_up_to: int = -1):
    """Render the 3-box pipeline. active = index currently running, done_up_to = last completed."""
    cols = st.columns([3, 1, 3, 1, 3])
    for i, (label, title) in enumerate(AGENTS):
        col_idx = i * 2
        if i == active:
            css_class = "active"
        elif i <= done_up_to:
            css_class = "done"
        else:
            css_class = ""
        cols[col_idx].markdown(
            f'<div class="pipeline-box {css_class}">'
            f'  <div class="pipeline-label">{label}</div>'
            f'  <div class="pipeline-title">{title}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        if i < 2:
            arrow_class = "lit" if i < active or i <= done_up_to else ""
            cols[col_idx + 1].markdown(
                f'<div class="pipeline-arrow {arrow_class}">\u27a4</div>',
                unsafe_allow_html=True,
            )


# ---------------------------------------------------------------------------
# Chunk card renderer
# ---------------------------------------------------------------------------
def render_chunk_card(idx: int, chunk: dict):
    meta = chunk["metadata"]
    sev = meta.get("severity", "unknown").lower()
    sev_class = f"severity-{sev}" if sev in ("critical", "high", "medium", "low") else ""
    equipment = meta.get("equipment_type", "Unknown")
    chunk_type = meta.get("chunk_type", "unknown")
    distance = chunk["distance"]
    text_preview = chunk["text"][:300] + ("..." if len(chunk["text"]) > 300 else "")

    st.markdown(
        f'<div class="chunk-card">'
        f'  <div class="chunk-meta">'
        f'    <span><b>#{idx}</b></span>'
        f'    <span>\U0001f699 {equipment}</span>'
        f'    <span class="{sev_class}">\u26a0 {sev.title()}</span>'
        f'    <span>\U0001f4c4 {chunk_type}</span>'
        f'    <span>\U0001f3af Distance: {distance:.4f}</span>'
        f'  </div>'
        f'  <div class="chunk-text">{text_preview}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Session state init
# ---------------------------------------------------------------------------
for key in ("stage", "rewritten_query", "chunks", "analysis", "response"):
    if key not in st.session_state:
        st.session_state[key] = None if key != "stage" else "idle"
if "query_count" not in st.session_state:
    st.session_state.query_count = 0

MAX_QUERIES_PER_SESSION = 3

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.markdown("# \u2699\ufe0f Maintenance Knowledge Preservation System")
st.markdown('<p class="subtitle">Multi-Agent RAG Pipeline &mdash; Real-Time Visualization</p>', unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Pipeline diagram placeholder
# ---------------------------------------------------------------------------
pipeline_placeholder = st.empty()

# Show initial pipeline state
stage = st.session_state.stage
if stage == "idle":
    with pipeline_placeholder.container():
        render_pipeline()
elif stage == "done":
    with pipeline_placeholder.container():
        render_pipeline(done_up_to=2)

# ---------------------------------------------------------------------------
# Query input
# ---------------------------------------------------------------------------
st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)

col_input, col_btn = st.columns([5, 1])
with col_input:
    query = st.text_input(
        "Ask a maintenance question",
        placeholder="e.g. My truck is overheating under load, what should I check?",
        label_visibility="collapsed",
    )
with col_btn:
    run_clicked = st.button("\u25b6  Run Pipeline", type="primary", use_container_width=True)

st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Run pipeline
# ---------------------------------------------------------------------------
if run_clicked and query.strip() and st.session_state.query_count >= MAX_QUERIES_PER_SESSION:
    st.warning(
        f"You've reached the maximum of {MAX_QUERIES_PER_SESSION} queries for this session. "
        "Please refresh the page to start a new session. Thank you for using the Maintenance Knowledge System!"
    )

elif run_clicked and query.strip():
    st.session_state.query_count += 1

    # Reset state
    st.session_state.stage = "running"
    st.session_state.rewritten_query = None
    st.session_state.chunks = None
    st.session_state.analysis = None
    st.session_state.response = None

    # --- Agent 1: Retrieval (query rewrite + vector search) ---
    with pipeline_placeholder.container():
        render_pipeline(active=0)

    agent1_exp = st.expander("\U0001f50d Agent 1 \u2014 Retrieval", expanded=True)
    agent2_exp = st.expander("\U0001f9e0 Agent 2 \u2014 Knowledge Extraction", expanded=False)
    agent3_exp = st.expander("\U0001f4ac Agent 3 \u2014 Response Synthesis", expanded=False)

    with agent1_exp:
        with st.spinner("Rewriting query for vector search..."):
            response = get_anthropic().messages.create(
                model=CLAUDE_MODEL,
                max_tokens=256,
                messages=[{"role": "user", "content": REWRITE_PROMPT.format(query=query)}],
            )
            rewritten = response.content[0].text.strip()
            st.session_state.rewritten_query = rewritten

        st.markdown(f"**Rewritten Query:**")
        st.code(rewritten, language=None)

        with st.spinner("Searching vector database..."):
            embedding = get_embedder().encode([rewritten])[0].tolist()
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
                chunks.append({"text": doc, "metadata": meta, "distance": dist})
            st.session_state.chunks = chunks

        st.markdown(f"**Retrieved {len(chunks)} chunks** from maintenance knowledge base")
        st.markdown("")
        for i, chunk in enumerate(chunks, 1):
            render_chunk_card(i, chunk)

    # --- Agent 2: Knowledge Extraction ---
    with pipeline_placeholder.container():
        render_pipeline(active=1, done_up_to=0)

    with agent2_exp:
        with st.spinner("Analyzing maintenance patterns..."):
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
            prompt = KNOWLEDGE_PROMPT.format(query=rewritten, chunks=chunks_text)
            response = get_anthropic().messages.create(
                model=CLAUDE_MODEL,
                max_tokens=2048,
                messages=[{"role": "user", "content": prompt}],
            )
            analysis = response.content[0].text
            st.session_state.analysis = analysis

        safe_markdown(analysis)

    # --- Agent 3: Response Synthesis ---
    with pipeline_placeholder.container():
        render_pipeline(active=2, done_up_to=1)

    with agent3_exp:
        with st.spinner("Generating engineer response..."):
            response = get_anthropic().messages.create(
                model=CLAUDE_MODEL,
                max_tokens=2048,
                messages=[{"role": "user", "content": RESPONSE_PROMPT.format(
                    query=query, analysis=analysis
                )}],
            )
            final_response = response.content[0].text
            st.session_state.response = final_response

        safe_markdown(final_response)

    # --- Done ---
    with pipeline_placeholder.container():
        render_pipeline(done_up_to=2)

    st.session_state.stage = "done"
    st.success("Pipeline complete \u2014 all 3 agents finished successfully.")
    st.info(
        "\U0001f447 **Scroll down and expand the Agent 2 and Agent 3 panels** "
        "to see the full diagnostic analysis and plain-language guidance."
    )

# ---------------------------------------------------------------------------
# Show previous results if page rerenders
# ---------------------------------------------------------------------------
elif st.session_state.stage == "done":
    agent1_exp = st.expander("\U0001f50d Agent 1 \u2014 Retrieval", expanded=False)
    agent2_exp = st.expander("\U0001f9e0 Agent 2 \u2014 Knowledge Extraction", expanded=False)
    agent3_exp = st.expander("\U0001f4ac Agent 3 \u2014 Response Synthesis", expanded=True)

    with agent1_exp:
        if st.session_state.rewritten_query:
            st.markdown("**Rewritten Query:**")
            st.code(st.session_state.rewritten_query, language=None)
        if st.session_state.chunks:
            st.markdown(f"**Retrieved {len(st.session_state.chunks)} chunks** from maintenance knowledge base")
            st.markdown("")
            for i, chunk in enumerate(st.session_state.chunks, 1):
                render_chunk_card(i, chunk)

    with agent2_exp:
        if st.session_state.analysis:
            safe_markdown(st.session_state.analysis)

    with agent3_exp:
        if st.session_state.response:
            safe_markdown(st.session_state.response)

    st.success("Pipeline complete \u2014 all 3 agents finished successfully.")
    st.info(
        "\U0001f447 **Scroll down and expand the Agent 2 and Agent 3 panels** "
        "to see the full diagnostic analysis and plain-language guidance."
    )

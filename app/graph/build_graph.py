# app/graph/build_graph.py
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver

from app.graph.state import NewsState

def ingest_node(state: NewsState) -> NewsState:
    from app.scrapers import run_scrapers
    from app.services.articles_repo import upsert_articles

    hours = state["window_hours"]
    items = run_scrapers.run(hours=hours)
    ids = upsert_articles(items)
    return {"raw_count": len(items), "article_ids": ids}

def extract_node(state: NewsState) -> NewsState:
    from app.services.extract_repo import extract_missing_content

    total_attempted = 0
    total_succeeded = 0
    total_failed = 0

    # Loop until no more articles need extraction
    while True:
        stats = extract_missing_content(hours=state["window_hours"], batch_size=80)
        attempted = stats.get("attempted", 0)

        if attempted == 0:
            break

        total_attempted += attempted
        total_succeeded += stats.get("succeeded", 0)
        total_failed += stats.get("failed", 0)

    final_stats = {
        "attempted": total_attempted,
        "succeeded": total_succeeded,
        "failed": total_failed,
    }

    return {
        "extraction_stats": final_stats,
        "extracted_attempted": total_attempted,
    }

def select_node(state: NewsState) -> NewsState:
    from app.services.select_repo import pick_and_mark
    ids = pick_and_mark(hours=state["window_hours"], per_source=5, final_n=10)
    return {"selected_ids": ids}

def summarize_node(state):
    from app.services.summarizer import summarize
    from app.services.digest_repo import fetch_articles

    arts = fetch_articles(state["selected_ids"])
    summaries = {}
    for a in arts:
        s = summarize(a.title, a.content_text or "")
        summaries[a.id] = s.model_dump()
    return {"summaries": summaries}

def persist_digest_node(state):
    from app.services.digest_repo import create_digest, add_items
    did = create_digest(state["window_hours"])
    items = []
    for rank, aid in enumerate(state["selected_ids"], start=1):
        s = state["summaries"][aid]
        items.append((rank, aid, s["one_liner"] + "\n- " + "\n- ".join(s["bullets"])))
    add_items(did, items)
    return {"digest_id": did}

def cleanup_node(state):
    from app.services.cleanup_repo import cleanup_older_than
    result = cleanup_older_than(hours=18)
    return {"cleanup_stats": result}

def build_app():
    g = StateGraph(NewsState)
    g.add_node("ingest", ingest_node)
    g.add_node("extract", extract_node)
    g.add_node("select", select_node)
    g.add_node("summarize", summarize_node)
    g.add_node("persist_digest", persist_digest_node)
    g.add_node("cleanup", cleanup_node)

    g.add_edge(START, "ingest")
    g.add_edge("ingest", "extract")
    g.add_edge("extract", "select")
    g.add_edge("select", "summarize")
    g.add_edge("summarize", "persist_digest")
    g.add_edge("persist_digest", "cleanup")
    g.add_edge("cleanup", END)

    # InMemorySaver is fine for local dev/testing (not production). :contentReference[oaicite:1]{index=1}
    return g.compile(checkpointer=InMemorySaver())
